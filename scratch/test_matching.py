import os
import io
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
df_holdout = df_all[df_all["season"] == "2425"].copy().reset_index(drop=True)
print(f"Loaded holdout matches (2024/25): {len(df_holdout)}")

# Load Mozzart dataset
candidates = [
    "/kaggle/input/mozzart-historical-odds/mozzart_historical_odds.csv",
    "./unified_betting_core/output/mozzart_parsed/mozzart_historical_odds.csv",
    "./unified_betting_core/data/mozzart_parsed.csv",
]
mozzart_csv_path = None
for p in candidates:
    if os.path.exists(p):
        mozzart_csv_path = p
        break

df_moz = pd.read_csv(mozzart_csv_path, low_memory=False)
df_moz["iso_date"] = df_moz["date"].apply(normalize_date_to_iso)
for c in ["ht_1", "ht_x", "ht_2", "ft_1", "ft_x", "ft_2"]:
    if c in df_moz.columns:
        df_moz[c] = pd.to_numeric(df_moz[c], errors="coerce")

# Filter clean matches with genuine ht_x
moz_clean = df_moz[
    df_moz["ht_x"].between(1.70, 3.80) & 
    (df_moz["ft_x"].between(2.40, 6.50) if "ft_x" in df_moz.columns else True)
].copy()
print(f"Clean Mozzart matches with genuine ht_x: {len(moz_clean)}")

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

# Index clean Mozzart by date
moz_by_date = {}
for _, m_row in moz_clean.iterrows():
    d = str(m_row["iso_date"]).strip()
    if d:
        moz_by_date.setdefault(d, []).append(m_row)

print(f"Indexed dates: {len(moz_by_date)}")

matches_found = 0
for idx, row in df_holdout.iterrows():
    h_syns = team_synonyms.get(row["home"], [row["home"].upper()]) + [row["home"].upper()]
    a_syns = team_synonyms.get(row["away"], [row["away"].upper()]) + [row["away"].upper()]
    
    target_dates = [row["date"]]
    try:
        dt = pd.to_datetime(row["date"])
        for offset in [-2, -1, 1, 2]:
            target_dates.append((dt + pd.Timedelta(days=offset)).strftime("%Y-%m-%d"))
    except Exception:
        pass
        
    matched = None
    for td in target_dates:
        for m in moz_by_date.get(td, []):
            mh = str(m.get("home_team", "")).upper()
            ma = str(m.get("away_team", "")).upper()
            if any(s in mh for s in h_syns) and any(s in ma for s in a_syns):
                matched = m
                break
        if matched is not None:
            break
            
    if matched is not None:
        matches_found += 1

print(f"Holdout matches directly matched to genuine Mozzart quotes (with +/-2 days): {matches_found}/{len(df_holdout)} ({matches_found/len(df_holdout):.1%})")
