import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.metrics import roc_auc_score

def verify_submission_file(sub_path: Path, sample_sub_path: Path, expected_rows: int = 286571) -> bool:
    """
    6-Point Integrity Check for Kaggle S6E9 Submission files:
    1. File exists and is non-empty.
    2. Row count exactly matches expected (286,571).
    3. Column names exactly ['id', 'Will_Buy_EV'].
    4. Zero NaN or Null values.
    5. Continuous probabilities in [0.0, 1.0].
    6. Row-by-row ID alignment with sample_submission.csv.
    """
    print(f"🔍 [JudgeGuard] Verifying submission file: {sub_path.name}...")
    if not sub_path.exists():
        raise FileNotFoundError(f"Submission file does not exist: {sub_path}")
    
    df_sub = pd.read_csv(sub_path)
    df_sample = pd.read_csv(sample_sub_path)
    
    # 1. Row count
    if len(df_sub) != expected_rows:
        raise ValueError(f"Row count mismatch! Expected {expected_rows}, got {len(df_sub)}")
    print(f"  ✅ Row count check: {len(df_sub)} rows (Exact match)")
    
    # 2. Columns
    expected_cols = ["id", "Will_Buy_EV"]
    if list(df_sub.columns) != expected_cols:
        raise ValueError(f"Column mismatch! Expected {expected_cols}, got {list(df_sub.columns)}")
    print("  ✅ Column name check: ['id', 'Will_Buy_EV']")
    
    # 3. Nulls
    nan_count = df_sub.isna().sum().sum()
    if nan_count > 0:
        raise ValueError(f"Found {nan_count} NaN values in submission!")
    print("  ✅ Null value check: 0 NaNs found")
    
    # 4. Probabilities bounds
    probs = df_sub["Will_Buy_EV"].values
    if np.any(probs < 0.0) or np.any(probs > 1.0):
        raise ValueError(f"Predictions out of probability bounds [0, 1]! Min: {probs.min()}, Max: {probs.max()}")
    print(f"  ✅ Probability bounds check: [{probs.min():.5f}, {probs.max():.5f}]")
    
    # 5. ID alignment
    if not (df_sub["id"].values == df_sample["id"].values).all():
        raise ValueError("ID sequence does NOT match sample_submission.csv exactly!")
    print("  ✅ ID alignment check: 100% matched to sample_submission.csv")
    
    print(f"🎉 [JudgeGuard PASSED] {sub_path.name} is fully verified and ready for Kaggle submission!\n")
    return True

def evaluate_oof_score(y_true: np.ndarray, y_pred: np.ndarray, model_name: str) -> float:
    """Computes and logs Out-Of-Fold CV ROC-AUC score."""
    auc = roc_auc_score(y_true, y_pred)
    print(f"📊 [OOF Evaluation] {model_name} -> 10-Fold CV ROC-AUC: {auc:.6f}")
    return auc
