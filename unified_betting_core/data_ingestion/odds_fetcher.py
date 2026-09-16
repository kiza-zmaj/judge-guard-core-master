"""
Odds Fetcher & Bookmaker Feed Ingestion.
Supports The-Odds-API, Pinnacle, and local upcoming fixtures fallback.
"""

import os
import logging
import requests
import pandas as pd
from typing import List, Dict, Any, Optional
from unified_betting_core.config import ODDS_API_URL, DATA_DIR

logger = logging.getLogger("SharpBet.OddsFetcher")

class OddsFetcher:
    def __init__(self, data_dir: Optional[str] = None):
        self.data_dir = data_dir or str(DATA_DIR)

    def fetch_upcoming_fixtures(self) -> List[Dict[str, Any]]:
        """
        Fetches upcoming matches with 1X2 market odds.
        Tries remote The-Odds-API first; on failure, loads local upcoming_fixtures.csv.
        """
        try:
            res = requests.get(ODDS_API_URL, timeout=5)
            if res.status_code == 200:
                data = res.json()
                parsed = self._parse_odds_api_response(data)
                if parsed:
                    logger.info(f"Retrieved {len(parsed)} live fixtures from The-Odds-API.")
                    return parsed
        except Exception as e:
            logger.warning(f"Live odds API request failed: {e}. Falling back to local upcoming fixtures.")

        return self._load_local_fixtures()

    def _parse_odds_api_response(self, raw_matches: list) -> List[Dict[str, Any]]:
        matches = []
        for item in raw_matches:
            home = item.get("home_team")
            away = item.get("away_team")
            commence = item.get("commence_time")

            bookmakers = item.get("bookmakers", [])
            if not bookmakers:
                continue

            # Prioritize sharp bookmaker Pinnacle if present
            bookie = next((b for b in bookmakers if b.get("key") == "pinnacle"), bookmakers[0])
            markets = bookie.get("markets", [])
            if not markets:
                continue

            h2h = markets[0].get("outcomes", [])
            home_odds = next((o["price"] for o in h2h if o["name"] == home), 2.0)
            away_odds = next((o["price"] for o in h2h if o["name"] == away), 3.0)
            draw_odds = next((o["price"] for o in h2h if o["name"].lower() == "draw"), 3.2)

            matches.append({
                "date": commence,
                "league": "EPL",
                "home_team": home,
                "away_team": away,
                "home_odds": float(home_odds),
                "draw_odds": float(draw_odds),
                "away_odds": float(away_odds),
                "bookmaker": bookie.get("title", "Market Average")
            })

        return matches

    def _load_local_fixtures(self) -> List[Dict[str, Any]]:
        """Loads upcoming fixtures and odds from local CSV."""
        path = os.path.join(self.data_dir, "upcoming_fixtures.csv")
        if not os.path.exists(path):
            logger.error(f"Local fixtures file not found at {path}")
            return []

        df = pd.read_csv(path)
        records = df.to_dict(orient="records")
        logger.info(f"Loaded {len(records)} fixtures from local storage ({path}).")
        return records
