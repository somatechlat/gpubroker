"""
Property tests for content similarity bounds and ensemble weight constraints.

- Property 10: Content-Based Similarity Bounds (Requirements 7.3)
- Property 11: Ensemble Recommendation Weight Sum (Requirements 7.4)
"""

import numpy as np
import pytest
from hypothesis import given, strategies as st, settings

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from algorithms.content_based import ContentSimilarity
from algorithms.ensemble import EnsembleRecommender
from algorithms.topsis import TOPSISEngine
from algorithms.collaborative import ALSRecommender


content = ContentSimilarity()


@given(
    st.lists(st.floats(min_value=-1e6, max_value=1e6, allow_nan=False, allow_infinity=False), min_size=3, max_size=16),
    st.lists(st.floats(min_value=-1e6, max_value=1e6, allow_nan=False, allow_infinity=False), min_size=3, max_size=16)
)
@settings(max_examples=100)
def test_cosine_similarity_bounds(vec1, vec2):
    # match lengths
    n = min(len(vec1), len(vec2))
    a = np.array(vec1[:n], dtype=np.float64)
    b = np.array(vec2[:n], dtype=np.float64)
    score = content.cosine_similarity(a, b)
    assert -1.0 <= score <= 1.0


def test_cosine_similarity_zero_vector_returns_zero():
    score = content.cosine_similarity(np.array([0.0, 0.0, 0.0]), np.array([1.0, 2.0, 3.0]))
    assert score == 0.0


def test_ensemble_default_weights_sum_to_one():
    ens = EnsembleRecommender(TOPSISEngine(), ALSRecommender(), ContentSimilarity())
    assert abs(sum(ens.weights.values()) - 1.0) < 1e-9


def test_ensemble_rejects_invalid_weight_sum():
    with pytest.raises(ValueError):
        EnsembleRecommender(
            TOPSISEngine(),
            ALSRecommender(),
            ContentSimilarity(),
            weights={"topsis": 0.5, "collaborative": 0.5, "content_based": 0.2},
        )
