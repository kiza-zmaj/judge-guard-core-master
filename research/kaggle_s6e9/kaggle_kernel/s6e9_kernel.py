#!/usr/bin/env python3
"""
Kaggle Kernel: S6E9 Top-10 Triple-TE & Recipe Base Margin Pipeline
Target: Break 0.94660 into Public Leaderboard Top 10
Architecture:
  - Folds: 5-Fold StratifiedKFold
  - Feature Engineering: Full Digit Decomposition (-4 to 3), Domain Interactions, 
    Original Dataset Target Means, Markus Smooth Keys, Global Frequency Encodings
  - In-Fold Triple Target Encoding: smooth='auto', smooth=10.0, smooth=100.0
  - Dynamic Noise Pruning (88 noise features removed)
  - Models:
    1. Lossguide XGBoost (Najiama baseline, target ~0.94639)
    2. Lossguide XGBoost + Chris Deotte Recipe Base Margin (target ~0.94665)
    3. LightGBM + Recipe init_score (target ~0.94655)
    4. CatBoost Oblivious Trees (target ~0.94650)
    5. Master Rank Nelder-Mead Blend across all 4 models (target >=0.94670)
Platform: Kaggle Cloud GPU
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
from catboost import CatBoostClassifier, Pool

warnings.filterwarnings('ignore')

print("=" * 80)
print("🚀⚡ KAGGLE S6E9: TOP-10 TRIPLE-TE & RECIPE BASE MARGIN PIPELINE")
print("=" * 80)

OUTPUT_DIR = Path("/kaggle/working")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# -------------------------------------------------------------
# 0. HARDWARE ACCELERATION DETECTION
# -------------------------------------------------------------
try:
    import torch
    HAS_CUDA = torch.cuda.is_available()
except ImportError:
    HAS_CUDA = False

XGB_DEVICE = "cuda" if HAS_CUDA else "cpu"
CAT_TASK = "GPU" if HAS_CUDA else "CPU"
print(f"🔧 Device Configuration: CUDA={HAS_CUDA} | XGBoost Device='{XGB_DEVICE}' | CatBoost Task='{CAT_TASK}'")

# -------------------------------------------------------------
# 1. ROBUST INPUT LOCATOR
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
    raise FileNotFoundError(f"Could not locate '{name}' in /kaggle environment!")

print("📂 Available files in /kaggle/input:")
for root, dirs, files in os.walk("/kaggle/input"):
    for f in files:
        print("  ", os.path.join(root, f))

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
    print("⚠️ Original dataset not found, generating synthetic baseline for priors.")
    orig = train.sample(frac=0.1, random_state=42).copy()

TARGET = 'Will_Buy_EV'
train[TARGET] = train[TARGET].map({'Yes': 1, 'No': 0})
orig[TARGET] = orig[TARGET].map({'Yes': 1, 'No': 0})

train_id = train['id'].copy()
test_id = test['id'].copy()

# -------------------------------------------------------------
# 2. CHRIS DEOTTE EV RECIPE SCORE & BASE MARGIN LOGIT
# -------------------------------------------------------------
def compute_recipe_prior(df: pd.DataFrame):
    """
    Computes exact EV generation latent utility:
    utility = 1.2 * Income/1e5 + 0.6 * EnvConcern + 2.0 * Subsidy - 1.0 * MedAnxiety - 3.0 * HighAnxiety
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

recipe_auc = roc_auc_score(train[TARGET], score_train)
print(f"\n🌟 Chris Deotte Recipe Prior Alone Train ROC-AUC: {recipe_auc:.5f}")

# -------------------------------------------------------------
# 3. COMPREHENSIVE FEATURE ENGINEERING (TRIPLE TE + DIGIT DECOMPOSITION)
# -------------------------------------------------------------
print("\n🛠️ Constructing Feature Space (Digits, Domain Interactions, Smooth Keys)...")

train['is_train'] = 1
test['is_train'] = 0
test[TARGET] = np.nan
combined = pd.concat([train, test], ignore_index=True)

# Drop irrelevant / zero-importance column
combined.drop(columns=['Number_of_Cars_Owned'], inplace=True, errors='ignore')

# Add Chris Deotte domain interactions
home = (combined['Home_Charging_Possible'] == "Yes").astype(int)
subsidy = (combined['Subsidy_Available'] == "Yes").astype(int)

combined["worry_score"] = (
    combined['Daily_Commute_km'] 
    - 5 * combined['Charging_Stations_Near_Home'] 
    - 5 * combined['Charging_Stations_Near_Work'] 
    - 150 * home
)
combined["chargers_total"] = combined['Charging_Stations_Near_Home'] + combined['Charging_Stations_Near_Work']
combined["income_x_subsidy"] = (combined['Annual_Income_USD'] / 1e5) * subsidy
combined["concern_x_subsidy"] = combined['Environmental_Concern_Level'] * subsidy
combined["recipe_score"] = np.concatenate([score_train, score_test])

cat_cols = combined.select_dtypes(include=['object', 'string']).columns.tolist()
num_cols = [c for c in combined.columns if c not in cat_cols + ['id', 'is_train', TARGET]]

# Extract digits from 10^-4 place up to 10^3 place
digit_features = []
for c in ['Age', 'Annual_Income_USD', 'Daily_Commute_km', 'Charging_Stations_Near_Home', 'Charging_Stations_Near_Work']:
    if c in combined.columns:
        for k in range(-4, 4):
            col_name = f"{c}_digit{k}"
            combined[col_name] = (combined[c].fillna(0) // (10**k) % 10).astype('int8')
            digit_features.append(col_name)

num_cols.extend(digit_features)

# Map original dataset target means
orig_global_mean = float(orig[TARGET].mean())
for col in cat_cols + num_cols:
    if col in orig.columns:
        real_world_stats = orig.groupby(col, observed=False)[TARGET].mean()
        combined[f"{col}_org_mean"] = combined[col].map(real_world_stats).fillna(orig_global_mean).astype(float)

# Convert numerics to string categories for frequency & target encoding
num_to_cat_cols = []
for col in num_cols:
    cat_name = f"{col}_cat"
    combined[cat_name] = combined[col].fillna('NaN').astype(str)
    num_to_cat_cols.append(cat_name)

# Global Frequency Encoding
all_cats = cat_cols + num_to_cat_cols
for col in all_cats:
    freq_mapping = combined[col].value_counts(normalize=True).to_dict()
    combined[f"{col}_fe"] = combined[col].map(freq_mapping).astype(float).fillna(0.0)

# Environmental concern extreme
combined['is_env_hater'] = (combined['Environmental_Concern_Level'] == 1).astype('int8')

# Markus's Smooth Keys (binned numerics)
combined['income_exact_int'] = np.floor(combined['Annual_Income_USD']).astype(str)
combined['income100_floor']  = np.floor(combined['Annual_Income_USD'] / 100.0).astype(str)
combined['income1000_floor'] = np.floor(combined['Annual_Income_USD'] / 1000.0).astype(str)
combined['commute_integer']  = np.floor(combined['Daily_Commute_km']).astype(str)
all_cats.extend(['income_exact_int', 'income100_floor', 'income1000_floor', 'commute_integer'])

# Separate back to train and test
train_proc = combined[combined['is_train'] == 1].drop(columns=['is_train'])
test_proc = combined[combined['is_train'] == 0].drop(columns=['is_train', TARGET])

# Feature dropping: constant and perfectly correlated
eval_cols = [c for c in train_proc.columns if c not in ['id', TARGET] and pd.api.types.is_numeric_dtype(train_proc[c])]
corr_matrix = train_proc[eval_cols].corr().abs()
upper_tri = corr_matrix.where(np.triu(np.ones(corr_matrix.shape), k=1).astype(bool))
to_drop_corr = [column for column in upper_tri.columns if any(upper_tri[column] == 1.0)]
to_drop_const = [c for c in train_proc.columns if train_proc[c].nunique() == 1] + [c for c in test_proc.columns if test_proc[c].nunique() == 1]

DROP = list(set(to_drop_corr).union(set(to_drop_const)))
DROP = [c for c in DROP if c not in ['id', TARGET]]

if len(DROP) > 0:
    print(f"✂️ Dropping {len(DROP)} redundant/constant features.")
    train_proc.drop(columns=DROP, inplace=True, errors='ignore')
    test_proc.drop(columns=DROP, inplace=True, errors='ignore')

FEATURES = [c for c in test_proc.columns if c != 'id']
TARGET_ENCODE_COLS = [c for c in all_cats if c not in DROP and c in train_proc.columns]

print(f"✅ Total Base Features: {len(FEATURES)}")
print(f"✅ Columns to Target Encode: {len(TARGET_ENCODE_COLS)}")

# 88-Feature Dynamic Pruning List (Najiama Gain Thresholding)
features_to_drop = [
    'Age', 'Daily_Commute_km_digit-3_cat_TE_100', 'Charging_Stations_Near_Home_digit0',
    'Daily_Commute_km_digit1_cat_TE_100', 'Annual_Income_USD_digit1', 'Charging_Stations_Near_Work_digit1_cat_TE_auto',
    'Daily_Commute_km_digit1_cat_TE_auto', 'Daily_Commute_km_digit0_cat_TE_10', 'Gender_org_mean',
    'Daily_Commute_km_digit-4_cat_TE_100', 'Daily_Commute_km_digit0_cat_TE_auto', 'Daily_Commute_km_digit-4_cat_TE_auto',
    'Daily_Commute_km_cat_fe', 'Annual_Income_USD_digit1_cat_fe', 'Charging_Stations_Near_Work_digit0_cat_TE_100',
    'Annual_Income_USD_digit2_cat_TE_100', 'Annual_Income_USD_digit0', 'Charging_Stations_Near_Home_digit-3_cat_TE_auto',
    'Gender_TE_100', 'Current_Car_Type_TE_10', 'Age_digit1_cat_fe', 'Charging_Stations_Near_Work_digit1_cat_TE_100',
    'Annual_Income_USD_digit0_cat_TE_10', 'Daily_Commute_km_digit-3_cat_TE_10', 'Charging_Stations_Near_Work_digit0_cat_TE_10',
    'Gender_TE_auto', 'Daily_Commute_km_digit0_cat_TE_100', 'Charging_Stations_Near_Home_digit-4_cat_TE_auto',
    'Daily_Commute_km_digit-1_cat_TE_10', 'Charging_Stations_Near_Work_digit0_cat_TE_auto', 'Daily_Commute_km_digit-1',
    'Charging_Stations_Near_Work_digit0', 'Annual_Income_USD_digit0_cat_TE_auto', 'Daily_Commute_km_digit-4_cat_TE_10',
    'Charging_Stations_Near_Work_digit-3_cat_TE_auto', 'Charging_Stations_Near_Work_org_mean', 'Age_digit0_cat_TE_auto',
    'Age_digit0_cat_fe', 'Annual_Income_USD_digit0_cat_fe', 'Charging_Stations_Near_Home_digit-4_cat_TE_100',
    'Daily_Commute_km_digit-3_cat_TE_auto', 'Age_digit0', 'Annual_Income_USD_digit2_cat_TE_auto',
    'Annual_Income_USD_digit0_cat_TE_100', 'Daily_Commute_km_org_mean', 'Age_digit0_cat_TE_10',
    'Current_Car_Type_TE_auto', 'Current_Car_Type_TE_100', 'Age_digit1_cat_TE_auto', 'Charging_Stations_Near_Home_digit-4',
    'Annual_Income_USD_digit2_cat_TE_10', 'Daily_Commute_km_digit-1_cat_TE_100', 'Age_cat_fe',
    'Daily_Commute_km_digit0_cat_fe', 'Daily_Commute_km_digit-1_cat_fe', 'Daily_Commute_km_digit-1_cat_TE_auto',
    'Daily_Commute_km_digit-2_cat_TE_10', 'Age_digit1', 'Age_digit1_cat_TE_100', 'Gender_TE_10', 'Age_digit1_cat_TE_10',
    'Age_digit0_cat_TE_100', 'Daily_Commute_km_digit-3', 'Charging_Stations_Near_Home_digit-3_cat_TE_100', 'Gender_fe',
    'Charging_Stations_Near_Home_digit-3_cat_TE_10', 'Daily_Commute_km_digit-4_cat_fe', 'Daily_Commute_km_digit-4',
    'Daily_Commute_km_digit-3_cat_fe', 'Charging_Stations_Near_Work_digit-3_cat_TE_10', 'Daily_Commute_km_digit-2_cat_TE_100',
    'Charging_Stations_Near_Home_digit-2_cat_TE_auto', 'Charging_Stations_Near_Home_digit-1_cat_TE_auto',
    'Charging_Stations_Near_Work_digit1_cat_fe', 'Charging_Stations_Near_Work_digit-2_cat_TE_100',
    'Charging_Stations_Near_Home_digit-2_cat_TE_100', 'Charging_Stations_Near_Work_digit-3_cat_TE_100', 'is_dead_zone',
    'is_millionaire_cliff', 'is_30k_spike', 'Charging_Stations_Near_Home_digit-1_cat_TE_100',
    'Charging_Stations_Near_Home_digit-1_cat_TE_10', 'Charging_Stations_Near_Home_digit-2_cat_TE_10',
    'Charging_Stations_Near_Work_digit-1_cat_TE_10', 'Charging_Stations_Near_Work_digit-2_cat_TE_auto',
    'Charging_Stations_Near_Work_digit-1_cat_TE_auto', 'Charging_Stations_Near_Work_digit-1_cat_TE_100',
    'Charging_Stations_Near_Work_digit-2_cat_TE_10'
]

# -------------------------------------------------------------
# 4. CROSS-VALIDATION ENCODING & PREPARATION (5 FOLDS)
# -------------------------------------------------------------
FOLDS = 5
print(f"\n🔄 Running 5-Fold Stratified Split and Triple Target Encoding...")
skf = StratifiedKFold(n_splits=FOLDS, shuffle=True, random_state=42)

X_raw = train_proc[FEATURES].copy()
y = train_proc[TARGET].values
X_test_raw = test_proc[FEATURES].copy()

# Store transformed fold datasets
fold_datasets = []

for fold, (train_idx, valid_idx) in enumerate(skf.split(X_raw, y), 1):
    print(f"  -> Processing Fold {fold}/{FOLDS} Triple TE...")
    X_train_f = X_raw.iloc[train_idx].copy()
    y_train_f = y[train_idx]
    X_valid_f = X_raw.iloc[valid_idx].copy()
    y_valid_f = y[valid_idx]
    X_test_f = X_test_raw.copy()

    # Triple Target Encoders (Auto, Strict 10, Massive 100)
    te_auto = TargetEncoder(smooth='auto', cv=FOLDS)
    te_10   = TargetEncoder(smooth=10.0, cv=FOLDS)
    te_100  = TargetEncoder(smooth=100.0, cv=FOLDS)

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

    # Apply dynamic feature pruning
    safe_to_drop = [c for c in features_to_drop if c in X_train_f.columns]
    X_train_f.drop(columns=safe_to_drop, inplace=True, errors='ignore')
    X_valid_f.drop(columns=safe_to_drop, inplace=True, errors='ignore')
    X_test_f.drop(columns=safe_to_drop, inplace=True, errors='ignore')

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

print(f"✅ Prepared all {FOLDS} folds. Final feature count per fold: {fold_datasets[0]['X_train'].shape[1]}")

# -------------------------------------------------------------
# 5. MODEL 1: LOSSGUIDE XGBOOST (TRIPLE-TE + DYNAMIC PRUNING) -> SUB 6
# -------------------------------------------------------------
print("\n" + "=" * 80)
print("🌲 [MODEL 1 / SUB 6] Lossguide XGBoost (Najiama Architecture, Target ~0.94639)")
print("=" * 80)

oof_m1 = np.zeros(len(train))
test_m1 = np.zeros(len(test))

for f_data in fold_datasets:
    fold = f_data['fold']
    X_tr, y_tr = f_data['X_train'], f_data['y_train']
    X_va, y_va = f_data['X_valid'], f_data['y_valid']
    X_te = f_data['X_test']

    clf = xgb.XGBClassifier(
        n_estimators=10000,
        learning_rate=0.01,
        max_depth=4,
        max_leaves=16,
        grow_policy='lossguide',
        gamma=3.673225596759869,
        min_child_weight=4.532387806880492,
        subsample=0.7400402414525654,
        colsample_bytree=0.5695776529558766,
        alpha=0.7523885021652775,
        reg_lambda=0.6189949691705282,
        max_bin=1024,
        random_state=42 + fold,
        eval_metric='auc',
        early_stopping_rounds=400,
        tree_method='hist',
        device=XGB_DEVICE,
        n_jobs=-1
    )

    clf.fit(X_tr, y_tr, eval_set=[(X_va, y_va)], verbose=500)
    va_prob = clf.predict_proba(X_va)[:, 1]
    te_prob = clf.predict_proba(X_te)[:, 1]

    oof_m1[f_data['valid_idx']] = va_prob
    test_m1 += te_prob / FOLDS

    f_auc = roc_auc_score(y_va, va_prob)
    print(f"  -> Model 1 Fold {fold} ROC-AUC: {f_auc:.5f} (Best Iter: {clf.best_iteration})")

cv_m1 = roc_auc_score(y, oof_m1)
print(f"🏆 MODEL 1 OOF ROC-AUC: {cv_m1:.5f}")

# -------------------------------------------------------------
# 6. MODEL 2: LOSSGUIDE XGBOOST WITH RECIPE BASE_MARGIN -> SUB 7
# -------------------------------------------------------------
print("\n" + "=" * 80)
print("⚡ [MODEL 2 / SUB 7] Lossguide XGBoost + Recipe Base Margin (Target >=0.94660)")
print("=" * 80)

oof_m2 = np.zeros(len(train))
test_m2 = np.zeros(len(test))

for f_data in fold_datasets:
    fold = f_data['fold']
    X_tr, y_tr = f_data['X_train'], f_data['y_train']
    X_va, y_va = f_data['X_valid'], f_data['y_valid']
    X_te = f_data['X_test']
    m_tr, m_va, m_te = f_data['margin_train'], f_data['margin_valid'], f_data['margin_test']

    clf = xgb.XGBClassifier(
        n_estimators=10000,
        learning_rate=0.015,
        max_depth=4,
        max_leaves=16,
        grow_policy='lossguide',
        gamma=3.0,
        min_child_weight=4.0,
        subsample=0.75,
        colsample_bytree=0.60,
        alpha=0.6,
        reg_lambda=0.7,
        max_bin=1024,
        random_state=142 + fold,
        eval_metric='auc',
        early_stopping_rounds=400,
        tree_method='hist',
        device=XGB_DEVICE,
        n_jobs=-1
    )

    clf.fit(
        X_tr, y_tr, 
        eval_set=[(X_va, y_va)], 
        base_margin=m_tr, 
        base_margin_eval_set=[m_va], 
        verbose=500
    )
    va_prob = clf.predict_proba(X_va, base_margin=m_va)[:, 1]
    te_prob = clf.predict_proba(X_te, base_margin=m_te)[:, 1]

    oof_m2[f_data['valid_idx']] = va_prob
    test_m2 += te_prob / FOLDS

    f_auc = roc_auc_score(y_va, va_prob)
    print(f"  -> Model 2 Fold {fold} (Recipe Margin) ROC-AUC: {f_auc:.5f} (Best Iter: {clf.best_iteration})")

cv_m2 = roc_auc_score(y, oof_m2)
print(f"🏆 MODEL 2 OOF ROC-AUC: {cv_m2:.5f}")

# -------------------------------------------------------------
# 7. MODEL 3: LIGHTGBM WITH RECIPE INIT_SCORE -> SUB 8
# -------------------------------------------------------------
print("\n" + "=" * 80)
print("💡 [MODEL 3 / SUB 8] LightGBM Triple-TE + Recipe init_score (Target ~0.94655)")
print("=" * 80)

oof_m3 = np.zeros(len(train))
test_m3 = np.zeros(len(test))

lgb_params = {
    'objective': 'binary',
    'metric': 'auc',
    'boosting_type': 'gbdt',
    'learning_rate': 0.015,
    'num_leaves': 31,
    'max_depth': 6,
    'feature_fraction': 0.60,
    'bagging_fraction': 0.80,
    'bagging_freq': 1,
    'min_child_samples': 30,
    'lambda_l1': 0.5,
    'lambda_l2': 1.0,
    'verbosity': -1,
    'n_jobs': -1,
    'random_state': 242
}

for f_data in fold_datasets:
    fold = f_data['fold']
    X_tr, y_tr = f_data['X_train'], f_data['y_train']
    X_va, y_va = f_data['X_valid'], f_data['y_valid']
    X_te = f_data['X_test']
    m_tr, m_va, m_te = f_data['margin_train'], f_data['margin_valid'], f_data['margin_test']

    trn_data = lgb.Dataset(X_tr, label=y_tr, init_score=m_tr)
    val_data = lgb.Dataset(X_va, label=y_va, init_score=m_va, reference=trn_data)

    callbacks = [lgb.early_stopping(stopping_rounds=300, verbose=False), lgb.log_evaluation(period=500)]
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

    oof_m3[f_data['valid_idx']] = va_prob
    test_m3 += te_prob / FOLDS

    f_auc = roc_auc_score(y_va, va_prob)
    print(f"  -> Model 3 Fold {fold} ROC-AUC: {f_auc:.5f} (Best Iter: {bst.best_iteration})")

cv_m3 = roc_auc_score(y, oof_m3)
print(f"🏆 MODEL 3 OOF ROC-AUC: {cv_m3:.5f}")

# -------------------------------------------------------------
# 8. MODEL 4: CATBOOST OBLIVIOUS TREES ON TRIPLE-TE -> SUB 9
# -------------------------------------------------------------
print("\n" + "=" * 80)
print("🐱 [MODEL 4 / SUB 9] CatBoost Oblivious Trees (Target ~0.94650)")
print("=" * 80)

oof_m4 = np.zeros(len(train))
test_m4 = np.zeros(len(test))

for f_data in fold_datasets:
    fold = f_data['fold']
    X_tr, y_tr = f_data['X_train'], f_data['y_train']
    X_va, y_va = f_data['X_valid'], f_data['y_valid']
    X_te = f_data['X_test']

    cb = CatBoostClassifier(
        iterations=3500,
        learning_rate=0.03,
        depth=6,
        l2_leaf_reg=5.0,
        eval_metric='AUC',
        random_seed=342 + fold,
        early_stopping_rounds=300,
        task_type=CAT_TASK,
        verbose=1000
    )

    cb.fit(X_tr, y_tr, eval_set=(X_va, y_va), verbose=1000)
    va_prob = cb.predict_proba(X_va)[:, 1]
    te_prob = cb.predict_proba(X_te)[:, 1]

    oof_m4[f_data['valid_idx']] = va_prob
    test_m4 += te_prob / FOLDS

    f_auc = roc_auc_score(y_va, va_prob)
    print(f"  -> Model 4 Fold {fold} ROC-AUC: {f_auc:.5f}")

cv_m4 = roc_auc_score(y, oof_m4)
print(f"🏆 MODEL 4 OOF ROC-AUC: {cv_m4:.5f}")

# -------------------------------------------------------------
# 9. MODEL 5: MASTER NELDER-MEAD RANK BLEND -> SUB 10 (TOP 10 TARGET)
# -------------------------------------------------------------
print("\n" + "=" * 80)
print("👑 [MODEL 5 / SUB 10] Master Nelder-Mead Rank Blend (Target >=0.94670 — Top 10)")
print("=" * 80)

r_m1 = rankdata(oof_m1) / len(oof_m1)
r_m2 = rankdata(oof_m2) / len(oof_m2)
r_m3 = rankdata(oof_m3) / len(oof_m3)
r_m4 = rankdata(oof_m4) / len(oof_m4)

print(f"Correlation Matrix (OOF Ranks):")
corr_df = pd.DataFrame({
    'XGB_Base': r_m1,
    'XGB_Margin': r_m2,
    'LGB_Margin': r_m3,
    'CatBoost': r_m4
}).corr()
print(corr_df.round(4))

def blend_objective(weights):
    w = np.array(weights)
    if w.sum() == 0:
        return 0.0
    w = w / w.sum()
    blended_rank = w[0] * r_m1 + w[1] * r_m2 + w[2] * r_m3 + w[3] * r_m4
    return -roc_auc_score(y, blended_rank)

init_weights = [0.25, 0.40, 0.20, 0.15]
bounds = [(0.0, 1.0)] * 4
res = minimize(blend_objective, init_weights, method='Nelder-Mead', bounds=bounds)

best_w = res.x / res.x.sum()
cv_m5 = -res.fun

print(f"\n🎯 Optimal Blend Weights:")
print(f"   XGBoost Base (Sub 6):   {best_w[0]:.4f}")
print(f"   XGBoost Margin (Sub 7): {best_w[1]:.4f}")
print(f"   LightGBM Margin (Sub 8):{best_w[2]:.4f}")
print(f"   CatBoost (Sub 9):       {best_w[3]:.4f}")
print(f"🏆 MASTER BLEND OOF ROC-AUC: {cv_m5:.5f}")

# Compute final test predictions via rank aggregation
r_test_m1 = rankdata(test_m1) / len(test_m1)
r_test_m2 = rankdata(test_m2) / len(test_m2)
r_test_m3 = rankdata(test_m3) / len(test_m3)
r_test_m4 = rankdata(test_m4) / len(test_m4)

test_m5 = (
    best_w[0] * r_test_m1 +
    best_w[1] * r_test_m2 +
    best_w[2] * r_test_m3 +
    best_w[3] * r_test_m4
)

# -------------------------------------------------------------
# 10. VERIFICATION & EXPORT OF ALL 5 SUBMISSION TIERS
# -------------------------------------------------------------
print("\n" + "=" * 80)
print("💾 VERIFYING AND SAVING SUBMISSIONS 6 THROUGH 10")
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

save_and_verify(test_m1, "submission_6_xgb_triple_te.csv", f"Sub 6: Lossguide XGBoost Triple TE (CV {cv_m1:.5f})")
save_and_verify(test_m2, "submission_7_xgb_recipe_base_margin.csv", f"Sub 7: Lossguide XGBoost Recipe Margin (CV {cv_m2:.5f})")
save_and_verify(test_m3, "submission_8_lgbm_triple_te_init_score.csv", f"Sub 8: LightGBM Triple TE Recipe Prior (CV {cv_m3:.5f})")
save_and_verify(test_m4, "submission_9_catboost_triple_te.csv", f"Sub 9: CatBoost Triple TE Oblivious (CV {cv_m4:.5f})")
save_and_verify(test_m5, "submission_10_top10_master_blend.csv", f"Sub 10: Master Rank Nelder-Mead Blend (CV {cv_m5:.5f})")

print("\n🎉 ALL 5 TOP-10 SUBMISSIONS GENERATED AND VERIFIED SUCCESSFULLY!")
