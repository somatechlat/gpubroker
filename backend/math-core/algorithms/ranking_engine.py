"""
Multi-Criteria Decision Analysis (MCDA) Ranking Engine

Enterprise-grade ranking algorithms for GPU recommendations:
- TOPSIS (Technique for Order of Preference by Similarity to Ideal Solution)
- AHP (Analytic Hierarchy Process)
- ELECTRE (Elimination and Choice Translating Reality)
- PROMETHEE (Preference Ranking Organization Method)
- Weighted Sum Model (WSM)
- Weighted Product Model (WPM)

⚠️ WARNING: REAL IMPLEMENTATION ONLY ⚠️
We do NOT mock, bypass, or invent data.
"""

import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)


class BaseRanker(ABC):
    """Abstract base class for ranking algorithms."""
    
    @abstractmethod
    def rank(
        self,
        alternatives: np.ndarray,
        weights: List[float],
        criteria_types: List[str]
    ) -> Dict[str, Any]:
        """Rank alternatives based on criteria."""
        pass


class WeightedSumModel(BaseRanker):
    """
    Weighted Sum Model (WSM) - Simple additive weighting.
    
    Score = Σ (w_j * r_ij)
    where r_ij is normalized value of alternative i on criterion j
    """
    
    def rank(
        self,
        alternatives: np.ndarray,
        weights: List[float],
        criteria_types: List[str]
    ) -> Dict[str, Any]:
        """
        Rank using weighted sum.
        
        Args:
            alternatives: Matrix (n_alternatives x n_criteria)
            weights: Criterion weights (must sum to 1)
            criteria_types: 'benefit' or 'cost' for each criterion
        """
        normalized = self._normalize(alternatives, criteria_types)
        weights_array = np.array(weights)
        
        scores = np.sum(normalized * weights_array, axis=1)
        rankings = np.argsort(-scores)
        
        return {
            "rankings": rankings.tolist(),
            "scores": scores.tolist(),
            "method": "weighted_sum_model"
        }
    
    def _normalize(
        self,
        matrix: np.ndarray,
        criteria_types: List[str]
    ) -> np.ndarray:
        """Min-max normalization."""
        normalized = np.zeros_like(matrix, dtype=np.float64)
        
        for j in range(matrix.shape[1]):
            col = matrix[:, j]
            min_val, max_val = col.min(), col.max()
            
            if max_val - min_val < 1e-10:
                normalized[:, j] = 1.0
            elif criteria_types[j].lower() == 'benefit':
                normalized[:, j] = (col - min_val) / (max_val - min_val)
            else:  # cost
                normalized[:, j] = (max_val - col) / (max_val - min_val)
        
        return normalized


class WeightedProductModel(BaseRanker):
    """
    Weighted Product Model (WPM) - Multiplicative weighting.
    
    Score = Π (r_ij ^ w_j)
    Handles ratio scale data better than WSM.
    """
    
    def rank(
        self,
        alternatives: np.ndarray,
        weights: List[float],
        criteria_types: List[str]
    ) -> Dict[str, Any]:
        """Rank using weighted product."""
        # Ensure positive values
        matrix = np.maximum(alternatives, 1e-10)
        weights_array = np.array(weights)
        
        # Adjust weights for cost criteria (negative exponent)
        adjusted_weights = np.array([
            w if ct.lower() == 'benefit' else -w
            for w, ct in zip(weights, criteria_types)
        ])
        
        # Calculate product
        scores = np.prod(matrix ** adjusted_weights, axis=1)
        rankings = np.argsort(-scores)
        
        return {
            "rankings": rankings.tolist(),
            "scores": scores.tolist(),
            "method": "weighted_product_model"
        }


class AHPRanker(BaseRanker):
    """
    Analytic Hierarchy Process (AHP)
    
    Uses pairwise comparisons to derive weights and scores.
    Includes consistency ratio check.
    
    Reference: Saaty, T.L. (1980). The Analytic Hierarchy Process.
    """
    
    # Random Index for consistency check
    RI = {1: 0, 2: 0, 3: 0.58, 4: 0.90, 5: 1.12, 6: 1.24, 7: 1.32, 8: 1.41, 9: 1.45, 10: 1.49}
    
    def rank(
        self,
        alternatives: np.ndarray,
        weights: List[float],
        criteria_types: List[str]
    ) -> Dict[str, Any]:
        """
        Rank using AHP with provided weights.
        
        For full AHP, use derive_weights_from_comparisons() first.
        """
        # Normalize alternatives per criterion
        normalized = self._normalize_ahp(alternatives, criteria_types)
        weights_array = np.array(weights)
        
        # Calculate global scores
        scores = np.sum(normalized * weights_array, axis=1)
        rankings = np.argsort(-scores)
        
        return {
            "rankings": rankings.tolist(),
            "scores": scores.tolist(),
            "method": "ahp",
            "normalized_matrix": normalized.tolist()
        }
    
    def derive_weights_from_comparisons(
        self,
        comparison_matrix: np.ndarray
    ) -> Dict[str, Any]:
        """
        Derive criterion weights from pairwise comparison matrix.
        
        Args:
            comparison_matrix: Square matrix where a[i,j] = importance of i vs j
                              (1 = equal, 3 = moderate, 5 = strong, 7 = very strong, 9 = extreme)
        
        Returns:
            Dict with weights and consistency ratio
        """
        n = comparison_matrix.shape[0]
        
        # Normalize columns
        col_sums = comparison_matrix.sum(axis=0)
        normalized = comparison_matrix / col_sums
        
        # Average rows to get weights
        weights = normalized.mean(axis=1)
        
        # Calculate consistency
        weighted_sum = comparison_matrix @ weights
        lambda_max = np.mean(weighted_sum / weights)
        
        ci = (lambda_max - n) / (n - 1) if n > 1 else 0
        ri = self.RI.get(n, 1.49)
        cr = ci / ri if ri > 0 else 0
        
        return {
            "weights": weights.tolist(),
            "consistency_index": float(ci),
            "consistency_ratio": float(cr),
            "is_consistent": cr < 0.1,  # CR < 0.1 is acceptable
            "lambda_max": float(lambda_max)
        }
    
    def _normalize_ahp(
        self,
        matrix: np.ndarray,
        criteria_types: List[str]
    ) -> np.ndarray:
        """Normalize using sum normalization (AHP style)."""
        normalized = np.zeros_like(matrix, dtype=np.float64)
        
        for j in range(matrix.shape[1]):
            col = matrix[:, j]
            
            if criteria_types[j].lower() == 'cost':
                # Invert for cost criteria
                col = 1.0 / np.maximum(col, 1e-10)
            
            col_sum = col.sum()
            if col_sum > 1e-10:
                normalized[:, j] = col / col_sum
            else:
                normalized[:, j] = 1.0 / len(col)
        
        return normalized


class ELECTRERanker(BaseRanker):
    """
    ELECTRE I (Elimination and Choice Translating Reality)
    
    Outranking method based on concordance and discordance.
    
    Reference: Roy, B. (1968). Classement et choix en présence de points de vue multiples.
    """
    
    def rank(
        self,
        alternatives: np.ndarray,
        weights: List[float],
        criteria_types: List[str],
        concordance_threshold: float = 0.7,
        discordance_threshold: float = 0.3
    ) -> Dict[str, Any]:
        """
        Rank using ELECTRE I outranking.
        
        Args:
            alternatives: Decision matrix
            weights: Criterion weights
            criteria_types: 'benefit' or 'cost'
            concordance_threshold: Minimum concordance for outranking
            discordance_threshold: Maximum discordance for outranking
        """
        n_alt = alternatives.shape[0]
        weights_array = np.array(weights)
        
        # Normalize
        normalized = self._normalize_vector(alternatives)
        
        # Calculate concordance and discordance matrices
        concordance = np.zeros((n_alt, n_alt))
        discordance = np.zeros((n_alt, n_alt))
        
        for i in range(n_alt):
            for j in range(n_alt):
                if i != j:
                    c, d = self._calculate_concordance_discordance(
                        normalized[i], normalized[j],
                        weights_array, criteria_types
                    )
                    concordance[i, j] = c
                    discordance[i, j] = d
        
        # Build outranking matrix
        outranking = (concordance >= concordance_threshold) & (discordance <= discordance_threshold)
        
        # Calculate dominance scores
        dominance_scores = outranking.sum(axis=1) - outranking.sum(axis=0)
        rankings = np.argsort(-dominance_scores)
        
        return {
            "rankings": rankings.tolist(),
            "scores": dominance_scores.tolist(),
            "concordance_matrix": concordance.tolist(),
            "discordance_matrix": discordance.tolist(),
            "outranking_matrix": outranking.astype(int).tolist(),
            "method": "electre_i",
            "thresholds": {
                "concordance": concordance_threshold,
                "discordance": discordance_threshold
            }
        }
    
    def _normalize_vector(self, matrix: np.ndarray) -> np.ndarray:
        """Vector normalization (L2 norm)."""
        norms = np.sqrt(np.sum(matrix ** 2, axis=0))
        norms = np.where(norms > 1e-10, norms, 1.0)
        return matrix / norms
    
    def _calculate_concordance_discordance(
        self,
        alt_i: np.ndarray,
        alt_j: np.ndarray,
        weights: np.ndarray,
        criteria_types: List[str]
    ) -> Tuple[float, float]:
        """Calculate concordance and discordance between two alternatives."""
        concordance_sum = 0.0
        max_discordance = 0.0
        max_range = 0.0
        
        for k, ct in enumerate(criteria_types):
            if ct.lower() == 'benefit':
                if alt_i[k] >= alt_j[k]:
                    concordance_sum += weights[k]
                discordance = max(0, alt_j[k] - alt_i[k])
            else:  # cost
                if alt_i[k] <= alt_j[k]:
                    concordance_sum += weights[k]
                discordance = max(0, alt_i[k] - alt_j[k])
            
            max_discordance = max(max_discordance, discordance)
            max_range = max(max_range, abs(alt_i[k] - alt_j[k]))
        
        concordance = concordance_sum / weights.sum() if weights.sum() > 0 else 0
        discordance = max_discordance / max_range if max_range > 0 else 0
        
        return concordance, discordance


class PROMETHEERanker(BaseRanker):
    """
    PROMETHEE II (Preference Ranking Organization Method for Enrichment Evaluation)
    
    Outranking method using preference functions.
    
    Reference: Brans, J.P., Vincke, P. (1985). A Preference Ranking Organisation Method.
    """
    
    def rank(
        self,
        alternatives: np.ndarray,
        weights: List[float],
        criteria_types: List[str],
        preference_type: str = "linear"
    ) -> Dict[str, Any]:
        """
        Rank using PROMETHEE II.
        
        Args:
            alternatives: Decision matrix
            weights: Criterion weights
            criteria_types: 'benefit' or 'cost'
            preference_type: 'linear', 'usual', or 'gaussian'
        """
        n_alt, n_crit = alternatives.shape
        weights_array = np.array(weights)
        
        # Calculate preference matrix for each criterion
        preference_matrices = []
        for j in range(n_crit):
            pref_matrix = self._calculate_preference_matrix(
                alternatives[:, j],
                criteria_types[j],
                preference_type
            )
            preference_matrices.append(pref_matrix)
        
        # Aggregate preferences
        aggregated = np.zeros((n_alt, n_alt))
        for j, pref_matrix in enumerate(preference_matrices):
            aggregated += weights_array[j] * pref_matrix
        
        # Calculate flows
        positive_flow = aggregated.sum(axis=1) / (n_alt - 1)  # Φ+
        negative_flow = aggregated.sum(axis=0) / (n_alt - 1)  # Φ-
        net_flow = positive_flow - negative_flow  # Φ
        
        rankings = np.argsort(-net_flow)
        
        return {
            "rankings": rankings.tolist(),
            "scores": net_flow.tolist(),
            "positive_flow": positive_flow.tolist(),
            "negative_flow": negative_flow.tolist(),
            "method": "promethee_ii",
            "preference_type": preference_type
        }
    
    def _calculate_preference_matrix(
        self,
        criterion_values: np.ndarray,
        criterion_type: str,
        preference_type: str
    ) -> np.ndarray:
        """Calculate pairwise preference matrix for one criterion."""
        n = len(criterion_values)
        pref_matrix = np.zeros((n, n))
        
        for i in range(n):
            for j in range(n):
                if i != j:
                    if criterion_type.lower() == 'benefit':
                        diff = criterion_values[i] - criterion_values[j]
                    else:
                        diff = criterion_values[j] - criterion_values[i]
                    
                    pref_matrix[i, j] = self._preference_function(diff, preference_type)
        
        return pref_matrix
    
    def _preference_function(self, diff: float, pref_type: str) -> float:
        """Calculate preference value based on difference."""
        if pref_type == "usual":
            return 1.0 if diff > 0 else 0.0
        elif pref_type == "linear":
            # Linear preference with threshold
            threshold = 0.1  # Can be parameterized
            if diff <= 0:
                return 0.0
            elif diff >= threshold:
                return 1.0
            else:
                return diff / threshold
        elif pref_type == "gaussian":
            # Gaussian preference
            sigma = 0.1  # Can be parameterized
            if diff <= 0:
                return 0.0
            return 1.0 - np.exp(-(diff ** 2) / (2 * sigma ** 2))
        else:
            return 1.0 if diff > 0 else 0.0


class MCDARankingEngine:
    """
    Master MCDA Ranking Engine - Combines multiple ranking methods.
    
    Provides:
    - Individual method rankings
    - Ensemble ranking (aggregated from multiple methods)
    - Sensitivity analysis
    - Rank reversal detection
    """
    
    def __init__(self):
        self.rankers = {
            "topsis": None,  # Imported from topsis.py
            "wsm": WeightedSumModel(),
            "wpm": WeightedProductModel(),
            "ahp": AHPRanker(),
            "electre": ELECTRERanker(),
            "promethee": PROMETHEERanker()
        }
    
    def rank_all_methods(
        self,
        alternatives: np.ndarray,
        weights: List[float],
        criteria_types: List[str],
        methods: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Rank using all (or specified) MCDA methods.
        
        Args:
            alternatives: Decision matrix
            weights: Criterion weights
            criteria_types: 'benefit' or 'cost'
            methods: List of methods to use (default: all)
        
        Returns:
            Dict with rankings from each method and ensemble
        """
        if methods is None:
            methods = ["wsm", "wpm", "ahp", "electre", "promethee"]
        
        results = {}
        all_rankings = []
        
        for method in methods:
            if method in self.rankers and self.rankers[method] is not None:
                try:
                    result = self.rankers[method].rank(
                        alternatives, weights, criteria_types
                    )
                    results[method] = result
                    all_rankings.append(result["rankings"])
                except Exception as e:
                    logger.error(f"Error in {method}: {e}")
                    results[method] = {"error": str(e)}
        
        # Calculate ensemble ranking using Borda count
        if all_rankings:
            ensemble = self._borda_count_ensemble(all_rankings, alternatives.shape[0])
            results["ensemble"] = ensemble
        
        # Calculate rank correlation between methods
        if len(all_rankings) > 1:
            correlations = self._calculate_rank_correlations(all_rankings, methods)
            results["rank_correlations"] = correlations
        
        return results
    
    def _borda_count_ensemble(
        self,
        rankings_list: List[List[int]],
        n_alternatives: int
    ) -> Dict[str, Any]:
        """Aggregate rankings using Borda count."""
        borda_scores = np.zeros(n_alternatives)
        
        for rankings in rankings_list:
            for rank, alt_idx in enumerate(rankings):
                # Higher score for better rank
                borda_scores[alt_idx] += (n_alternatives - rank - 1)
        
        final_rankings = np.argsort(-borda_scores)
        
        return {
            "rankings": final_rankings.tolist(),
            "scores": borda_scores.tolist(),
            "method": "borda_count_ensemble",
            "n_methods_aggregated": len(rankings_list)
        }
    
    def _calculate_rank_correlations(
        self,
        rankings_list: List[List[int]],
        method_names: List[str]
    ) -> Dict[str, float]:
        """Calculate Spearman rank correlations between methods."""
        from scipy.stats import spearmanr
        
        correlations = {}
        for i, (name_i, rank_i) in enumerate(zip(method_names, rankings_list)):
            for j, (name_j, rank_j) in enumerate(zip(method_names, rankings_list)):
                if i < j:
                    # Convert rankings to rank positions
                    pos_i = np.argsort(rank_i)
                    pos_j = np.argsort(rank_j)
                    corr, _ = spearmanr(pos_i, pos_j)
                    correlations[f"{name_i}_vs_{name_j}"] = float(corr)
        
        return correlations
    
    def sensitivity_analysis(
        self,
        alternatives: np.ndarray,
        base_weights: List[float],
        criteria_types: List[str],
        method: str = "wsm",
        perturbation: float = 0.1
    ) -> Dict[str, Any]:
        """
        Perform sensitivity analysis on weights.
        
        Args:
            alternatives: Decision matrix
            base_weights: Original weights
            criteria_types: Criterion types
            method: Ranking method to use
            perturbation: Weight change amount (±)
        
        Returns:
            Dict with sensitivity results for each criterion
        """
        if method not in self.rankers or self.rankers[method] is None:
            raise ValueError(f"Unknown method: {method}")
        
        ranker = self.rankers[method]
        base_result = ranker.rank(alternatives, base_weights, criteria_types)
        base_ranking = base_result["rankings"]
        
        sensitivity = {}
        
        for i in range(len(base_weights)):
            # Increase weight
            weights_up = base_weights.copy()
            weights_up[i] = min(1.0, weights_up[i] + perturbation)
            # Renormalize
            weights_up = [w / sum(weights_up) for w in weights_up]
            result_up = ranker.rank(alternatives, weights_up, criteria_types)
            
            # Decrease weight
            weights_down = base_weights.copy()
            weights_down[i] = max(0.0, weights_down[i] - perturbation)
            if sum(weights_down) > 0:
                weights_down = [w / sum(weights_down) for w in weights_down]
            result_down = ranker.rank(alternatives, weights_down, criteria_types)
            
            # Check for rank changes
            rank_changes_up = sum(1 for a, b in zip(base_ranking, result_up["rankings"]) if a != b)
            rank_changes_down = sum(1 for a, b in zip(base_ranking, result_down["rankings"]) if a != b)
            
            sensitivity[f"criterion_{i}"] = {
                "base_weight": base_weights[i],
                "rank_changes_on_increase": rank_changes_up,
                "rank_changes_on_decrease": rank_changes_down,
                "is_sensitive": rank_changes_up > 0 or rank_changes_down > 0,
                "top_rank_stable": base_ranking[0] == result_up["rankings"][0] == result_down["rankings"][0]
            }
        
        return {
            "base_ranking": base_ranking,
            "sensitivity_by_criterion": sensitivity,
            "perturbation_amount": perturbation,
            "method": method
        }
