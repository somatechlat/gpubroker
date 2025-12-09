"""
Ensemble Recommender

Combines multiple recommendation algorithms:
- TOPSIS (0.4) - Multi-criteria decision analysis
- Collaborative Filtering (0.3) - User behavior patterns
- Content-Based (0.3) - Feature similarity

Cold-start fallback to popularity-based ranking.
"""

from typing import Dict, Any, List, Optional
import numpy as np
import logging

from .topsis import TOPSISEngine
from .collaborative import ALSRecommender
from .content_based import ContentSimilarity

logger = logging.getLogger(__name__)


class EnsembleRecommender:
    """
    Ensemble recommendation engine combining multiple algorithms.
    
    Weights must sum to 1.0:
    - TOPSIS: 0.4 (multi-criteria ranking)
    - Collaborative: 0.3 (user similarity)
    - Content-Based: 0.3 (feature matching)
    """
    
    def __init__(
        self,
        topsis_engine: TOPSISEngine,
        als_recommender: ALSRecommender,
        content_similarity: ContentSimilarity,
        weights: Optional[Dict[str, float]] = None
    ):
        self.topsis = topsis_engine
        self.collaborative = als_recommender
        self.content = content_similarity
        
        # Default weights (must sum to 1.0)
        self.weights = weights or {
            "topsis": 0.4,
            "collaborative": 0.3,
            "content_based": 0.3
        }
        
        # Validate weights
        weight_sum = sum(self.weights.values())
        if abs(weight_sum - 1.0) > 0.001:
            raise ValueError(f"Weights must sum to 1.0, got {weight_sum}")
    
    def recommend(
        self,
        user_id: Optional[str],
        workload_profile: Dict[str, Any],
        candidate_offers: List[Dict[str, Any]],
        top_k: int = 5
    ) -> Dict[str, Any]:
        """
        Generate ensemble recommendations.
        
        Args:
            user_id: User identifier (None for anonymous/cold-start)
            workload_profile: User's workload requirements
            candidate_offers: List of GPU offers to rank
            top_k: Number of recommendations to return
        
        Returns:
            Dict with recommendations and algorithm contributions
        """
        if not candidate_offers:
            return {
                "recommendations": [],
                "algorithm_contributions": self.weights,
                "confidence": 0.0
            }
        
        n_offers = len(candidate_offers)
        
        # Initialize score arrays
        topsis_scores = np.zeros(n_offers)
        collab_scores = np.zeros(n_offers)
        content_scores = np.zeros(n_offers)
        
        # Track which algorithms contributed
        contributions = {
            "topsis": 0.0,
            "collaborative": 0.0,
            "content_based": 0.0
        }
        
        # 1. TOPSIS scoring
        try:
            topsis_scores = self._get_topsis_scores(candidate_offers, workload_profile)
            contributions["topsis"] = self.weights["topsis"]
        except Exception as e:
            logger.warning(f"TOPSIS scoring failed: {e}")
            contributions["topsis"] = 0.0
        
        # 2. Collaborative filtering scoring
        if user_id and self.collaborative.is_fitted:
            try:
                collab_scores = self._get_collaborative_scores(
                    user_id, candidate_offers
                )
                contributions["collaborative"] = self.weights["collaborative"]
            except Exception as e:
                logger.warning(f"Collaborative scoring failed: {e}")
                contributions["collaborative"] = 0.0
        else:
            # Cold start - use popularity fallback
            collab_scores = self._get_popularity_scores(candidate_offers)
            contributions["collaborative"] = self.weights["collaborative"] * 0.5
        
        # 3. Content-based scoring
        try:
            content_scores = self._get_content_scores(
                workload_profile, candidate_offers
            )
            contributions["content_based"] = self.weights["content_based"]
        except Exception as e:
            logger.warning(f"Content scoring failed: {e}")
            contributions["content_based"] = 0.0
        
        # Normalize scores to [0, 1]
        topsis_scores = self._normalize_scores(topsis_scores)
        collab_scores = self._normalize_scores(collab_scores)
        content_scores = self._normalize_scores(content_scores)
        
        # Combine with weights
        total_weight = sum(contributions.values())
        if total_weight > 0:
            # Re-normalize weights based on what actually contributed
            w_topsis = contributions["topsis"] / total_weight
            w_collab = contributions["collaborative"] / total_weight
            w_content = contributions["content_based"] / total_weight
            
            final_scores = (
                w_topsis * topsis_scores +
                w_collab * collab_scores +
                w_content * content_scores
            )
        else:
            # Fallback to equal weights
            final_scores = (topsis_scores + collab_scores + content_scores) / 3
        
        # Rank and select top-k
        ranked_indices = np.argsort(-final_scores)[:top_k]
        
        recommendations = []
        for idx in ranked_indices:
            offer = candidate_offers[idx].copy()
            offer["ensemble_score"] = float(final_scores[idx])
            offer["score_breakdown"] = {
                "topsis": float(topsis_scores[idx]),
                "collaborative": float(collab_scores[idx]),
                "content_based": float(content_scores[idx])
            }
            recommendations.append(offer)
        
        # Calculate confidence based on score distribution
        confidence = self._calculate_confidence(final_scores, contributions)
        
        return {
            "recommendations": recommendations,
            "algorithm_contributions": contributions,
            "confidence": confidence
        }
    
    def _get_topsis_scores(
        self,
        offers: List[Dict[str, Any]],
        workload_profile: Dict[str, Any]
    ) -> np.ndarray:
        """Get TOPSIS scores for offers."""
        # Define criteria based on workload
        criteria_config = {
            "price_per_hour": {"weight": 0.30, "type": "cost"},
            "vram_gb": {"weight": 0.25, "type": "benefit"},
            "tflops": {"weight": 0.20, "type": "benefit"},
            "availability_score": {"weight": 0.15, "type": "benefit"},
            "reliability_score": {"weight": 0.10, "type": "benefit"}
        }
        
        # Adjust weights based on workload
        budget = workload_profile.get("budget_per_hour")
        if budget and budget < 1.0:
            criteria_config["price_per_hour"]["weight"] = 0.40
            criteria_config["vram_gb"]["weight"] = 0.20
        
        # Build decision matrix
        criteria_names = list(criteria_config.keys())
        n_offers = len(offers)
        n_criteria = len(criteria_names)
        
        matrix = np.zeros((n_offers, n_criteria))
        for i, offer in enumerate(offers):
            for j, criterion in enumerate(criteria_names):
                value = offer.get(criterion, 0)
                # Handle missing values
                if value is None:
                    if criterion == "availability_score":
                        value = 0.8
                    elif criterion == "reliability_score":
                        value = 0.8
                    elif criterion == "tflops":
                        value = 20.0
                    elif criterion == "vram_gb":
                        value = 16
                    else:
                        value = 0
                matrix[i, j] = float(value)
        
        weights = [criteria_config[c]["weight"] for c in criteria_names]
        criteria_types = [criteria_config[c]["type"] for c in criteria_names]
        
        result = self.topsis.calculate(matrix, weights, criteria_types)
        return np.array(result["scores"])
    
    def _get_collaborative_scores(
        self,
        user_id: str,
        offers: List[Dict[str, Any]]
    ) -> np.ndarray:
        """Get collaborative filtering scores."""
        scores = np.zeros(len(offers))
        
        # Get recommendations for user
        recommendations = self.collaborative.recommend(user_id, n=100)
        rec_dict = {r["item_id"]: r["score"] for r in recommendations}
        
        for i, offer in enumerate(offers):
            offer_id = offer.get("id") or offer.get("offer_id")
            if offer_id and offer_id in rec_dict:
                scores[i] = rec_dict[offer_id]
        
        return scores
    
    def _get_content_scores(
        self,
        workload_profile: Dict[str, Any],
        offers: List[Dict[str, Any]]
    ) -> np.ndarray:
        """Get content-based similarity scores."""
        # Extract workload features
        workload_vector = self.content.extract_workload_features(workload_profile)
        
        # Extract offer features
        offer_vectors = np.array([
            self.content.extract_offer_features(offer) for offer in offers
        ])
        
        # Calculate similarities
        scores = np.zeros(len(offers))
        for i in range(len(offers)):
            scores[i] = self.content.cosine_similarity(
                workload_vector, offer_vectors[i]
            )
        
        # Convert from [-1, 1] to [0, 1]
        scores = (scores + 1) / 2
        
        return scores
    
    def _get_popularity_scores(
        self,
        offers: List[Dict[str, Any]]
    ) -> np.ndarray:
        """Get popularity-based scores for cold start."""
        scores = np.zeros(len(offers))
        
        for i, offer in enumerate(offers):
            # Use booking count or rating if available
            booking_count = offer.get("booking_count", 0)
            rating = offer.get("rating_avg", 3.0)
            
            # Combine into popularity score
            scores[i] = (booking_count / 100) * 0.5 + (rating / 5) * 0.5
        
        return scores
    
    def _normalize_scores(self, scores: np.ndarray) -> np.ndarray:
        """Normalize scores to [0, 1] range."""
        if len(scores) == 0:
            return scores
        
        min_score = np.min(scores)
        max_score = np.max(scores)
        
        if max_score - min_score < 1e-10:
            return np.ones_like(scores) * 0.5
        
        return (scores - min_score) / (max_score - min_score)
    
    def _calculate_confidence(
        self,
        scores: np.ndarray,
        contributions: Dict[str, float]
    ) -> float:
        """Calculate confidence in recommendations."""
        # Base confidence on algorithm coverage
        coverage = sum(1 for v in contributions.values() if v > 0) / 3
        
        # Adjust based on score distribution
        if len(scores) > 1:
            score_std = np.std(scores)
            # Higher std = clearer differentiation = higher confidence
            differentiation = min(score_std * 2, 1.0)
        else:
            differentiation = 0.5
        
        confidence = coverage * 0.6 + differentiation * 0.4
        return round(confidence, 2)
