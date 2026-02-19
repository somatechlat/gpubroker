"""
TOPSIS Algorithm Implementation.

Technique for Order of Preference by Similarity to Ideal Solution.
Multi-criteria decision analysis algorithm for ranking GPU offers.

Reference: Hwang, C.L.; Yoon, K. (1981). Multiple Attribute Decision Making.

NO MOCKS. NO FAKE DATA. IEEE 754 double precision throughout.
"""

import logging
from typing import Any

import numpy as np

logger = logging.getLogger("gpubroker.math_core.algorithms.topsis")


class TOPSISEngine:
    """
    TOPSIS (Technique for Order of Preference by Similarity to Ideal Solution).

    Steps:
    1. Normalize the decision matrix using vector normalization
    2. Calculate weighted normalized matrix
    3. Determine ideal (A+) and anti-ideal (A-) solutions
    4. Calculate separation measures using Euclidean distance
    5. Calculate relative closeness to ideal solution
    6. Rank alternatives by closeness score
    """

    def calculate(
        self,
        decision_matrix: np.ndarray,
        weights: list[float],
        criteria_types: list[str],
    ) -> dict[str, Any]:
        """
        Execute TOPSIS algorithm.

        Args:
            decision_matrix: numpy array of shape (alternatives, criteria)
            weights: List of weights for each criterion (must sum to 1.0)
            criteria_types: List of 'benefit' or 'cost' for each criterion

        Returns:
            Dict with rankings, scores, ideal and anti-ideal solutions
        """
        self._validate_inputs(decision_matrix, weights, criteria_types)

        n_alternatives, n_criteria = decision_matrix.shape

        # Step 1: Normalize (vector normalization)
        normalized = self._normalize_matrix(decision_matrix)

        # Step 2: Weighted normalized matrix
        weights_array = np.array(weights, dtype=np.float64)
        weighted = normalized * weights_array

        # Step 3: Ideal and anti-ideal solutions
        ideal, anti_ideal = self._find_ideal_solutions(weighted, criteria_types)

        # Step 4: Separation measures
        separation_positive = self._calculate_separation(weighted, ideal)
        separation_negative = self._calculate_separation(weighted, anti_ideal)

        # Step 5: Relative closeness
        denominator = separation_positive + separation_negative
        closeness = np.where(
            denominator > 1e-10, separation_negative / denominator, 0.0
        )

        # Step 6: Rank (higher closeness = better)
        rankings = np.argsort(-closeness)

        return {
            "rankings": rankings.tolist(),
            "scores": closeness.tolist(),
            "ideal_solution": ideal.tolist(),
            "anti_ideal_solution": anti_ideal.tolist(),
        }

    def _validate_inputs(
        self,
        decision_matrix: np.ndarray,
        weights: list[float],
        criteria_types: list[str],
    ) -> None:
        """Validate TOPSIS inputs."""
        if decision_matrix.ndim != 2:
            raise ValueError("Decision matrix must be 2-dimensional")

        n_alternatives, n_criteria = decision_matrix.shape

        if n_alternatives < 2:
            raise ValueError("Need at least 2 alternatives")

        if len(weights) != n_criteria:
            raise ValueError(
                f"Weights length ({len(weights)}) must match criteria count ({n_criteria})"
            )

        if len(criteria_types) != n_criteria:
            raise ValueError(
                f"Criteria types length ({len(criteria_types)}) must match criteria count ({n_criteria})"
            )

        weight_sum = sum(weights)
        if abs(weight_sum - 1.0) > 0.001:
            raise ValueError(f"Weights must sum to 1.0, got {weight_sum}")

        valid_types = {"benefit", "cost"}
        for ct in criteria_types:
            if ct.lower() not in valid_types:
                raise ValueError(f"Invalid criteria type: {ct}")

    def _normalize_matrix(self, matrix: np.ndarray) -> np.ndarray:
        """Normalize using vector normalization (L2 norm)."""
        norms = np.sqrt(np.sum(matrix**2, axis=0))
        norms = np.where(norms > 1e-10, norms, 1.0)
        return matrix / norms

    def _find_ideal_solutions(
        self, weighted_matrix: np.ndarray, criteria_types: list[str]
    ) -> tuple:
        """Find ideal (A+) and anti-ideal (A-) solutions."""
        n_criteria = weighted_matrix.shape[1]

        ideal = np.zeros(n_criteria, dtype=np.float64)
        anti_ideal = np.zeros(n_criteria, dtype=np.float64)

        for j in range(n_criteria):
            column = weighted_matrix[:, j]

            if criteria_types[j].lower() == "benefit":
                ideal[j] = np.max(column)
                anti_ideal[j] = np.min(column)
            else:
                ideal[j] = np.min(column)
                anti_ideal[j] = np.max(column)

        return ideal, anti_ideal

    def _calculate_separation(
        self, weighted_matrix: np.ndarray, reference: np.ndarray
    ) -> np.ndarray:
        """Calculate Euclidean distance from each alternative to reference."""
        diff = weighted_matrix - reference
        return np.sqrt(np.sum(diff**2, axis=1))

    def rank_offers(
        self, offers: list[dict[str, Any]], criteria_config: dict[str, dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """
        Convenience method to rank GPU offers using TOPSIS.

        Args:
            offers: List of offer dicts
            criteria_config: Dict mapping attribute names to config

        Returns:
            List of offers with topsis_score and topsis_rank
        """
        if not offers:
            return []

        criteria_names = list(criteria_config.keys())
        weights = [criteria_config[c]["weight"] for c in criteria_names]
        criteria_types = [criteria_config[c]["type"] for c in criteria_names]

        n_offers = len(offers)
        n_criteria = len(criteria_names)
        matrix = np.zeros((n_offers, n_criteria), dtype=np.float64)

        for i, offer in enumerate(offers):
            for j, criterion in enumerate(criteria_names):
                value = offer.get(criterion, 0)
                matrix[i, j] = float(value) if value is not None else 0.0

        result = self.calculate(matrix, weights, criteria_types)

        ranked_offers = []
        for i, offer in enumerate(offers):
            offer_copy = offer.copy()
            offer_copy["topsis_score"] = result["scores"][i]
            offer_copy["topsis_rank"] = result["rankings"].index(i) + 1
            ranked_offers.append(offer_copy)

        ranked_offers.sort(key=lambda x: x["topsis_rank"])
        return ranked_offers
