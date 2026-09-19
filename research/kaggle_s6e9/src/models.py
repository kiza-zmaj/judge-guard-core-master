import numpy as np
import pandas as pd
from typing import Tuple, List, Optional
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import roc_auc_score
import lightgbm as lgb
import xgboost as xgb
from catboost import CatBoostClassifier

def train_lgbm_baseline(
    X: pd.DataFrame, 
    y: np.ndarray, 
    X_test: pd.DataFrame, 
    folds: StratifiedKFold, 
    seed: int = 42
) -> Tuple[np.ndarray, np.ndarray, float]:
    """
    Model 1: Baseline 10-Fold LightGBM.
    Serves as clean benchmark and CV anchor.
    """
    print("\n🚀 [Model 1] Training Baseline 10-Fold LightGBM...")
    oof_preds = np.zeros(len(X))
    test_preds = np.zeros(len(X_test))
    
    params = {
        "objective": "binary",
        "metric": "auc",
        "boosting_type": "gbdt",
        "learning_rate": 0.05,
        "num_leaves": 63,
        "colsample_bytree": 0.75,
        "subsample": 0.8,
        "random_state": seed,
        "n_jobs": -1,
        "verbose": -1,
    }
    
    for fold, (trn_idx, val_idx) in enumerate(folds.split(X, y)):
        X_train, y_train = X.iloc[trn_idx], y[trn_idx]
        X_val, y_val = X.iloc[val_idx], y[val_idx]
        
        trn_data = lgb.Dataset(X_train, label=y_train)
        val_data = lgb.Dataset(X_val, label=y_val, reference=trn_data)
        
        model = lgb.train(
            params,
            trn_data,
            num_boost_round=1200,
            valid_sets=[trn_data, val_data],
            callbacks=[lgb.early_stopping(50, verbose=False), lgb.log_evaluation(0)],
        )
        
        val_pred = model.predict(X_val)
        oof_preds[val_idx] = val_pred
        test_preds += model.predict(X_test) / folds.n_splits
        
        fold_auc = roc_auc_score(y_val, val_pred)
        print(f"  Fold {fold + 1}/{folds.n_splits} AUC: {fold_auc:.6f}")
        
    overall_auc = roc_auc_score(y, oof_preds)
    print(f"✅ [Model 1 Complete] Baseline LightGBM Overall 10-Fold CV AUC: {overall_auc:.6f}")
    return oof_preds, test_preds, overall_auc

def train_catboost_symmetric(
    X: pd.DataFrame, 
    y: np.ndarray, 
    X_test: pd.DataFrame, 
    folds: StratifiedKFold, 
    seed: int = 42
) -> Tuple[np.ndarray, np.ndarray, float]:
    """
    Model 2: CatBoost with Oblivious Symmetric Trees.
    Provides structural orthogonality against leaf-wise GBDTs.
    """
    print("\n🚀 [Model 2] Training CatBoost Symmetric Trees (10-Fold)...")
    oof_preds = np.zeros(len(X))
    test_preds = np.zeros(len(X_test))
    
    for fold, (trn_idx, val_idx) in enumerate(folds.split(X, y)):
        X_train, y_train = X.iloc[trn_idx], y[trn_idx]
        X_val, y_val = X.iloc[val_idx], y[val_idx]
        
        model = CatBoostClassifier(
            iterations=1200,
            learning_rate=0.06,
            depth=6,
            eval_metric="AUC",
            random_seed=seed + fold,
            task_type="CPU",
            verbose=0,
            early_stopping_rounds=50,
        )
        
        model.fit(X_train, y_train, eval_set=(X_val, y_val), verbose=False)
        
        val_pred = model.predict_proba(X_val)[:, 1]
        oof_preds[val_idx] = val_pred
        test_preds += model.predict_proba(X_test)[:, 1] / folds.n_splits
        
        fold_auc = roc_auc_score(y_val, val_pred)
        print(f"  Fold {fold + 1}/{folds.n_splits} AUC: {fold_auc:.6f}")
        
    overall_auc = roc_auc_score(y, oof_preds)
    print(f"✅ [Model 2 Complete] CatBoost Overall 10-Fold CV AUC: {overall_auc:.6f}")
    return oof_preds, test_preds, overall_auc

def train_xgboost_formula_margin(
    X: pd.DataFrame, 
    y: np.ndarray, 
    X_test: pd.DataFrame, 
    folds: StratifiedKFold, 
    train_margin: np.ndarray, 
    test_margin: np.ndarray, 
    seed: int = 42
) -> Tuple[np.ndarray, np.ndarray, float]:
    """
    Model 3: XGBoost with base_margin Prior + String-Safe Digits + Simpson Pairs.
    Direct implementation of Chris Deotte's discovered generator formula injection.
    """
    print("\n🚀 [Model 3] Training XGBoost with Generator base_margin Prior...")
    oof_preds = np.zeros(len(X))
    test_preds = np.zeros(len(X_test))
    
    dtest = xgb.DMatrix(X_test, base_margin=test_margin)
    
    params = {
        "objective": "binary:logistic",
        "eval_metric": "auc",
        "tree_method": "hist",
        "learning_rate": 0.05,
        "max_depth": 6,
        "colsample_bytree": 0.75,
        "subsample": 0.85,
        "random_state": seed,
        "nthread": -1,
    }
    
    for fold, (trn_idx, val_idx) in enumerate(folds.split(X, y)):
        X_train, y_train = X.iloc[trn_idx], y[trn_idx]
        X_val, y_val = X.iloc[val_idx], y[val_idx]
        
        dtrain = xgb.DMatrix(X_train, label=y_train, base_margin=train_margin[trn_idx])
        dval = xgb.DMatrix(X_val, label=y_val, base_margin=train_margin[val_idx])
        
        evallist = [(dtrain, "train"), (dval, "val")]
        
        bst = xgb.train(
            params,
            dtrain,
            num_boost_round=1200,
            evals=evallist,
            early_stopping_rounds=50,
            verbose_eval=False,
        )
        
        val_pred = bst.predict(dval)
        oof_preds[val_idx] = val_pred
        test_preds += bst.predict(dtest) / folds.n_splits
        
        fold_auc = roc_auc_score(y_val, val_pred)
        print(f"  Fold {fold + 1}/{folds.n_splits} AUC: {fold_auc:.6f}")
        
    overall_auc = roc_auc_score(y, oof_preds)
    print(f"✅ [Model 3 Complete] XGBoost Margin Overall 10-Fold CV AUC: {overall_auc:.6f}")
    return oof_preds, test_preds, overall_auc

def train_lgbm_init_score(
    X: pd.DataFrame, 
    y: np.ndarray, 
    X_test: pd.DataFrame, 
    folds: StratifiedKFold, 
    train_margin: np.ndarray, 
    test_margin: np.ndarray, 
    seed: int = 101
) -> Tuple[np.ndarray, np.ndarray, float]:
    """
    Model 4: LightGBM with init_score Generator Prior and Constrained Depth.
    Provides diverse prior-guided boosting representation.
    """
    print("\n🚀 [Model 4] Training LightGBM with Generator init_score Prior...")
    oof_preds = np.zeros(len(X))
    test_preds = np.zeros(len(X_test))
    
    params = {
        "objective": "binary",
        "metric": "auc",
        "boosting_type": "gbdt",
        "learning_rate": 0.04,
        "num_leaves": 45,
        "max_depth": 7,
        "colsample_bytree": 0.70,
        "subsample": 0.85,
        "random_state": seed,
        "n_jobs": -1,
        "verbose": -1,
    }
    
    for fold, (trn_idx, val_idx) in enumerate(folds.split(X, y)):
        X_train, y_train = X.iloc[trn_idx], y[trn_idx]
        X_val, y_val = X.iloc[val_idx], y[val_idx]
        
        trn_data = lgb.Dataset(X_train, label=y_train, init_score=train_margin[trn_idx])
        val_data = lgb.Dataset(X_val, label=y_val, reference=trn_data, init_score=train_margin[val_idx])
        
        model = lgb.train(
            params,
            trn_data,
            num_boost_round=1200,
            valid_sets=[trn_data, val_data],
            callbacks=[lgb.early_stopping(50, verbose=False), lgb.log_evaluation(0)],
        )
        
        # In LightGBM with init_score, raw predict requires passing init_score or raw score
        # Using model.predict returns the calibrated probability including init_score
        val_raw = model.predict(X_val, raw_score=True) + train_margin[val_idx]
        val_pred = 1.0 / (1.0 + np.exp(-val_raw))
        oof_preds[val_idx] = val_pred
        
        test_raw = model.predict(X_test, raw_score=True) + test_margin
        test_pred = 1.0 / (1.0 + np.exp(-test_raw))
        test_preds += test_pred / folds.n_splits
        
        fold_auc = roc_auc_score(y_val, val_pred)
        print(f"  Fold {fold + 1}/{folds.n_splits} AUC: {fold_auc:.6f}")
        
    overall_auc = roc_auc_score(y, oof_preds)
    print(f"✅ [Model 4 Complete] LightGBM init_score Overall 10-Fold CV AUC: {overall_auc:.6f}")
    return oof_preds, test_preds, overall_auc
