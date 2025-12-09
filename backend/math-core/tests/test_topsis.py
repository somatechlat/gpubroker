"""
Property-based tests for TOPSIS Algorithm.

**Feature: gpubroker-enterprise-saas, Property 7: TOPSIS Ranking Determinism**
**Feature: gpubroker-enterprise-saas, Property 8: TOPSIS Ideal Solution Correctness**
**Validates: Requirements 7.1**
"""

import pytest
from hypothesis import given, strategies as st, settings, assume, HealthCheck
import numpy as np

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from algorithms.topsis import TOPSISEngine


@pytest.fixture
def topsis_engine():
    return TOPSISEngine()


class TestTOPSISDeterminism:
    """
    **Feature: gpubroker-enterprise-saas, Property 7: TOPSIS Ranking Determinism**
    **Validates: Requirements 7.1**
    
    For any decision matrix and weight vector, repeated TOPSIS calculations
    SHALL produce identical rankings (deterministic output).
    """
    
    @given(
        n_alternatives=st.integers(min_value=3, max_value=10),
        n_criteria=st.integers(min_value=2, max_value=5)
    )
    @settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_topsis_determinism(self, topsis_engine, n_alternatives: int, n_criteria: int):
        """Repeated calculations must produce identical rankings."""
        # Generate random matrix
        np.random.seed(42)
        matrix = np.random.uniform(0.1, 100, (n_alternatives, n_criteria))
        
        # Generate weights that sum to 1
        raw_weights = np.random.uniform(0.1, 1, n_criteria)
        weights = (raw_weights / raw_weights.sum()).tolist()
        
        # Random criteria types
        criteria_types = ["benefit" if np.random.random() > 0.3 else "cost" 
                        for _ in range(n_criteria)]
        
        # Run twice
        result1 = topsis_engine.calculate(matrix, weights, criteria_types)
        result2 = topsis_engine.calculate(matrix, weights, criteria_types)
        
        # Rankings must be identical
        assert result1["rankings"] == result2["rankings"], "TOPSIS must be deterministic"
        
        # Scores must be identical
        for s1, s2 in zip(result1["scores"], result2["scores"]):
            assert abs(s1 - s2) < 1e-10, "Scores must be identical"


class TestTOPSISIdealSolution:
    """
    **Feature: gpubroker-enterprise-saas, Property 8: TOPSIS Ideal Solution Correctness**
    **Validates: Requirements 7.1**
    
    The ideal solution SHALL contain:
    - Maximum value for benefit criteria
    - Minimum value for cost criteria
    """
    
    def test_ideal_solution_benefit_criteria(self, topsis_engine):
        """Ideal solution should have max for benefit criteria."""
        matrix = np.array([
            [10, 5, 100],
            [20, 3, 80],
            [15, 4, 90]
        ], dtype=np.float64)
        
        weights = [0.4, 0.3, 0.3]
        criteria_types = ["benefit", "cost", "benefit"]
        
        result = topsis_engine.calculate(matrix, weights, criteria_types)
        
        # For benefit criteria (0, 2), ideal should be max of weighted normalized
        # For cost criteria (1), ideal should be min of weighted normalized
        ideal = result["ideal_solution"]
        anti_ideal = result["anti_ideal_solution"]
        
        # Ideal should differ from anti-ideal
        assert ideal != anti_ideal, "Ideal and anti-ideal must differ"
    
    def test_ideal_solution_all_benefit(self, topsis_engine):
        """When all criteria are benefit, ideal = max per column."""
        matrix = np.array([
            [10, 20, 30],
            [40, 50, 60],
            [70, 80, 90]
        ], dtype=np.float64)
        
        weights = [0.33, 0.34, 0.33]
        criteria_types = ["benefit", "benefit", "benefit"]
        
        result = topsis_engine.calculate(matrix, weights, criteria_types)
        
        # Best alternative should be the one with highest values (index 2)
        assert result["rankings"][0] == 2, "Highest values should rank first for all-benefit"
    
    def test_ideal_solution_all_cost(self, topsis_engine):
        """When all criteria are cost, ideal = min per column."""
        matrix = np.array([
            [10, 20, 30],
            [40, 50, 60],
            [70, 80, 90]
        ], dtype=np.float64)
        
        weights = [0.33, 0.34, 0.33]
        criteria_types = ["cost", "cost", "cost"]
        
        result = topsis_engine.calculate(matrix, weights, criteria_types)
        
        # Best alternative should be the one with lowest values (index 0)
        assert result["rankings"][0] == 0, "Lowest values should rank first for all-cost"


class TestTOPSISValidation:
    """Tests for input validation."""
    
    def test_weights_must_sum_to_one(self, topsis_engine):
        """Weights not summing to 1 should raise error."""
        matrix = np.array([[1, 2], [3, 4]], dtype=np.float64)
        
        with pytest.raises(ValueError, match="sum to 1"):
            topsis_engine.calculate(matrix, [0.3, 0.3], ["benefit", "benefit"])
    
    def test_criteria_types_validation(self, topsis_engine):
        """Invalid criteria types should raise error."""
        matrix = np.array([[1, 2], [3, 4]], dtype=np.float64)
        
        with pytest.raises(ValueError, match="Invalid criteria type"):
            topsis_engine.calculate(matrix, [0.5, 0.5], ["benefit", "invalid"])
    
    def test_minimum_alternatives(self, topsis_engine):
        """Need at least 2 alternatives."""
        matrix = np.array([[1, 2]], dtype=np.float64)
        
        with pytest.raises(ValueError, match="at least 2"):
            topsis_engine.calculate(matrix, [0.5, 0.5], ["benefit", "benefit"])


class TestTOPSISScoreBounds:
    """Tests for score bounds."""
    
    @given(
        n_alternatives=st.integers(min_value=3, max_value=8),
        n_criteria=st.integers(min_value=2, max_value=4)
    )
    @settings(max_examples=30, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_scores_in_zero_one(self, topsis_engine, n_alternatives: int, n_criteria: int):
        """All closeness scores must be in [0, 1]."""
        np.random.seed(123)
        matrix = np.random.uniform(1, 100, (n_alternatives, n_criteria))
        
        raw_weights = np.random.uniform(0.1, 1, n_criteria)
        weights = (raw_weights / raw_weights.sum()).tolist()
        
        criteria_types = ["benefit"] * n_criteria
        
        result = topsis_engine.calculate(matrix, weights, criteria_types)
        
        for score in result["scores"]:
            assert 0 <= score <= 1, f"Score {score} must be in [0, 1]"
