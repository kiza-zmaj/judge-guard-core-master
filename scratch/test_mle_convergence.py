import io
import requests
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.stats import poisson

SEASONS = ["2223", "2324"]
LEAGUES = {
    "E0": "Premier League (England)",
    "SP1": "La Liga (Spain)",
    "I1": "Serie A (Italy)",
    "D1": "Bundesliga (Germany)",
    "F1": "Ligue 1 (France)"
}
BASE_URL = "https://www.football-data.co.uk/mmz4281"

all_matches = []
print("Fetching training data (2022/23 & 2023/24)...")
for season in SEASONS:
    for lg, lg_name in LEAGUES.items():
        url = f"{BASE_URL}/{season}/{lg}.csv"
        try:
            resp = requests.get(url, timeout=12)
            if resp.status_code == 200:
                df_s = pd.read_csv(io.StringIO(resp.text))
                for _, row in df_s.iterrows():
                    if pd.isna(row.get("HomeTeam")) or pd.isna(row.get("HTHG")) or pd.isna(row.get("HTAG")):
                        continue
                    all_matches.append({
                        "season": season,
                        "league_code": lg,
                        "home": str(row["HomeTeam"]).strip(),
                        "away": str(row["AwayTeam"]).strip(),
                        "hthg": int(row["HTHG"]),
                        "htag": int(row["HTAG"]),
                    })
        except Exception as e:
            print(f"Error {url}: {e}")

df_train = pd.DataFrame(all_matches)
print(f"Total train matches: {len(df_train)}")

def neg_log_likelihood_1h(params, matches, n_teams):
    mu = params[0]
    gamma = params[1]
    rho = params[2]
    alphas = params[3:3 + n_teams - 1]
    betas = params[3 + n_teams - 1:]
    
    alphas = np.append(alphas, -np.sum(alphas))
    betas = np.append(betas, -np.sum(betas))
    
    lh = np.exp(mu + alphas[matches[:, 0]] + betas[matches[:, 1]] + gamma)
    la = np.exp(mu + alphas[matches[:, 1]] + betas[matches[:, 0]])
    
    x = matches[:, 2]
    y = matches[:, 3]
    
    p_x = poisson.pmf(x, lh)
    p_y = poisson.pmf(y, la)
    
    tau = np.ones_like(lh)
    c00 = (x == 0) & (y == 0)
    c01 = (x == 0) & (y == 1)
    c10 = (x == 1) & (y == 0)
    c11 = (x == 1) & (y == 1)
    
    tau[c00] = 1.0 - (lh[c00] * la[c00] * rho)
    tau[c01] = 1.0 + (lh[c01] * rho)
    tau[c10] = 1.0 + (la[c10] * rho)
    tau[c11] = 1.0 - rho
    
    prob = np.maximum(p_x * p_y * tau, 1e-12)
    return -np.sum(np.log(prob))

print("\n--- Testing Per-League Dixon-Coles Fitting ---")
for lg, lg_name in LEAGUES.items():
    df_lg = df_train[df_train["league_code"] == lg].copy()
    teams = sorted(list(set(df_lg["home"].unique()) | set(df_lg["away"].unique())))
    team_map = {t: i for i, t in enumerate(teams)}
    n_teams = len(teams)
    
    train_data = []
    for _, r in df_lg.iterrows():
        train_data.append([team_map[r["home"]], team_map[r["away"]], r["hthg"], r["htag"]])
    train_arr = np.array(train_data, dtype=int)
    
    init_params = np.zeros(3 + 2 * (n_teams - 1))
    init_params[0] = -0.55
    init_params[1] = 0.20
    init_params[2] = -0.02
    
    bounds = [(-2.0, 0.5), (0.0, 0.6), (-0.15, 0.15)] + [(-1.5, 1.5)] * (2 * (n_teams - 1))
    res = minimize(neg_log_likelihood_1h, init_params, args=(train_arr, n_teams), method="L-BFGS-B", bounds=bounds, options={"maxiter": 200})
    
    opt_alphas = np.append(res.x[3:3 + n_teams - 1], -np.sum(res.x[3:3 + n_teams - 1]))
    opt_betas = np.append(res.x[3 + n_teams - 1:], -np.sum(res.x[3 + n_teams - 1:]))
    
    print(f"League {lg} ({lg_name}):")
    print(f"  Matches: {len(train_arr)}, Teams: {n_teams}")
    print(f"  Success: {res.success}, Iterations: {res.nit}")
    print(f"  Baseline mu: {res.x[0]:.3f}, Home gamma: {res.x[1]:.3f}, rho: {res.x[2]:.4f}")
    print(f"  Alpha std: {np.std(opt_alphas):.4f}, Beta std: {np.std(opt_betas):.4f}")
    print(f"  Sum alpha: {np.sum(opt_alphas):.6f}, Sum beta: {np.sum(opt_betas):.6f}")
