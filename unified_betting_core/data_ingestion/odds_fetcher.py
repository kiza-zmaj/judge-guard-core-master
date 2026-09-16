"""
Odds Fetcher & Bookmaker Feed Ingestion.
Supports The-Odds-API, Pinnacle, and local upcoming fixtures fallback.
"""

import os
import logging
import requests
import datetime
import pandas as pd
from typing import List, Dict, Any, Optional
from unified_betting_core.config import ODDS_API_URL, ODDS_API_KEY, DATA_DIR

logger = logging.getLogger("SharpBet.OddsFetcher")

DEFAULT_TARGET_SPORTS = [
    "soccer_conmebol_copa_sudamericana",
    "soccer_mexico_ligamx",
    "soccer_england_efl_cup",
    "soccer_uefa_europa_league",
    "soccer_spain_la_liga",
    "soccer_epl"
]

class OddsFetcher:
    def __init__(self, data_dir: Optional[str] = None):
        self.data_dir = data_dir or str(DATA_DIR)
        self.api_key = os.getenv("ODDS_API_KEY", ODDS_API_KEY)

    def fetch_live_and_today_fixtures(self, sports: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Fetches real-time live in-play matches and today's upcoming fixtures across active competitions.
        Extracts live scores from /scores/ and sharp Pinnacle odds from /odds/.
        Zero mock, zero simulation.
        """
        target_sports = sports or DEFAULT_TARGET_SPORTS
        now = datetime.datetime.now(datetime.timezone.utc)
        fixtures: List[Dict[str, Any]] = []

        for s in target_sports:
            try:
                # 1. Fetch live scores endpoint
                scores_map = {}
                try:
                    scores_res = requests.get(
                        f"https://api.the-odds-api.com/v4/sports/{s}/scores/?daysFrom=1&apiKey={self.api_key}",
                        timeout=5
                    )
                    if scores_res.status_code == 200:
                        for item in scores_res.json():
                            scores_map[item.get("id")] = item
                except Exception as e:
                    logger.debug(f"Scores fetch error for {s}: {e}")

                # 2. Fetch live odds endpoint
                odds_res = requests.get(
                    f"https://api.the-odds-api.com/v4/sports/{s}/odds?regions=eu,us&markets=h2h&apiKey={self.api_key}",
                    timeout=5
                )
                if odds_res.status_code != 200:
                    continue

                events = odds_res.json()
                for ev in events:
                    ev_id = ev.get("id")
                    commence_str = ev.get("commence_time")
                    if not commence_str:
                        continue

                    commence = datetime.datetime.fromisoformat(commence_str.replace("Z", "+00:00"))
                    diff_hours = (commence - now).total_seconds() / 3600.0

                    # Filter: in-play matches (-3.5h <= diff <= 0) or matches today (0 < diff <= 24h)
                    if not (-3.5 <= diff_hours <= 24.0):
                        continue

                    score_info = scores_map.get(ev_id, {})
                    if score_info.get("completed", False):
                        continue

                    scores_list = score_info.get("scores")
                    current_score = {}
                    if scores_list:
                        for sc in scores_list:
                            current_score[sc["name"]] = int(sc["score"])

                    is_live = diff_hours <= 0.0
                    elapsed_minutes = max(0.0, -diff_hours * 60.0) if is_live else 0.0

                    bookmakers = ev.get("bookmakers", [])
                    if not bookmakers:
                        continue

                    # Sharp bookmaker selection hierarchy: Pinnacle -> Betfair -> Coolbet -> Unibet -> First
                    sharp_keys = ["pinnacle", "betfair_ex_eu", "coolbet", "unibet_eu", "unibet_se", "leovegas_se", "sport888"]
                    chosen_b = None
                    for k in sharp_keys:
                        for b in bookmakers:
                            if b.get("key") == k:
                                chosen_b = b
                                break
                        if chosen_b:
                            break
                    if not chosen_b:
                        chosen_b = bookmakers[0]

                    markets = chosen_b.get("markets", [])
                    if not markets:
                        continue

                    h2h = markets[0].get("outcomes", [])
                    home = ev.get("home_team")
                    away = ev.get("away_team")

                    h_odds = next((o["price"] for o in h2h if o["name"] == home), None)
                    a_odds = next((o["price"] for o in h2h if o["name"] == away), None)
                    d_odds = next((o["price"] for o in h2h if o["name"].lower() == "draw"), None)

                    if h_odds and a_odds and d_odds:
                        fixtures.append({
                            "id": ev_id,
                            "sport": s,
                            "league": ev.get("sport_title", s.replace("soccer_", "").upper()),
                            "date": commence_str,
                            "home_team": home,
                            "away_team": away,
                            "is_live": is_live,
                            "current_score": current_score,
                            "elapsed_minutes": elapsed_minutes,
                            "bookmaker": chosen_b.get("title", "Market Average"),
                            "home_odds": float(h_odds),
                            "draw_odds": float(d_odds),
                            "away_odds": float(a_odds)
                        })

            except Exception as e:
                logger.warning(f"Error fetching live fixtures for {s}: {e}")

        logger.info(f"Retrieved {len(fixtures)} live/today matches from The-Odds-API.")
        return fixtures

    def fetch_upcoming_fixtures(self) -> List[Dict[str, Any]]:
        """
        Fetches upcoming matches with 1X2 market odds.
        Attempts live multi-competition retrieval first; falls back to EPL or local CSV.
        """
        live_matches = self.fetch_live_and_today_fixtures()
        if live_matches:
            return live_matches

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
                "is_live": False,
                "current_score": {},
                "elapsed_minutes": 0.0,
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
        for r in records:
            r["is_live"] = False
            r["current_score"] = {}
            r["elapsed_minutes"] = 0.0
        logger.info(f"Loaded {len(records)} fixtures from local storage ({path}).")
        return records

