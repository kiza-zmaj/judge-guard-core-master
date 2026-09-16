"""
Data Pipeline & Team Name Normalization.
Merges bookmaker fixtures with Understat xG metrics.
"""

import pandas as pd
from typing import List, Dict, Any, Optional
from unified_betting_core.data_ingestion.understat_scraper import UnderstatScraper
from unified_betting_core.data_ingestion.odds_fetcher import OddsFetcher

# Standardize names across Bookmakers, Understat, and Historical datasets
TEAM_NAME_MAPPING = {
    "man utd": "Manchester United",
    "manchester utd": "Manchester United",
    "man united": "Manchester United",
    "man city": "Manchester City",
    "manchester c": "Manchester City",
    "spurs": "Tottenham",
    "tottenham hotspur": "Tottenham",
    "wolves": "Wolverhampton Wanderers",
    "wolverhampton": "Wolverhampton Wanderers",
    "newcastle": "Newcastle United",
    "newcastle utd": "Newcastle United",
    "nottingham": "Nottingham Forest",
    "nott'm forest": "Nottingham Forest",
    "nottm forest": "Nottingham Forest",
    "brighton and hove albion": "Brighton",
    "brighton & hove albion": "Brighton",
    "leicester": "Leicester City",
    "west ham": "West Ham United",
    "sheffield utd": "Sheffield United",
    "sheffield united": "Sheffield United",
    "luton": "Luton Town",
    "ipswich": "Ipswich Town"
}

def normalize_name(raw_name: str) -> str:
    """Normalizes team name to a canonical form."""
    if not raw_name:
        return ""
    cleaned = raw_name.strip().lower()
    return TEAM_NAME_MAPPING.get(cleaned, raw_name.strip())

class DataPipeline:
    def __init__(self):
        self.understat = UnderstatScraper()
        self.odds_fetcher = OddsFetcher()

    def get_unified_dataset(self, fixtures: Optional[List[Dict[str, Any]]] = None) -> pd.DataFrame:
        """
        Gathers upcoming fixtures, normalizes team names,
        attaches home and away xG / xGA metrics, and returns a DataFrame.
        """
        if fixtures is None:
            fixtures = self.odds_fetcher.fetch_upcoming_fixtures()
        team_stats = self.understat.get_team_stats()

        rows = []
        for match in fixtures:
            home_raw = match.get("home_team", "")
            away_raw = match.get("away_team", "")
            home = normalize_name(home_raw)
            away = normalize_name(away_raw)

            # Match stats fallback
            # League averages: ~1.4 home xG, ~1.2 away xG
            h_stat = team_stats.get(home, {})
            a_stat = team_stats.get(away, {})

            # Estimate match xG using team attack and opponent defense
            base_home_xg = h_stat.get("xG", 1.4)
            opp_away_xga = a_stat.get("xGA", 1.3)
            est_home_xg = round((base_home_xg + opp_away_xga) / 2.0, 2)

            base_away_xg = a_stat.get("xG", 1.1)
            opp_home_xga = h_stat.get("xGA", 1.2)
            est_away_xg = round((base_away_xg + opp_home_xga) / 2.0, 2)

            # If match has specific match xG provided, preserve it
            final_home_xg = float(match.get("home_xg", est_home_xg))
            final_away_xg = float(match.get("away_xg", est_away_xg))

            rows.append({
                "id": match.get("id"),
                "date": match.get("date", "Upcoming"),
                "league": match.get("league", "EPL"),
                "home_team": home,
                "away_team": away,
                "home_team_raw": home_raw,
                "away_team_raw": away_raw,
                "home_odds": float(match.get("home_odds", 2.0)),
                "draw_odds": float(match.get("draw_odds", 3.2)),
                "away_odds": float(match.get("away_odds", 3.5)),
                "bookmaker": match.get("bookmaker", "Market Average"),
                "home_xg": final_home_xg,
                "away_xg": final_away_xg,
                "is_live": match.get("is_live", False),
                "current_score": match.get("current_score", {}),
                "elapsed_minutes": match.get("elapsed_minutes", 0.0)
            })

        df = pd.DataFrame(rows)
        return df

    def get_live_and_today_dataset(self, sports: Optional[List[str]] = None) -> pd.DataFrame:
        """
        Gathers real-time in-play and today's matches directly from The-Odds-API.
        """
        fixtures = self.odds_fetcher.fetch_live_and_today_fixtures(sports=sports)
        return self.get_unified_dataset(fixtures=fixtures)

