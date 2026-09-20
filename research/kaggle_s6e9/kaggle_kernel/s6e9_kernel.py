#!/usr/bin/env python3
"""
Kaggle Kernel: S6E9 Top-10 Assault Pipeline (Submissions 11 through 15)
Target: Break >=0.94660 into Public Leaderboard Top 10

Key Enhancements over Submissions 6-10:
1. Fix IEEE-754 bug: string/integer digit extraction on Annual_Income_USD only (k=0..5).
2. Pruned noisy digit decompositions (Age, commute fractional digits, count columns).
3. 10-Fold Stratified K-Fold CV (upgraded from 5-fold to eliminate test estimation noise).
4. Deotte Latent Utility Formula as base_margin (XGBoost) and init_score (LightGBM).
5. High-resolution numerical binning (max_bin=1024).
6. In-Fold Multi-Scale Target Encoding (auto, 10, 100).
7. Multi-Seed Averaging across Seeds 42 & 101.
8. Nelder-Mead Rank-Space Ensembling on OOF ROC-AUC.
9. Deterministic Physics Boundary Corrections & Zero-Tie Ordinal Sorting.
10. Output 5 progressive submission files (Submissions 11 through 15).

Platform: Kaggle Cloud GPU (CUDA)
"""

import os
import sys
import time
import warnings
import numpy as np
import pandas as pd
from pathlib import Path
from scipy.stats import norm, rankdata
from scipy.optimize import minimize
from scipy.special import expit
from sklearn.model_selection import StratifiedKFold
from sklearn.preprocessing import TargetEncoder
from sklearn.metrics import roc_auc_score

import xgboost as xgb
import lightgbm as lgb
from catboost import CatBoostClassifier

warnings.filterwarnings('ignore')

print("=" * 80)
print("🚀⚡ KAGGLE S6E9: TOP-10 ASSAULT (10-FOLD MULTI-SEED 5-SUBMISSION PIPELINE)")
print("=" * 80)

# Detect runtime environment
IN_KAGGLE = os.path.exists("/kaggle")
OUTPUT_DIR = Path("/kaggle/working") if IN_KAGGLE else Path(__file__).resolve().parent

# Check GPU availability
try:
    import torch
    HAS_CUDA = torch.cuda.is_available()
except ImportError:
    HAS_CUDA = False

XGB_DEVICE = "cuda" if HAS_CUDA else "cpu"
CAT_TASK = "GPU" if HAS_CUDA else "CPU"
print(f"🔧 Device Configuration: CUDA={HAS_CUDA} | XGBoost Device='{XGB_DEVICE}' | CatBoost Task='{CAT_TASK}'")

# -------------------------------------------------------------
# 1. INPUT LOCATOR & DATA INGESTION
# -------------------------------------------------------------
def find_input_file(name: str) -> Path:
    print(f"🔍 Searching for '{name}' in /kaggle/input...")
    for root, dirs, files in os.walk("/kaggle/input"):
        if name in files:
            p = Path(root) / name
            print(f"  -> Found: {p}")
            return p
    for root, dirs, files in os.walk("/kaggle"):
        if name in files:
            p = Path(root) / name
            print(f"  -> Found in /kaggle: {p}")
            return p
    # Fallback to local data dir if not on Kaggle
    local_p = Path(__file__).resolve().parent.parent / "data" / name
    if local_p.exists():
        return local_p
    raise FileNotFoundError(f"Could not locate '{name}' in environment!")

TRAIN_PATH = find_input_file("train.csv")
TEST_PATH = find_input_file("test.csv")
SAMPLE_SUB_PATH = find_input_file("sample_submission.csv")

try:
    ORIG_PATH = find_input_file("EV_Adoption_and_Range_Anxiety_Dataset.csv")
except FileNotFoundError:
    try:
        ORIG_PATH = find_input_file("ev_adoption_behavior.csv")
    except FileNotFoundError:
        ORIG_PATH = None

print(f"📊 Loading Train: {TRAIN_PATH}")
train = pd.read_csv(TRAIN_PATH)
print(f"📊 Loading Test: {TEST_PATH}")
test = pd.read_csv(TEST_PATH)
sample_sub = pd.read_csv(SAMPLE_SUB_PATH)

if ORIG_PATH is not None:
    print(f"📊 Loading Original Dataset: {ORIG_PATH}")
    orig = pd.read_csv(ORIG_PATH)
else:
    print("⚠️ Original dataset not found, using sampled train for priors.")
    orig = train.sample(frac=0.1, random_state=42).copy()

TARGET = 'Will_Buy_EV'
train[TARGET] = train[TARGET].map({'Yes': 1, 'No': 0, 1: 1, 0: 0})
orig[TARGET] = orig[TARGET].map({'Yes': 1, 'No': 0, 1: 1, 0: 0})

train_id = train['id'].copy()
test_id = test['id'].copy()

# -------------------------------------------------------------
# 2. CHRIS DEOTTE LATENT RECIPE PRIOR (BASE_MARGIN / INIT_SCORE)
# -------------------------------------------------------------
def compute_recipe_prior(df: pd.DataFrame):
    """
    Computes exact latent utility from reverse-engineered generator:
    score = 1.2 * Income/1e5 + 0.6 * EnvConcern + 2.0 * Subsidy - 1.0 * MedAnxiety - 3.0 * HighAnxiety
    p = Phi(score - 5.5)
    logit = log(p / (1 - p))
    """
    income = df["Annual_Income_USD"].astype(float) / 100000.0
    env = df["Environmental_Concern_Level"].astype(float)
    subsidy = (df["Subsidy_Available"] == "Yes").astype(float)
    med_anxiety = (df["Range_Anxiety_Level"] == "Medium").astype(float)
    high_anxiety = (df["Range_Anxiety_Level"] == "High").astype(float)

    score = 1.2 * income + 0.6 * env + 2.0 * subsidy - 1.0 * med_anxiety - 3.0 * high_anxiety
    p = np.clip(norm.cdf(score.values - 5.5), 1e-6, 1.0 - 1e-6)
    logit = np.log(p / (1.0 - p))
    return score.values, logit

score_train, margin_train = compute_recipe_prior(train)
score_test, margin_test = compute_recipe_prior(test)

raw_recipe_auc = roc_auc_score(train[TARGET], score_train)
print(f"🔬 Chris Deotte Latent Recipe Standalone ROC-AUC: {raw_recipe_auc:.5f}")

# -------------------------------------------------------------
# 3. FEATURE ENGINEERING: CLEAN INTEGER DIGITS & DOMAIN INTERACTIONS
# -------------------------------------------------------------
print("\n🛠️ Constructing Feature Space (Clean Digits, Interactions, Markus Keys)...")

train['is_train'] = 1
test['is_train'] = 0
test[TARGET] = np.nan
combined = pd.concat([train, test], ignore_index=True)

# Drop zero-importance column
combined.drop(columns=['Number_of_Cars_Owned'], inplace=True, errors='ignore')

# Domain physics & generator interaction features
home = (combined['Home_Charging_Possible'] == "Yes").astype(int)
subsidy = (combined['Subsidy_Available'] == "Yes").astype(int)

combined["worry_score"] = (
    combined['Daily_Commute_km'] 
    - 5.0 * combined['Charging_Stations_Near_Home'] 
    - 5.0 * combined['Charging_Stations_Near_Work'] 
    - 150.0 * home
)
combined["chargers_total"] = combined['Charging_Stations_Near_Home'] + combined['Charging_Stations_Near_Work']
combined["income_x_subsidy"] = (combined['Annual_Income_USD'] / 1e5) * subsidy
combined["concern_x_subsidy"] = combined['Environmental_Concern_Level'] * subsidy
combined["recipe_score"] = np.concatenate([score_train, score_test])

# Deterministic boundary indicators
combined["is_millionaire_cliff"] = (combined['Annual_Income_USD'] >= 170537.0).astype('int8')
combined["is_dead_zone"] = (
    (combined['Annual_Income_USD'] >= 31004.0) & (combined['Annual_Income_USD'] <= 41970.0)
).astype('int8')
combined["is_commute_cliff"] = (combined['Daily_Commute_km'] >= 83.0).astype('int8')
combined["is_30k_spike"] = (combined['Annual_Income_USD'] == 30000.0).astype('int8')

# Clean Integer Digit Decomposition for Annual_Income_USD (k=0..5)
# Eliminates IEEE-754 float division bug completely
income_ints = combined['Annual_Income_USD'].fillna(0).round().astype(np.int64)
digit_cols = []
for k in range(6):
    col_name = f"Annual_Income_USD_digit{k}"
    combined[col_name] = ((income_ints // (10**k)) % 10).astype('int8')
    digit_cols.append(col_name)

# Integer commute digits (0..2)
commute_ints = combined['Daily_Commute_km'].fillna(0).round().astype(np.int64)
for k in range(3):
    col_name = f"Daily_Commute_km_digit{k}"
    combined[col_name] = ((commute_ints // (10**k)) % 10).astype('int8')
    digit_cols.append(col_name)

cat_cols = combined.select_dtypes(include=['object', 'string']).columns.tolist()
num_cols = [c for c in combined.columns if c not in cat_cols + ['id', 'is_train', TARGET]]

# Map original dataset target means
orig_global_mean = float(orig[TARGET].mean())
for col in cat_cols + ['Annual_Income_USD', 'Daily_Commute_km']:
    if col in orig.columns:
        real_world_stats = orig.groupby(col, observed=False)[TARGET].mean()
        combined[f"{col}_org_mean"] = combined[col].map(real_world_stats).fillna(orig_global_mean).astype(float)

# Markus's Smooth Keys (binned numerics for categorical frequency encoding)
combined['income_exact_int'] = income_ints.astype(str)
combined['income100_floor']  = (income_ints // 100).astype(str)
combined['income1000_floor'] = (income_ints // 1000).astype(str)
combined['commute_integer']  = commute_ints.astype(str)

encode_cats = cat_cols + ['income_exact_int', 'income100_floor', 'income1000_floor', 'commute_integer'] + digit_cols

# Global Frequency Encoding
for col in encode_cats:
    freq_mapping = combined[col].value_counts(normalize=True).to_dict()
    combined[f"{col}_fe"] = combined[col].map(freq_mapping).astype(float).fillna(0.0)

# Separate back to train and test
train_proc = combined[combined['is_train'] == 1].drop(columns=['is_train'])
test_proc = combined[combined['is_train'] == 0].drop(columns=['is_train', TARGET])

# Drop constant or duplicated features
eval_cols = [c for c in train_proc.columns if c not in ['id', TARGET] and pd.api.types.is_numeric_dtype(train_proc[c])]
to_drop_const = [c for c in train_proc.columns if train_proc[c].nunique() == 1] + [c for c in test_proc.columns if test_proc[c].nunique() == 1]
DROP = list(set(to_drop_const))
DROP = [c for c in DROP if c not in ['id', TARGET]]

if DROP:
    print(f"✂️ Dropping {len(DROP)} constant features: {DROP}")
    train_proc.drop(columns=DROP, inplace=True, errors='ignore')
    test_proc.drop(columns=DROP, inplace=True, errors='ignore')

FEATURES = [c for c in test_proc.columns if c != 'id']
TARGET_ENCODE_COLS = [c for c in encode_cats if c in train_proc.columns and c not in DROP]

print(f"✅ Total Base Features: {len(FEATURES)}")
print(f"✅ Columns to Target Encode: {len(TARGET_ENCODE_COLS)}")

# -------------------------------------------------------------
# 4. CROSS-VALIDATION ENCODING & PREPARATION (10 FOLDS)
# -------------------------------------------------------------
FOLDS = 10
print(f"\n🔄 Running {FOLDS}-Fold Stratified Split and Triple Target Encoding...")
skf = StratifiedKFold(n_splits=FOLDS, shuffle=True, random_state=42)

X_raw = train_proc[FEATURES].copy()
y = train_proc[TARGET].values
X_test_raw = test_proc[FEATURES].copy()

fold_datasets = []

for fold, (train_idx, valid_idx) in enumerate(skf.split(X_raw, y), 1):
    print(f"  -> Processing Fold {fold}/{FOLDS} Triple TE...")
    X_train_f = X_raw.iloc[train_idx].copy()
    y_train_f = y[train_idx]
    X_valid_f = X_raw.iloc[valid_idx].copy()
    y_valid_f = y[valid_idx]
    X_test_f = X_test_raw.copy()

    # Triple Target Encoders (Auto, Strict 10, Massive 100)
    te_auto = TargetEncoder(smooth='auto', cv=FOLDS, random_state=42)
    te_10   = TargetEncoder(smooth=10.0, cv=FOLDS, random_state=42)
    te_100  = TargetEncoder(smooth=100.0, cv=FOLDS, random_state=42)

    X_tr_enc_auto = te_auto.fit_transform(X_train_f[TARGET_ENCODE_COLS], y_train_f)
    X_va_enc_auto = te_auto.transform(X_valid_f[TARGET_ENCODE_COLS])
    X_te_enc_auto = te_auto.transform(X_test_f[TARGET_ENCODE_COLS])

    X_tr_enc_10 = te_10.fit_transform(X_train_f[TARGET_ENCODE_COLS], y_train_f)
    X_va_enc_10 = te_10.transform(X_valid_f[TARGET_ENCODE_COLS])
    X_te_enc_10 = te_10.transform(X_test_f[TARGET_ENCODE_COLS])

    X_tr_enc_100 = te_100.fit_transform(X_train_f[TARGET_ENCODE_COLS], y_train_f)
    X_va_enc_100 = te_100.transform(X_valid_f[TARGET_ENCODE_COLS])
    X_te_enc_100 = te_100.transform(X_test_f[TARGET_ENCODE_COLS])

    for i, col in enumerate(TARGET_ENCODE_COLS):
        X_train_f[f"{col}_TE_auto"] = X_tr_enc_auto[:, i].astype('float32')
        X_valid_f[f"{col}_TE_auto"] = X_va_enc_auto[:, i].astype('float32')
        X_test_f[f"{col}_TE_auto"] = X_te_enc_auto[:, i].astype('float32')

        X_train_f[f"{col}_TE_10"] = X_tr_enc_10[:, i].astype('float32')
        X_valid_f[f"{col}_TE_10"] = X_va_enc_10[:, i].astype('float32')
        X_test_f[f"{col}_TE_10"] = X_te_enc_10[:, i].astype('float32')

        X_train_f[f"{col}_TE_100"] = X_tr_enc_100[:, i].astype('float32')
        X_valid_f[f"{col}_TE_100"] = X_va_enc_100[:, i].astype('float32')
        X_test_f[f"{col}_TE_100"] = X_te_enc_100[:, i].astype('float32')

        X_train_f.drop(columns=[col], inplace=True, errors='ignore')
        X_valid_f.drop(columns=[col], inplace=True, errors='ignore')
        X_test_f.drop(columns=[col], inplace=True, errors='ignore')

    fold_datasets.append({
        'fold': fold,
        'train_idx': train_idx,
        'valid_idx': valid_idx,
        'X_train': X_train_f,
        'y_train': y_train_f,
        'X_valid': X_valid_f,
        'y_valid': y_valid_f,
        'X_test': X_test_f,
        'margin_train': margin_train[train_idx],
        'margin_valid': margin_train[valid_idx],
        'margin_test': margin_test
    })

print(f"✅ Prepared all {FOLDS} folds. Feature count per fold: {fold_datasets[0]['X_train'].shape[1]}")

# -------------------------------------------------------------
# 5. MODEL 1: REFINED 10-FOLD LIGHTGBM (INIT_SCORE) -> SUB 11
# -------------------------------------------------------------
print("\n" + "=" * 80)
print("💡 [MODEL 1 / SUB 11] Refined 10-Fold LightGBM + Recipe init_score (Target ~0.94648)")
print("=" * 80)

oof_sub11 = np.zeros(len(train))
test_sub11 = np.zeros(len(test))

lgb_params = {
    'objective': 'binary',
    'metric': 'auc',
    'boosting_type': 'gbdt',
    'learning_rate': 0.015,
    'num_leaves': 32,
    'max_depth': 5,
    'max_bin': 1024,
    'feature_fraction': 0.65,
    'bagging_fraction': 0.80,
    'bagging_freq': 1,
    'min_child_samples': 30,
    'lambda_l1': 0.5,
    'lambda_l2': 1.0,
    'verbosity': -1,
    'n_jobs': -1,
    'random_state': 42
}

for f_data in fold_datasets:
    fold = f_data['fold']
    X_tr, y_tr = f_data['X_train'], f_data['y_train']
    X_va, y_va = f_data['X_valid'], f_data['y_valid']
    X_te = f_data['X_test']
    m_tr, m_va, m_te = f_data['margin_train'], f_data['margin_valid'], f_data['margin_test']

    trn_data = lgb.Dataset(X_tr, label=y_tr, init_score=m_tr)
    val_data = lgb.Dataset(X_va, label=y_va, init_score=m_va, reference=trn_data)

    callbacks = [lgb.early_stopping(stopping_rounds=300, verbose=False), lgb.log_evaluation(period=0)]
    bst = lgb.train(
        lgb_params,
        trn_data,
        num_boost_round=8000,
        valid_sets=[val_data],
        callbacks=callbacks
    )

    va_raw = bst.predict(X_va, raw_score=True)
    te_raw = bst.predict(X_te, raw_score=True)

    va_prob = expit(m_va + va_raw)
    te_prob = expit(m_te + te_raw)

    oof_sub11[f_data['valid_idx']] = va_prob
    test_sub11 += te_prob / FOLDS

    f_auc = roc_auc_score(y_va, va_prob)
    print(f"  -> LGBM Fold {fold} ROC-AUC: {f_auc:.5f} (Best Iter: {bst.best_iteration})")

cv_sub11 = roc_auc_score(y, oof_sub11)
print(f"🏆 SUBMISSION 11 (10-Fold LightGBM) OOF ROC-AUC: {cv_sub11:.5f}")

# -------------------------------------------------------------
# 6. MODEL 2: REFINED 10-FOLD LOSSGUIDE XGBOOST (BASE_MARGIN) -> SUB 12
# -------------------------------------------------------------
print("\n" + "=" * 80)
print("🌲 [MODEL 2 / SUB 12] Refined 10-Fold Lossguide XGBoost + Recipe Margin (Target ~0.94652)")
print("=" * 80)

oof_sub12 = np.zeros(len(train))
test_sub12 = np.zeros(len(test))

for f_data in fold_datasets:
    fold = f_data['fold']
    X_tr, y_tr = f_data['X_train'], f_data['y_train']
    X_va, y_va = f_data['X_valid'], f_data['y_valid']
    X_te = f_data['X_test']
    m_tr, m_va, m_te = f_data['margin_train'], f_data['margin_valid'], f_data['margin_test']

    clf = xgb.XGBClassifier(
        n_estimators=10000,
        learning_rate=0.012,
        max_depth=5,
        max_leaves=16,
        grow_policy='lossguide',
        gamma=3.0,
        min_child_weight=4.0,
        subsample=0.74,
        colsample_bytree=0.57,
        alpha=0.6,
        reg_lambda=0.7,
        max_bin=1024,
        random_state=42 + fold,
        eval_metric='auc',
        early_stopping_rounds=350,
        tree_method='hist',
        device=XGB_DEVICE,
        n_jobs=-1
    )

    clf.fit(
        X_tr, y_tr, 
        eval_set=[(X_va, y_va)], 
        base_margin=m_tr, 
        base_margin_eval_set=[m_va], 
        verbose=False
    )
    va_prob = clf.predict_proba(X_va, base_margin=m_va)[:, 1]
    te_prob = clf.predict_proba(X_te, base_margin=m_te)[:, 1]

    oof_sub12[f_data['valid_idx']] = va_prob
    test_sub12 += te_prob / FOLDS

    f_auc = roc_auc_score(y_va, va_prob)
    print(f"  -> XGBoost Fold {fold} ROC-AUC: {f_auc:.5f} (Best Iter: {clf.best_iteration})")

cv_sub12 = roc_auc_score(y, oof_sub12)
print(f"🏆 SUBMISSION 12 (10-Fold XGBoost) OOF ROC-AUC: {cv_sub12:.5f}")

# -------------------------------------------------------------
# 7. MODEL 3: ELITE DUAL-ENGINE RANK BLEND -> SUB 13 (TOP 10 CROSSOVER)
# -------------------------------------------------------------
print("\n" + "=" * 80)
print("⚡ [MODEL 3 / SUB 13] Elite Dual-Engine Rank Blend (Target >=0.94660)")
print("=" * 80)

r_oof11 = rankdata(oof_sub11) / len(oof_sub11)
r_oof12 = rankdata(oof_sub12) / len(oof_sub12)

def dual_blend_objective(w):
    blended = w[0] * r_oof11 + (1.0 - w[0]) * r_oof12
    return -roc_auc_score(y, blended)

opt_dual = minimize(dual_blend_objective, [0.5], method='Nelder-Mead', bounds=[(0.0, 1.0)])
w_dual = opt_dual.x[0]
cv_sub13 = -opt_dual.fun

print(f"🎯 Optimal Dual Blend Weight: LGBM={w_dual:.4f} | XGBoost={1.0 - w_dual:.4f}")
print(f"🏆 SUBMISSION 13 OOF ROC-AUC: {cv_sub13:.5f}")

r_te11 = rankdata(test_sub11) / len(test_sub11)
r_te12 = rankdata(test_sub12) / len(test_sub12)
test_sub13 = w_dual * r_te11 + (1.0 - w_dual) * r_te12

# -------------------------------------------------------------
# 8. MODEL 4: MULTI-SEED TRI-ENGINE AVERAGING (SEEDS 42 & 101) -> SUB 14
# -------------------------------------------------------------
print("\n" + "=" * 80)
print("🌱 [MODEL 4 / SUB 14] Multi-Seed Tri-Engine Averaging (Seeds 42 & 101, Target ~0.94668)")
print("=" * 80)

# Run Seed 101 for LightGBM & XGBoost
oof_lgb_s101 = np.zeros(len(train))
test_lgb_s101 = np.zeros(len(test))
oof_xgb_s101 = np.zeros(len(train))
test_xgb_s101 = np.zeros(len(test))
oof_cb = np.zeros(len(train))
test_cb = np.zeros(len(test))

lgb_params_s101 = lgb_params.copy()
lgb_params_s101['random_state'] = 101

for f_data in fold_datasets:
    fold = f_data['fold']
    X_tr, y_tr = f_data['X_train'], f_data['y_train']
    X_va, y_va = f_data['X_valid'], f_data['y_valid']
    X_te = f_data['X_test']
    m_tr, m_va, m_te = f_data['margin_train'], f_data['margin_valid'], f_data['margin_test']

    # LightGBM Seed 101
    trn_data = lgb.Dataset(X_tr, label=y_tr, init_score=m_tr)
    val_data = lgb.Dataset(X_va, label=y_va, init_score=m_va, reference=trn_data)
    callbacks = [lgb.early_stopping(stopping_rounds=300, verbose=False)]
    bst101 = lgb.train(lgb_params_s101, trn_data, num_boost_round=8000, valid_sets=[val_data], callbacks=callbacks)
    oof_lgb_s101[f_data['valid_idx']] = expit(m_va + bst101.predict(X_va, raw_score=True))
    test_lgb_s101 += expit(m_te + bst101.predict(X_te, raw_score=True)) / FOLDS

    # XGBoost Seed 101
    clf101 = xgb.XGBClassifier(
        n_estimators=10000, learning_rate=0.012, max_depth=5, max_leaves=16,
        grow_policy='lossguide', gamma=3.0, min_child_weight=4.0, subsample=0.74,
        colsample_bytree=0.57, alpha=0.6, reg_lambda=0.7, max_bin=1024,
        random_state=101 + fold, eval_metric='auc', early_stopping_rounds=350,
        tree_method='hist', device=XGB_DEVICE, n_jobs=-1
    )
    clf101.fit(X_tr, y_tr, eval_set=[(X_va, y_va)], base_margin=m_tr, base_margin_eval_set=[m_va], verbose=False)
    oof_xgb_s101[f_data['valid_idx']] = clf101.predict_proba(X_va, base_margin=m_va)[:, 1]
    test_xgb_s101 += clf101.predict_proba(X_te, base_margin=m_te)[:, 1] / FOLDS

    # CatBoost Oblivious Model
    cb = CatBoostClassifier(
        iterations=3000, learning_rate=0.03, depth=6, l2_leaf_reg=5.0,
        eval_metric='AUC', random_seed=101 + fold, early_stopping_rounds=300,
        task_type=CAT_TASK, verbose=False
    )
    cb.fit(X_tr, y_tr, eval_set=(X_va, y_va), verbose=False)
    oof_cb[f_data['valid_idx']] = cb.predict_proba(X_va)[:, 1]
    test_cb += cb.predict_proba(X_te)[:, 1] / FOLDS

# Seed-averaged legs
oof_lgb_avg = 0.5 * (oof_sub11 + oof_lgb_s101)
test_lgb_avg = 0.5 * (test_sub11 + test_lgb_s101)

oof_xgb_avg = 0.5 * (oof_sub12 + oof_xgb_s101)
test_xgb_avg = 0.5 * (test_sub12 + test_xgb_s101)

print(f"  -> LGBM Multi-Seed OOF ROC-AUC: {roc_auc_score(y, oof_lgb_avg):.5f}")
print(f"  -> XGBoost Multi-Seed OOF ROC-AUC: {roc_auc_score(y, oof_xgb_avg):.5f}")
print(f"  -> CatBoost OOF ROC-AUC: {roc_auc_score(y, oof_cb):.5f}")

# Tri-engine Rank Blend
r_lgb = rankdata(oof_lgb_avg) / len(oof_lgb_avg)
r_xgb = rankdata(oof_xgb_avg) / len(oof_xgb_avg)
r_cb  = rankdata(oof_cb) / len(oof_cb)

def tri_objective(w):
    w_arr = np.array(w)
    if w_arr.sum() == 0: return 0.0
    w_norm = w_arr / w_arr.sum()
    b = w_norm[0] * r_lgb + w_norm[1] * r_xgb + w_norm[2] * r_cb
    return -roc_auc_score(y, b)

opt_tri = minimize(tri_objective, [0.45, 0.45, 0.10], method='Nelder-Mead', bounds=[(0.0, 1.0)]*3)
w_tri = opt_tri.x / opt_tri.x.sum()
cv_sub14 = -opt_tri.fun

print(f"🎯 Tri-Engine Blend Weights: LGBM={w_tri[0]:.4f} | XGB={w_tri[1]:.4f} | CB={w_tri[2]:.4f}")
print(f"🏆 SUBMISSION 14 (Multi-Seed Tri-Engine) OOF ROC-AUC: {cv_sub14:.5f}")

r_te_lgb = rankdata(test_lgb_avg) / len(test_lgb_avg)
r_te_xgb = rankdata(test_xgb_avg) / len(test_xgb_avg)
r_te_cb  = rankdata(test_cb) / len(test_cb)
test_sub14 = w_tri[0] * r_te_lgb + w_tri[1] * r_te_xgb + w_tri[2] * r_te_cb

# -------------------------------------------------------------
# 9. MODEL 5: MASTER TOP-10 ASSAULT (PHYSICS BOUNDARIES + ZERO TIES) -> SUB 15
# -------------------------------------------------------------
print("\n" + "=" * 80)
print("👑 [MODEL 5 / SUB 15] Master Top-10 Assault: Physics Shifts & Zero-Tie Lexsort (Target >=0.94672)")
print("=" * 80)

test_incomes = test['Annual_Income_USD'].values
test_commute = test['Daily_Commute_km'].values
test_subsidy_no = (test['Subsidy_Available'] == "No").values
test_env_1 = (test['Environmental_Concern_Level'] == 1).values
test_anx_high = (test['Range_Anxiety_Level'] == "High").values

# Base normalized ranks
calibrated_preds = test_sub14.copy()

# Deterministic Boundary Physics Shifts
calibrated_preds[test_incomes >= 170537.0] += 10.0
calibrated_preds[(test_incomes >= 31004.0) & (test_incomes <= 41970.0)] -= 10.0
calibrated_preds[test_commute >= 83.0] -= 5.0
calibrated_preds[(test_incomes == 30000.0) & test_subsidy_no & (test_env_1 | test_anx_high)] -= 5.0

# Zero-Tie Ordinal Sorting via Lexsort
order_final = np.lexsort((test_sub14, calibrated_preds))
ranks_final = np.empty(len(order_final), dtype=np.int64)
ranks_final[order_final] = np.arange(1, len(order_final) + 1)
test_sub15 = (ranks_final - 0.5) / len(ranks_final)

print(f"🎯 Zero-Tie Ordinal Rank Status:")
print(f"  • Unique Predicted Ranks: {pd.Series(test_sub15).nunique():,} / {len(test_sub15):,} (100% Zero Ties)")
print(f"  • Min Rank Score: {test_sub15.min():.6f}")
print(f"  • Max Rank Score: {test_sub15.max():.6f}")

# -------------------------------------------------------------
# 10. 6-POINT INTEGRITY VERIFICATION & SAVING ALL 5 TIERS
# -------------------------------------------------------------
print("\n" + "=" * 80)
print("💾 VERIFYING AND SAVING SUBMISSIONS 11 THROUGH 15")
print("=" * 80)

def save_and_verify(preds: np.ndarray, filename: str, desc: str):
    sub = pd.DataFrame({'id': test_id, TARGET: preds})
    
    # 6-Point Integrity Verification
    assert len(sub) == 286571, f"Row count mismatch: {len(sub)} != 286571"
    assert list(sub.columns) == ['id', TARGET], f"Columns mismatch: {list(sub.columns)}"
    assert (sub['id'] == test_id).all(), "ID alignment mismatch!"
    assert not sub[TARGET].isna().any(), "Found NaNs in predictions!"
    assert not np.isinf(sub[TARGET]).any(), "Found infinite values in predictions!"
    assert sub[TARGET].min() >= 0.0 and sub[TARGET].max() <= 1.0, f"Predictions out of [0, 1] range: min={sub[TARGET].min()}, max={sub[TARGET].max()}"

    p = OUTPUT_DIR / filename
    sub.to_csv(p, index=False)
    mean_val = sub[TARGET].mean()
    std_val = sub[TARGET].std()
    print(f"✅ Saved & Verified: {filename} | {desc} | Mean: {mean_val:.4f} | Std: {std_val:.4f}")

save_and_verify(test_sub11, "submission_11_lgbm_refined_10fold.csv", f"Sub 11: 10-Fold LightGBM (CV {cv_sub11:.5f})")
save_and_verify(test_sub12, "submission_12_xgb_lossguide_10fold.csv", f"Sub 12: 10-Fold Lossguide XGBoost (CV {cv_sub12:.5f})")
save_and_verify(test_sub13, "submission_13_dual_engine_rank_blend.csv", f"Sub 13: Dual-Engine Rank Blend (CV {cv_sub13:.5f})")
save_and_verify(test_sub14, "submission_14_multiseed_tri_engine.csv", f"Sub 14: Multi-Seed Tri-Engine Blend (CV {cv_sub14:.5f})")
save_and_verify(test_sub15, "submission_15_top10_master_assault.csv", f"Sub 15: Master Top-10 Assault (CV {cv_sub14:.5f} + Physics)")

print("\n🎉 ALL 5 PROGRESSIVE SUBMISSIONS GENERATED AND VERIFIED SUCCESSFULLY!")
