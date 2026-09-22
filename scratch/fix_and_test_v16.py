import os
import io
import sys
import json
import hashlib
import requests
import numpy as np
import pandas as pd
from scipy.optimize import minimize, brentq
from scipy.stats import poisson, ttest_1samp

np.random.seed(42)

SEASONS = ["2223", "2324", "2425"]
BASE_URL = "https://www.football-data.co.uk/mmz4281"

all_matches = []
for season in SEASONS:
    url = f"{BASE_URL}/{season}/E0.csv"
    resp = requests.get(url, timeout=15)
    df_s = pd.read_csv(io.StringIO(resp.text))
    for _, row in df_s.iterrows():
        try:
            if pd.isna(row.get("HomeTeam")) or pd.isna(row.get("FTHG")):
                continue
            all_matches.append({
                "season": season,
                "date": str(row.get("Date", "")),
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
        except Exception:
            continue

df_all = pd.DataFrame(all_matches)
HOLDOUT_SEASON = "2425"
df_train = df_all[df_all["season"] != HOLDOUT_SEASON].copy()
df_holdout = df_all[df_all["season"] == HOLDOUT_SEASON].copy()

# Fit Dixon-Coles 1H
teams = sorted(list(set(df_train["home"].unique()) | set(df_train["away"].unique())))
team_map = {t: i for i, t in enumerate(teams)}
n_teams = len(teams)
h_idx = np.array([team_map[t] for t in df_train["home"]])
a_idx = np.array([team_map[t] for t in df_train["away"]])
ht_hg = df_train["hthg"].values
ht_ag = df_train["htag"].values
n_train = len(df_train)

def unpack_params(p):
    alphas = np.append(p[:n_teams-1], -np.sum(p[:n_teams-1]))
    betas = np.append(p[n_teams-1:2*n_teams-2], -np.sum(p[n_teams-1:2*n_teams-2]))
    return alphas, betas, p[-3], p[-2], p[-1]

def neg_log_lik_1h(params):
    alphas, betas, gamma, mu, rho = unpack_params(params)
    lh = np.exp(mu + alphas[h_idx] + betas[a_idx] + gamma)
    la = np.exp(mu + alphas[a_idx] + betas[h_idx])
    tau_vals = np.ones(n_train)
    m00 = (ht_hg == 0) & (ht_ag == 0)
    m01 = (ht_hg == 0) & (ht_ag == 1)
    m10 = (ht_hg == 1) & (ht_ag == 0)
    m11 = (ht_hg == 1) & (ht_ag == 1)
    tau_vals[m00] = np.maximum(1.0 - lh[m00] * la[m00] * rho, 1e-5)
    tau_vals[m01] = np.maximum(1.0 + lh[m01] * rho, 1e-5)
    tau_vals[m10] = np.maximum(1.0 + la[m10] * rho, 1e-5)
    tau_vals[m11] = np.maximum(1.0 - rho, 1e-5)
    ll = np.log(tau_vals) - lh + ht_hg * np.log(np.maximum(lh, 1e-5)) - la + ht_ag * np.log(np.maximum(la, 1e-5))
    return -np.sum(ll) + 0.05 * (np.sum(alphas**2) + np.sum(betas**2))

init_p = np.zeros(2*n_teams + 1)
init_p[-3], init_p[-2], init_p[-1] = 0.20, -0.45, -0.05
bounds = [(-1.5, 1.5)] * (2*n_teams - 2) + [(0.0, 0.8), (-1.5, 0.5), (-0.4, 0.2)]
res_1h = minimize(neg_log_lik_1h, init_p, method="L-BFGS-B", bounds=bounds)
opt_alphas_1h, opt_betas_1h, opt_gamma_1h, opt_mu_1h, opt_rho_1h = unpack_params(res_1h.x)

def get_team_ratings(team: str):
    if team in team_map:
        idx = team_map[team]
        return opt_alphas_1h[idx], opt_betas_1h[idx]
    return -0.15, 0.15

def compute_1h_grid(lh: float, la: float, rho: float, max_g: int = 5) -> np.ndarray:
    grid = np.zeros((max_g + 1, max_g + 1))
    for x in range(max_g + 1):
        for y in range(max_g + 1):
            t = 1.0
            if x == 0 and y == 0: t = 1.0 - (lh * la * rho)
            elif x == 0 and y == 1: t = 1.0 + (lh * rho)
            elif x == 1 and y == 0: t = 1.0 + (la * rho)
            elif x == 1 and y == 1: t = 1.0 - rho
            grid[x, y] = max(poisson.pmf(x, lh) * poisson.pmf(y, la) * t, 0.0)
    s = grid.sum()
    return grid / s if s > 0 else grid

def calculate_mozzart_probabilities(home: str, away: str):
    ah, bh = get_team_ratings(home)
    aa, ba = get_team_ratings(away)
    lh_1h = np.exp(opt_mu_1h + ah + ba + opt_gamma_1h)
    la_1h = np.exp(opt_mu_1h + aa + bh)
    grid = compute_1h_grid(lh_1h, la_1h, opt_rho_1h)
    return {
        "I1+": float(1.0 - grid[0, 0]),
        "I2+": float(1.0 - grid[0, 0] - grid[0, 1] - grid[1, 0]),
        "I_1-2": float(grid[0, 1] + grid[1, 0] + grid[1, 1] + grid[2, 0] + grid[0, 2]),
        "HT_1": float(np.sum(np.tril(grid, -1))),
        "HT_X": float(np.sum(np.diag(grid))),
        "HT_2": float(np.sum(np.triu(grid, 1)))
    }

def devig_power_2way(o1: float, o2: float):
    inv1, inv2 = 1.0 / o1, 1.0 / o2
    try:
        k_opt = brentq(lambda k: (inv1 ** k + inv2 ** k) - 1.0, 0.5, 5.0)
        return float(inv1 ** k_opt), float(inv2 ** k_opt)
    except Exception:
        s = inv1 + inv2
        return float(inv1 / s), float(inv2 / s)

def devig_power_3way(o1: float, ox: float, o2: float):
    inv1, invx, inv2 = 1.0 / o1, 1.0 / ox, 1.0 / o2
    try:
        k_opt = brentq(lambda k: (inv1 ** k + invx ** k + inv2 ** k) - 1.0, 0.5, 5.0)
        return float(inv1 ** k_opt), float(invx ** k_opt), float(inv2 ** k_opt), float(k_opt)
    except Exception:
        s = inv1 + invx + inv2
        return float(inv1 / s), float(invx / s), float(inv2 / s), 1.0

def solve_implied_poisson_lambda(p_over_25: float) -> float:
    try:
        return float(brentq(lambda lam: (1.0 - poisson.cdf(2, lam)) - p_over_25, 0.5, 6.0))
    except Exception:
        return 2.80

mean_margin = 0.145

wagers_fwd = []
wagers_rev = []
bankroll_rev = 1000.0
unit_stake = 10.0

for idx, row in df_holdout.iterrows():
    m_probs = calculate_mozzart_probabilities(row["home"], row["away"])
    
    p_open_o25, _ = devig_power_2way(row["p_o25"], row["p_u25"])
    lam_open_1h = solve_implied_poisson_lambda(p_open_o25) * 0.44
    
    p_close_o25, _ = devig_power_2way(row["p_close_o25"], row["p_close_u25"])
    lam_close_1h = solve_implied_poisson_lambda(p_close_o25) * 0.44
    
    p_mkt_open_i2 = 1.0 - np.exp(-lam_open_1h) - lam_open_1h * np.exp(-lam_open_1h)
    p_mkt_close_i2 = 1.0 - np.exp(-lam_close_1h) - lam_close_1h * np.exp(-lam_close_1h)
    
    p_mkt_open_i0_1 = 1.0 - p_mkt_open_i2
    p_mkt_close_i0_1 = 1.0 - p_mkt_close_i2
    
    p_mkt_open_i0 = np.exp(-lam_open_1h)
    p_mkt_close_i0 = np.exp(-lam_close_1h)
    
    tot_ht = row["hthg"] + row["htag"]
    won_i0_1 = 1 if tot_ht <= 1 else 0
    won_i0 = 1 if tot_ht == 0 else 0
    won_ht_x = 1 if row["hthg"] == row["htag"] else 0
    
    # 1. Reverse Market 1: I 0-1 (Under 1.5 Goals HT)
    p_mod_i0_1 = 1.0 - m_probs["I2+"]
    odds_rev_i0_1 = round(max((1.0 / p_mkt_open_i0_1) * (1.0 - mean_margin * 0.22), 1.22), 2)
    fair_close_i0_1 = 1.0 / p_mkt_close_i0_1
    clv_i0_1 = (odds_rev_i0_1 / fair_close_i0_1) - 1.0
    ev_rev_i0_1 = (p_mod_i0_1 * odds_rev_i0_1) - 1.0
    
    if ev_rev_i0_1 > 0.012 and clv_i0_1 > -0.005:
        pnl = round(unit_stake * (odds_rev_i0_1 - 1.0), 2) if won_i0_1 else -unit_stake
        bankroll_rev += pnl
        wagers_rev.append({
            "match_id": idx, "market": "I 0-1", "odds": odds_rev_i0_1, "won": won_i0_1,
            "stake": unit_stake, "pnl": pnl, "real_clv": clv_i0_1
        })
        
    # 2. Reverse Market 2: I 0 (0-0 HT)
    p_mod_i0 = 1.0 - m_probs["I1+"]
    odds_rev_i0 = round(max((1.0 / p_mkt_open_i0) * (1.0 - mean_margin * 0.25), 1.55), 2)
    fair_close_i0 = 1.0 / p_mkt_close_i0
    clv_i0 = (odds_rev_i0 / fair_close_i0) - 1.0
    ev_rev_i0 = (p_mod_i0 * odds_rev_i0) - 1.0
    
    if ev_rev_i0 > 0.015 and clv_i0 > -0.005:
        pnl = round(unit_stake * (odds_rev_i0 - 1.0), 2) if won_i0 else -unit_stake
        bankroll_rev += pnl
        wagers_rev.append({
            "match_id": idx, "market": "I 0", "odds": odds_rev_i0, "won": won_i0,
            "stake": unit_stake, "pnl": pnl, "real_clv": clv_i0
        })

    # 3. Reverse Market 3: HT X (Draw HT)
    p_mod_htx = m_probs["HT_X"]
    p_open_ht1, p_open_htx, p_open_ht2 = devig_power_3way(row["ps_h"], row["ps_d"], row["ps_a"])[:3]
    p_close_ht1, p_close_htx, p_close_ht2 = devig_power_3way(row["ps_close_h"], row["ps_close_d"], row["ps_close_a"])[:3]
    
    # Halftime Draw opening odds (Mozzart retail line shading is smaller on HT draw)
    odds_rev_htx = round(max((1.0 / p_open_htx) * (1.0 - mean_margin * 0.15), 1.65), 2)
    fair_close_htx = 1.0 / p_close_htx
    clv_htx = (odds_rev_htx / fair_close_htx) - 1.0
    ev_rev_htx = (p_mod_htx * odds_rev_htx) - 1.0
    
    if ev_rev_htx > 0.010 and clv_htx > -0.005:
        pnl = round(unit_stake * (odds_rev_htx - 1.0), 2) if won_ht_x else -unit_stake
        bankroll_rev += pnl
        wagers_rev.append({
            "match_id": idx, "market": "HT X", "odds": odds_rev_htx, "won": won_ht_x,
            "stake": unit_stake, "pnl": pnl, "real_clv": clv_htx
        })

df_w = pd.DataFrame(wagers_rev)
print(f"Total Reverse Wagers: {len(df_w)}")
print(f"Win Rate: {df_w['won'].mean():.2%}")
print(f"Mean CLV: {df_w['real_clv'].mean():.2%}")
print(f"Total PnL: €{df_w['pnl'].sum():.2f}")
print(f"ROI: {df_w['pnl'].sum() / df_w['stake'].sum():.2%}")
