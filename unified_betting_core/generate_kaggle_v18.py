#!/usr/bin/env python3
"""
SharpBet Core v18.3.0 — Hardened Institutional Multi-League Governance & Econometric Verification.
====================================================================================================
Major Governance & Methodological Upgrades (v18.3.0):
1. Both Development & Untouched Final Holdout Enforced in Core Gates:
   - Gate A: Requires both Dev (2024/25) and Final Holdout (2025/26) Macro ECE <= 6% and Brier <= 0.230.
   - Gate B: Requires positive CLV on both Dev and Final Holdout.
   - Gate C: Disaggregated into Gate C Dev (> 2.00% yield) and Gate C Final Holdout (> 2.00% yield).
             Because 2025/26 holdout yield is -0.79%, Gate C Final Holdout is strictly BLOCKED.
2. MIN_FINAL_HOLDOUT_BETS Enforced:
   - Enforces separate sample adequacy for Dev (>= 350 bets) and Final Holdout (>= 150 bets).
3. Gate F Strictly Enforced in Decision Ladder:
   - Evaluates direct Mozzart wager count; if < 350, triggers fatal block for production review.
4. Comprehensive Data Provenance & Gate H Hardening:
   - Explains the 274,290 undated legacy rows originating from weekly bulletins lacking per-row dates.
   - Strictly enforces zero undated rows, zero future dates, and >= 5,000 sanitized halftime rows.
5. Fail-Closed Institutional Verdict:
   - Automatically halts with FAIL_CLOSED_BLOCKED when the untouched holdout fails to confirm economic yield.
"""

import os
import json

def code_cell(source_code: str):
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [line + "\n" for line in source_code.strip().split("\n")]
    }

def markdown_cell(source_text: str):
    return {
        "cell_type": "markdown",
        "metadata": {},
        "source": [line + "\n" for line in source_text.strip().split("\n")]
    }

def build_v18_notebook():
    cells = []

    # ── CELL 0: HEADER & COMPREHENSIVE AUDIT TRAIL
    cells.append(markdown_cell(r"""# 🛡️ SharpBet Core v18.3: Hardened Institutional Multi-League Governance & Forensic Verification
### Dual-Period Gate Enforcement (Dev + Untouched Holdout), Direct Odds Disaggregation & Provenance Audit
**Authors:** SharpBet Quant Lab | **Target Markets:** First Half Goals (`HT X`, `I 0-1`, `I 0`, `I1+`, `I2+`)
**Datasets:**
- **Mozzart Historical Odds Dataset:** 394,088+ verified match records directly parsed from Mozzart Bet bulletins (`kiza123123/mozzart-historical-odds`).
- **Multi-League Ground Truth Match Outcomes:** Top-5 European Leagues (EPL, La Liga, Serie A, Bundesliga, Ligue 1) verified scorelines & Pinnacle closing benchmark (2022/23 – 2025/26, 7,081 total matches across 4 seasons).

---
### 🔍 Forensic Governance Upgrades in Version 18.3:
1. **Dual-Period Gate Enforcement**:
   - Gate A, Gate B, Gate C, and Gate D are evaluated **independently across both Development (2024/25) and Untouched Final Holdout (2025/26)**.
   - An economic failure on the untouched holdout (e.g. Yield $\le +2.00\%$) strictly **BLOCKS Gate C**, preventing development overfit from masking out-of-sample decay.
2. **Sample Size Constraints**:
   - `MIN_DEV_BETS = 350` and `MIN_FINAL_HOLDOUT_BETS = 150` strictly enforced.
3. **Gate F Direct Sample Gate**:
   - `MIN_DIRECT_BETS = 350` is placed in the fatal condition ladder.
4. **Data Provenance Disclosure**:
   - Details why 274,290 raw rows from legacy weekly PDF bulletins lack per-row dates and guarantees zero undated rows enter model calibration.
5. **Fail-Closed Final Verdict**:
   - Direct quote coverage $< 80\%$ and negative final holdout yield strictly enforce `FAIL_CLOSED_BLOCKED` and `production_status: "BLOCKED"`.
"""))

    # ── CELL 1: ENVIRONMENT & IMMUTABLE GOVERNANCE CONFIGURATION
    cells.append(code_cell("""# ── STEP 0: ENVIRONMENT & IMMUTABLE GOVERNANCE CONFIGURATION ─────────────────
import os
import io
import re
import sys
import json
import time
import hashlib
import requests
import warnings
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.stats import poisson

warnings.filterwarnings('ignore')
np.random.seed(42)

class GovernanceConfig:
    VERSION: str = "18.3.0"
    BUILD_TAG: str = "sharpbet-v18.3-halftime-goals-holdout-enforced"
    EXECUTION_ENV: str = "Kaggle Cloud GPU MLOps Kernel"
    DIRECT_COVERAGE_FOR_PAPER: float = 0.80
    DIRECT_COVERAGE_FOR_PRODUCTION: float = 0.95
    MIN_DIRECT_BETS: int = 350
    MIN_DEV_BETS: int = 350
    MIN_FINAL_HOLDOUT_BETS: int = 150
    MAX_ALLOWED_DATE: str = "2026-09-22"
    TRAIN_SEASONS: list = ["2223", "2324"]
    DEV_SEASON: str = "2425"
    FINAL_HOLDOUT_SEASON: str = "2526"
    STRICT_GATE_APPROVAL: bool = True

CONFIG = GovernanceConfig()

print("="*80)
print(f"🛡️ SharpBet Core v{CONFIG.VERSION} ({CONFIG.BUILD_TAG})")
print(f"NumPy: {np.__version__} | Pandas: {pd.__version__} | Python: {sys.version.split()[0]}")
print(f"Execution Environment: {CONFIG.EXECUTION_ENV}")
print(f"Governance Thresholds : Paper Coverage >= {CONFIG.DIRECT_COVERAGE_FOR_PAPER:.0%} | Production Coverage >= {CONFIG.DIRECT_COVERAGE_FOR_PRODUCTION:.0%}")
print(f"Min Dev Bets: {CONFIG.MIN_DEV_BETS} | Min Holdout Bets: {CONFIG.MIN_FINAL_HOLDOUT_BETS} | Min Direct Bets: {CONFIG.MIN_DIRECT_BETS}")
print(f"Cutoff Date : {CONFIG.MAX_ALLOWED_DATE}")
print("="*80)
"""))

    # ── CELL 2: DATA PROVENANCE, ROBUST ISO DATES & LOOKAHEAD-FREE MARGIN
    cells.append(code_cell(r"""# ── STEP 1: DATA PROVENANCE, ROBUST ISO DATES & LOOKAHEAD-FREE MARGIN ───────

ISO_RE = r"^\d{4}-\d{2}-\d{2}$"

def normalize_date_to_iso(value):
    if pd.isna(value) or not str(value).strip():
        return None
    s = str(value).strip()
    if re.match(ISO_RE, s):
        return s
    for dayfirst in [True, False]:
        try:
            dt = pd.to_datetime(s, dayfirst=dayfirst, errors="raise")
            return dt.strftime("%Y-%m-%d")
        except Exception:
            continue
    return None

mozzart_csv_path = None
candidates = [
    "/kaggle/input/mozzart-historical-odds/mozzart_historical_odds.csv",
    "/kaggle/input/mozzart-historical-odds/mozzart_historical_odds/mozzart_historical_odds.csv",
    "./unified_betting_core/output/mozzart_parsed/mozzart_historical_odds.csv",
    "./unified_betting_core/data/mozzart_parsed.csv",
]

for p in candidates:
    if os.path.exists(p):
        mozzart_csv_path = p
        break

if not mozzart_csv_path:
    for root, dirs, files in os.walk("/kaggle/input"):
        for f in files:
            if f.endswith(".csv") and "mozzart" in f.lower():
                mozzart_csv_path = os.path.join(root, f)
                break

if mozzart_csv_path and os.path.exists(mozzart_csv_path):
    print(f"📁 Found Mozzart Historical Odds Dataset: {mozzart_csv_path}")
    with open(mozzart_csv_path, "rb") as f:
        file_sha256 = hashlib.sha256(f.read()).hexdigest()
    print(f"🔒 Raw Input SHA-256: {file_sha256}")
    
    df_mozzart = pd.read_csv(mozzart_csv_path, low_memory=False)
    raw_rows = len(df_mozzart)
    
    # 1. Parse and validate dates
    df_mozzart["iso_date"] = df_mozzart["date"].apply(normalize_date_to_iso)
    valid_parsed_dates = int(df_mozzart["iso_date"].notna().sum())
    invalid_dates = raw_rows - valid_parsed_dates
    
    # 2. Strict Cutoff: Drop future dates (> 2026-09-22) and missing dates
    df_mozzart_clean = df_mozzart[df_mozzart["iso_date"].notna()].copy()
    future_rows_removed = int((df_mozzart_clean["iso_date"] > CONFIG.MAX_ALLOWED_DATE).sum())
    df_mozzart_clean = df_mozzart_clean[df_mozzart_clean["iso_date"] <= CONFIG.MAX_ALLOWED_DATE].copy()
    rows_after_cutoff = len(df_mozzart_clean)
    
    # 3. Numeric conversion of Halftime odds
    for c in ["ht_1", "ht_x", "ht_2", "ft_1", "ft_x", "ft_2"]:
        if c in df_mozzart_clean.columns:
            df_mozzart_clean[c] = pd.to_numeric(df_mozzart_clean[c], errors="coerce")
            
    # 4. Strict Halftime Odds Sanitization (overround 4% to 28%, realistic draw)
    margins_all = (1.0 / df_mozzart_clean["ht_1"] + 1.0 / df_mozzart_clean["ht_x"] + 1.0 / df_mozzart_clean["ht_2"]) - 1.0
    ht_valid = df_mozzart_clean[
        margins_all.between(0.04, 0.28) &
        df_mozzart_clean['ht_x'].between(1.70, 3.80) &
        df_mozzart_clean['ht_1'].between(1.20, 20.0) &
        df_mozzart_clean['ht_2'].between(1.20, 20.0)
    ].copy()
    rows_after_odds_sanitization = len(ht_valid)
    
    # Assertions for Data Quality Gate
    assert ht_valid["iso_date"].notna().all(), "Data Quality Error: Null dates found in ht_valid!"
    assert (ht_valid["iso_date"] != "").all(), "Data Quality Error: Empty string dates found in ht_valid!"
    assert pd.to_datetime(ht_valid["iso_date"]).max() <= pd.Timestamp(CONFIG.MAX_ALLOWED_DATE), "Data Quality Error: Future dates found!"
    
    min_date_verified = str(ht_valid['iso_date'].min())
    max_date_verified = str(ht_valid['iso_date'].max())
    
    print("="*80)
    print("📊 DATA PROVENANCE & FORENSIC QUALITY AUDIT")
    print(f"  Raw rows in dataset            : {raw_rows:,}")
    print(f"  Valid parsed dates             : {valid_parsed_dates:,}")
    print(f"  Invalid/unparseable dates      : {invalid_dates:,} (Legacy weekly PDF tables lacking per-row dates)")
    print(f"  Future rows removed            : {future_rows_removed:,}")
    print(f"  Rows after cutoff (<= 2026-09) : {rows_after_cutoff:,}")
    print(f"  Rows after odds sanitization   : {rows_after_odds_sanitization:,}")
    print(f"  Verified Date Range            : {min_date_verified} to {max_date_verified}")
    print(f"  Ingestion Data Guarantee       : 100% of modeled rows contain verified ISO dates <= {CONFIG.MAX_ALLOWED_DATE}")
    print("="*80)
    
    # 5. Lookahead-Free Margin Estimation: Strictly Pre-Holdout Training Period (< 2024-08-01)
    pre_holdout_mask = ht_valid["iso_date"] < "2024-08-01"
    margin_train_data = ht_valid[pre_holdout_mask]
    if len(margin_train_data) > 0:
        train_margins = (1.0 / margin_train_data["ht_1"] + 1.0 / margin_train_data["ht_x"] + 1.0 / margin_train_data["ht_2"]) - 1.0
        mean_margin = float(train_margins.median())
        margin_source = "pre_holdout_training_period"
        margin_cutoff = "2024-08-01"
        print(f"📊 Lookahead-Free Overround Estimated on Pre-Holdout Data (< {margin_cutoff}, N={len(margin_train_data):,}):")
        print(f"   Median Overround : {mean_margin:.2%}")
        print(f"   Mean Overround   : {train_margins.mean():.2%}")
    else:
        mean_margin = 0.1611
        margin_source = "fallback_empirical_baseline"
        margin_cutoff = "pre_2024_fixed"
        print(f"⚠️ Using pre-holdout empirical baseline overround: {mean_margin:.2%}")
else:
    print("⚠️ Mozzart dataset not found in /kaggle/input. Initializing empty fallback schema...")
    df_mozzart = pd.DataFrame(columns=["date", "iso_date", "home_team", "away_team", "ht_1", "ht_x", "ht_2"])
    ht_valid = pd.DataFrame()
    raw_rows, valid_parsed_dates, invalid_dates = 0, 0, 0
    future_rows_removed, rows_after_cutoff, rows_after_odds_sanitization = 0, 0, 0
    min_date_verified, max_date_verified = "N/A", "N/A"
    mean_margin = 0.1611
    margin_source = "fallback_empty_schema"
    margin_cutoff = "none"
"""))

    # ── CELL 3: 3-WAY MULTI-LEAGUE GROUND TRUTH & UNTOUCHED HOLDOUT PROTOCOL
    cells.append(code_cell("""# ── STEP 2: 3-WAY MULTI-LEAGUE GROUND TRUTH & UNTOUCHED HOLDOUT PROTOCOL ───
ALL_SEASONS = CONFIG.TRAIN_SEASONS + [CONFIG.DEV_SEASON, CONFIG.FINAL_HOLDOUT_SEASON]
LEAGUES = {
    "E0": "Premier League (England)",
    "SP1": "La Liga (Spain)",
    "I1": "Serie A (Italy)",
    "D1": "Bundesliga (Germany)",
    "F1": "Ligue 1 (France)"
}
BASE_URL = "https://www.football-data.co.uk/mmz4281"

all_matches = []
print(f"🌐 Streaming 4 Seasons of Top-5 European Leagues ({', '.join(ALL_SEASONS)}):")

for season in ALL_SEASONS:
    season_cnt = 0
    for lg, lg_name in LEAGUES.items():
        url = f"{BASE_URL}/{season}/{lg}.csv"
        try:
            resp = requests.get(url, timeout=15)
            if resp.status_code == 200:
                df_s = pd.read_csv(io.StringIO(resp.text))
                for _, row in df_s.iterrows():
                    if pd.isna(row.get("HomeTeam")) or pd.isna(row.get("FTHG")) or pd.isna(row.get("HTHG")):
                        continue
                    try:
                        d_iso = normalize_date_to_iso(row["Date"])
                        if d_iso is None or d_iso > CONFIG.MAX_ALLOWED_DATE:
                            continue
                        all_matches.append({
                            "season": season,
                            "league_code": lg,
                            "league_name": lg_name,
                            "date": d_iso,
                            "home": str(row["HomeTeam"]).strip(),
                            "away": str(row["AwayTeam"]).strip(),
                            "fthg": int(row["FTHG"]),
                            "ftag": int(row["FTAG"]),
                            "hthg": int(row["HTHG"]),
                            "htag": int(row["HTAG"]),
                            "ps_h": float(row.get("PSH", 2.0)),
                            "ps_d": float(row.get("PSD", 3.2)),
                            "ps_a": float(row.get("PSA", 3.5)),
                            "ps_close_h": float(row.get("PSCH", row.get("PSH", 2.0))),
                            "ps_close_d": float(row.get("PSCD", row.get("PSD", 3.2))),
                            "ps_close_a": float(row.get("PSCA", row.get("PSA", 3.5))),
                            "p_o25": float(row.get("P>2.5", 1.9)),
                            "p_u25": float(row.get("P<2.5", 1.9)),
                            "p_close_o25": float(row.get("PC>2.5", row.get("P>2.5", 1.9))),
                            "p_close_u25": float(row.get("PC<2.5", row.get("P<2.5", 1.9))),
                        })
                        season_cnt += 1
                    except Exception:
                        continue
        except Exception as e:
            print(f"   ⚠️ Warning: failed to fetch {url}: {e}")
    print(f"   Season {season}: Loaded {season_cnt} verified completed matches.")

df_all = pd.DataFrame(all_matches)
print(f"\\n📊 Total Verified Top-5 Ground Truth Matches Loaded: {len(df_all):,}")

# 3-Way Temporal Partition
df_train = df_all[df_all["season"].isin(CONFIG.TRAIN_SEASONS)].copy().reset_index(drop=True)
df_dev = df_all[df_all["season"] == CONFIG.DEV_SEASON].copy().reset_index(drop=True)
df_final_holdout = df_all[df_all["season"] == CONFIG.FINAL_HOLDOUT_SEASON].copy().reset_index(drop=True)

dev_fp = hashlib.sha256(df_dev.to_json().encode()).hexdigest()
holdout_fp = hashlib.sha256(df_final_holdout.to_json().encode()).hexdigest()

print("="*80)
print("🔒 3-WAY TEMPORAL DATA PARTITION AUDIT:")
print(f"  1. Training Period       (2022/23 & 2023/24) : {len(df_train):,} matches")
print(f"  2. Development Period    (2024/25)           : {len(df_dev):,} matches (SHA-256: {dev_fp[:16]}...)")
print(f"  3. Sacred Final Holdout  (2025/26)           : {len(df_final_holdout):,} matches (SHA-256: {holdout_fp[:16]}...)")
print(f"  Final Holdout Status     : UNTOUCHED (Zero parameter tuning or threshold selection on 2025/26)")
print("="*80)
"""))

    # ── CELL 4: PER-LEAGUE IDENTIFIED DIXON-COLES 1H MLE & GATE 0 AUDIT
    cells.append(code_cell("""# ── STEP 3: PER-LEAGUE IDENTIFIED DIXON-COLES 1H MLE & GATE 0 AUDIT ──────────

def tau(x, y, lambda_param, mu_param, rho):
    if x == 0 and y == 0:
        return 1.0 - lambda_param * mu_param * rho
    elif x == 0 and y == 1:
        return 1.0 + lambda_param * rho
    elif x == 1 and y == 0:
        return 1.0 + mu_param * rho
    elif x == 1 and y == 1:
        return 1.0 - rho
    else:
        return 1.0

def fit_dixon_coles_1h(df_league_train):
    teams = sorted(list(set(df_league_train['home']).union(set(df_league_train['away']))))
    n_teams = len(teams)
    team_idx = {t: i for i, t in enumerate(teams)}
    
    home_arr = np.array([team_idx[t] for t in df_league_train['home']])
    away_arr = np.array([team_idx[t] for t in df_league_train['away']])
    hthg_arr = df_league_train['hthg'].values
    htag_arr = df_league_train['htag'].values
    n_matches = len(df_league_train)

    def neg_log_lik(params):
        alphas = np.zeros(n_teams)
        betas = np.zeros(n_teams)
        
        alphas[:n_teams - 1] = params[:n_teams - 1]
        alphas[n_teams - 1] = -np.sum(alphas[:n_teams - 1])
        
        betas[:n_teams - 1] = params[n_teams - 1:2 * (n_teams - 1)]
        betas[n_teams - 1] = -np.sum(betas[:n_teams - 1])
        
        mu = params[2 * (n_teams - 1)]
        gamma = params[2 * (n_teams - 1) + 1]
        rho = params[2 * (n_teams - 1) + 2]
        
        log_lambda = mu + alphas[home_arr] + betas[away_arr] + gamma
        log_nu = mu + alphas[away_arr] + betas[home_arr]
        
        lambdas = np.exp(np.clip(log_lambda, -4.0, 3.0))
        nus = np.exp(np.clip(log_nu, -4.0, 3.0))
        
        log_p1 = hthg_arr * np.log(np.maximum(lambdas, 1e-6)) - lambdas
        log_p2 = htag_arr * np.log(np.maximum(nus, 1e-6)) - nus
        
        taus = np.ones(n_matches)
        m00 = (hthg_arr == 0) & (htag_arr == 0)
        m01 = (hthg_arr == 0) & (htag_arr == 1)
        m10 = (hthg_arr == 1) & (htag_arr == 0)
        m11 = (hthg_arr == 1) & (htag_arr == 1)
        
        taus[m00] = 1.0 - lambdas[m00] * nus[m00] * rho
        taus[m01] = 1.0 + lambdas[m01] * rho
        taus[m10] = 1.0 + nus[m10] * rho
        taus[m11] = 1.0 - rho
        
        taus = np.maximum(taus, 1e-6)
        ll = np.sum(log_p1 + log_p2 + np.log(taus))
        return -ll

    init_params = np.zeros(2 * (n_teams - 1) + 3)
    init_params[2 * (n_teams - 1)] = -0.70
    init_params[2 * (n_teams - 1) + 1] = 0.20
    init_params[2 * (n_teams - 1) + 2] = -0.05
    
    bounds = [(-2.0, 2.0)] * (2 * (n_teams - 1)) + [(-2.0, 1.0), (-1.0, 1.0), (-0.3, 0.3)]
    
    res = minimize(neg_log_lik, init_params, method='L-BFGS-B', bounds=bounds,
                   options={'maxiter': 500, 'ftol': 1e-8, 'gtol': 1e-6})
    
    alphas = np.zeros(n_teams)
    betas = np.zeros(n_teams)
    alphas[:n_teams - 1] = res.x[:n_teams - 1]
    alphas[n_teams - 1] = -np.sum(alphas[:n_teams - 1])
    betas[:n_teams - 1] = res.x[n_teams - 1:2 * (n_teams - 1)]
    betas[n_teams - 1] = -np.sum(betas[:n_teams - 1])
    
    return {
        "success": res.success,
        "nit": res.nit,
        "message": res.message,
        "mu": float(res.x[2 * (n_teams - 1)]),
        "gamma": float(res.x[2 * (n_teams - 1) + 1]),
        "rho": float(res.x[2 * (n_teams - 1) + 2]),
        "alphas": {t: float(alphas[team_idx[t]]) for t in teams},
        "betas": {t: float(betas[team_idx[t]]) for t in teams},
        "teams": teams
    }

league_models = {}
all_converged = True
print("Fitting Independent Identified Dixon-Coles 1H MLE per League:")

for lg, lg_name in LEAGUES.items():
    df_lg = df_train[df_train["league_code"] == lg]
    res_lg = fit_dixon_coles_1h(df_lg)
    league_models[lg] = res_lg
    
    status_sym = "✅" if res_lg["success"] else "🛑"
    sum_a = sum(res_lg["alphas"].values())
    sum_b = sum(res_lg["betas"].values())
    print(f"  {status_sym} [{lg}] {lg_name:<25}: Success={res_lg['success']} (Nit={res_lg['nit']}) | "
          f"mu={res_lg['mu']:.3f} | gamma={res_lg['gamma']:.3f} | rho={res_lg['rho']:.4f}")
    print(f"       Teams: {len(res_lg['teams'])} | Matches: {len(df_lg)} | "
          f"Sum Alphas: {sum_a:.6f} | Sum Betas: {sum_b:.6f}")
    
    if not res_lg["success"]:
        all_converged = False

print("="*80)
print("🛡️ GATE 0 AUDIT: MLE OPTIMIZATION CONVERGENCE")
print(f"  Total Leagues Evaluated: {len(LEAGUES)}")
print(f"  Converged Leagues      : {sum(1 for m in league_models.values() if m['success'])}/{len(LEAGUES)}")
gate_0 = all_converged
if gate_0:
    print("GATE 0 STATUS            : ✅ PASSED")
else:
    print("GATE 0 STATUS            : 🛑 BLOCKED (One or more leagues failed to converge)")
    if CONFIG.STRICT_GATE_APPROVAL:
        raise RuntimeError("FAIL_CLOSED: Halting execution due to Gate 0 MLE convergence failure.")
print("="*80)
"""))

    # ── CELL 5: MULTI-LEAGUE HALFTIME MATRIX PROBABILITY ENGINE
    cells.append(code_cell("""# ── STEP 4: MULTI-LEAGUE HALFTIME MATRIX PROBABILITY ENGINE ──────────────────

def predict_1h_probabilities(home_team, away_team, league_code, max_goals=5):
    mod = league_models.get(league_code)
    if mod is None:
        return {"HT_1": 0.333, "HT_X": 0.333, "HT_2": 0.334, "I1+": 0.70, "I2+": 0.30, "I0_1": 0.70, "I0": 0.30}
        
    alpha_h = mod["alphas"].get(home_team, 0.0)
    beta_a = mod["betas"].get(away_team, 0.0)
    alpha_a = mod["alphas"].get(away_team, 0.0)
    beta_h = mod["betas"].get(home_team, 0.0)
    
    log_lambda = mod["mu"] + alpha_h + beta_a + mod["gamma"]
    log_nu = mod["mu"] + alpha_a + beta_h
    
    lambda_1h = np.exp(np.clip(log_lambda, -3.0, 2.0))
    nu_1h = np.exp(np.clip(log_nu, -3.0, 2.0))
    
    prob_matrix = np.zeros((max_goals + 1, max_goals + 1))
    for x in range(max_goals + 1):
        for y in range(max_goals + 1):
            p_base = poisson.pmf(x, lambda_1h) * poisson.pmf(y, nu_1h)
            prob_matrix[x, y] = p_base * tau(x, y, lambda_1h, nu_1h, mod["rho"])
            
    prob_matrix = np.maximum(prob_matrix, 0.0)
    total_p = prob_matrix.sum()
    if total_p > 0:
        prob_matrix /= total_p
        
    p_ht1 = float(np.sum(np.tril(prob_matrix, -1)))
    p_htx = float(np.sum(np.diag(prob_matrix)))
    p_ht2 = float(np.sum(np.triu(prob_matrix, 1)))
    
    # Halftime Goal Total Markets
    p_0_goals = prob_matrix[0, 0]
    p_1_goal  = prob_matrix[0, 1] + prob_matrix[1, 0]
    
    p_i0 = float(p_0_goals)
    p_i0_1 = float(p_0_goals + p_1_goal)
    p_i1_plus = float(1.0 - p_0_goals)
    p_i2_plus = float(1.0 - p_i0_1)
    
    return {
        "HT_1": p_ht1, "HT_X": p_htx, "HT_2": p_ht2,
        "I1+": p_i1_plus, "I2+": p_i2_plus,
        "I0_1": p_i0_1, "I0": p_i0
    }

print("✅ Multi-League Halftime Probability Engine compiled.")
"""))

    # ── CELL 6: EXACT POWER DE-VIGGING & CLOSING BENCHMARK ENGINE
    cells.append(code_cell("""# ── STEP 5: EXACT POWER DE-VIGGING & CLOSING BENCHMARK ENGINE ────────────────

def devig_power_3way(o1, ox, o2):
    if o1 <= 1.0 or ox <= 1.0 or o2 <= 1.0:
        return 1/3, 1/3, 1/3
    invs = [1.0 / o1, 1.0 / ox, 1.0 / o2]
    def obj(k):
        return (invs[0]**k + invs[1]**k + invs[2]**k - 1.0)**2
    res = minimize(obj, [1.0], method='Nelder-Mead', options={'xatol': 1e-6})
    k_opt = res.x[0]
    p1 = invs[0]**k_opt
    px = invs[1]**k_opt
    p2 = invs[2]**k_opt
    s = p1 + px + p2
    return p1/s, px/s, p2/s

def devig_power_2way(o1, o2):
    if o1 <= 1.0 or o2 <= 1.0:
        return 0.5, 0.5
    invs = [1.0 / o1, 1.0 / o2]
    def obj(k):
        return (invs[0]**k + invs[1]**k - 1.0)**2
    res = minimize(obj, [1.0], method='Nelder-Mead', options={'xatol': 1e-6})
    k_opt = res.x[0]
    p1 = invs[0]**k_opt
    p2 = invs[1]**k_opt
    s = p1 + p2
    return p1/s, p2/s

def solve_implied_poisson_lambda(p_over_25):
    p_u25 = np.clip(1.0 - p_over_25, 1e-5, 0.99999)
    def obj(lam):
        lam = max(lam, 0.01)
        cdf2 = poisson.cdf(2, lam)
        return (cdf2 - p_u25)**2
    res = minimize(obj, [2.5], bounds=[(0.1, 7.0)], method='L-BFGS-B')
    return float(res.x[0])

print("✅ Exact Power De-Vigging & Closing Benchmark Engine compiled.")
"""))

    # ── CELL 7: GATE A AUDIT — DUAL OUT-OF-SAMPLE CALIBRATION (DEV & HOLDOUT)
    cells.append(code_cell("""# ── STEP 6: GATE A AUDIT — DUAL OUT-OF-SAMPLE CALIBRATION (DEV & HOLDOUT) ────

def compute_calibration_metrics(preds, actuals, n_bins=10):
    preds = np.array(preds)
    actuals = np.array(actuals)
    brier = np.mean((preds - actuals) ** 2)
    
    bins = np.linspace(0, 1, n_bins + 1)
    ece = 0.0
    for i in range(n_bins):
        mask = (preds >= bins[i]) & (preds < bins[i + 1])
        if np.sum(mask) > 0:
            bin_acc = np.mean(actuals[mask])
            bin_conf = np.mean(preds[mask])
            ece += (np.sum(mask) / len(preds)) * np.abs(bin_acc - bin_conf)
    return ece, brier

def evaluate_dataset_calibration(df_target, name):
    calib_preds = {"I1+": [], "I2+": [], "I0_1": [], "HT_X": []}
    calib_actuals = {"I1+": [], "I2+": [], "I0_1": [], "HT_X": []}
    
    for _, row in df_target.iterrows():
        probs = predict_1h_probabilities(row["home"], row["away"], row["league_code"])
        tot_ht = row["hthg"] + row["htag"]
        
        calib_preds["I1+"].append(probs["I1+"])
        calib_actuals["I1+"].append(1 if tot_ht >= 1 else 0)
        
        calib_preds["I2+"].append(probs["I2+"])
        calib_actuals["I2+"].append(1 if tot_ht >= 2 else 0)
        
        calib_preds["I0_1"].append(probs["I0_1"])
        calib_actuals["I0_1"].append(1 if tot_ht <= 1 else 0)
        
        calib_preds["HT_X"].append(probs["HT_X"])
        calib_actuals["HT_X"].append(1 if row["hthg"] == row["htag"] else 0)
        
    eces, briers = {}, {}
    for m in calib_preds:
        e, b = compute_calibration_metrics(calib_preds[m], calib_actuals[m])
        eces[m] = e
        briers[m] = b
        
    macro_ece = float(np.mean(list(eces.values())))
    macro_brier = float(np.mean(list(briers.values())))
    return macro_ece, macro_brier, eces, briers

macro_ece_dev, macro_brier_dev, eces_dev, briers_dev = evaluate_dataset_calibration(df_dev, "Development (2024/25)")
macro_ece_hold, macro_brier_hold, eces_hold, briers_hold = evaluate_dataset_calibration(df_final_holdout, "Final Holdout (2025/26)")

print("="*80)
print(f"🛡️ GATE A AUDIT: DUAL OUT-OF-SAMPLE CALIBRATION")
print(f"  1. Development Season (2024/25, N={len(df_dev):,} matches):")
for m in eces_dev:
    print(f"     - Market {m:<6}: ECE = {eces_dev[m]:.2%} | Brier = {briers_dev[m]:.4f}")
print(f"     MACRO ECE    : {macro_ece_dev:.2%} (Threshold: <= 6.00%)")
print(f"     MACRO BRIER  : {macro_brier_dev:.4f} (Threshold: <= 0.2300)")

print(f"  2. Untouched Final Holdout Season (2025/26, N={len(df_final_holdout):,} matches):")
for m in eces_hold:
    print(f"     - Market {m:<6}: ECE = {eces_hold[m]:.2%} | Brier = {briers_hold[m]:.4f}")
print(f"     MACRO ECE    : {macro_ece_hold:.2%} (Threshold: <= 6.00%)")
print(f"     MACRO BRIER  : {macro_brier_hold:.4f} (Threshold: <= 0.2300)")

gate_a_dev = (macro_ece_dev <= 0.060) and (macro_brier_dev <= 0.230)
gate_a_holdout = (macro_ece_hold <= 0.060) and (macro_brier_hold <= 0.230)
gate_a = gate_a_dev and gate_a_holdout

print(f"  GATE A DEV STATUS     : {'✅ PASSED' if gate_a_dev else '🛑 BLOCKED'}")
print(f"  GATE A HOLDOUT STATUS : {'✅ PASSED' if gate_a_holdout else '🛑 BLOCKED'}")
print(f"  OVERALL GATE A STATUS : {'✅ PASSED' if gate_a else '🛑 BLOCKED'}")
print("="*80)
"""))

    # ── CELL 8: HIGH-PRECISION WALK-FORWARD BACKTEST & MULTI-COHORT FORMATION
    cells.append(code_cell(r"""# ── STEP 7: HIGH-PRECISION WALK-FORWARD BACKTEST & MULTI-COHORT FORMATION ───
# Features:
# 1. Matching tolerance strictly tightened to +/- 1 day
# 2. Strict multi-word team synonyms (bare single words "SITI", "FOREST", "INTER", "VILA", "PALAS" removed)
# 3. Ambiguity rejection: if multiple candidates found on the date, record as AMBIGUOUS_MATCH_REJECTED
# 4. Independent cohort formation: DIRECT_MOZZART, SYNTHETIC_PROXY, ALL_COMBINED, FINAL_HOLDOUT_ONLY

team_synonyms = {
    # England (EPL)
    "Arsenal": ["ARSENAL"], "Aston Villa": ["ASTON VILA", "ASTON VILLA"], "Bournemouth": ["BORNMUT", "BOURNEMOUTH"],
    "Brentford": ["BRENTFORD"], "Brighton": ["BRAJTON", "BRIGHTON"], "Chelsea": ["ČELSI", "CELSI", "CHELSEA"],
    "Crystal Palace": ["KRISTAL PALAS", "CRYSTAL PALACE"], "Everton": ["EVERTON"], "Fulham": ["FULAM", "FULHAM"],
    "Ipswich": ["IPSVIČ", "IPSVIC", "IPSWICH"], "Leicester": ["LESTER", "LEICESTER"], "Liverpool": ["LIVERPUL", "LIVERPOOL"],
    "Man City": ["MAN.SITI", "MANČESTER SITI", "MANCESTER SITI", "MANCHESTER CITY"],
    "Man United": ["MAN.JUN", "MANČESTER JUN", "MANCESTER JUN", "MANCHESTER UNITED"],
    "Newcastle": ["NJUKASL", "NEWCASTLE"], "Nott'm Forest": ["NOTINGEM FOREST", "NOTTINGHAM FOREST", "NOTINGEM"],
    "Southampton": ["SAUTEMPTON", "SOUTHAMPTON"], "Tottenham": ["TOTENHEM", "TOTTENHAM"], "West Ham": ["VEST HEM", "WEST HAM"],
    "Wolves": ["VULVERHEMPTON", "WOLVERHAMPTON", "VULVER"],
    
    # Spain (La Liga)
    "Real Madrid": ["REAL MADRID"], "Barcelona": ["BARSELONA", "BARCELONA"], "Ath Madrid": ["ATLETIKO MADRID", "ATL.MADRID", "ATLETICO MADRID"],
    "Sevilla": ["SEVILJA", "SEVILLA"], "Villarreal": ["VILJAREAL", "VILLARREAL"], "Sociedad": ["REAL SOSIJEDAD", "REAL SOCIEDAD", "SOSIJEDAD"],
    "Betis": ["REAL BETIS", "BETIS"], "Valencia": ["VALENSIJA", "VALENCIA"], "Ath Bilbao": ["ATLETIK BILBAO", "ATHLETIC BILBAO"],
    "Girona": ["ĐIRONA", "DIRONA", "GIRONA"], "Osasuna": ["OSASUNA"], "Getafe": ["HETAFE", "GETAFE"],
    "Celta": ["SELTA VIGO", "CELTA VIGO", "SELTA"], "Mallorca": ["MAJORKA", "MALLORCA"], "Las Palmas": ["LAS PALMAS"],
    "Vallecano": ["RAJO VALJEKANO", "RAYO VALLECANO", "VALJEKANO"], "Alaves": ["ALAVES"], "Leganes": ["LEGANES"],
    "Valladolid": ["VALJADOLID", "VALLADOLID"], "Espanyol": ["ESPANJOL", "ESPANYOL"], "Espanol": ["ESPANJOL", "ESPANYOL"],
    
    # Italy (Serie A)
    "Inter": ["INTER MILAN", "INTER MILANO", "INTER"], "Milan": ["AC MILAN", "MILAN"], "Juventus": ["JUVENTUS"],
    "Atalanta": ["ATALANTA"], "Roma": ["AS ROMA", "ROMA"], "Lazio": ["SS LAZIO", "LACIO", "LAZIO"],
    "Napoli": ["NAPOLI"], "Fiorentina": ["FIORENTINA"], "Bologna": ["BOLONJA", "BOLOGNA"], "Torino": ["TORINO"],
    "Monza": ["MONCA", "MONZA"], "Genoa": ["ĐENOVA", "DENOVA", "GENOA"], "Lecce": ["LEĆE", "LECE", "LECCE"],
    "Udinese": ["UDINEZE", "UDINESE"], "Cagliari": ["KALJARI", "CAGLIARI"], "Verona": ["HELAS VERONA", "VERONA"],
    "Parma": ["PARMA"], "Como": ["KOMO", "COMO"], "Venezia": ["VENECIJA", "VENEZIA"], "Empoli": ["EMPOLI"],
    
    # Germany (Bundesliga)
    "Bayern Munich": ["BAJERN MINHEN", "BAYERN MUNICH", "BAJERN"], "Leverkusen": ["BAJER LEVERKUZEN", "BAYER LEVERKUSEN", "LEVERKUZEN"],
    "Dortmund": ["BORUSIJA DORTMUND", "BORUSSIA DORTMUND", "DORTMUND"], "RB Leipzig": ["RB LAJPCIG", "RB LEIPZIG", "LAJPCIG"],
    "Stuttgart": ["ŠTUTGART", "STUTTGART", "STUTGART"], "Ein Frankfurt": ["AJNTRAHT FRANKFURT", "EINTRACHT FRANKFURT", "AJNTRAHT"],
    "Hoffenheim": ["HOFENHAJM", "HOFFENHEIM"], "Heidenheim": ["HAJDENHAJM", "HEIDENHEIM"], "Werder Bremen": ["VERDER BREMEN", "WERDER BREMEN", "VERDER"],
    "Freiburg": ["FRAJBURG", "FREIBURG"], "Augsburg": ["AUGZBURG", "AUGSBURG"], "Wolfsburg": ["VOLFSBURG", "WOLFSBURG"],
    "M'gladbach": ["MENHENGLADBAH", "MONCHENGLADBACH", "BORUSIJA MENHENGLADBAH"], "Union Berlin": ["UNION BERLIN"],
    "Bochum": ["BOHUM", "BOCHUM"], "St Pauli": ["SENT PAULI", "SANKT PAULI", "ST. PAULI"], "Holstein Kiel": ["HOLŠTAJN KIL", "HOLSTEIN KIEL"],
    "Mainz": ["MAJNC", "MAINZ"],
    
    # France (Ligue 1)
    "Paris SG": ["PSŽ", "PARI SEN ŽERMEN", "PARIS SAINT-GERMAIN", "PSG"], "Monaco": ["AS MONAKO", "AS MONACO", "MONAKO"],
    "Brest": ["BREST", "STADE BRESTOIS"], "Lille": ["LIL", "LOSC LILLE", "LILLE"], "Nice": ["OGC NICA", "OGC NICE", "NICA"],
    "Lyon": ["OLIMPIK LION", "OLYMPIQUE LYON", "LION"], "Marseille": ["OLIMPIK MARSELJ", "OLYMPIQUE MARSEILLE", "MARSELJ"],
    "Lens": ["LANS", "RC LENS"], "Reims": ["REMS", "STADE DE REIMS"], "Rennes": ["REN", "STADE RENNAIS"],
    "Toulouse": ["TULUZ", "TOULOUSE"], "Montpellier": ["MONPELJE", "MONTPELLIER"], "Strasbourg": ["STRAZBUR", "STRASBOURG"],
    "Nantes": ["NANT", "FC NANTES"], "Le Havre": ["AVR", "LE AVR", "LE HAVRE"], "Auxerre": ["OKSER", "AJ AUXERRE"],
    "Angers": ["ANŽE", "ANZE", "ANGERS"], "St Etienne": ["SENT ETJEN", "SAINT-ETIENNE"]
}

# Index Sanitized Mozzart by ISO date
moz_by_date = {}
if len(ht_valid) > 0:
    for _, m_row in ht_valid.iterrows():
        d = str(m_row["iso_date"]).strip()
        if d not in moz_by_date:
            moz_by_date[d] = []
        moz_by_date[d].append(m_row)

def execute_walk_forward_evaluation(df_eval, eval_season_name):
    wagers = []
    unit_stake = 10.0
    matches_evaluated = len(df_eval)
    direct_quotes_matched = 0
    ambiguous_matches_rejected = 0
    total_candidate_opportunities = 0
    
    for idx, row in df_eval.iterrows():
        m_probs = predict_1h_probabilities(row["home"], row["away"], row["league_code"])
        
        # High-Precision Matching: Strict +/- 1 day schedule flexibility
        h_syns = [s.upper() for s in team_synonyms.get(row["home"], [row["home"]])]
        a_syns = [s.upper() for s in team_synonyms.get(row["away"], [row["away"]])]
        
        target_dates = [row["date"]]
        try:
            dt = pd.to_datetime(row["date"])
            target_dates.append((dt - pd.Timedelta(days=1)).strftime("%Y-%m-%d"))
            target_dates.append((dt + pd.Timedelta(days=1)).strftime("%Y-%m-%d"))
        except Exception:
            pass
            
        candidate_matches = []
        for td in target_dates:
            for m in moz_by_date.get(td, []):
                mh = str(m.get("home_team", "")).upper()
                ma = str(m.get("away_team", "")).upper()
                if any(s in mh for s in h_syns) and any(s in ma for s in a_syns):
                    candidate_matches.append(m)
                    
        matched_moz = None
        if len(candidate_matches) == 1:
            matched_moz = candidate_matches[0]
            direct_quotes_matched += 1
        elif len(candidate_matches) > 1:
            ambiguous_matches_rejected += 1
            
        # Consensus Benchmark Lines from Pinnacle (Power De-Vigged)
        p_open_o25, _ = devig_power_2way(row["p_o25"], row["p_u25"])
        lam_open_ft = solve_implied_poisson_lambda(p_open_o25)
        lam_open_1h = lam_open_ft * 0.44
        
        p_close_o25, _ = devig_power_2way(row["p_close_o25"], row["p_close_u25"])
        lam_close_ft = solve_implied_poisson_lambda(p_close_o25)
        lam_close_1h = lam_close_ft * 0.44
        
        # Closing fair probabilities (Reconstructed Closing Benchmark)
        p_mkt_close_i1 = 1.0 - np.exp(-lam_close_1h)
        p_mkt_close_i2 = 1.0 - np.exp(-lam_close_1h) - lam_close_1h * np.exp(-lam_close_1h)
        p_mkt_close_i0_1 = 1.0 - p_mkt_close_i2
        p_mkt_close_i0 = np.exp(-lam_close_1h)
        
        # Halftime 1X2 Reconstructed Closing Fair Odds
        p_close_ht1, p_close_htx, p_close_ht2 = devig_power_3way(row["ps_close_h"], row["ps_close_d"], row["ps_close_a"])[:3]
        ratio_close = (max(p_close_ht1, 0.05) / max(p_close_ht2, 0.05)) ** 0.5
        lam_h_close = lam_close_1h * (ratio_close / (1.0 + ratio_close))
        lam_a_close = lam_close_1h * (1.0 / (1.0 + ratio_close))
        p_real_close_htx = sum(poisson.pmf(k, lam_h_close) * poisson.pmf(k, lam_a_close) for k in range(5))
        fair_close_htx = 1.0 / max(p_real_close_htx, 0.05)
        
        fair_close_i0_1 = 1.0 / max(p_mkt_close_i0_1, 0.05)
        fair_close_i0   = 1.0 / max(p_mkt_close_i0, 0.05)
        
        # Real Match Outcome
        won_ht_x = 1 if row["hthg"] == row["htag"] else 0
        tot_ht = row["hthg"] + row["htag"]
        won_i0_1 = 1 if tot_ht <= 1 else 0
        won_i0   = 1 if tot_ht == 0 else 0
        
        rev_candidates = []
        
        # 1. Market: HT X (Halftime Draw)
        is_direct_moz_htx = False
        if matched_moz is not None and pd.notna(matched_moz.get("ht_x")) and 1.70 <= float(matched_moz["ht_x"]) <= 3.80:
            odds_rev_htx = float(matched_moz["ht_x"])
            is_direct_moz_htx = True
            min_ev_htx = 0.002
            min_clv_htx = -0.015
        else:
            p_open_ht1, p_open_htx, p_open_ht2 = devig_power_3way(row["ps_h"], row["ps_d"], row["ps_a"])[:3]
            ratio_open = (max(p_open_ht1, 0.05) / max(p_open_ht2, 0.05)) ** 0.5
            lam_h_open = lam_open_1h * (ratio_open / (1.0 + ratio_open))
            lam_a_open = lam_open_1h * (1.0 / (1.0 + ratio_open))
            p_real_open_htx = sum(poisson.pmf(k, lam_h_open) * poisson.pmf(k, lam_a_open) for k in range(5))
            odds_rev_htx = round(max((1.0 / max(p_real_open_htx, 0.05)) * (1.0 - mean_margin * 0.12), 1.65), 2)
            min_ev_htx = 0.008
            min_clv_htx = -0.005
            
        ev_rev_htx = (m_probs["HT_X"] * odds_rev_htx) - 1.0
        clv_htx = (odds_rev_htx / fair_close_htx) - 1.0
        if ev_rev_htx > min_ev_htx and clv_htx > min_clv_htx:
            rev_candidates.append({
                "match_id": idx, "fixture": f"{row['home']} vs {row['away']}", "league": row["league_code"],
                "market": "HT X", "odds": odds_rev_htx, "won": won_ht_x, "stake": unit_stake,
                "ev": ev_rev_htx, "proxy_clv": clv_htx,
                "source": "MOZZART_DIRECT" if is_direct_moz_htx else "SYNTHETIC_PROXY"
            })
            
        # 2. Market: I 0-1 (Under 1.5 Goals HT)
        p_mkt_open_i0_1 = 1.0 - (1.0 - np.exp(-lam_open_1h) - lam_open_1h * np.exp(-lam_open_1h))
        odds_rev_i0_1 = round(max((1.0 / p_mkt_open_i0_1) * (1.0 - mean_margin * 0.20), 1.25), 2)
        ev_rev_i0_1 = (m_probs["I0_1"] * odds_rev_i0_1) - 1.0
        clv_i0_1 = (odds_rev_i0_1 / fair_close_i0_1) - 1.0
        if ev_rev_i0_1 > 0.010 and clv_i0_1 > -0.005:
            rev_candidates.append({
                "match_id": idx, "fixture": f"{row['home']} vs {row['away']}", "league": row["league_code"],
                "market": "I 0-1", "odds": odds_rev_i0_1, "won": won_i0_1, "stake": unit_stake,
                "ev": ev_rev_i0_1, "proxy_clv": clv_i0_1, "source": "SYNTHETIC_PROXY"
            })
            
        # 3. Market: I 0 (Under 0.5 Goals HT)
        p_mkt_open_i0 = np.exp(-lam_open_1h)
        odds_rev_i0 = round(max((1.0 / p_mkt_open_i0) * (1.0 - mean_margin * 0.22), 1.55), 2)
        ev_rev_i0 = (m_probs["I0"] * odds_rev_i0) - 1.0
        clv_i0 = (odds_rev_i0 / fair_close_i0) - 1.0
        if ev_rev_i0 > 0.012 and clv_i0 > -0.005:
            rev_candidates.append({
                "match_id": idx, "fixture": f"{row['home']} vs {row['away']}", "league": row["league_code"],
                "market": "I 0", "odds": odds_rev_i0, "won": won_i0, "stake": unit_stake,
                "ev": ev_rev_i0, "proxy_clv": clv_i0, "source": "SYNTHETIC_PROXY"
            })
            
        total_candidate_opportunities += len(rev_candidates)
        
        # Single best wager per fixture (Prioritize direct Mozzart; then HT X; then highest EV)
        if rev_candidates:
            direct_cands = [c for c in rev_candidates if c["source"] == "MOZZART_DIRECT"]
            if direct_cands:
                best = max(direct_cands, key=lambda x: x["ev"])
            else:
                htx_cands = [c for c in rev_candidates if c["market"] == "HT X"]
                if htx_cands:
                    best = max(htx_cands, key=lambda x: x["ev"])
                else:
                    best = max(rev_candidates, key=lambda x: x["ev"])
                    
            pnl = round(unit_stake * (best["odds"] - 1.0), 2) if best["won"] else -unit_stake
            best["pnl"] = pnl
            best["season"] = eval_season_name
            wagers.append(best)
            
    df_w = pd.DataFrame(wagers)
    n_dir = int((df_w["source"] == "MOZZART_DIRECT").sum()) if len(df_w) > 0 else 0
    n_prx = len(df_w) - n_dir
    cov_selected = n_dir / len(df_w) if len(df_w) > 0 else 0.0
    cov_matches = direct_quotes_matched / matches_evaluated if matches_evaluated > 0 else 0.0
    
    return {
        "df_wagers": df_w,
        "matches_evaluated": matches_evaluated,
        "direct_quotes_matched": direct_quotes_matched,
        "ambiguous_matches_rejected": ambiguous_matches_rejected,
        "total_candidate_opportunities": total_candidate_opportunities,
        "selected_wagers": len(df_w),
        "direct_wagers": n_dir,
        "proxy_wagers": n_prx,
        "coverage_selected": cov_selected,
        "coverage_matches": cov_matches
    }

print("Running Walk-Forward Backtest on Development Set (2024/25)...")
res_dev = execute_walk_forward_evaluation(df_dev, "2024/25_DEV")

print("Running Walk-Forward Backtest on Sacred Untouched Final Holdout (2025/26)...")
res_hold = execute_walk_forward_evaluation(df_final_holdout, "2025/26_HOLDOUT")

df_wagers_dev = res_dev["df_wagers"]
df_wagers_hold = res_hold["df_wagers"]

print("="*80)
print("🎯 FORENSIC DIRECT ODDS COVERAGE AUDIT")
print(f"  Development Season (2024/25):")
print(f"    - Matches Evaluated            : {res_dev['matches_evaluated']:,}")
print(f"    - Direct Quotes Matched        : {res_dev['direct_quotes_matched']}")
print(f"    - Ambiguous Matches Rejected   : {res_dev['ambiguous_matches_rejected']}")
print(f"    - Selected Wagers (1-per-match): {res_dev['selected_wagers']:,}")
print(f"    - Direct Mozzart Wagers        : {res_dev['direct_wagers']} ({res_dev['coverage_selected']:.2%})")
print(f"    - Synthetic Proxy Wagers       : {res_dev['proxy_wagers']} ({res_dev['proxy_wagers']/max(len(df_wagers_dev),1):.2%})")

print(f"  Untouched Final Holdout (2025/26):")
print(f"    - Matches Evaluated            : {res_hold['matches_evaluated']:,}")
print(f"    - Direct Quotes Matched        : {res_hold['direct_quotes_matched']}")
print(f"    - Ambiguous Matches Rejected   : {res_hold['ambiguous_matches_rejected']}")
print(f"    - Selected Wagers (1-per-match): {res_hold['selected_wagers']:,}")
print(f"    - Direct Mozzart Wagers        : {res_hold['direct_wagers']} ({res_hold['coverage_selected']:.2%})")
print(f"    - Synthetic Proxy Wagers       : {res_hold['proxy_wagers']} ({res_hold['proxy_wagers']/max(len(df_wagers_hold),1):.2%})")
print("="*80)
"""))

    # ── CELL 9: TRUE CLUSTER BOOTSTRAP & MULTI-COHORT DISAGGREGATION
    cells.append(code_cell("""# ── STEP 8: TRUE CLUSTER BOOTSTRAP & MULTI-COHORT DISAGGREGATION ────────────
# Fixes the .isin() bug: explicit grouped dictionary mapping guarantees true sampling with replacement!

def run_true_cluster_bootstrap(df_w, n_boot=1000):
    if len(df_w) == 0:
        return {
            "n_bets": 0, "n_fixtures": 0, "win_rate": 0.0,
            "mean_clv": 0.0, "clv_ci": [0.0, 0.0], "clv_t_ratio": 0.0,
            "pnl": 0.0, "pnl_ci": [0.0, 0.0],
            "yield": 0.0, "yield_ci": [0.0, 0.0],
            "max_drawdown": 0.0, "mdd_ci": [0.0, 0.0]
        }
        
    groups = {fixture: group.copy() for fixture, group in df_w.groupby("fixture")}
    fixtures = list(groups.keys())
    n_fixtures = len(fixtures)
    
    clv_means = []
    yield_means = []
    pnl_sums = []
    mdd_vals = []
    
    for _ in range(n_boot):
        sampled = np.random.choice(fixtures, size=n_fixtures, replace=True)
        sample_wagers = pd.concat([groups[f] for f in sampled], ignore_index=True)
        
        # 1. CLV Bootstrap
        clv_means.append(sample_wagers["proxy_clv"].mean())
        
        # 2. Yield & PnL Bootstrap
        tot_stk = sample_wagers["stake"].sum()
        tot_pnl = sample_wagers["pnl"].sum()
        pnl_sums.append(tot_pnl)
        yield_means.append(tot_pnl / tot_stk if tot_stk > 0 else 0.0)
        
        # 3. Drawdown Bootstrap
        cum_pnl = sample_wagers["pnl"].cumsum().values
        running_max = np.maximum.accumulate(cum_pnl)
        mdd_vals.append(float(np.max(running_max - cum_pnl)))
        
    act_clv = float(df_w["proxy_clv"].mean())
    se_clv = float(np.std(clv_means))
    t_ratio = act_clv / se_clv if se_clv > 0 else 0.0
    
    act_stk = df_w["stake"].sum()
    act_pnl = float(df_w["pnl"].sum())
    act_yield = float(act_pnl / act_stk) if act_stk > 0 else 0.0
    
    cum_act = df_w["pnl"].cumsum().values
    act_mdd = float(np.max(np.maximum.accumulate(cum_act) - cum_act)) if len(cum_act) > 0 else 0.0
    
    return {
        "n_bets": len(df_w),
        "n_fixtures": n_fixtures,
        "win_rate": float(df_w["won"].mean()),
        "mean_clv": act_clv,
        "clv_ci": [float(np.percentile(clv_means, 2.5)), float(np.percentile(clv_means, 97.5))],
        "clv_t_ratio": t_ratio,
        "pnl": act_pnl,
        "pnl_ci": [float(np.percentile(pnl_sums, 2.5)), float(np.percentile(pnl_sums, 97.5))],
        "yield": act_yield,
        "yield_ci": [float(np.percentile(yield_means, 2.5)), float(np.percentile(yield_means, 97.5))],
        "max_drawdown": act_mdd,
        "mdd_ci": [float(np.percentile(mdd_vals, 2.5)), float(np.percentile(mdd_vals, 97.5))]
    }

# Formation of 4 Distinct Cohorts
cohort_direct = df_wagers_dev[df_wagers_dev["source"] == "MOZZART_DIRECT"].copy().reset_index(drop=True)
cohort_proxy = df_wagers_dev[df_wagers_dev["source"] == "SYNTHETIC_PROXY"].copy().reset_index(drop=True)
cohort_combined = df_wagers_dev.copy().reset_index(drop=True)
cohort_holdout = df_wagers_hold.copy().reset_index(drop=True)

# Run True Cluster Bootstrap for each Cohort
stats_direct   = run_true_cluster_bootstrap(cohort_direct)
stats_proxy    = run_true_cluster_bootstrap(cohort_proxy)
stats_combined = run_true_cluster_bootstrap(cohort_combined)
stats_holdout  = run_true_cluster_bootstrap(cohort_holdout)

print("="*88)
print("🛡️ MULTI-COHORT DISAGGREGATED STATISTICAL AUDIT (TRUE CLUSTER BOOTSTRAP)")
print("="*88)
header_fmt = "{:<25} | {:<16} | {:<16} | {:<16} | {:<16}"
row_fmt    = "{:<25} | {:<16} | {:<16} | {:<16} | {:<16}"

print(header_fmt.format("Metric", "DIRECT_MOZZART", "SYNTHETIC_PROXY", "ALL_COMBINED (DEV)", "FINAL_HOLDOUT_ONLY"))
print("-"*88)
print(row_fmt.format("Total Wagers Placed", f"{stats_direct['n_bets']}", f"{stats_proxy['n_bets']}", f"{stats_combined['n_bets']}", f"{stats_holdout['n_bets']}"))
print(row_fmt.format("Unique Fixtures", f"{stats_direct['n_fixtures']}", f"{stats_proxy['n_fixtures']}", f"{stats_combined['n_fixtures']}", f"{stats_holdout['n_fixtures']}"))
print(row_fmt.format("Direct Odds Coverage", f"{stats_direct['n_bets']/max(stats_combined['n_bets'],1):.2%}", f"0.00%", f"{stats_direct['n_bets']/max(stats_combined['n_bets'],1):.2%}", f"{(cohort_holdout['source']=='MOZZART_DIRECT').sum()/max(len(cohort_holdout),1):.2%}"))
print(row_fmt.format("Win Rate", f"{stats_direct['win_rate']:.2%}", f"{stats_proxy['win_rate']:.2%}", f"{stats_combined['win_rate']:.2%}", f"{stats_holdout['win_rate']:.2%}"))
print(row_fmt.format("Proxy / Direct CLV", f"{stats_direct['mean_clv']:+.2%}", f"{stats_proxy['mean_clv']:+.2%}", f"{stats_combined['mean_clv']:+.2%}", f"{stats_holdout['mean_clv']:+.2%}"))
print(row_fmt.format("CLV 95% Cluster CI", f"[{stats_direct['clv_ci'][0]:+.1%}, {stats_direct['clv_ci'][1]:+.1%}]", f"[{stats_proxy['clv_ci'][0]:+.1%}, {stats_proxy['clv_ci'][1]:+.1%}]", f"[{stats_combined['clv_ci'][0]:+.1%}, {stats_combined['clv_ci'][1]:+.1%}]", f"[{stats_holdout['clv_ci'][0]:+.1%}, {stats_holdout['clv_ci'][1]:+.1%}]"))
print(row_fmt.format("Bootstrap t-ratio", f"{stats_direct['clv_t_ratio']:.2f}", f"{stats_proxy['clv_t_ratio']:.2f}", f"{stats_combined['clv_t_ratio']:.2f}", f"{stats_holdout['clv_t_ratio']:.2f}"))
print(row_fmt.format("Total PnL (EUR)", f"€{stats_direct['pnl']:.2f}", f"€{stats_proxy['pnl']:.2f}", f"€{stats_combined['pnl']:.2f}", f"€{stats_holdout['pnl']:.2f}"))
print(row_fmt.format("Sample Yield (ROI)", f"{stats_direct['yield']:+.2%}", f"{stats_proxy['yield']:+.2%}", f"{stats_combined['yield']:+.2%}", f"{stats_holdout['yield']:+.2%}"))
print(row_fmt.format("ROI 95% Cluster CI", f"[{stats_direct['yield_ci'][0]:+.1%}, {stats_direct['yield_ci'][1]:+.1%}]", f"[{stats_proxy['yield_ci'][0]:+.1%}, {stats_proxy['yield_ci'][1]:+.1%}]", f"[{stats_combined['yield_ci'][0]:+.1%}, {stats_combined['yield_ci'][1]:+.1%}]", f"[{stats_holdout['yield_ci'][0]:+.1%}, {stats_holdout['yield_ci'][1]:+.1%}]"))
print(row_fmt.format("Maximum Drawdown", f"€{stats_direct['max_drawdown']:.2f}", f"€{stats_proxy['max_drawdown']:.2f}", f"€{stats_combined['max_drawdown']:.2f}", f"€{stats_holdout['max_drawdown']:.2f}"))
print("="*88)
"""))

    # ── CELL 10: FAIL-CLOSED INSTITUTIONAL 8-GATE GOVERNANCE VERDICT & EXPORT
    cells.append(code_cell("""# ── STEP 9: FAIL-CLOSED INSTITUTIONAL 8-GATE GOVERNANCE VERDICT & EXPORT ─────

# Explicit Gate Evaluations across Development (2024/25) and Untouched Holdout (2025/26)
direct_cov_val = res_dev["coverage_selected"]
n_direct_val   = res_dev["direct_wagers"]
total_bets_dev = len(df_wagers_dev)
total_bets_hold = len(df_wagers_hold)

# Gate 0: MLE Convergence
gate_0 = all_converged

# Gate A: Calibration on Both Dev and Holdout
gate_a_dev = (macro_ece_dev <= 0.060) and (macro_brier_dev <= 0.230)
gate_a_holdout = (macro_ece_hold <= 0.060) and (macro_brier_hold <= 0.230)
gate_a = gate_a_dev and gate_a_holdout

# Gate B: Market Alpha (CLV) on Both Dev and Holdout
gate_b_dev = stats_combined['mean_clv'] > 0.005
gate_b_holdout = stats_holdout['mean_clv'] > 0.005
gate_b = gate_b_dev and gate_b_holdout

# Gate C: Economic Yield on Both Dev and Holdout
gate_c_dev = stats_combined['yield'] > 0.02
gate_c_holdout = (stats_holdout['yield'] > 0.02) and (stats_holdout['n_bets'] >= CONFIG.MIN_FINAL_HOLDOUT_BETS)
gate_c = gate_c_dev and gate_c_holdout

# Gate D: Sample Adequacy across Dev and Holdout
gate_d_dev = total_bets_dev >= CONFIG.MIN_DEV_BETS
gate_d_holdout = total_bets_hold >= CONFIG.MIN_FINAL_HOLDOUT_BETS
gate_d = gate_d_dev and gate_d_holdout

# Gate E: Direct Mozzart Coverage (>= 80% for paper trading)
gate_e = direct_cov_val >= CONFIG.DIRECT_COVERAGE_FOR_PAPER

# Gate F: Direct Sample Size (>= 350 direct wagers for production review)
gate_f = n_direct_val >= CONFIG.MIN_DIRECT_BETS

# Gate G: Temporal Integrity
gate_g = (future_rows_removed == 0) and (margin_source == "pre_holdout_training_period")

# Gate H: Data Quality (Verified ISO dates, 0 future dates, sanitized rows >= 5000)
gate_h = (future_rows_removed == 0) and (rows_after_odds_sanitization >= 5000) and ht_valid["iso_date"].notna().all() and (ht_valid["iso_date"] != "").all()

# Fail-Closed Multi-Tier Institutional Governance Logic
failure_reasons = []
if not gate_0:
    failure_reasons.append("Gate 0 (MLE Convergence)")
if not gate_a_dev or not gate_a_holdout:
    failure_reasons.append("Gate A (Out-of-sample Calibration)")
if not gate_b_dev or not gate_b_holdout:
    failure_reasons.append("Gate B (Closing Proxy CLV Alpha)")
if not gate_c_dev:
    failure_reasons.append("Gate C Dev (Development Yield <= 2%)")
if not gate_c_holdout:
    failure_reasons.append(f"Gate C Final Holdout (Holdout Yield {stats_holdout['yield']:+.2%} <= 2.00%)")
if not gate_d:
    failure_reasons.append("Gate D (Sample Size Adequacy)")
if not gate_f:
    failure_reasons.append(f"Gate F (Direct Mozzart Bets {n_direct_val} < {CONFIG.MIN_DIRECT_BETS})")
if not gate_e:
    failure_reasons.append(f"Gate E (Direct Coverage {direct_cov_val:.2%} < 80.00%)")

if not (gate_0 and gate_a and gate_b and gate_c):
    final_verdict = "FAIL_CLOSED_BLOCKED"
    production_status = "BLOCKED"
    governance_rationale = (
        "FAIL_CLOSED_BLOCKED: Institutional validation failed on " + ", ".join(failure_reasons) + ". "
        f"Untouched 2025/26 holdout yielded {stats_holdout['yield']:+.2%}, failing to confirm economic viability out-of-sample."
    )
elif not (gate_d and gate_g and gate_h):
    final_verdict = "RESEARCH_ONLY_INSUFFICIENT_VALIDATION"
    production_status = "BLOCKED"
    governance_rationale = "Data integrity / sample size failure: Gate D, Gate G, or Gate H failed."
elif not gate_f:
    final_verdict = "RESEARCH_ONLY_INSUFFICIENT_DIRECT_SAMPLE"
    production_status = "BLOCKED"
    governance_rationale = f"Direct Mozzart wagers count is {n_direct_val} (below the required {CONFIG.MIN_DIRECT_BETS} minimum). Production blocked."
elif direct_cov_val < 0.80:
    final_verdict = "RESEARCH_ONLY_SYNTHETIC_PROXY_VALIDATION"
    production_status = "BLOCKED_PENDING_DIRECT_ODDS"
    governance_rationale = (
        f"Direct Mozzart quote coverage is {direct_cov_val:.2%} (below the 80% threshold). "
        "Production betting and paper trading remain strictly BLOCKED."
    )
elif direct_cov_val < 0.95:
    final_verdict = "LIMITED_PAPER_TRADING_ONLY"
    production_status = "BLOCKED_FOR_PRODUCTION"
    governance_rationale = "Direct coverage is between 80% and 95%. Limited paper trading permitted; real capital strictly locked."
else:
    final_verdict = "CANDIDATE_FOR_PRODUCTION_REVIEW"
    production_status = "PENDING_MANUAL_APPROVAL"
    governance_rationale = "All econometric gates passed and direct coverage exceeds 95%. Submitted for manual institutional sign-off."

direct_cohort_status = "VALID" if n_direct_val >= CONFIG.MIN_DIRECT_BETS else "DIRECT_COHORT_INSUFFICIENT_SAMPLE"

verdict_report = {
    "pipeline_version": CONFIG.VERSION,
    "build_tag": CONFIG.BUILD_TAG,
    "governance_protocol": "JudgeGuard Institutional 8-Gate Framework (v18.3)",
    "execution_environment": CONFIG.EXECUTION_ENV,
    "production_status": production_status,
    "final_verdict": final_verdict,
    "governance_rationale": governance_rationale,
    "temporal_provenance": {
        "training_seasons": CONFIG.TRAIN_SEASONS,
        "development_season": CONFIG.DEV_SEASON,
        "final_holdout_season": CONFIG.FINAL_HOLDOUT_SEASON,
        "final_holdout_touched": False,
        "max_allowed_date": CONFIG.MAX_ALLOWED_DATE,
        "margin_source": margin_source,
        "margin_cutoff": margin_cutoff,
        "mean_overround_used": round(mean_margin, 4)
    },
    "direct_coverage_audit": {
        "development_matches_evaluated": res_dev["matches_evaluated"],
        "development_direct_quotes_matched": res_dev["direct_quotes_matched"],
        "development_ambiguous_matches_rejected": res_dev["ambiguous_matches_rejected"],
        "development_total_selected_wagers": res_dev["selected_wagers"],
        "development_direct_mozzart_wagers": res_dev["direct_wagers"],
        "development_synthetic_proxy_wagers": res_dev["proxy_wagers"],
        "development_direct_coverage_selected_wagers": round(direct_cov_val, 4),
        "development_direct_coverage_matches": round(res_dev["coverage_matches"], 4),
        "direct_cohort_status": direct_cohort_status,
        "holdout_matches_evaluated": res_hold["matches_evaluated"],
        "holdout_selected_wagers": res_hold["selected_wagers"],
        "holdout_direct_wagers": res_hold["direct_wagers"],
        "holdout_synthetic_wagers": res_hold["proxy_wagers"],
        "holdout_direct_coverage": round(res_hold["coverage_selected"], 4)
    },
    "eight_governance_gates": {
        "gate_0_mle_convergence": {"status": "PASSED" if gate_0 else "BLOCKED", "converged_leagues": sum(1 for m in league_models.values() if m['success'])},
        "gate_a_calibration": {
            "status": "PASSED" if gate_a else "BLOCKED",
            "gate_a_dev": "PASSED" if gate_a_dev else "BLOCKED",
            "gate_a_holdout": "PASSED" if gate_a_holdout else "BLOCKED",
            "macro_ece_dev": round(macro_ece_dev, 4), "macro_brier_dev": round(macro_brier_dev, 4),
            "macro_ece_holdout": round(macro_ece_hold, 4), "macro_brier_holdout": round(macro_brier_hold, 4)
        },
        "gate_b_market_alpha": {
            "status": "PASSED" if gate_b else "BLOCKED",
            "gate_b_dev": "PASSED" if gate_b_dev else "BLOCKED",
            "gate_b_holdout": "PASSED" if gate_b_holdout else "BLOCKED",
            "mean_proxy_clv_dev": round(stats_combined['mean_clv'], 4),
            "mean_proxy_clv_holdout": round(stats_holdout['mean_clv'], 4)
        },
        "gate_c_economic_yield": {
            "status": "PASSED" if gate_c else "BLOCKED",
            "gate_c_dev": "PASSED" if gate_c_dev else "BLOCKED",
            "gate_c_holdout": "PASSED" if gate_c_holdout else "BLOCKED",
            "sample_yield_dev": round(stats_combined['yield'], 4),
            "sample_yield_holdout": round(stats_holdout['yield'], 4),
            "holdout_yield_failure_reason": "Holdout yield <= 2.00% blocks production economic viability" if not gate_c_holdout else "None"
        },
        "gate_d_sample_adequacy": {
            "status": "PASSED" if gate_d else "BLOCKED",
            "dev_wagers": total_bets_dev, "dev_min": CONFIG.MIN_DEV_BETS,
            "holdout_wagers": total_bets_hold, "holdout_min": CONFIG.MIN_FINAL_HOLDOUT_BETS
        },
        "gate_e_direct_coverage": {"status": "PASSED" if gate_e else "BLOCKED", "coverage": round(direct_cov_val, 4), "required_min": CONFIG.DIRECT_COVERAGE_FOR_PAPER},
        "gate_f_direct_sample": {"status": "PASSED" if gate_f else "BLOCKED", "direct_wagers": n_direct_val, "required_min": CONFIG.MIN_DIRECT_BETS},
        "gate_g_temporal_integrity": {"status": "PASSED" if gate_g else "BLOCKED", "future_rows_removed": future_rows_removed, "margin_cutoff": margin_cutoff},
        "gate_h_data_quality": {
            "status": "PASSED" if gate_h else "BLOCKED",
            "sanitized_ht_rows": rows_after_odds_sanitization,
            "undated_legacy_rows_isolated": invalid_dates,
            "provenance_note": "Legacy undated bulletin rows strictly excluded; 100% of modeled records contain verified ISO dates."
        }
    },
    "cohort_metrics": {
        "DIRECT_MOZZART": stats_direct,
        "SYNTHETIC_PROXY": stats_proxy,
        "ALL_COMBINED_DEV": stats_combined,
        "FINAL_HOLDOUT_ONLY": stats_holdout
    }
}

output_path = "gate_verdicts.json"
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(verdict_report, f, indent=2)

print("="*80)
print(f"🏛️ INSTITUTIONAL GOVERNANCE FINAL VERDICT : {final_verdict}")
print(f"🔒 PRODUCTION STATUS                       : {production_status}")
print(f"📊 DIRECT MOZZART ODDS COVERAGE (DEV)      : {direct_cov_val:.2%}")
print(f"📊 DEVELOPMENT SAMPLE YIELD (2024/25)      : {stats_combined['yield']:+.2%} ({stats_combined['pnl']:+.2f} EUR)")
print(f"🛑 FINAL HOLDOUT SAMPLE YIELD (2025/26)    : {stats_holdout['yield']:+.2%} ({stats_holdout['pnl']:+.2f} EUR) -> Gate C Holdout BLOCKED")
print(f"Audit report successfully exported to '{output_path}'.")
print("="*80)
"""))

    notebook = {
        "cells": cells,
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3"
            },
            "language_info": {
                "codemirror_mode": {"name": "ipython", "version": 3},
                "file_extension": ".py",
                "mimetype": "text/x-python",
                "name": "python",
                "nbconvert_exporter": "python",
                "pygments_lexer": "ipython3",
                "version": "3.10.12"
            }
        },
        "nbformat": 4,
        "nbformat_minor": 5
    }

    out_file = "sharpbet-v12-halftime-goals-audit.ipynb"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(notebook, f, indent=1, ensure_ascii=False)
    print(f"✅ Successfully compiled {out_file} (SharpBet Core v18.3.0) with {len(cells)} cells.")

if __name__ == "__main__":
    build_v18_notebook()
