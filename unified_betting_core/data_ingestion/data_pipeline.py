"""
Data Pipeline & Team Name Normalization.
Merges bookmaker fixtures with Understat xG metrics.
"""

from typing import Any

import pandas as pd

from unified_betting_core.data_ingestion.odds_fetcher import OddsFetcher
from unified_betting_core.data_ingestion.understat_scraper import UnderstatScraper

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
    "ipswich": "Ipswich Town",
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

    def get_unified_dataset(
        self, fixtures: list[dict[str, Any]] | None = None
    ) -> pd.DataFrame:
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

            rows.append(
                {
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
                    "elapsed_minutes": match.get("elapsed_minutes", 0.0),
                }
            )

        df = pd.DataFrame(rows)
        return df

    def get_live_and_today_dataset(
        self, sports: list[str] | None = None
    ) -> pd.DataFrame:
        """
        Gathers real-time in-play and today's matches directly from The-Odds-API.
        """
        fixtures = self.odds_fetcher.fetch_live_and_today_fixtures(sports=sports)
        return self.get_unified_dataset(fixtures=fixtures)

    def get_upcoming_pre_match_dataset(self) -> pd.DataFrame:
        """
        Gathers only pre-match (not in-play) upcoming fixtures.
        Zero mock, zero simulation.
        """
        fixtures = self.odds_fetcher.fetch_upcoming_pre_match()
        return self.get_unified_dataset(fixtures=fixtures)

    def get_mozzart_dataset(
        self,
        mecevi_csv: str = "/home/kizamladjanijebac/Downloads/mozzart_fudbal_mecevi_2026-09-20.csv",
        marketi_csv: str | None = "/home/kizamladjanijebac/Downloads/mozzart_fudbal_marketi_2026-09-20 (copy).csv",
    ) -> pd.DataFrame:
        """
        Loads real Mozzart football matches and detailed markets from local CSV exports.
        Estimates league-calibrated xG for Poisson modeling and attaches derivative markets.
        """
        import os

        if not os.path.exists(mecevi_csv):
            raise FileNotFoundError(f"Mozzart mečevi CSV not found at {mecevi_csv}")

        mecevi_df = pd.read_csv(mecevi_csv)

        # Parse markets if present
        markets_by_match: dict[int, list[dict[str, Any]]] = {}
        if marketi_csv and os.path.exists(marketi_csv):
            marketi_df = pd.read_csv(marketi_csv)
            for _, mrow in marketi_df.iterrows():
                mid = int(mrow["match_id"])
                if mid not in markets_by_match:
                    markets_by_match[mid] = []
                markets_by_match[mid].append(
                    {
                        "trziste": str(mrow.get("trziste", "")),
                        "ishod": str(mrow.get("ishod", "")),
                        "kvota": float(mrow.get("kvota", 1.0)),
                        "redosled": int(mrow.get("redosled", 0)),
                    }
                )

        LEAGUE_GOALS = {
            "Argentina 1 - Klausura": 2.15,
            "Argentina 2": 1.95,
            "Argentina 4": 2.10,
            "Azijske igre": 2.80,
            "Bolivija Liga Kup": 3.10,
            "Brazil 1": 2.40,
            "Brazil 2": 2.05,
            "Bugarska 2": 2.45,
            "Danska 2": 2.95,
            "Dominikanska Republika 1": 2.65,
            "Ekvador 1": 2.60,
            "El Salvador 1 - Apertura": 2.50,
            "Engleska 7 - Central": 3.00,
            "Engleska M21": 3.65,
            "Engleska razvojna liga": 3.50,
            "Gruzija 1": 2.50,
            "Gvatemala 1 - Apertura": 2.35,
            "Honduras 1 - Apertura": 2.60,
            "Italija 3 A": 2.20,
            "Italija 3 B": 2.15,
            "Kolumbija 1 - Klausura": 2.25,
            "Kolumbija 2 - Klausura": 2.20,
        }

        rows = []
        for _, row in mecevi_df.iterrows():
            mid = int(row["match_id"])
            league = str(row.get("takmicenje", "Fudbal"))
            h_raw = str(row.get("domacin", ""))
            a_raw = str(row.get("gost", ""))
            h_odds = float(row.get("1", 2.0))
            x_odds = float(row.get("X", 3.2))
            a_odds = float(row.get("2", 3.5))

            # Expected goals estimation based on league prior and odds ratio
            tot_goals = LEAGUE_GOALS.get(league, 2.50)
            inv_h = 1.0 / max(h_odds, 1.01)
            inv_a = 1.0 / max(a_odds, 1.01)
            p_tot = inv_h + inv_a
            ratio_h = inv_h / p_tot if p_tot > 0 else 0.55

            # Incorporate home advantage (+0.25 goal baseline)
            h_xg = round(max(0.3, min(3.8, tot_goals * ratio_h * 1.12)), 2)
            a_xg = round(max(0.2, min(3.5, tot_goals * (1.0 - ratio_h) * 0.88)), 2)

            rows.append(
                {
                    "id": mid,
                    "date": f"{row.get('dan_label', '')} {row.get('vreme', '')}".strip(),
                    "league": league,
                    "home_team": normalize_name(h_raw),
                    "away_team": normalize_name(a_raw),
                    "home_team_raw": h_raw,
                    "away_team_raw": a_raw,
                    "home_odds": h_odds,
                    "draw_odds": x_odds,
                    "away_odds": a_odds,
                    "bookmaker": "Mozzart",
                    "home_xg": h_xg,
                    "away_xg": a_xg,
                    "is_live": False,
                    "current_score": {},
                    "elapsed_minutes": 0.0,
                    "markets": markets_by_match.get(mid, []),
                    "match_id": mid,
                    "favorit": row.get("favorit", ""),
                    "favorit_kvota": float(row.get("favorit_kvota", h_odds)),
                    "trziste_marza": float(row.get("trziste_marza", 0.07)),
                }
            )

        return pd.DataFrame(rows)
