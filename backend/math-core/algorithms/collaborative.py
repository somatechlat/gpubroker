"""
Collaborative Filtering using Alternating Least Squares (ALS)

Matrix factorization for "users like you also chose..." recommendations.
Parameters: k=50 factors, λ=0.1 regularization, tolerance=1e-6

Reference: Hu, Y., Koren, Y., & Volinsky, C. (2008). 
Collaborative Filtering for Implicit Feedback Datasets.
"""

import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from scipy import sparse
import logging

logger = logging.getLogger(__name__)


class ALSRecommender:
    """
    Alternating Least Squares for Collaborative Filtering.
    
    Factorizes user-item interaction matrix R ≈ U × V^T
    where U is user factors and V is item factors.
    
    Uses implicit feedback (interactions) rather than explicit ratings.
    """
    
    def __init__(
        self,
        factors: int = 50,
        regularization: float = 0.1,
        iterations: int = 15,
        convergence_tolerance: float = 1e-6
    ):
        """
        Initialize ALS recommender.
        
        Args:
            factors: Number of latent factors (k)
            regularization: Regularization parameter (λ)
            iterations: Maximum iterations
            convergence_tolerance: Stop if loss change < tolerance
        """
        self.factors = factors
        self.regularization = regularization
        self.iterations = iterations
        self.convergence_tolerance = convergence_tolerance
        
        # Model state
        self.user_factors: Optional[np.ndarray] = None
        self.item_factors: Optional[np.ndarray] = None
        self.user_index: Dict[str, int] = {}
        self.item_index: Dict[str, int] = {}
        self.is_fitted = False
        self.loss_history: List[float] = []
    
    def fit(
        self,
        interactions: List[Dict[str, Any]],
        confidence_weight: float = 40.0
    ) -> Dict[str, Any]:
        """
        Fit the ALS model on user-item interactions.
        
        Args:
            interactions: List of dicts with 'user_id', 'item_id', and optional 'weight'
            confidence_weight: Scaling factor for confidence (α in paper)
        
        Returns:
            Dict with training metrics
        """
        if not interactions:
            raise ValueError("No interactions provided")
        
        # Build indices
        users = sorted(set(i['user_id'] for i in interactions))
        items = sorted(set(i['item_id'] for i in interactions))
        
        self.user_index = {u: idx for idx, u in enumerate(users)}
        self.item_index = {i: idx for idx, i in enumerate(items)}
        
        n_users = len(users)
        n_items = len(items)
        
        logger.info(f"Fitting ALS: {n_users} users, {n_items} items, {len(interactions)} interactions")
        
        # Build sparse interaction matrix
        row_indices = []
        col_indices = []
        data = []
        
        for interaction in interactions:
            user_idx = self.user_index[interaction['user_id']]
            item_idx = self.item_index[interaction['item_id']]
            weight = interaction.get('weight', 1.0)
            
            row_indices.append(user_idx)
            col_indices.append(item_idx)
            data.append(weight)
        
        # Confidence matrix C = 1 + α * R
        R = sparse.csr_matrix(
            (data, (row_indices, col_indices)),
            shape=(n_users, n_items),
            dtype=np.float64
        )
        
        # Initialize factors randomly
        np.random.seed(42)  # Reproducibility
        self.user_factors = np.random.normal(0, 0.01, (n_users, self.factors))
        self.item_factors = np.random.normal(0, 0.01, (n_items, self.factors))
        
        # Alternating optimization
        self.loss_history = []
        prev_loss = float('inf')
        
        for iteration in range(self.iterations):
            # Update user factors
            self._update_factors(
                R, self.user_factors, self.item_factors,
                confidence_weight, update_users=True
            )
            
            # Update item factors
            self._update_factors(
                R.T.tocsr(), self.item_factors, self.user_factors,
                confidence_weight, update_users=False
            )
            
            # Calculate loss
            loss = self._calculate_loss(R, confidence_weight)
            self.loss_history.append(loss)
            
            # Check convergence
            loss_change = abs(prev_loss - loss)
            if loss_change < self.convergence_tolerance:
                logger.info(f"Converged at iteration {iteration + 1}")
                break
            
            prev_loss = loss
            
            if (iteration + 1) % 5 == 0:
                logger.info(f"Iteration {iteration + 1}, Loss: {loss:.6f}")
        
        self.is_fitted = True
        
        return {
            "n_users": n_users,
            "n_items": n_items,
            "n_interactions": len(interactions),
            "iterations_run": len(self.loss_history),
            "final_loss": self.loss_history[-1] if self.loss_history else None,
            "converged": len(self.loss_history) < self.iterations
        }
    
    def _update_factors(
        self,
        R: sparse.csr_matrix,
        target_factors: np.ndarray,
        fixed_factors: np.ndarray,
        confidence_weight: float,
        update_users: bool
    ) -> None:
        """
        Update either user or item factors while holding the other fixed.
        
        Solves: (Y^T * C * Y + λI) * x = Y^T * C * p
        where Y is fixed factors, x is target factor vector, p is preference
        """
        n_targets = target_factors.shape[0]
        YtY = fixed_factors.T @ fixed_factors
        
        # Regularization term
        reg_matrix = self.regularization * np.eye(self.factors)
        
        for i in range(n_targets):
            # Get interactions for this user/item
            if update_users:
                row = R.getrow(i)
            else:
                row = R.getrow(i)
            
            indices = row.indices
            values = row.data
            
            if len(indices) == 0:
                # No interactions, use regularized mean
                target_factors[i] = np.zeros(self.factors)
                continue
            
            # Confidence for each interaction
            confidence = 1.0 + confidence_weight * values
            
            # Y_i = factors for interacted items
            Y_i = fixed_factors[indices]
            
            # C_i * Y_i
            CY = Y_i * confidence[:, np.newaxis]
            
            # (Y^T * C * Y + λI)
            A = Y_i.T @ CY + reg_matrix
            
            # Y^T * C * p (p = 1 for all interactions in implicit feedback)
            b = np.sum(CY, axis=0)
            
            # Solve linear system
            try:
                target_factors[i] = np.linalg.solve(A, b)
            except np.linalg.LinAlgError:
                # Fallback to pseudo-inverse if singular
                target_factors[i] = np.linalg.lstsq(A, b, rcond=None)[0]
    
    def _calculate_loss(
        self,
        R: sparse.csr_matrix,
        confidence_weight: float
    ) -> float:
        """
        Calculate weighted squared error loss with regularization.
        
        Loss = Σ c_ui * (p_ui - u_i^T * v_j)^2 + λ * (||U||^2 + ||V||^2)
        """
        # Predicted ratings
        predictions = self.user_factors @ self.item_factors.T
        
        # Only calculate loss on observed interactions
        loss = 0.0
        for i in range(R.shape[0]):
            row = R.getrow(i)
            for j, r in zip(row.indices, row.data):
                confidence = 1.0 + confidence_weight * r
                pred = predictions[i, j]
                loss += confidence * (1.0 - pred) ** 2  # p_ui = 1 for implicit
        
        # Regularization
        loss += self.regularization * (
            np.sum(self.user_factors ** 2) +
            np.sum(self.item_factors ** 2)
        )
        
        return loss
    
    def recommend(
        self,
        user_id: str,
        n: int = 5,
        exclude_seen: bool = True,
        seen_items: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Get top-N recommendations for a user.
        
        Args:
            user_id: User identifier
            n: Number of recommendations
            exclude_seen: Whether to exclude items user has interacted with
            seen_items: Optional list of item IDs to exclude
        
        Returns:
            List of dicts with 'item_id' and 'score'
        """
        if not self.is_fitted:
            raise ValueError("Model not fitted. Call fit() first.")
        
        if user_id not in self.user_index:
            # Cold start - return empty or popular items
            logger.warning(f"Unknown user: {user_id}")
            return []
        
        user_idx = self.user_index[user_id]
        user_vector = self.user_factors[user_idx]
        
        # Calculate scores for all items
        scores = self.item_factors @ user_vector
        
        # Build exclusion set
        exclude_indices = set()
        if seen_items:
            for item_id in seen_items:
                if item_id in self.item_index:
                    exclude_indices.add(self.item_index[item_id])
        
        # Get reverse index
        idx_to_item = {idx: item for item, idx in self.item_index.items()}
        
        # Sort and filter
        recommendations = []
        sorted_indices = np.argsort(-scores)
        
        for idx in sorted_indices:
            if idx in exclude_indices:
                continue
            
            recommendations.append({
                "item_id": idx_to_item[idx],
                "score": float(scores[idx])
            })
            
            if len(recommendations) >= n:
                break
        
        return recommendations
    
    def similar_items(
        self,
        item_id: str,
        n: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Find items similar to a given item based on factor similarity.
        
        Args:
            item_id: Item identifier
            n: Number of similar items
        
        Returns:
            List of dicts with 'item_id' and 'similarity'
        """
        if not self.is_fitted:
            raise ValueError("Model not fitted. Call fit() first.")
        
        if item_id not in self.item_index:
            logger.warning(f"Unknown item: {item_id}")
            return []
        
        item_idx = self.item_index[item_id]
        item_vector = self.item_factors[item_idx]
        
        # Cosine similarity with all items
        norms = np.linalg.norm(self.item_factors, axis=1)
        norms = np.where(norms > 1e-10, norms, 1.0)
        
        similarities = (self.item_factors @ item_vector) / (norms * np.linalg.norm(item_vector))
        
        # Get reverse index
        idx_to_item = {idx: item for item, idx in self.item_index.items()}
        
        # Sort and return top-N (excluding self)
        sorted_indices = np.argsort(-similarities)
        
        results = []
        for idx in sorted_indices:
            if idx == item_idx:
                continue
            
            results.append({
                "item_id": idx_to_item[idx],
                "similarity": float(similarities[idx])
            })
            
            if len(results) >= n:
                break
        
        return results
    
    def get_user_vector(self, user_id: str) -> Optional[np.ndarray]:
        """Get latent factor vector for a user."""
        if not self.is_fitted or user_id not in self.user_index:
            return None
        return self.user_factors[self.user_index[user_id]].copy()
    
    def get_item_vector(self, item_id: str) -> Optional[np.ndarray]:
        """Get latent factor vector for an item."""
        if not self.is_fitted or item_id not in self.item_index:
            return None
        return self.item_factors[self.item_index[item_id]].copy()
