import numpy as np
import pandas as pd
from typing import Tuple, Dict, Any, List

def compute_generator_utility(df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
    """
    Reconstructs the latent utility formula discovered by Chris Deotte & Fable 5.1:
    utility = 1.2 * (Income / 100,000) 
            + 0.6 * Environmental_Concern_Level 
            + 2.0 * Subsidy_Available (1 for Yes, 0 for No)
            - 1.0 * (Range_Anxiety == 'Medium')
            - 3.0 * (Range_Anxiety == 'High')
    Threshold ~ 5.5.
    
    Returns:
        utility: Raw continuous score
        margin: Log-odds prior for base_margin (XGBoost) and init_score (LightGBM)
    """
    income_term = 1.2 * (df["Annual_Income_USD"].astype(float) / 100000.0)
    env_term = 0.6 * df["Environmental_Concern_Level"].astype(float)
    
    subsidy_flag = df["Subsidy_Available"].map({"Yes": 1.0, "No": 0.0, 1: 1.0, 0: 0.0, 1.0: 1.0, 0.0: 0.0}).fillna(0.0)
    subsidy_term = 2.0 * subsidy_flag
    
    anx_med = (df["Range_Anxiety_Level"].str.lower() == "medium").astype(float)
    anx_high = (df["Range_Anxiety_Level"].str.lower() == "high").astype(float)
    anxiety_term = -1.0 * anx_med - 3.0 * anx_high
    
    raw_utility = income_term + env_term + subsidy_term + anxiety_term
    # Net utility relative to decision threshold 5.5
    net_utility = raw_utility - 5.5
    
    # Clip margin to reasonable log-odds bounds [-5.0, 5.0] to prevent gradient explosion
    base_margin = np.clip(net_utility.values, -5.0, 5.0)
    
    return raw_utility.values, base_margin

def extract_string_safe_digits(df: pd.DataFrame, col: str, is_decimal: bool = False) -> pd.DataFrame:
    """
    Extracts digit decomposition safely from string representations to avoid
    Python's IEEE-754 floating-point truncation bugs (flagged in Kaggle discussion #740824).
    """
    str_series = df[col].astype(str)
    splits = str_series.str.split(".", expand=True)
    int_parts = splits[0].fillna("")
    
    digits_df = pd.DataFrame(index=df.index)
    
    # Integer digits (1s, 10s, 100s, 1000s, 10000s)
    for pos, power in enumerate([1, 2, 3, 4, 5]):
        # pos 0 -> last char (10^0), pos 1 -> second to last (10^1)
        digits_df[f"{col}_digit_10e{pos}"] = int_parts.str[-power:-power+1 if power > 1 else None].replace("", "0").astype(int)
    
    if is_decimal and splits.shape[1] > 1:
        dec_parts = splits[1].fillna("")
        for pos in range(3): # tenths, hundredths, thousandths
            digits_df[f"{col}_dec_10e_neg{pos+1}"] = dec_parts.str[pos:pos+1].replace("", "0").astype(int)
            
    return digits_df

def build_features(train_df: pd.DataFrame, test_df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame, np.ndarray, np.ndarray]:
    """
    Transforms raw DataFrames into high-signal feature matrices incorporating:
    1. Reconstructed generator formula features & prior base_margins.
    2. String-safe digit decomposition.
    3. Simpson's paradox cross-features.
    4. Deterministic edge flags & frequency encoding of generator clumping points.
    5. Clean ordinal and categorical encodings.
    """
    print("🛠️ [Feature Engineering] Building generator forensics feature set...")
    
    df_all = pd.concat([train_df.assign(is_test=0), test_df.assign(is_test=1)], ignore_index=True)
    
    # 1. Generator Utility & Prior Margins
    train_util, train_margin = compute_generator_utility(train_df)
    test_util, test_margin = compute_generator_utility(test_df)
    
    df_all["formula_buy_score"], df_all["formula_margin"] = compute_generator_utility(df_all)
    df_all["formula_prob"] = 1.0 / (1.0 + np.exp(-df_all["formula_margin"]))
    
    # 2. String-Safe Digit Decomposition (Income, Commute, Age)
    print("  -> Extracting string-safe digit features...")
    income_digits = extract_string_safe_digits(df_all, "Annual_Income_USD", is_decimal=False)
    commute_digits = extract_string_safe_digits(df_all, "Daily_Commute_km", is_decimal=True)
    age_digits = extract_string_safe_digits(df_all, "Age", is_decimal=False)
    
    df_all = pd.concat([df_all, income_digits, commute_digits, age_digits], axis=1)
    
    # 3. Simpson's Paradox & Charger Subgroup Features
    print("  -> Creating Simpson's paradox interaction terms...")
    home_charging_num = df_all["Home_Charging_Possible"].map({"Yes": 1, "No": 0, 1: 1, 0: 0}).fillna(0).astype(int)
    subsidy_num = df_all["Subsidy_Available"].map({"Yes": 1, "No": 0, 1: 1, 0: 0}).fillna(0).astype(int)
    
    df_all["chargers_total"] = df_all["Charging_Stations_Near_Home"] + df_all["Charging_Stations_Near_Work"]
    df_all["chargers_diff"] = df_all["Charging_Stations_Near_Home"] - df_all["Charging_Stations_Near_Work"]
    
    # The Simpson's reversal term: chargers * home_charging
    df_all["home_charge_x_home_stations"] = home_charging_num * df_all["Charging_Stations_Near_Home"]
    df_all["home_charge_x_total_stations"] = home_charging_num * df_all["chargers_total"]
    
    # Commute to infrastructure ratio
    df_all["commute_to_chargers_ratio"] = df_all["Daily_Commute_km"] / (df_all["chargers_total"] + 1.0)
    df_all["income_to_commute_ratio"] = df_all["Annual_Income_USD"] / (df_all["Daily_Commute_km"] + 1.0)
    df_all["income_x_subsidy"] = df_all["Annual_Income_USD"] * subsidy_num
    
    # 4. Deterministic Hard Edges & Discrete Cluster Artifacts
    print("  -> Encoding deterministic bounds and generator cluster spikes...")
    # Edge discovered in discussion #738968: Income >= $170,537 has 100% buy rate
    df_all["is_income_above_170537"] = (df_all["Annual_Income_USD"] >= 170537.0).astype(int)
    
    # Discrete generator spikes
    df_all["is_income_30k_spike"] = (df_all["Annual_Income_USD"] == 30000.0).astype(int)
    df_all["is_commute_5km_cluster"] = ((df_all["Daily_Commute_km"] >= 4.8) & (df_all["Daily_Commute_km"] <= 5.2)).astype(int)
    df_all["is_commute_83km_cluster"] = ((df_all["Daily_Commute_km"] >= 82.8) & (df_all["Daily_Commute_km"] <= 83.2)).astype(int)
    
    # Rounded frequency features (clustering signatures)
    commute_rounded = df_all["Daily_Commute_km"].round(1)
    df_all["commute_rounded_freq"] = commute_rounded.map(commute_rounded.value_counts(normalize=True))
    
    income_rounded_10k = (df_all["Annual_Income_USD"] // 10000) * 10000
    df_all["income_10k_freq"] = income_rounded_10k.map(income_rounded_10k.value_counts(normalize=True))
    
    # 5. Categorical Encoding
    print("  -> Encoding categoricals and interactions...")
    # Ordinal mappings
    anxiety_map = {"Low": 0, "Medium": 1, "High": 2}
    df_all["range_anxiety_ordinal"] = df_all["Range_Anxiety_Level"].map(anxiety_map).fillna(1).astype(int)
    
    # Label encoding for remaining strings
    cat_cols_to_encode = ["Gender", "City_Type", "Current_Car_Type", "Home_Charging_Possible", "Subsidy_Available"]
    for c in cat_cols_to_encode:
        df_all[c] = df_all[c].astype("category").cat.codes
        
    # Interaction categorical codes
    df_all["city_x_home_charge"] = (df_all["City_Type"].astype(str) + "_" + df_all["Home_Charging_Possible"].astype(str)).astype("category").cat.codes
    df_all["city_x_anxiety"] = (df_all["City_Type"].astype(str) + "_" + df_all["range_anxiety_ordinal"].astype(str)).astype("category").cat.codes
    
    # Drop raw unneeded text columns
    if "Range_Anxiety_Level" in df_all.columns:
        df_all = df_all.drop(columns=["Range_Anxiety_Level"])
        
    # Split back to train and test
    train_feats = df_all[df_all["is_test"] == 0].drop(columns=["is_test"]).copy()
    test_feats = df_all[df_all["is_test"] == 1].drop(columns=["is_test", "Will_Buy_EV"], errors="ignore").copy()
    
    print(f"✅ [Feature Engineering Complete] Total features generated: {train_feats.shape[1] - 2}")
    
    return train_feats, test_feats, train_margin, test_margin
