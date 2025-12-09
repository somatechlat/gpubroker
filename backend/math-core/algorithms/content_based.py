"""
Content-Based Similarity using Cosine Similarity

Matches workload profiles to GPU offer attributes.
Bounds: [-1, 1], identical vectors = 1.0
"""

import numpy as np
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class ContentSimilarity:
    """
    Content-based filtering using cosine similarity.
    
    Computes similarity between feature vectors representing
    workload requirements and GPU offer attributes.
    """
    
    def cosine_similarity(
        self,
        vec1: np.ndarray,
        vec2: np.ndarray
    ) -> float:
        """
        Calculate cosine similarity between two vectors.
        
        cos(θ) = (A · B) / (||A|| × ||B||)
        
        Returns value in [-1, 1], where 1 = identical direction
        """
        vec1 = np.asarray(vec1, dtype=np.float64).flatten()
        vec2 = np.asarray(vec2, dtype=np.float64).flatten()
        
        if vec1.shape != vec2.shape:
            raise ValueError(f"Vector shapes must match: {vec1.shape} vs {vec2.shape}")
        
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        # Handle zero vectors
        if norm1 < 1e-10 or norm2 < 1e-10:
            return 0.0
        
        dot_product = np.dot(vec1, vec2)
        similarity = dot_product / (norm1 * norm2)
        
        # Clamp to [-1, 1] to handle floating point errors
        return float(np.clip(similarity, -1.0, 1.0))
    
    def find_similar(
        self,
        query_vector: np.ndarray,
        candidate_vectors: np.ndarray,
        top_k: int = 5
    ) -> Dict[str, Any]:
        """
        Find most similar candidates to query vector.
        
        Args:
            query_vector: Feature vector for query (workload profile)
            candidate_vectors: Matrix of candidate feature vectors (offers)
            top_k: Number of top matches to return
        
        Returns:
            Dict with 'matches' (indices) and 'scores' (similarities)
        """
        query = np.asarray(query_vector, dtype=np.float64).flatten()
        candidates = np.asarray(candidate_vectors, dtype=np.float64)
        
        if candidates.ndim == 1:
            candidates = candidates.reshape(1, -1)
        
        n_candidates = candidates.shape[0]
        
        # Calculate similarities
        scores = np.zeros(n_candidates, dtype=np.float64)
        for i in range(n_candidates):
            scores[i] = self.cosine_similarity(query, candidates[i])
        
        # Get top-k indices
        top_k = min(top_k, n_candidates)
        top_indices = np.argsort(-scores)[:top_k]
        
        return {
            "matches": top_indices.tolist(),
            "scores": scores[top_indices].tolist()
        }
    
    def batch_similarity(
        self,
        query_vectors: np.ndarray,
        candidate_vectors: np.ndarray
    ) -> np.ndarray:
        """
        Calculate pairwise similarities between query and candidate vectors.
        
        Args:
            query_vectors: Matrix of query vectors (n_queries × n_features)
            candidate_vectors: Matrix of candidate vectors (n_candidates × n_features)
        
        Returns:
            Similarity matrix (n_queries × n_candidates)
        """
        queries = np.asarray(query_vectors, dtype=np.float64)
        candidates = np.asarray(candidate_vectors, dtype=np.float64)
        
        if queries.ndim == 1:
            queries = queries.reshape(1, -1)
        if candidates.ndim == 1:
            candidates = candidates.reshape(1, -1)
        
        # Normalize vectors
        query_norms = np.linalg.norm(queries, axis=1, keepdims=True)
        candidate_norms = np.linalg.norm(candidates, axis=1, keepdims=True)
        
        # Handle zero vectors
        query_norms = np.where(query_norms > 1e-10, query_norms, 1.0)
        candidate_norms = np.where(candidate_norms > 1e-10, candidate_norms, 1.0)
        
        queries_normalized = queries / query_norms
        candidates_normalized = candidates / candidate_norms
        
        # Compute similarity matrix
        similarity_matrix = queries_normalized @ candidates_normalized.T
        
        return np.clip(similarity_matrix, -1.0, 1.0)
    
    def extract_offer_features(
        self,
        offer: Dict[str, Any],
        feature_config: Optional[Dict[str, Dict[str, Any]]] = None
    ) -> np.ndarray:
        """
        Extract normalized feature vector from GPU offer.
        
        Args:
            offer: GPU offer dict with attributes
            feature_config: Optional config for feature extraction and normalization
        
        Returns:
            Normalized feature vector
        """
        if feature_config is None:
            feature_config = self._default_feature_config()
        
        features = []
        for feature_name, config in feature_config.items():
            value = offer.get(feature_name, config.get('default', 0))
            
            # Handle None values
            if value is None:
                value = config.get('default', 0)
            
            # Normalize to [0, 1]
            min_val = config.get('min', 0)
            max_val = config.get('max', 1)
            
            if max_val > min_val:
                normalized = (float(value) - min_val) / (max_val - min_val)
                normalized = np.clip(normalized, 0.0, 1.0)
            else:
                normalized = 0.5
            
            # Apply weight
            weight = config.get('weight', 1.0)
            features.append(normalized * weight)
        
        return np.array(features, dtype=np.float64)
    
    def extract_workload_features(
        self,
        workload: Dict[str, Any],
        feature_config: Optional[Dict[str, Dict[str, Any]]] = None
    ) -> np.ndarray:
        """
        Extract normalized feature vector from workload profile.
        
        Args:
            workload: Workload profile dict
            feature_config: Optional config for feature extraction
        
        Returns:
            Normalized feature vector
        """
        if feature_config is None:
            feature_config = self._default_workload_config()
        
        features = []
        for feature_name, config in feature_config.items():
            value = workload.get(feature_name, config.get('default', 0))
            
            if value is None:
                value = config.get('default', 0)
            
            min_val = config.get('min', 0)
            max_val = config.get('max', 1)
            
            if max_val > min_val:
                normalized = (float(value) - min_val) / (max_val - min_val)
                normalized = np.clip(normalized, 0.0, 1.0)
            else:
                normalized = 0.5
            
            weight = config.get('weight', 1.0)
            features.append(normalized * weight)
        
        return np.array(features, dtype=np.float64)
    
    def _default_feature_config(self) -> Dict[str, Dict[str, Any]]:
        """Default feature configuration for GPU offers."""
        return {
            'price_per_hour': {'min': 0, 'max': 10, 'default': 5, 'weight': 1.0},
            'vram_gb': {'min': 0, 'max': 80, 'default': 16, 'weight': 1.0},
            'tflops': {'min': 0, 'max': 100, 'default': 20, 'weight': 1.0},
            'availability_score': {'min': 0, 'max': 1, 'default': 0.5, 'weight': 0.8},
            'reliability_score': {'min': 0, 'max': 1, 'default': 0.5, 'weight': 0.8},
        }
    
    def _default_workload_config(self) -> Dict[str, Dict[str, Any]]:
        """Default feature configuration for workload profiles."""
        return {
            'budget_per_hour': {'min': 0, 'max': 10, 'default': 2, 'weight': 1.0},
            'min_vram_gb': {'min': 0, 'max': 80, 'default': 16, 'weight': 1.0},
            'min_tflops': {'min': 0, 'max': 100, 'default': 20, 'weight': 1.0},
            'availability_required': {'min': 0, 'max': 1, 'default': 0.8, 'weight': 0.8},
            'reliability_required': {'min': 0, 'max': 1, 'default': 0.8, 'weight': 0.8},
        }
    
    def match_workload_to_offers(
        self,
        workload: Dict[str, Any],
        offers: List[Dict[str, Any]],
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Match a workload profile to GPU offers using content similarity.
        
        Args:
            workload: Workload profile dict
            offers: List of GPU offer dicts
            top_k: Number of top matches
        
        Returns:
            List of offers with added 'content_score'
        """
        if not offers:
            return []
        
        # Extract feature vectors
        workload_vector = self.extract_workload_features(workload)
        offer_vectors = np.array([
            self.extract_offer_features(offer) for offer in offers
        ])
        
        # Find similar
        result = self.find_similar(workload_vector, offer_vectors, top_k)
        
        # Build response
        matched_offers = []
        for idx, score in zip(result['matches'], result['scores']):
            offer_copy = offers[idx].copy()
            offer_copy['content_score'] = score
            matched_offers.append(offer_copy)
        
        return matched_offers
