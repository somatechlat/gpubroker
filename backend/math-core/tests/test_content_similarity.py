"""
Property-based tests for Content-Based Similarity.

**Feature: gpubroker-enterprise-saas, Property 10: Content-Based Similarity Bounds**
**Validates: Requirements 7.3**
"""

import pytest
from hypothesis import given, strategies as st, settings, assume, HealthCheck
import numpy as np

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from algorithms.content_based import ContentSimilarity


@pytest.fixture
def content_similarity():
    return ContentSimilarity()


class TestCosineSimilarityBounds:
    """
    **Feature: gpubroker-enterprise-saas, Property 10: Content-Based Similarity Bounds**
    **Validates: Requirements 7.3**
    
    For any two feature vectors:
    - Cosine similarity SHALL be in range [-1, 1]
    - Identical vectors SHALL produce similarity = 1.0
    """
    
    @given(
        vec1=st.lists(st.floats(min_value=-100, max_value=100, allow_nan=False, allow_infinity=False), 
                      min_size=3, max_size=10),
        vec2=st.lists(st.floats(min_value=-100, max_value=100, allow_nan=False, allow_infinity=False), 
                      min_size=3, max_size=10)
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_cosine_similarity_bounds(self, content_similarity, vec1, vec2):
        """Cosine similarity must be in [-1, 1]."""
        # Ensure same length
        min_len = min(len(vec1), len(vec2))
        vec1 = vec1[:min_len]
        vec2 = vec2[:min_len]
        
        # Skip zero vectors
        assume(np.linalg.norm(vec1) > 1e-10)
        assume(np.linalg.norm(vec2) > 1e-10)
        
        similarity = content_similarity.cosine_similarity(
            np.array(vec1), np.array(vec2)
        )
        
        assert -1.0 <= similarity <= 1.0, f"Similarity {similarity} must be in [-1, 1]"
    
    @given(
        vec=st.lists(st.floats(min_value=-100, max_value=100, allow_nan=False, allow_infinity=False), 
                     min_size=3, max_size=10)
    )
    @settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_identical_vectors_similarity_one(self, content_similarity, vec):
        """Identical vectors must have similarity = 1.0."""
        # Skip zero vectors
        assume(np.linalg.norm(vec) > 1e-10)
        
        vec_array = np.array(vec)
        similarity = content_similarity.cosine_similarity(vec_array, vec_array)
        
        assert abs(similarity - 1.0) < 1e-10, "Identical vectors must have similarity 1.0"
    
    def test_opposite_vectors_similarity_negative_one(self, content_similarity):
        """Opposite vectors should have similarity = -1.0."""
        vec1 = np.array([1.0, 2.0, 3.0])
        vec2 = np.array([-1.0, -2.0, -3.0])
        
        similarity = content_similarity.cosine_similarity(vec1, vec2)
        
        assert abs(similarity - (-1.0)) < 1e-10, "Opposite vectors must have similarity -1.0"
    
    def test_orthogonal_vectors_similarity_zero(self, content_similarity):
        """Orthogonal vectors should have similarity = 0."""
        vec1 = np.array([1.0, 0.0, 0.0])
        vec2 = np.array([0.0, 1.0, 0.0])
        
        similarity = content_similarity.cosine_similarity(vec1, vec2)
        
        assert abs(similarity) < 1e-10, "Orthogonal vectors must have similarity 0"


class TestFindSimilar:
    """Tests for find_similar functionality."""
    
    def test_find_similar_returns_correct_count(self, content_similarity):
        """Should return requested number of matches."""
        query = np.array([1.0, 2.0, 3.0])
        candidates = np.array([
            [1.0, 2.0, 3.0],
            [1.1, 2.1, 3.1],
            [0.0, 0.0, 1.0],
            [1.0, 0.0, 0.0],
            [2.0, 4.0, 6.0]
        ])
        
        result = content_similarity.find_similar(query, candidates, top_k=3)
        
        assert len(result["matches"]) == 3
        assert len(result["scores"]) == 3
    
    def test_find_similar_ordered_by_score(self, content_similarity):
        """Results should be ordered by descending similarity."""
        query = np.array([1.0, 2.0, 3.0])
        candidates = np.array([
            [0.0, 0.0, 1.0],  # Low similarity
            [1.0, 2.0, 3.0],  # Identical - highest
            [1.1, 2.1, 3.1],  # Very similar
        ])
        
        result = content_similarity.find_similar(query, candidates, top_k=3)
        
        # Scores should be descending
        scores = result["scores"]
        assert scores == sorted(scores, reverse=True), "Scores must be descending"
        
        # First match should be the identical vector (index 1)
        assert result["matches"][0] == 1


class TestFeatureExtraction:
    """Tests for feature extraction from offers and workloads."""
    
    def test_extract_offer_features(self, content_similarity):
        """Should extract normalized features from offer."""
        offer = {
            "price_per_hour": 2.5,
            "vram_gb": 24,
            "tflops": 40.0,
            "availability_score": 0.9,
            "reliability_score": 0.95
        }
        
        features = content_similarity.extract_offer_features(offer)
        
        assert len(features) == 5
        assert all(0 <= f <= 1 for f in features), "Features must be normalized to [0, 1]"
    
    def test_extract_workload_features(self, content_similarity):
        """Should extract normalized features from workload."""
        workload = {
            "budget_per_hour": 3.0,
            "min_vram_gb": 16,
            "min_tflops": 30.0,
            "availability_required": 0.8,
            "reliability_required": 0.9
        }
        
        features = content_similarity.extract_workload_features(workload)
        
        assert len(features) == 5
        assert all(0 <= f <= 1 for f in features), "Features must be normalized to [0, 1]"
    
    def test_match_workload_to_offers(self, content_similarity):
        """Should match workload to offers with scores."""
        workload = {
            "budget_per_hour": 2.0,
            "min_vram_gb": 24,
            "min_tflops": 35.0,
            "availability_required": 0.9,
            "reliability_required": 0.9
        }
        
        offers = [
            {"id": "1", "price_per_hour": 2.0, "vram_gb": 24, "tflops": 40.0, 
             "availability_score": 0.9, "reliability_score": 0.95},
            {"id": "2", "price_per_hour": 5.0, "vram_gb": 80, "tflops": 60.0,
             "availability_score": 0.95, "reliability_score": 0.98},
            {"id": "3", "price_per_hour": 0.5, "vram_gb": 8, "tflops": 10.0,
             "availability_score": 0.7, "reliability_score": 0.8},
        ]
        
        matched = content_similarity.match_workload_to_offers(workload, offers, top_k=2)
        
        assert len(matched) == 2
        assert all("content_score" in m for m in matched)
