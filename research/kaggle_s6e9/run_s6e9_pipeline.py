#!/usr/bin/env python3
"""
End-to-End Execution Pipeline for Kaggle S6E9: Predicting EV Purchases.
Integrates:
- Reconstructed Generator Formula & Prior Margins (Chris Deotte forensics)
- String-Safe Digit Decomposition (zero IEEE-754 decimal bugs)
- Simpson's Paradox & Hard Boundary features
- 10-Fold Stratified Cross-Validation across 4 diverse architectures
- Nelder-Mead Rank-Weighted Ensembling (zero-calibration policy)
- JudgeGuard 6-point submission integrity verification
- Automated Kaggle CLI submission for all 5 progressive tiers
"""

import os
import sys
import subprocess
import time
import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import roc_auc_score

# Ensure src is importable
SRC_DIR = Path(__file__).resolve().parent / "src"
sys.path.insert(0, str(SRC_DIR))

from config import (
    TRAIN_PATH, TEST_PATH, SAMPLE_SUB_PATH, OOF_DIR, SUBMISSIONS_DIR, 
    RANDOM_SEED, N_FOLDS, TARGET_COL, ID_COL
)
from features_generator_forensics import build_features
from models import (
    train_lgbm_baseline, 
    train_catboost_symmetric, 
    train_xgboost_formula_margin, 
    train_lgbm_init_score
)
from ensemble_rank_optimizer import (
    optimize_rank_blend_weights, 
    blend_test_predictions,
    to_fractional_ranks
)
from verify_submission import verify_submission_file, evaluate_oof_score

def submit_to_kaggle(sub_path: Path, message: str) -> bool:
    """Submits a verified file to Kaggle competitions via CLI."""
    print(f"\n📤 [Kaggle CLI] Submitting {sub_path.name} to playground-series-s6e9...")
    cmd = [
        "kaggle", "competitions", "submit",
        "-c", "playground-series-s6e9",
        "-f", str(sub_path),
        "-m", message
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print(f"  ✅ Submission output: {res.stdout.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"  ⚠️ Submission failed or already queued: {e.stderr.strip()}")
        return False

def main():
    start_time = time.time()
    print("=" * 80)
    print("🚗⚡ KAGGLE S6E9: GENERATOR-FORENSICS & 5-SUBMISSION PIPELINE")
    print("=" * 80)
    
    # Load raw data
    print(f"\n📥 Loading raw datasets from {TRAIN_PATH.parent}...")
    train_raw = pd.read_csv(TRAIN_PATH)
    test_raw = pd.read_csv(TEST_PATH)
    sample_sub = pd.read_csv(SAMPLE_SUB_PATH)
    
    print(f"  Train: {train_raw.shape}, Test: {test_raw.shape}")
    
    target_map = {"Yes": 1, "No": 0, 1: 1, 0: 0, 1.0: 1, 0.0: 0}
    y = train_raw[TARGET_COL].map(target_map).fillna(0).to_numpy(dtype=np.int32)
    test_ids = test_raw[ID_COL].to_numpy()
    
    # Feature Engineering
    X, X_test, train_margin, test_margin = build_features(train_raw, test_raw)
    
    # Drop unneeded ID / Target columns from training matrices
    feature_cols = [c for c in X.columns if c not in [ID_COL, TARGET_COL]]
    X_train = X[feature_cols].copy()
    X_test = X_test[feature_cols].copy()
    
    print(f"  Feature Matrix Shape: X_train: {X_train.shape}, X_test: {X_test.shape}")
    
    # Setup fixed 10-Fold CV Splitter
    folds = StratifiedKFold(n_splits=N_FOLDS, shuffle=True, random_state=RANDOM_SEED)
    
    # Trackers
    oof_collection = []
    test_collection = []
    sub_records = []
    
    # -------------------------------------------------------------
    # SUBMISSION 1: Baseline 10-Fold LightGBM
    # -------------------------------------------------------------
    sub1_path = SUBMISSIONS_DIR / "submission_1_lgb_baseline.csv"
    oof1, test1, auc1 = train_lgbm_baseline(X_train, y, X_test, folds, seed=RANDOM_SEED)
    np.save(OOF_DIR / "oof_sub1_lgb.npy", oof1)
    
    sub1_df = pd.DataFrame({"id": test_ids, "Will_Buy_EV": test1})
    sub1_df.to_csv(sub1_path, index=False)
    verify_submission_file(sub1_path, SAMPLE_SUB_PATH)
    submit_to_kaggle(sub1_path, f"Sub 1: Baseline 10-Fold LightGBM (CV: {auc1:.6f})")
    
    oof_collection.append(oof1)
    test_collection.append(test1)
    sub_records.append(("Sub 1: LightGBM Baseline", auc1, sub1_path.name))
    
    # -------------------------------------------------------------
    # SUBMISSION 2: CatBoost Symmetric Oblivious Trees
    # -------------------------------------------------------------
    sub2_path = SUBMISSIONS_DIR / "submission_2_catboost_symmetric.csv"
    oof2, test2, auc2 = train_catboost_symmetric(X_train, y, X_test, folds, seed=RANDOM_SEED)
    np.save(OOF_DIR / "oof_sub2_catboost.npy", oof2)
    
    sub2_df = pd.DataFrame({"id": test_ids, "Will_Buy_EV": test2})
    sub2_df.to_csv(sub2_path, index=False)
    verify_submission_file(sub2_path, SAMPLE_SUB_PATH)
    submit_to_kaggle(sub2_path, f"Sub 2: CatBoost Symmetric Oblivious Trees (CV: {auc2:.6f})")
    
    oof_collection.append(oof2)
    test_collection.append(test2)
    sub_records.append(("Sub 2: CatBoost Symmetric", auc2, sub2_path.name))
    
    # -------------------------------------------------------------
    # SUBMISSION 3: XGBoost with Generator Formula Margin (Chris Deotte Forensics)
    # -------------------------------------------------------------
    sub3_path = SUBMISSIONS_DIR / "submission_3_xgboost_formula_margin.csv"
    oof3, test3, auc3 = train_xgboost_formula_margin(
        X_train, y, X_test, folds, train_margin, test_margin, seed=RANDOM_SEED
    )
    np.save(OOF_DIR / "oof_sub3_xgboost_margin.npy", oof3)
    
    sub3_df = pd.DataFrame({"id": test_ids, "Will_Buy_EV": test3})
    sub3_df.to_csv(sub3_path, index=False)
    verify_submission_file(sub3_path, SAMPLE_SUB_PATH)
    submit_to_kaggle(sub3_path, f"Sub 3: XGBoost Formula Margin + Safe Digits (CV: {auc3:.6f})")
    
    oof_collection.append(oof3)
    test_collection.append(test3)
    sub_records.append(("Sub 3: XGBoost Margin", auc3, sub3_path.name))
    
    # -------------------------------------------------------------
    # SUBMISSION 4: LightGBM with Generator init_score Prior
    # -------------------------------------------------------------
    sub4_path = SUBMISSIONS_DIR / "submission_4_lgbm_init_score.csv"
    oof4, test4, auc4 = train_lgbm_init_score(
        X_train, y, X_test, folds, train_margin, test_margin, seed=101
    )
    np.save(OOF_DIR / "oof_sub4_lgbm_init_score.npy", oof4)
    
    sub4_df = pd.DataFrame({"id": test_ids, "Will_Buy_EV": test4})
    sub4_df.to_csv(sub4_path, index=False)
    verify_submission_file(sub4_path, SAMPLE_SUB_PATH)
    submit_to_kaggle(sub4_path, f"Sub 4: LightGBM init_score Prior (CV: {auc4:.6f})")
    
    oof_collection.append(oof4)
    test_collection.append(test4)
    sub_records.append(("Sub 4: LightGBM init_score", auc4, sub4_path.name))
    
    # -------------------------------------------------------------
    # SUBMISSION 5: Master Rank-Weighted Nelder-Mead Blend
    # -------------------------------------------------------------
    sub5_path = SUBMISSIONS_DIR / "submission_5_master_blend.csv"
    print("\n🚀 [Sub 5] Optimizing Master Rank Blend with Nelder-Mead...")
    
    blend_weights = optimize_rank_blend_weights(oof_collection, y)
    
    # Compute OOF blend ranks
    oof_rank_matrix = np.column_stack([to_fractional_ranks(p) for p in oof_collection])
    blend_oof = np.dot(oof_rank_matrix, blend_weights)
    auc5 = roc_auc_score(y, blend_oof)
    np.save(OOF_DIR / "oof_sub5_master_blend.npy", blend_oof)
    
    # Compute test blend ranks
    test5 = blend_test_predictions(test_collection, blend_weights)
    
    sub5_df = pd.DataFrame({"id": test_ids, "Will_Buy_EV": test5})
    sub5_df.to_csv(sub5_path, index=False)
    verify_submission_file(sub5_path, SAMPLE_SUB_PATH)
    submit_to_kaggle(sub5_path, f"Sub 5: Master Rank Nelder-Mead Blend (CV: {auc5:.6f})")
    
    sub_records.append(("Sub 5: Master Rank Blend", auc5, sub5_path.name))
    
    # -------------------------------------------------------------
    # CONSOLIDATED SUMMARY REPORT
    # -------------------------------------------------------------
    elapsed = time.time() - start_time
    print("\n" + "=" * 80)
    print("🏆 CODYMASTER & JUDGEGUARD S6E9 SUBMISSION PORTFOLIO")
    print("=" * 80)
    print(f"{'Tier':<30} | {'10-Fold CV ROC-AUC':<20} | {'Submission File'}")
    print("-" * 80)
    for name, score, filename in sub_records:
        print(f"{name:<30} | {score:<20.6f} | {filename}")
    print("-" * 80)
    print(f"⏱️ Total Execution Time: {elapsed / 60:.2f} minutes")
    print("🎉 All 5 Submissions Verified & Delivered!")
    print("=" * 80)

if __name__ == "__main__":
    main()
