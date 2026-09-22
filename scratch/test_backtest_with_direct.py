import os
import io
import json
import requests
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.stats import poisson

SEASONS = ["2223", "2324", "2425"]
LEAGUES = {
    "E0": "Premier League (England)",
    "SP1": "La Liga (Spain)",
    "I1": "Serie A (Italy)",
    "D1": "Bundesliga (Germany)",
    "F1": "Ligue 1 (France)"
}
BASE_URL = "https://www.football-data.co.uk/mmz4281"

def normalize_date_to_iso(date_str: str) -> str:
    if pd.isna(date_str) or not str(date_str).strip():
        return ""
    s = str(date_str).strip()
    try:
        return pd.to_datetime(s, dayfirst=True).strftime('%Y-%m-%d')
    except Exception:
        pass
    try:
        return pd.to_datetime(s).strftime('%Y-%m-%d')
    except Exception:
        return s

all_matches = []
for season in SEASONS:
    for lg, lg_name in LEAGUES.items():
        url = f"{BASE_URL}/{season}/{lg}.csv"
        try:
            resp = requests.get(url, timeout=12)
            if resp.status_code == 200:
                df_s = pd.read_csv(io.StringIO(resp.text))
                for _, row in df_s.iterrows():
                    if pd.isna(row.get("HomeTeam")) or pd.isna(row.get("FTHG")) or pd.isna(row.get("HTHG")):
                        continue
                    try:
                        d_iso = normalize_date_to_iso(row["Date"])
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
                            "ps_h": float(row.get("PSCH", row.get("PSH", 2.5))),
                            "ps_d": float(row.get("PSCD", row.get("PSD", 3.2))),
                            "ps_a": float(row.get("PSCA", row.get("PSA", 3.0))),
                            "p_o25": float(row.get("B365>2.5", row.get("P>2.5", 1.9))),
                            "p_u25": float(row.get("B365<2.5", row.get("P<2.5", 1.9))),
                            "p_close_o25": float(row.get("PCD>2.5", row.get("B365CD>2.5", 1.9))),
                            "p_close_u25": float(row.get("PCD<2.5", row.get("B365CD<2.5", 1.9))),
                            "ps_close_h": float(row.get("PSCH", 2.5)),
                            "ps_close_d": float(row.get("PSCD", 3.2)),
                            "ps_close_a": float(row.get("PSCA", 3.0)),
                        })
                    except Exception:
                        continue
        except Exception:
            continue

df_all = pd.DataFrame(all_matches)
df_train = df_all[df_all["season"].isin(["2223", "2324"])].copy()
df_holdout = df_all[df_all["season"] == "2425"].copy().reset_index(drop=True)

# Fit Dixon-Coles Per-League
def tau(x, y, lambda_param, nu_param, rho):
    if x == 0 and y == 0:
        return 1.0 - (lambda_param * nu_param * rho)
    elif x == 0 and y == 1:
        return 1.0 + (lambda_param * rho)
    elif x == 1 and y == 0:
        return 1.0 + (nu_param * rho)
    elif x == 1 and y == 1:
        return 1.0 - rho
    else:
        return 1.0

def fit_league_dixon_coles(df_lg):
    teams = sorted(list(set(df_lg["home"].unique()) | set(df_lg["away"].unique())))
    n_teams = len(teams)
    team_idx = {t: i for i, t in enumerate(teams)}
    
    home_idx = df_lg["home"].map(team_idx).values
    away_idx = df_lg["away"].map(team_idx).values
    h_goals = df_lg["hthg"].values
    a_goals = df_lg["htag"].values
    
    def neg_log_likelihood(params):
        alphas = params[:n_teams]
        betas = params[n_teams:2*n_teams]
        gamma = params[2*n_teams]
        mu = params[2*n_teams + 1]
        rho = params[2*n_teams + 2]
        
        pen = 1e4 * (alphas.sum()**2 + betas.sum()**2)
        log_lambda = mu + alphas[home_idx] + betas[away_idx] + gamma
        log_nu = mu + alphas[away_idx] + betas[home_idx]
        
        lam = np.exp(np.clip(log_lambda, -4.0, 3.0))
        nu = np.exp(np.clip(log_nu, -4.0, 3.0))
        
        ll = poisson.logpmf(h_goals, lam) + poisson.logpmf(a_goals, nu)
        adj = np.array([tau(h, a, l, n, rho) for h, a, l, n in zip(h_goals, a_goals, lam, nu)])
        adj = np.maximum(adj, 1e-6)
        ll += np.log(adj)
        return -np.sum(ll) + pen

    init_params = np.zeros(2 * n_teams + 3)
    init_params[2*n_teams] = 0.20
    init_params[2*n_teams + 1] = -0.65
    init_params[2*n_teams + 2] = -0.05
    
    bnds = [(-2.0, 2.0)] * (2 * n_teams) + [(0.0, 1.0), (-2.0, 0.5), (-0.3, 0.3)]
    res = minimize(neg_log_likelihood, init_params, method='L-BFGS-B', bounds=bnds, options={'maxiter': 300, 'ftol': 1e-7})
    
    return {
        "success": res.success,
        "alphas": {t: res.x[i] for t, i in team_idx.items()},
        "betas": {t: res.x[n_teams + i] for t, i in team_idx.items()},
        "gamma": float(res.x[2*n_teams]),
        "mu": float(res.x[2*n_teams + 1]),
        "rho": float(res.x[2*n_teams + 2]),
    }

league_models = {}
for lg in LEAGUES:
    df_lg = df_train[df_train["league_code"] == lg]
    league_models[lg] = fit_league_dixon_coles(df_lg)

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
    lam_1h = np.exp(np.clip(log_lambda, -3.0, 2.0))
    nu_1h = np.exp(np.clip(log_nu, -3.0, 2.0))
    
    prob_matrix = np.zeros((max_goals + 1, max_goals + 1))
    for x in range(max_goals + 1):
        for y in range(max_goals + 1):
            prob_matrix[x, y] = poisson.pmf(x, lam_1h) * poisson.pmf(y, nu_1h) * tau(x, y, lam_1h, nu_1h, mod["rho"])
    prob_matrix = np.maximum(prob_matrix, 0.0)
    prob_matrix /= prob_matrix.sum()
    
    return {
        "HT_1": float(np.sum(np.tril(prob_matrix, -1))),
        "HT_X": float(np.sum(np.diag(prob_matrix))),
        "HT_2": float(np.sum(np.triu(prob_matrix, 1))),
        "I1+": float(1.0 - prob_matrix[0, 0]),
        "I2+": float(1.0 - prob_matrix[0, 0] - prob_matrix[0, 1] - prob_matrix[1, 0]),
        "I0_1": float(prob_matrix[0, 0] + prob_matrix[0, 1] + prob_matrix[1, 0]),
        "I0": float(prob_matrix[0, 0])
    }

def devig_power_3way(o1, ox, o2):
    if o1 <= 1.0 or ox <= 1.0 or o2 <= 1.0:
        return 1/3, 1/3, 1/3
    invs = [1.0 / o1, 1.0 / ox, 1.0 / o2]
    def obj(k):
        return (invs[0]**k + invs[1]**k + invs[2]**k - 1.0)**2
    res = minimize(obj, [1.0], method='Nelder-Mead', options={'xatol': 1e-6})
    k_opt = res.x[0]
    p = [invs[i]**k_opt for i in range(3)]
    s = sum(p)
    return p[0]/s, p[1]/s, p[2]/s

def devig_power_2way(o1, o2):
    if o1 <= 1.0 or o2 <= 1.0:
        return 0.5, 0.5
    invs = [1.0 / o1, 1.0 / o2]
    def obj(k):
        return (invs[0]**k + invs[1]**k - 1.0)**2
    res = minimize(obj, [1.0], method='Nelder-Mead', options={'xatol': 1e-6})
    k_opt = res.x[0]
    p = [invs[i]**k_opt for i in range(2)]
    s = sum(p)
    return p[0]/s, p[1]/s

def solve_implied_poisson_lambda(p_over_25):
    p_u25 = np.clip(1.0 - p_over_25, 1e-5, 0.99999)
    def obj(lam):
        return (poisson.cdf(2, max(lam, 0.01)) - p_u25)**2
    res = minimize(obj, [2.5], bounds=[(0.1, 7.0)], method='L-BFGS-B')
    return float(res.x[0])

# Load and index Clean Mozzart Data
candidates = [
    "/kaggle/input/mozzart-historical-odds/mozzart_historical_odds.csv",
    "./unified_betting_core/output/mozzart_parsed/mozzart_historical_odds.csv",
]
p = candidates[1] if os.path.exists(candidates[1]) else candidates[0]
df_moz = pd.read_csv(p, low_memory=False)
df_moz["iso_date"] = df_moz["date"].apply(normalize_date_to_iso)
for c in ["ht_1", "ht_x", "ht_2", "ft_1", "ft_x", "ft_2"]:
    if c in df_moz.columns:
        df_moz[c] = pd.to_numeric(df_moz[c], errors="coerce")

# Strictly filter clean base matches with genuine halftime lines (overround 5% to 28%)
margins = (1.0 / df_moz["ht_1"] + 1.0 / df_moz["ht_x"] + 1.0 / df_moz["ht_2"]) - 1.0
clean_base = df_moz[
    margins.between(0.04, 0.28) &
    df_moz['ht_x'].between(1.80, 3.60) &
    df_moz['ht_1'].between(1.50, 15.0) &
    df_moz['ht_2'].between(1.50, 15.0)
].copy()
mean_margin = float(margins[clean_base.index].median())
print(f"Empirical Mozzart Halftime Median Overround (N={len(clean_base):,}): {mean_margin:.2%}")

moz_by_date = {}
for _, m_row in clean_base.iterrows():
    d = str(m_row["iso_date"]).strip()
    if d:
        moz_by_date.setdefault(d, []).append(m_row)

team_synonyms = {
    # England (EPL)
    "Arsenal": ["ARSENAL"], "Aston Villa": ["ASTON VILA", "VILA"], "Bournemouth": ["BORNMUT"],
    "Brentford": ["BRENTFORD"], "Brighton": ["BRAJTON"], "Chelsea": ["ČELSI", "CELSI"],
    "Crystal Palace": ["KRISTAL PALAS", "PALAS"], "Everton": ["EVERTON"], "Fulham": ["FULAM"],
    "Ipswich": ["IPSVIČ", "IPSVIC"], "Leicester": ["LESTER"], "Liverpool": ["LIVERPUL"],
    "Man City": ["MAN.SITI", "MANČESTER SITI", "MANCESTER SITI", "SITI", "MANCHESTER CITY"],
    "Man United": ["MAN.JUN", "MANČESTER JUN", "MANCESTER JUN", "JUNAJTED", "MANCHESTER UNITED"],
    "Newcastle": ["NJUKASL"], "Nott'm Forest": ["NOTINGEM", "FOREST", "NOTTINGHAM"], "Southampton": ["SAUTEMPTON"],
    "Tottenham": ["TOTENHEM"], "West Ham": ["VEST HEM"], "Wolves": ["VULVERHEMPTON", "VULVER"],
    
    # Spain (La Liga)
    "Real Madrid": ["REAL MADRID"], "Barcelona": ["BARSELONA"], "Ath Madrid": ["ATLETIKO MADRID", "ATL.MADRID"],
    "Sevilla": ["SEVILJA"], "Villarreal": ["VILJAREAL"], "Sociedad": ["SOSIJEDAD", "REAL SOSIJEDAD"],
    "Betis": ["BETIS", "REAL BETIS"], "Valencia": ["VALENSIJA"], "Ath Bilbao": ["ATLETIK BILBAO", "BILBAO"],
    "Girona": ["ĐIRONA", "DIRONA", "GIRONA"], "Osasuna": ["OSASUNA"], "Getafe": ["HETAFE"],
    "Celta": ["SELTA", "SELTA VIGO"], "Mallorca": ["MAJORKA"], "Las Palmas": ["LAS PALMAS"],
    "Vallecano": ["RAJO VALJEKANO", "VALJEKANO"], "Alaves": ["ALAVES"], "Leganes": ["LEGANES"],
    "Valladolid": ["VALJADOLID"], "Espanol": ["ESPANJOL"],
    
    # Italy (Serie A)
    "Inter": ["INTER"], "Milan": ["MILAN"], "Juventus": ["JUVENTUS"], "Atalanta": ["ATALANTA"],
    "Roma": ["ROMA"], "Lazio": ["LACIO"], "Napoli": ["NAPOLI"], "Fiorentina": ["FIORENTINA"],
    "Bologna": ["BOLONJA"], "Torino": ["TORINO"], "Monza": ["MONCA"], "Genoa": ["ĐENOVA", "DENOVA"],
    "Lecce": ["LEĆE", "LECE"], "Udinese": ["UDINEZE"], "Cagliari": ["KALJARI"], "Verona": ["VERONA"],
    "Parma": ["PARMA"], "Como": ["KOMO"], "Venezia": ["VENECIJA"], "Empoli": ["EMPOLI"],
    
    # Germany (Bundesliga)
    "Bayern Munich": ["BAJERN"], "Leverkusen": ["LEVERKUZEN"], "Dortmund": ["DORTMUND"],
    "RB Leipzig": ["LAJPCIG", "RB LAJPCIG"], "Stuttgart": ["ŠTUTGART", "STUTGART"],
    "Ein Frankfurt": ["AJNTRAHT"], "Hoffenheim": ["HOFENHAJM"], "Heidenheim": ["HAJDENHAJM"],
    "Werder Bremen": ["VERDER"], "Freiburg": ["FRAJBURG"], "Augsburg": ["AUGZBURG"],
    "Wolfsburg": ["VOLFSBURG"], "M'gladbach": ["MENHENGLADBAH", "GLADBAH"],
    "Union Berlin": ["UNION BERLIN"], "Bochum": ["BOHUM"], "St Pauli": ["ST. PAULI", "SANKT PAULI"],
    "Holstein Kiel": ["KIL", "HOLŠTAJN KIL"], "Mainz": ["MAJNC"],
    
    # France (Ligue 1)
    "Paris SG": ["PSŽ", "PARI SEN ŽERMEN", "PSG"], "Monaco": ["MONAKO"], "Brest": ["BREST"],
    "Lille": ["LIL"], "Nice": ["NICA"], "Lyon": ["LION"], "Marseille": ["MARSELJ"],
    "Lens": ["LANS"], "Reims": ["REMS"], "Rennes": ["REN"], "Toulouse": ["TULUZ"],
    "Montpellier": ["MONPELJE"], "Strasbourg": ["STRAZBUR"], "Nantes": ["NANT"],
    "Le Havre": ["AVR", "LE AVR"], "Auxerre": ["OKSER"], "Angers": ["ANŽE", "ANZE"],
    "St Etienne": ["SENT ETJEN"]
}

wagers_rev = []
bankroll_rev = 1000.0
unit_stake = 10.0
direct_matches = 0

for idx, row in df_holdout.iterrows():
    m_probs = predict_1h_probabilities(row["home"], row["away"], row["league_code"])
    
    h_syns = team_synonyms.get(row["home"], [row["home"].upper()]) + [row["home"].upper()]
    a_syns = team_synonyms.get(row["away"], [row["away"].upper()]) + [row["away"].upper()]
    
    target_dates = [row["date"]]
    try:
        dt = pd.to_datetime(row["date"])
        for off in [-3, -2, -1, 1, 2, 3]:
            target_dates.append((dt + pd.Timedelta(days=off)).strftime("%Y-%m-%d"))
    except Exception:
        pass
        
    matched_moz = None
    for td in target_dates:
        for m in moz_by_date.get(td, []):
            mh = str(m.get("home_team", "")).upper()
            ma = str(m.get("away_team", "")).upper()
            if any(s in mh for s in h_syns) and any(s in ma for s in a_syns):
                matched_moz = m
                direct_matches += 1
                break
        if matched_moz is not None:
            break
            
    p_open_h, _, p_open_a = devig_power_3way(row["ps_h"], row["ps_d"], row["ps_a"])
    ratio_open = np.sqrt(max(p_open_h, 0.05) / max(p_open_a, 0.05))
    p_open_o25, _ = devig_power_2way(row["p_o25"], row["p_u25"])
    lam_open_1h = solve_implied_poisson_lambda(p_open_o25) * 0.44
    lam_h_open = lam_open_1h * (ratio_open / (1.0 + ratio_open))
    lam_a_open = lam_open_1h * (1.0 / (1.0 + ratio_open))
    
    p_close_h, _, p_close_a = devig_power_3way(row["ps_close_h"], row["ps_close_d"], row["ps_close_a"])
    ratio_close = np.sqrt(max(p_close_h, 0.05) / max(p_close_a, 0.05))
    p_close_o25, _ = devig_power_2way(row["p_close_o25"], row["p_close_u25"])
    lam_close_1h = solve_implied_poisson_lambda(p_close_o25) * 0.44
    lam_h_close = lam_close_1h * (ratio_close / (1.0 + ratio_close))
    lam_a_close = lam_close_1h * (1.0 / (1.0 + ratio_close))
    
    # Halftime Draw Market Probabilities (Sum of (k,k) Poisson probabilities)
    p_mkt_open_htx = sum(poisson.pmf(k, lam_h_open) * poisson.pmf(k, lam_a_open) for k in range(5))
    p_mkt_close_htx = sum(poisson.pmf(k, lam_h_close) * poisson.pmf(k, lam_a_close) for k in range(5))
    
    # Closing fair probabilities (Strict Benchmark)
    p_mkt_close_i2 = 1.0 - np.exp(-lam_close_1h) - lam_close_1h * np.exp(-lam_close_1h)
    p_mkt_close_i0_1 = 1.0 - p_mkt_close_i2
    p_mkt_close_i0 = np.exp(-lam_close_1h)
    
    fair_close_htx = 1.0 / max(p_mkt_close_htx, 0.05)
    fair_close_i0_1= 1.0 / max(p_mkt_close_i0_1, 0.05)
    fair_close_i0  = 1.0 / max(p_mkt_close_i0, 0.05)
    
    tot_ht = row["hthg"] + row["htag"]
    won_ht_x = 1 if row["hthg"] == row["htag"] else 0
    won_i0_1 = 1 if tot_ht <= 1 else 0
    won_i0   = 1 if tot_ht == 0 else 0
    
    rev_candidates = []
    
    # 1. Market: HT X (Halftime Draw)
    is_direct_moz_htx = False
    if matched_moz is not None and pd.notna(matched_moz.get("ht_x")) and 1.70 <= float(matched_moz["ht_x"]) <= 3.80:
        odds_rev_htx = float(matched_moz["ht_x"])
        is_direct_moz_htx = True
    else:
        odds_rev_htx = round(max((1.0 / p_mkt_open_htx) * (1.0 - mean_margin * 0.65), 1.65), 2)
        
    ev_rev_htx = (m_probs["HT_X"] * odds_rev_htx) - 1.0
    clv_htx = (odds_rev_htx / fair_close_htx) - 1.0
    
    # Thresholds: Direct quotes get realistic institutional threshold
    min_ev_htx = 0.002 if is_direct_moz_htx else 0.008
    min_clv_htx = -0.015 if is_direct_moz_htx else -0.005
    
    if ev_rev_htx > min_ev_htx and clv_htx > min_clv_htx:
        rev_candidates.append({
            "match_id": idx, "fixture": f"{row['home']} vs {row['away']}", "league": row["league_code"],
            "market": "HT X", "odds": odds_rev_htx, "won": won_ht_x, "stake": unit_stake,
            "ev": ev_rev_htx, "real_clv": clv_htx,
            "source": "MOZZART_DIRECT" if is_direct_moz_htx else "SYNTHETIC_PROXY"
        })
        
    # 2. Market: I 0-1
    p_mkt_open_i2 = 1.0 - np.exp(-lam_open_1h) - lam_open_1h * np.exp(-lam_open_1h)
    p_mkt_open_i0_1 = 1.0 - p_mkt_open_i2
    odds_rev_i0_1 = round(max((1.0 / p_mkt_open_i0_1) * (1.0 - mean_margin * 0.20), 1.25), 2)
    ev_rev_i0_1 = (m_probs["I0_1"] * odds_rev_i0_1) - 1.0
    clv_i0_1 = (odds_rev_i0_1 / fair_close_i0_1) - 1.0
    if ev_rev_i0_1 > 0.010 and clv_i0_1 > -0.005:
        rev_candidates.append({
            "match_id": idx, "fixture": f"{row['home']} vs {row['away']}", "league": row["league_code"],
            "market": "I 0-1", "odds": odds_rev_i0_1, "won": won_i0_1, "stake": unit_stake,
            "ev": ev_rev_i0_1, "real_clv": clv_i0_1, "source": "SYNTHETIC_PROXY"
        })
        
    # 3. Market: I 0
    p_mkt_open_i0 = np.exp(-lam_open_1h)
    odds_rev_i0 = round(max((1.0 / p_mkt_open_i0) * (1.0 - mean_margin * 0.22), 1.55), 2)
    ev_rev_i0 = (m_probs["I0"] * odds_rev_i0) - 1.0
    clv_i0 = (odds_rev_i0 / fair_close_i0) - 1.0
    if ev_rev_i0 > 0.012 and clv_i0 > -0.005:
        rev_candidates.append({
            "match_id": idx, "fixture": f"{row['home']} vs {row['away']}", "league": row["league_code"],
            "market": "I 0", "odds": odds_rev_i0, "won": won_i0, "stake": unit_stake,
            "ev": ev_rev_i0, "real_clv": clv_i0, "source": "SYNTHETIC_PROXY"
        })
        
    if rev_candidates:
        direct_cands = [c for c in rev_candidates if c["source"] == "MOZZART_DIRECT"]
        if direct_cands:
            best_rev = max(direct_cands, key=lambda x: x["ev"])
        else:
            best_rev = max(rev_candidates, key=lambda x: x["ev"])
            
        pnl = round(unit_stake * (best_rev["odds"] - 1.0), 2) if best_rev["won"] else -unit_stake
        best_rev["pnl"] = pnl
        bankroll_rev += pnl
        wagers_rev.append(best_rev)

df_w = pd.DataFrame(wagers_rev)
n_dir = sum(1 for w in wagers_rev if w["source"] == "MOZZART_DIRECT")
print("="*60)
print(f"Total Reverse Wagers: {len(df_w)}")
print(f"Direct Mozzart Matches Found : {direct_matches}")
print(f"Direct Mozzart Wagers Placed : {n_dir} ({n_dir/len(df_w):.1%})")
print(f"Synthetic Proxy Wagers Placed: {len(df_w)-n_dir}")
print(f"Win Rate: {df_w['won'].mean():.2%}")
print(f"Mean CLV: {df_w['real_clv'].mean():+.2%}")
print(f"Total PnL: EUR {df_w['pnl'].sum():.2f}")
print(f"Sample Yield (ROI): {df_w['pnl'].sum()/df_w['stake'].sum():.2%}")
print("="*60)
