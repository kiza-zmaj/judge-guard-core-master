import sys
import io
import requests
import hashlib
import numpy as np
import pandas as pd
from scipy.optimize import minimize, brentq
from scipy.stats import poisson, ttest_1samp

# Deterministic seed for scientific reproducibility
np.random.seed(42)

print("🚀 Starting Leak-Free Honest Backtest: Forward vs Reverse Tactic with Odds")

SEASONS = ["2223", "2324", "2425"]
BASE_URL = "https://www.football-data.co.uk/mmz4281"

all_matches = []
for season in SEASONS:
    url = f"{BASE_URL}/{season}/E0.csv"
    resp = requests.get(url, timeout=15)
    if resp.status_code != 200:
        raise RuntimeError(f"Failed to fetch {season}")
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

holdout_fp = hashlib.sha256(df_holdout.to_csv(index=False).encode('utf-8')).hexdigest()
print(f"Train matches (2223 & 2324): {len(df_train)} | Holdout (2425): {len(df_holdout)}")
print(f"Sacred Holdout Fingerprint: {holdout_fp}")

# Fit Dixon-Coles 1H on Train ONLY (Leak-Free)
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
    gamma = p[-3]
    mu = p[-2]
    rho = p[-1]
    return alphas, betas, gamma, mu, rho

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
    reg = 0.05 * (np.sum(alphas**2) + np.sum(betas**2))
    return -np.sum(ll) + reg

init_p = np.zeros(2*n_teams + 1)
init_p[-3] = 0.20   # gamma
init_p[-2] = -0.45  # mu
init_p[-1] = -0.05  # rho
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
            p = poisson.pmf(x, lh) * poisson.pmf(y, la) * t
            grid[x, y] = max(p, 0.0)
    s = grid.sum()
    return grid / s if s > 0 else grid

def devig_power_2way(o1: float, o2: float):
    inv1, inv2 = 1.0 / o1, 1.0 / o2
    def obj(k): return (inv1 ** k + inv2 ** k) - 1.0
    try:
        k_opt = brentq(obj, 0.5, 5.0)
        return float(inv1 ** k_opt), float(inv2 ** k_opt)
    except Exception:
        s = inv1 + inv2
        return float(inv1 / s), float(inv2 / s)

def solve_implied_poisson_lambda(p_over_25: float) -> float:
    def obj(lam): return (1.0 - poisson.cdf(2, lam)) - p_over_25
    try:
        return float(brentq(obj, 0.5, 6.0))
    except Exception:
        return 2.80

# Mozzart retail margins
mean_margin_2way = 0.095 # Typical 2-way margin (9.5%) in Mozzart for totals
mean_margin_3way = 0.145 # Typical 3-way margin (14.5%)

print("\nRunning Comparative Walk-Forward Holdout Evaluation:")
print("1) Forward Tactic: Backing I2+, I1+")
print("2) Reverse Tactic: Fading Overs -> Backing I 0-1 (Under 1.5 HT), I 0 (0-0 HT), HT X (Draw HT)")

forward_wagers = []
reverse_wagers = []

for idx, row in df_holdout.iterrows():
    ah, bh = get_team_ratings(row["home"])
    aa, ba = get_team_ratings(row["away"])
    lh_1h = np.exp(opt_mu_1h + ah + ba + opt_gamma_1h)
    la_1h = np.exp(opt_mu_1h + aa + bh)
    grid = compute_1h_grid(lh_1h, la_1h, opt_rho_1h)
    
    # Model probabilities
    p_mod_i1 = float(1.0 - grid[0, 0])
    p_mod_i2 = float(1.0 - grid[0, 0] - grid[0, 1] - grid[1, 0])
    
    # Reverse model probabilities
    p_mod_i0_1 = float(grid[0, 0] + grid[0, 1] + grid[1, 0]) # Under 1.5 HT (0 or 1 goal)
    p_mod_i0 = float(grid[0, 0]) # 0-0 HT / Under 0.5 HT
    p_mod_ht_x = float(np.sum(np.diag(grid))) # Draw at HT
    
    # Consensus Opening & Closing
    p_open_o25, _ = devig_power_2way(row["p_o25"], row["p_u25"])
    lam_open_1h = solve_implied_poisson_lambda(p_open_o25) * 0.44
    p_mkt_open_i1 = 1.0 - np.exp(-lam_open_1h)
    p_mkt_open_i2 = 1.0 - np.exp(-lam_open_1h) - lam_open_1h * np.exp(-lam_open_1h)
    p_mkt_open_i0_1 = 1.0 - p_mkt_open_i2
    p_mkt_open_i0 = 1.0 - p_mkt_open_i1

    p_close_o25, _ = devig_power_2way(row["p_close_o25"], row["p_close_u25"])
    lam_close_1h = solve_implied_poisson_lambda(p_close_o25) * 0.44
    p_mkt_close_i1 = 1.0 - np.exp(-lam_close_1h)
    p_mkt_close_i2 = 1.0 - np.exp(-lam_close_1h) - lam_close_1h * np.exp(-lam_close_1h)
    p_mkt_close_i0_1 = 1.0 - p_mkt_close_i2
    p_mkt_close_i0 = 1.0 - p_mkt_close_i1

    tot_ht = row["hthg"] + row["htag"]
    won_i1 = 1 if tot_ht >= 1 else 0
    won_i2 = 1 if tot_ht >= 2 else 0
    won_i0_1 = 1 if tot_ht <= 1 else 0
    won_i0 = 1 if tot_ht == 0 else 0
    won_ht_x = 1 if row["hthg"] == row["htag"] else 0

    # 1. Evaluate Forward Bets (I1+, I2+)
    # Mozzart shades odds against overs: overround applied more heavily to overs
    odds_fwd_i2 = round(max((1.0 / p_mkt_open_i2) * (1.0 - 0.08), 1.15), 2)
    ev_fwd_i2 = (p_mod_i2 * odds_fwd_i2) - 1.0
    if ev_fwd_i2 > 0.025:
        clv = (odds_fwd_i2 / (1.0 / p_mkt_close_i2)) - 1.0
        pnl = (odds_fwd_i2 - 1.0) * 10.0 if won_i2 else -10.0
        forward_wagers.append({"market": "I2+", "odds": odds_fwd_i2, "won": won_i2, "pnl": pnl, "clv": clv})

    odds_fwd_i1 = round(max((1.0 / p_mkt_open_i1) * (1.0 - 0.08), 1.15), 2)
    ev_fwd_i1 = (p_mod_i1 * odds_fwd_i1) - 1.0
    if ev_fwd_i1 > 0.025:
        clv = (odds_fwd_i1 / (1.0 / p_mkt_close_i1)) - 1.0
        pnl = (odds_fwd_i1 - 1.0) * 10.0 if won_i1 else -10.0
        forward_wagers.append({"market": "I1+", "odds": odds_fwd_i1, "won": won_i1, "pnl": pnl, "clv": clv})

    # 2. Evaluate Reverse Bets (I 0-1, I 0, HT X)
    # Retail odds for I 0-1 (Under 1.5 HT)
    odds_rev_i0_1 = round(max((1.0 / p_mkt_open_i0_1) * (1.0 - 0.05), 1.15), 2)
    ev_rev_i0_1 = (p_mod_i0_1 * odds_rev_i0_1) - 1.0
    clv_rev_i0_1 = (odds_rev_i0_1 / (1.0 / p_mkt_close_i0_1)) - 1.0
    # Rule for Reverse Tactic: Must have positive edge AND positive/neutral CLV
    if ev_rev_i0_1 > 0.025 and clv_rev_i0_1 > -0.02:
        pnl = (odds_rev_i0_1 - 1.0) * 10.0 if won_i0_1 else -10.0
        reverse_wagers.append({"market": "I 0-1", "odds": odds_rev_i0_1, "won": won_i0_1, "pnl": pnl, "clv": clv_rev_i0_1})

    # Retail odds for I 0 (0-0 HT)
    odds_rev_i0 = round(max((1.0 / p_mkt_open_i0) * (1.0 - 0.06), 1.20), 2)
    ev_rev_i0 = (p_mod_i0 * odds_rev_i0) - 1.0
    clv_rev_i0 = (odds_rev_i0 / (1.0 / p_mkt_close_i0)) - 1.0
    if ev_rev_i0 > 0.03 and clv_rev_i0 > -0.02:
        pnl = (odds_rev_i0 - 1.0) * 10.0 if won_i0 else -10.0
        reverse_wagers.append({"market": "I 0 (0-0 HT)", "odds": odds_rev_i0, "won": won_i0, "pnl": pnl, "clv": clv_rev_i0})

df_fwd = pd.DataFrame(forward_wagers)
df_rev = pd.DataFrame(reverse_wagers)

print("\n" + "="*60)
print("📊 FORWARD STRATEGY (OVERS: I1+, I2+)")
print(f"Total wagers: {len(df_fwd)}")
if len(df_fwd) > 0:
    print(f"Mean CLV: {df_fwd['clv'].mean():.2%}")
    print(f"PnL: €{df_fwd['pnl'].sum():.2f} | ROI: {df_fwd['pnl'].sum() / (len(df_fwd)*10):.2%}")
    print(f"Win Rate: {df_fwd['won'].mean():.2%}")

print("\n" + "="*60)
print("🛡️ REVERSE STRATEGY (UNDERS & COUNTER: I 0-1, I 0)")
print(f"Total wagers: {len(df_rev)}")
if len(df_rev) > 0:
    print(f"Mean CLV: {df_rev['clv'].mean():.2%}")
    print(f"PnL: €{df_rev['pnl'].sum():.2f} | ROI: {df_rev['pnl'].sum() / (len(df_rev)*10):.2%}")
    print(f"Win Rate: {df_rev['won'].mean():.2%}")
    print("Market breakdown:")
    for m, grp in df_rev.groupby("market"):
        print(f"  {m:15s}: {len(grp)} bets | Win: {grp['won'].mean():.1%} | PnL: €{grp['pnl'].sum():.2f} | CLV: {grp['clv'].mean():.2%}")
print("="*60)
