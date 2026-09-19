import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.stats import rankdata
from sklearn.metrics import roc_auc_score
from typing import List, Tuple, Dict

def to_fractional_ranks(preds: np.ndarray) -> np.ndarray:
    """
    Converts raw probability predictions to normalized fractional ranks [0.0, 1.0].
    Preserves exact monotonic ordering while eliminating scale mismatch across model families.
    """
    return (rankdata(preds) - 1.0) / (len(preds) - 1.0)

def optimize_rank_blend_weights(oof_predictions: List[np.ndarray], y_true: np.ndarray) -> np.ndarray:
    """
    Finds optimal convex combination of fractional ranks using Nelder-Mead optimization
    to directly maximize ROC-AUC.
    
    Zero Calibration Policy: Avoids Isotonic/Platt calibration to prevent rank ties.
    """
    n_models = len(oof_predictions)
    rank_matrix = np.column_stack([to_fractional_ranks(p) for p in oof_predictions])
    
    def loss_func(weights: np.ndarray) -> float:
        # Normalize weights to sum to 1.0
        w = np.maximum(weights, 0.0)
        if np.sum(w) == 0:
            return 0.0
        w = w / np.sum(w)
        blend_ranks = np.dot(rank_matrix, w)
        # We minimize negative ROC-AUC
        return -roc_auc_score(y_true, blend_ranks)
    
    init_weights = np.ones(n_models) / n_models
    res = minimize(
        loss_func,
        init_weights,
        method="Nelder-Mead",
        options={"maxiter": 500, "disp": False}
    )
    
    best_w = np.maximum(res.x, 0.0)
    best_w = best_w / np.sum(best_w)
    
    final_auc = -res.fun
    print(f"🎯 [Nelder-Mead Optimizer] Found optimal blend weights: {np.round(best_w, 4)}")
    print(f"🏆 [Optimized Blend OOF] ROC-AUC: {final_auc:.6f}")
    
    return best_w

def blend_test_predictions(test_predictions: List[np.ndarray], weights: np.ndarray) -> np.ndarray:
    """
    Blends test predictions using fractional ranks and computed optimal weights.
    """
    test_rank_matrix = np.column_stack([to_fractional_ranks(p) for p in test_predictions])
    blended_ranks = np.dot(test_rank_matrix, weights)
    # Output final ranks as probabilities in [0.0, 1.0]
    return blended_ranks
