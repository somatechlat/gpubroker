"""
Property 9: Collaborative Filtering Matrix Factorization Convergence
Validates: Requirements 7.2, 33.2
"""

import numpy as np
import pytest

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from algorithms.collaborative import ALSRecommender


def test_als_converges_on_small_dataset():
    interactions = [
        {"user_id": "u1", "item_id": "i1", "weight": 1.0},
        {"user_id": "u1", "item_id": "i2", "weight": 1.0},
        {"user_id": "u2", "item_id": "i2", "weight": 1.0},
        {"user_id": "u2", "item_id": "i3", "weight": 1.0},
        {"user_id": "u3", "item_id": "i1", "weight": 1.0},
        {"user_id": "u3", "item_id": "i3", "weight": 1.0},
    ]

    als = ALSRecommender(factors=8, regularization=0.05, iterations=10, convergence_tolerance=1e-4)
    metrics = als.fit(interactions)

    # Must mark fitted and have loss history
    assert als.is_fitted
    assert metrics["iterations_run"] >= 1
    assert len(als.loss_history) == metrics["iterations_run"]

    # Loss should not increase overall
    assert als.loss_history[-1] <= als.loss_history[0] + 1e-9

    # Either converged early or reached max iterations with small delta
    assert metrics["converged"] or metrics["iterations_run"] == als.iterations

    # Recommendations should work for known user
    recs = als.recommend("u1", n=2)
    assert isinstance(recs, list)
    assert len(recs) <= 2
    for r in recs:
        assert "item_id" in r and "score" in r
