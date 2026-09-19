#!/usr/bin/env python3
"""
Kaggle Kernel: S6E9 Generator Forensics & 5-Submission Pipeline
Execution Platform: Kaggle Cloud GPU
Author: Kizabgd123 (CodyMaster & JudgeGuard Governance)
"""

import os
import sys
import time
import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import roc_auc_score
from scipy.optimize import minimize
from scipy.stats import rankdata

import lightgbm as lgb
import xgboost as xgb
from catboost import CatBoostClassifier

print("=" * 80)
print("🚗⚡ KAGGLE S6E9: GENERATOR-FORENSICS & 5-SUBMISSION PIPELINE (CLOUD GPU)")
print("=" * 80)

# Paths in Kaggle Environment
INPUT_DIR = Path("/kaggle/input/playground-series-s6e9")
ORIG_DIR = Path("/kaggle/input/ev-adoption-behavior-and-range-anxiety")
OUTPUT_DIR = Path("/kaggle/working")

TRAIN_PATH = INPUT_DIR / "train.csv"
TEST_PATH = INPUT_DIR / "test.csv"
SAMPLE_SUB_PATH = INPUT_DIR / "sample_submission.csv"

# Hyperparameters
RANDOM_SEED = 42
N_FOLDS = 10
TARGET_COL = "Will_Buy_EV"
ID_COL = "id"

# -------------------------------------------------------------
# 1. GENERATOR FORENSICS FEATURE ENGINEERING
# -------------------------------------------------------------
def compute_generator_utility(df: pd.DataFrame):
    """
    Reconstructs latent utility formula discovered by Chris Deotte & Fable 5.1:
    utility = 1.2 * (Income / 100,000) 
            + 0.6 * Environmental_Concern_Level 
            + 2.0 * Subsidy_Available (1 for Yes, 0 for No)
            - 1.0 * (Range_Anxiety == 'Medium')
            - 3.0 * (Range_Anxiety == 'High')
    Threshold ~ 5.5.
    """
    income_term = 1.2 * (df["Annual_Income_USD"].astype(float) / 100000.0)
    env_term = 0.6 * df["Environmental_Concern_Level"].astype(float)
    
    subsidy_flag = df["Subsidy_Available"].map({"Yes": 1.0, "No": 0.0, 1: 1.0, 0: 0.0, 1.0: 1.0, 0.0: 0.0}).fillna(0.0)
    subsidy_term = 2.0 * subsidy_flag
    
    anx_med = (df["Range_Anxiety_Level"].str.lower() == "medium").astype(float)
    anx_high = (df["Range_Anxiety_Level"].str.lower() == "high").astype(float)
    anxiety_term = -1.0 * anx_med - 3.0 * anx_high
    
    raw_utility = income_term + env_term + subsidy_term + anxiety_term
    net_utility = raw_utility - 5.5
    base_margin = np.clip(net_utility.values, -5.0, 5.0)
    return raw_utility.values, base_margin

def extract_string_safe_digits(df: pd.DataFrame, col: str, is_decimal: bool = False):
    str_series = df[col].astype(str)
    splits = str_series.str.split(".", expand=True)
    int_parts = splits[0].fillna("")
    
    digits_df = pd.DataFrame(index=df.index)
    for pos, power in enumerate([1, 2, 3, 4, 5]):
        digits_df[f"{col}_digit_10e{pos}"] = int_parts.str[-power:-power+1 if power > 1 else None].replace("", "0").astype(int)
    
    if is_decimal and splits.shape[1] > 1:
        dec_parts = splits[1].fillna("")
        for pos in range(3):
            digits_df[f"{col}_dec_10e_neg{pos+1}"] = dec_parts.str[pos:pos+1].replace("", "0").astype(int)
    return digits_df

def build_features(train_df: pd.DataFrame, test_df: pd.DataFrame):
    print("🛠️ [Feature Engineering] Building generator forensics feature set...")
    df_all = pd.concat([train_df.assign(is_test=0), test_df.assign(is_test=1)], ignore_index=True)
    
    train_util, train_margin = compute_generator_utility(train_df)
    test_util, test_margin = compute_generator_utility(test_df)
    
    df_all["formula_buy_score"], df_all["formula_margin"] = compute_generator_utility(df_all)
    df_all["formula_prob"] = 1.0 / (1.0 + np.exp(-df_all["formula_margin"]))
    
    print("  -> Extracting string-safe digit features...")
    income_digits = extract_string_safe_digits(df_all, "Annual_Income_USD", is_decimal=False)
    commute_digits = extract_string_safe_digits(df_all, "Daily_Commute_km", is_decimal=True)
    age_digits = extract_string_safe_digits(df_all, "Age", is_decimal=False)
    df_all = pd.concat([df_all, income_digits, commute_digits, age_digits], axis=1)
    
    print("  -> Creating Simpson's paradox interaction terms...")
    home_charging_num = df_all["Home_Charging_Possible"].map({"Yes": 1, "No": 0, 1: 1, 0: 0}).fillna(0).astype(int)
    subsidy_num = df_all["Subsidy_Available"].map({"Yes": 1, "No": 0, 1: 1, 0: 0}).fillna(0).astype(int)
    
    df_all["chargers_total"] = df_all["Charging_Stations_Near_Home"] + df_all["Charging_Stations_Near_Work"]
    df_all["chargers_diff"] = df_all["Charging_Stations_Near_Home"] - df_all["Charging_Stations_Near_Work"]
    df_all["home_charge_x_home_stations"] = home_charging_num * df_all["Charging_Stations_Near_Home"]
    df_all["home_charge_x_total_stations"] = home_charging_num * df_all["chargers_total"]
    
    df_all["commute_to_chargers_ratio"] = df_all["Daily_Commute_km"] / (df_all["chargers_total"] + 1.0)
    df_all["income_to_commute_ratio"] = df_all["Annual_Income_USD"] / (df_all["Daily_Commute_km"] + 1.0)
    df_all["income_x_subsidy"] = df_all["Annual_Income_USD"] * subsidy_num
    
    print("  -> Encoding deterministic bounds and generator cluster spikes...")
    df_all["is_income_above_170537"] = (df_all["Annual_Income_USD"] >= 170537.0).astype(int)
    df_all["is_income_30k_spike"] = (df_all["Annual_Income_USD"] == 30000.0).astype(int)
    df_all["is_commute_5km_cluster"] = ((df_all["Daily_Commute_km"] >= 4.8) & (df_all["Daily_Commute_km"] <= 5.2)).astype(int)
    df_all["is_commute_83km_cluster"] = ((df_all["Daily_Commute_km"] >= 82.8) & (df_all["Daily_Commute_km"] <= 83.2)).astype(int)
    
    commute_rounded = df_all["Daily_Commute_km"].round(1)
    df_all["commute_rounded_freq"] = commute_rounded.map(commute_rounded.value_counts(normalize=True))
    
    income_rounded_10k = (df_all["Annual_Income_USD"] // 10000) * 10000
    df_all["income_10k_freq"] = income_rounded_10k.map(income_rounded_10k.value_counts(normalize=True))
    
    print("  -> Encoding categoricals and interactions...")
    anxiety_map = {"Low": 0, "Medium": 1, "High": 2}
    df_all["range_anxiety_ordinal"] = df_all["Range_Anxiety_Level"].map(anxiety_map).fillna(1).astype(int)
    
    cat_cols_to_encode = ["Gender", "City_Type", "Current_Car_Type", "Home_Charging_Possible", "Subsidy_Available"]
    for c in cat_cols_to_encode:
        df_all[c] = df_all[c].astype("category").cat.codes
        
    df_all["city_x_home_charge"] = (df_all["City_Type"].astype(str) + "_" + df_all["Home_Charging_Possible"].astype(str)).astype("category").cat.codes
    df_all["city_x_anxiety"] = (df_all["City_Type"].astype(str) + "_" + df_all["range_anxiety_ordinal"].astype(str)).astype("category").cat.codes
    
    if "Range_Anxiety_Level" in df_all.columns:
        df_all = df_all.drop(columns=["Range_Anxiety_Level"])
        
    train_feats = df_all[df_all["is_test"] == 0].drop(columns=["is_test"]).copy()
    test_feats = df_all[df_all["is_test"] == 1].drop(columns=["is_test", "Will_Buy_EV"], errors="ignore").copy()
    
    print(f"✅ Total features: {train_feats.shape[1] - 2}")
    return train_feats, test_feats, train_margin, test_margin

# -------------------------------------------------------------
# 2. ENSEMBLING UTILITIES (Zero Calibration Policy)
# -------------------------------------------------------------
def to_fractional_ranks(preds: np.ndarray) -> np.ndarray:
    return (rankdata(preds) - 1.0) / (len(preds) - 1.0)

def optimize_rank_blend_weights(oof_predictions, y_true):
    n_models = len(oof_predictions)
    rank_matrix = np.column_stack([to_fractional_ranks(p) for p in oof_predictions])
    
    def loss_func(weights):
        w = np.maximum(weights, 0.0)
        if np.sum(w) == 0:
            return 0.0
        w = w / np.sum(w)
        blend_ranks = np.dot(rank_matrix, w)
        return -roc_auc_score(y_true, blend_ranks)
    
    init_weights = np.ones(n_models) / n_models
    res = minimize(loss_func, init_weights, method="Nelder-Mead", options={"maxiter": 500, "disp": False})
    best_w = np.maximum(res.x, 0.0)
    best_w = best_w / np.sum(best_w)
    return best_w

# -------------------------------------------------------------
# MAIN CLOUD EXECUTION
# -------------------------------------------------------------
def main():
    start_time = time.time()
    
    print(f"\n📥 Loading raw datasets...")
    train_raw = pd.read_csv(TRAIN_PATH)
    test_raw = pd.read_csv(TEST_PATH)
    sample_sub = pd.read_csv(SAMPLE_SUB_PATH)
    
    print(f"  Train: {train_raw.shape}, Test: {test_raw.shape}")
    
    target_map = {"Yes": 1, "No": 0, 1: 1, 0: 0, 1.0: 1, 0.0: 0}
    y = train_raw[TARGET_COL].map(target_map).fillna(0).to_numpy(dtype=np.int32)
    test_ids = test_raw[ID_COL].to_numpy()
    
    X, X_test, train_margin, test_margin = build_features(train_raw, test_raw)
    
    feature_cols = [c for c in X.columns if c not in [ID_COL, TARGET_COL]]
    X_train = X[feature_cols].copy()
    X_test = X_test[feature_cols].copy()
    
    folds = StratifiedKFold(n_splits=N_FOLDS, shuffle=True, random_state=RANDOM_SEED)
    
    oof_collection = []
    test_collection = []
    sub_records = []
    
    # ---------------------------------------------------------
    # MODEL 1: Baseline 10-Fold LightGBM
    # ---------------------------------------------------------
    print("\n🚀 [Sub 1] Training Baseline 10-Fold LightGBM...")
    oof1 = np.zeros(len(X_train))
    test1 = np.zeros(len(X_test))
    params_lgb1 = {
        "objective": "binary", "metric": "auc", "boosting_type": "gbdt",
        "learning_rate": 0.05, "num_leaves": 63, "colsample_bytree": 0.75,
        "subsample": 0.8, "random_state": RANDOM_SEED, "n_jobs": -1, "verbose": -1
    }
    for fold, (trn_idx, val_idx) in enumerate(folds.split(X_train, y)):
        X_tr, y_tr = X_train.iloc[trn_idx], y[trn_idx]
        X_va, y_va = X_train.iloc[val_idx], y[val_idx]
        trn_data = lgb.Dataset(X_tr, label=y_tr)
        val_data = lgb.Dataset(X_va, label=y_va, reference=trn_data)
        model = lgb.train(params_lgb1, trn_data, num_boost_round=1200, valid_sets=[trn_data, val_data],
                          callbacks=[lgb.early_stopping(50, verbose=False), lgb.log_evaluation(0)])
        val_pred = model.predict(X_va)
        oof1[val_idx] = val_pred
        test1 += model.predict(X_test) / N_FOLDS
        print(f"  Fold {fold + 1}/{N_FOLDS} AUC: {roc_auc_score(y_va, val_pred):.6f}")
        
    auc1 = roc_auc_score(y, oof1)
    print(f"✅ Sub 1 Overall 10-Fold CV AUC: {auc1:.6f}")
    sub1_path = OUTPUT_DIR / "submission_1_lgb_baseline.csv"
    pd.DataFrame({"id": test_ids, "Will_Buy_EV": test1}).to_csv(sub1_path, index=False)
    oof_collection.append(oof1)
    test_collection.append(test1)
    sub_records.append(("Sub 1: LightGBM Baseline", auc1, sub1_path.name))
    
    # ---------------------------------------------------------
    # MODEL 2: CatBoost Oblivious Symmetric Trees
    # ---------------------------------------------------------
    print("\n🚀 [Sub 2] Training CatBoost Symmetric Trees (10-Fold)...")
    oof2 = np.zeros(len(X_train))
    test2 = np.zeros(len(X_test))
    # Detect GPU for CatBoost
    cb_task_type = "GPU" if os.environ.get("CUDA_VISIBLE_DEVICES") != "" else "CPU"
    for fold, (trn_idx, val_idx) in enumerate(folds.split(X_train, y)):
        X_tr, y_tr = X_train.iloc[trn_idx], y[trn_idx]
        X_va, y_va = X_train.iloc[val_idx], y[val_idx]
        cb = CatBoostClassifier(iterations=1200, learning_rate=0.06, depth=6, eval_metric="AUC",
                                random_seed=RANDOM_SEED + fold, task_type=cb_task_type, verbose=0, early_stopping_rounds=50)
        cb.fit(X_tr, y_tr, eval_set=(X_va, y_va), verbose=False)
        val_pred = cb.predict_proba(X_va)[:, 1]
        oof2[val_idx] = val_pred
        test2 += cb.predict_proba(X_test)[:, 1] / N_FOLDS
        print(f"  Fold {fold + 1}/{N_FOLDS} AUC: {roc_auc_score(y_va, val_pred):.6f}")
        
    auc2 = roc_auc_score(y, oof2)
    print(f"✅ Sub 2 Overall 10-Fold CV AUC: {auc2:.6f}")
    sub2_path = OUTPUT_DIR / "submission_2_catboost_symmetric.csv"
    pd.DataFrame({"id": test_ids, "Will_Buy_EV": test2}).to_csv(sub2_path, index=False)
    oof_collection.append(oof2)
    test_collection.append(test2)
    sub_records.append(("Sub 2: CatBoost Symmetric", auc2, sub2_path.name))
    
    # ---------------------------------------------------------
    # MODEL 3: XGBoost with base_margin Prior (GPU Hist)
    # ---------------------------------------------------------
    print("\n🚀 [Sub 3] Training XGBoost with Generator base_margin Prior (GPU)...")
    oof3 = np.zeros(len(X_train))
    test3 = np.zeros(len(X_test))
    
    # Use GPU device if available
    xgb_params = {
        "objective": "binary:logistic", "eval_metric": "auc", "tree_method": "hist",
        "device": "cuda", "learning_rate": 0.05, "max_depth": 6,
        "colsample_bytree": 0.75, "subsample": 0.85, "random_state": RANDOM_SEED, "nthread": -1
    }
    dtest = xgb.DMatrix(X_test, base_margin=test_margin)
    for fold, (trn_idx, val_idx) in enumerate(folds.split(X_train, y)):
        dtrain = xgb.DMatrix(X_train.iloc[trn_idx], label=y[trn_idx], base_margin=train_margin[trn_idx])
        dval = xgb.DMatrix(X_train.iloc[val_idx], label=y[val_idx], base_margin=train_margin[val_idx])
        bst = xgb.train(xgb_params, dtrain, num_boost_round=1200, evals=[(dtrain, "train"), (dval, "val")],
                        early_stopping_rounds=50, verbose_eval=False)
        val_pred = bst.predict(dval)
        oof3[val_idx] = val_pred
        test3 += bst.predict(dtest) / N_FOLDS
        print(f"  Fold {fold + 1}/{N_FOLDS} AUC: {roc_auc_score(y[val_idx], val_pred):.6f}")
        
    auc3 = roc_auc_score(y, oof3)
    print(f"✅ Sub 3 Overall 10-Fold CV AUC: {auc3:.6f}")
    sub3_path = OUTPUT_DIR / "submission_3_xgboost_formula_margin.csv"
    pd.DataFrame({"id": test_ids, "Will_Buy_EV": test3}).to_csv(sub3_path, index=False)
    oof_collection.append(oof3)
    test_collection.append(test3)
    sub_records.append(("Sub 3: XGBoost Margin", auc3, sub3_path.name))
    
    # ---------------------------------------------------------
    # MODEL 4: LightGBM with Generator init_score Prior
    # ---------------------------------------------------------
    print("\n🚀 [Sub 4] Training LightGBM with Generator init_score Prior...")
    oof4 = np.zeros(len(X_train))
    test4 = np.zeros(len(X_test))
    params_lgb4 = {
        "objective": "binary", "metric": "auc", "boosting_type": "gbdt",
        "learning_rate": 0.04, "num_leaves": 45, "max_depth": 7,
        "colsample_bytree": 0.70, "subsample": 0.85, "random_state": 101, "n_jobs": -1, "verbose": -1
    }
    for fold, (trn_idx, val_idx) in enumerate(folds.split(X_train, y)):
        X_tr, y_tr = X_train.iloc[trn_idx], y[trn_idx]
        X_va, y_va = X_train.iloc[val_idx], y[val_idx]
        trn_data = lgb.Dataset(X_tr, label=y_tr, init_score=train_margin[trn_idx])
        val_data = lgb.Dataset(X_va, label=y_va, reference=trn_data, init_score=train_margin[val_idx])
        model = lgb.train(params_lgb4, trn_data, num_boost_round=1200, valid_sets=[trn_data, val_data],
                          callbacks=[lgb.early_stopping(50, verbose=False), lgb.log_evaluation(0)])
        val_raw = model.predict(X_va, raw_score=True) + train_margin[val_idx]
        val_pred = 1.0 / (1.0 + np.exp(-val_raw))
        oof4[val_idx] = val_pred
        
        test_raw = model.predict(X_test, raw_score=True) + test_margin
        test_pred = 1.0 / (1.0 + np.exp(-test_raw))
        test4 += test_pred / N_FOLDS
        print(f"  Fold {fold + 1}/{N_FOLDS} AUC: {roc_auc_score(y_va, val_pred):.6f}")
        
    auc4 = roc_auc_score(y, oof4)
    print(f"✅ Sub 4 Overall 10-Fold CV AUC: {auc4:.6f}")
    sub4_path = OUTPUT_DIR / "submission_4_lgbm_init_score.csv"
    pd.DataFrame({"id": test_ids, "Will_Buy_EV": test4}).to_csv(sub4_path, index=False)
    oof_collection.append(oof4)
    test_collection.append(test4)
    sub_records.append(("Sub 4: LightGBM init_score", auc4, sub4_path.name))
    
    # ---------------------------------------------------------
    # MODEL 5: Master Rank-Weighted Nelder-Mead Blend
    # ---------------------------------------------------------
    print("\n🚀 [Sub 5] Optimizing Master Rank Blend with Nelder-Mead...")
    blend_weights = optimize_rank_blend_weights(oof_collection, y)
    print(f"  Optimal Weights: {np.round(blend_weights, 4)}")
    
    oof_rank_matrix = np.column_stack([to_fractional_ranks(p) for p in oof_collection])
    blend_oof = np.dot(oof_rank_matrix, blend_weights)
    auc5 = roc_auc_score(y, blend_oof)
    print(f"🏆 Sub 5 Master Blend 10-Fold CV AUC: {auc5:.6f}")
    
    test_rank_matrix = np.column_stack([to_fractional_ranks(p) for p in test_collection])
    test5 = np.dot(test_rank_matrix, blend_weights)
    
    sub5_path = OUTPUT_DIR / "submission_5_master_blend.csv"
    pd.DataFrame({"id": test_ids, "Will_Buy_EV": test5}).to_csv(sub5_path, index=False)
    sub_records.append(("Sub 5: Master Rank Blend", auc5, sub5_path.name))
    
    # ---------------------------------------------------------
    # SUMMARY
    # ---------------------------------------------------------
    elapsed = time.time() - start_time
    print("\n" + "=" * 80)
    print("🏆 KAGGLE S6E9: ALL 5 SUBMISSION FILES CREATED IN /kaggle/working/")
    print("=" * 80)
    for name, score, filename in sub_records:
        print(f"{name:<30} | {score:<20.6f} | {filename}")
    print("-" * 80)
    print(f"⏱️ Total Cloud GPU Execution Time: {elapsed / 60:.2f} minutes")
    print("=" * 80)

if __name__ == "__main__":
    main()
