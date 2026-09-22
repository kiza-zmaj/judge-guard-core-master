import pandas as pd
import requests
import io

df_moz = pd.read_csv("./unified_betting_core/output/mozzart_parsed/mozzart_historical_odds.csv", low_memory=False)
df_moz["date_clean"] = df_moz["date"].astype(str).str.strip()

r = requests.get("https://www.football-data.co.uk/mmz4281/2425/E0.csv", timeout=10)
df_epl = pd.read_csv(io.StringIO(r.text))
df_epl["date_iso"] = pd.to_datetime(df_epl["Date"], dayfirst=True).dt.strftime("%Y-%m-%d")

team_syns = {
    "Arsenal": ["ARSENAL"], "Aston Villa": ["ASTON VILA", "VILA"], "Bournemouth": ["BORNMUT"],
    "Brentford": ["BRENTFORD"], "Brighton": ["BRAJTON"], "Chelsea": ["ČELSI", "CELSI"],
    "Crystal Palace": ["KRISTAL PALAS", "PALAS"], "Everton": ["EVERTON"], "Fulham": ["FULAM"],
    "Ipswich": ["IPSVIČ", "IPSVIC"], "Leicester": ["LESTER"], "Liverpool": ["LIVERPUL"],
    "Man City": ["MAN.SITI", "MANČESTER SITI", "MANCESTER SITI", "SITI"],
    "Man United": ["MAN.JUN", "MANČESTER JUN", "MANCESTER JUN", "JUNAJTED"],
    "Newcastle": ["NJUKASL"], "Nott'm Forest": ["NOTINGEM", "FOREST"], "Southampton": ["SAUTEMPTON"],
    "Tottenham": ["TOTENHEM"], "West Ham": ["VEST HEM"], "Wolves": ["VULVERHEMPTON", "VULVER"]
}

# Group Mozzart by date for O(1) date lookup
moz_by_date = {}
for idx, m in df_moz.iterrows():
    d = str(m["date_clean"])
    if d not in moz_by_date:
        moz_by_date[d] = []
    moz_by_date[d].append(m)

matches_found = 0
for idx, row in df_epl.iterrows():
    d = row["date_iso"]
    h_syns = team_syns.get(row["HomeTeam"], [row["HomeTeam"].upper()])
    a_syns = team_syns.get(row["AwayTeam"], [row["AwayTeam"].upper()])
    
    candidates = moz_by_date.get(d, [])
    matched = None
    for m in candidates:
        mh = str(m["home_team"]).upper()
        ma = str(m["away_team"]).upper()
        if any(s in mh for s in h_syns) and any(s in ma for s in a_syns):
            matched = m
            break
    if matched is not None:
        matches_found += 1

print(f"Matched {matches_found} out of {len(df_epl)} EPL matches ({matches_found/len(df_epl):.1%})!")
