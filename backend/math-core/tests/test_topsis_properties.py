"""
Property tests for TOPSIS engine.

- Property 7: TOPSIS Ranking Determinism (Requirements 7.1)
- Property 8: TOPSIS Ideal Solution Correctness (Requirements 7.1)
"""

import numpy as np
from hypothesis import given, strategies as st, settings

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from algorithms.topsis import TOPSISEngine


topsis = TOPSISEngine()


@given(
    st.integers(min_value=2, max_value=6),
    st.integers(min_value=2, max_value=6),
    st.lists(st.just('benefit'), min_size=1, max_size=6)
)
@settings(max_examples=50)
def test_topsis_deterministic(n_alt, n_crit, crit_types):
    # pad/trim criteria types to n_crit (all benefit for simplicity)
    criteria_types = (crit_types * n_crit)[:n_crit]
    weights = np.full(n_crit, 1.0 / n_crit).tolist()
    matrix = np.abs(np.random.rand(n_alt, n_crit)) * 100

    res1 = topsis.calculate(matrix, weights, criteria_types)
    res2 = topsis.calculate(matrix, weights, criteria_types)

    assert res1['rankings'] == res2['rankings']
    assert np.allclose(res1['scores'], res2['scores'])


def test_topsis_ideal_solution_correctness():
    # Simple 2x2 example with one benefit, one cost
    matrix = np.array([
        [10.0, 100.0],  # alt A
        [20.0,  50.0],  # alt B
    ])
    weights = [0.5, 0.5]
    criteria_types = ['benefit', 'cost']

    result = topsis.calculate(matrix, weights, criteria_types)

    # Recompute weighted matrix to validate ideal/anti-ideal
    norms = np.sqrt(np.sum(matrix ** 2, axis=0))
    normalized = matrix / norms
    weighted = normalized * np.array(weights)

    expected_ideal = [
        np.max(weighted[:, 0]),  # benefit -> max
        np.min(weighted[:, 1]),  # cost -> min
    ]
    expected_anti = [
        np.min(weighted[:, 0]),  # benefit -> min
        np.max(weighted[:, 1]),  # cost -> max
    ]

    assert np.allclose(result['ideal_solution'], expected_ideal)
    assert np.allclose(result['anti_ideal_solution'], expected_anti)

    # Ranking: B should be better (higher benefit, lower cost)
    assert result['rankings'][0] == 1  # alternative index 1 (B) best
