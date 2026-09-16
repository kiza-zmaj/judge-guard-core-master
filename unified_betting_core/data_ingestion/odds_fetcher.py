"""
Odds Fetcher & Live Multi-System Feed Ingestion.
Integrates ESPN Global Live Scoreboard & Market Feeds and The-Odds-API.
Strict Zero-Mock / Zero-Synthetic Policy Enforced.
"""

import os
import logging
import requests
import datetime
import pandas as pd
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor
from unified_betting_core.config import ODDS_API_KEY, DATA_DIR

logger = logging.getLogger("SharpBet.OddsFetcher")

ESPN_SOCCER_LEAGUES = {
    "mex.1": "Liga MX",
    "uefa.europa": "UEFA Europa League",
    "uefa.champions": "UEFA Champions League",
    "uefa.europa.conf": "UEFA Conference League",
    "eng.1": "Premier League",
    "eng.2": "Championship",
    "esp.1": "La Liga",
    "esp.2": "Segunda División",
    "ger.1": "Bundesliga",
    "ger.2": "2. Bundesliga",
    "ita.1": "Serie A",
    "ita.2": "Serie B",
    "fra.1": "Ligue 1",
    "fra.2": "Ligue 2",
    "ned.1": "Eredivisie",
    "por.1": "Primeira Liga",
    "tur.1": "Süper Lig",
    "sau.1": "Saudi Pro League",
    "arg.1": "Argentine Primera División",
    "bra.1": "Campeonato Brasileiro Série A",
    "col.1": "Categoría Primera A",
    "conmebol.sudamericana": "Copa Sudamericana",
    "conmebol.libertadores": "Copa Libertadores",
    "usa.1": "MLS",
    "aus.1": "A-League Men",
    "jpn.1": "J1 League"
}

def american_to_decimal(am: Any) -> Optional[float]:
    """Converts American moneyline string/int (e.g. +360, -175) to European decimal odds."""
    if not am:
        return None
    try:
        val = float(str(am).replace("+", ""))
        if val > 0:
            return round(1.0 + (val / 100.0), 2)
        elif val < 0:
            return round(1.0 + (100.0 / abs(val)), 2)
    except Exception:
        return None
    return None

class OddsFetcher:
    def __init__(self, data_dir: Optional[str] = None):
        self.data_dir = data_dir or str(DATA_DIR)
        self.the_odds_api_key = os.getenv("ODDS_API_KEY", ODDS_API_KEY)

    def fetch_espn_live_fixtures(self) -> List[Dict[str, Any]]:
        """
        Fetches live in-play and scheduled matches from ESPN Official Scoreboard API.
        Extracts live clock, current scores, match period, and DraftKings/Consensus odds.
        Zero mock, zero simulation.
        """
        def _fetch_league(league_code: str, league_name: str) -> List[Dict[str, Any]]:
            url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{league_code}/scoreboard"
            try:
                res = requests.get(url, timeout=5)
                if not res.ok:
                    return []
                events = res.json().get("events", [])
                league_fixtures = []

                for ev in events:
                    ev_id = ev.get("id")
                    date_str = ev.get("date")
                    status_obj = ev.get("status", {})
                    state = status_obj.get("type", {}).get("state")
                    clock_str = status_obj.get("displayClock", "0").replace("'", "").replace("+", "")
                    try:
                        elapsed_min = float(clock_str.split("+")[0]) if clock_str else 0.0
                    except Exception:
                        elapsed_min = 0.0

                    # Only process in-play ("in") or upcoming today ("pre")
                    if state not in ["in", "pre"]:
                        continue

                    comp = ev.get("competitions", [{}])[0]
                    home = next((c["team"]["displayName"] for c in comp.get("competitors", []) if c.get("homeAway") == "home"), None)
                    away = next((c["team"]["displayName"] for c in comp.get("competitors", []) if c.get("homeAway") == "away"), None)
                    if not home or not away:
                        continue

                    h_sc = int(next((c.get("score") for c in comp.get("competitors", []) if c.get("homeAway") == "home"), 0) or 0)
                    a_sc = int(next((c.get("score") for c in comp.get("competitors", []) if c.get("homeAway") == "away"), 0) or 0)

                    odds_list = comp.get("odds", [])
                    h_odds, d_odds, a_odds = None, None, None
                    bookmaker_name = "DraftKings / ESPN Consensus"

                    if odds_list:
                        o0 = odds_list[0]
                        bookmaker_name = o0.get("provider", {}).get("name", bookmaker_name)
                        ml = o0.get("moneyline", {})
                        h_am = ml.get("home", {}).get("current", {}).get("odds") or ml.get("home", {}).get("close", {}).get("odds")
                        d_am = ml.get("draw", {}).get("current", {}).get("odds") or ml.get("draw", {}).get("close", {}).get("odds")
                        a_am = ml.get("away", {}).get("current", {}).get("odds") or ml.get("away", {}).get("close", {}).get("odds")

                        if not d_am and "drawOdds" in o0:
                            d_am = o0["drawOdds"].get("moneyLine")

                        h_odds = american_to_decimal(h_am)
                        d_odds = american_to_decimal(d_am)
                        a_odds = american_to_decimal(a_am)

                    if not (h_odds and d_odds and a_odds):
                        continue

                    is_live = (state == "in")
                    league_fixtures.append({
                        "id": f"espn_{ev_id}",
                        "league": league_name,
                        "date": date_str,
                        "home_team": home,
                        "away_team": away,
                        "is_live": is_live,
                        "current_score": {home: h_sc, away: a_sc, "home": h_sc, "away": a_sc} if is_live else {},
                        "elapsed_minutes": elapsed_min if is_live else 0.0,
                        "bookmaker": bookmaker_name,
                        "home_odds": float(h_odds),
                        "draw_odds": float(d_odds),
                        "away_odds": float(a_odds)
                    })
                return league_fixtures
            except Exception as e:
                logger.debug(f"ESPN fetch error for {league_code}: {e}")
                return []

        leagues_to_fetch = dict(ESPN_SOCCER_LEAGUES)
        try:
            h_url = "https://site.web.api.espn.com/apis/v2/scoreboard/header?sport=soccer"
            h_res = requests.get(h_url, timeout=4)
            if h_res.ok:
                for lg in h_res.json().get("sports", [{}])[0].get("leagues", []):
                    slug = lg.get("slug")
                    name = lg.get("name")
                    if slug and name and slug not in leagues_to_fetch:
                        leagues_to_fetch[slug] = name
        except Exception as e:
            logger.debug(f"Dynamic league discovery note: {e}")

        all_fixtures: List[Dict[str, Any]] = []
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(_fetch_league, code, name) for code, name in leagues_to_fetch.items()]
            for f in futures:
                try:
                    res = f.result()
                    all_fixtures.extend(res)
                except Exception as e:
                    logger.debug(f"League future exception: {e}")

        logger.info(f"Retrieved {len(all_fixtures)} live/today fixtures across {len(leagues_to_fetch)} leagues from ESPN Scoreboard Feed.")
        return all_fixtures

    def fetch_the_odds_api_fixtures(self) -> List[Dict[str, Any]]:
        """
        Attempts to fetch live odds from The-Odds-API if credits are available.
        Skips gracefully if credits are exhausted (HTTP 401/429).
        """
        if not self.the_odds_api_key:
            return []

        url = f"https://api.the-odds-api.com/v4/sports/soccer_epl/odds?regions=eu&markets=h2h&apiKey={self.the_odds_api_key}"
        try:
            res = requests.get(url, timeout=4)
            if res.status_code == 401 or res.status_code == 429:
                logger.warning("The-Odds-API credit quota reached. Proceeding with ESPN live feeds.")
                return []
            if res.ok:
                events = res.json()
                parsed = []
                for ev in events:
                    home = ev.get("home_team")
                    away = ev.get("away_team")
                    bookmakers = ev.get("bookmakers", [])
                    if not bookmakers:
                        continue
                    b = next((x for x in bookmakers if x.get("key") == "pinnacle"), bookmakers[0])
                    markets = b.get("markets", [])
                    if not markets:
                        continue
                    h2h = markets[0].get("outcomes", [])
                    h_odds = next((o["price"] for o in h2h if o["name"] == home), None)
                    a_odds = next((o["price"] for o in h2h if o["name"] == away), None)
                    d_odds = next((o["price"] for o in h2h if o["name"].lower() == "draw"), None)
                    if h_odds and d_odds and a_odds:
                        parsed.append({
                            "id": f"toa_{ev.get('id')}",
                            "league": "Premier League",
                            "date": ev.get("commence_time"),
                            "home_team": home,
                            "away_team": away,
                            "is_live": False,
                            "current_score": {},
                            "elapsed_minutes": 0.0,
                            "bookmaker": b.get("title", "Pinnacle"),
                            "home_odds": float(h_odds),
                            "draw_odds": float(d_odds),
                            "away_odds": float(a_odds)
                        })
                return parsed
        except Exception as e:
            logger.debug(f"The-Odds-API attempt failed: {e}")
            return []
        return []

    def fetch_live_and_today_fixtures(self, sports: Optional[Any] = None) -> List[Dict[str, Any]]:
        """
        Master method: Fetches real-time in-play and today's matches from active live systems.
        Prioritizes ESPN's high-frequency live scoreboard, complemented by bookmaker lines.
        Enforces strict ZERO-MOCK policy: never falls back to static placeholder CSVs.
        """
        fixtures = self.fetch_espn_live_fixtures()
        
        # Merge any complementary feeds if available
        toa_fixtures = self.fetch_the_odds_api_fixtures()
        seen_pairs = {(f["home_team"], f["away_team"]) for f in fixtures}
        for tf in toa_fixtures:
            pair = (tf["home_team"], tf["away_team"])
            if pair not in seen_pairs:
                fixtures.append(tf)
                seen_pairs.add(pair)

        if not fixtures:
            logger.warning("No live or upcoming fixtures available from real endpoints. Zero-mock enforced.")
        return fixtures

    def fetch_upcoming_fixtures(self) -> List[Dict[str, Any]]:
        """Backwards-compatible wrapper. Calls live and today fixtures with zero mock."""
        return self.fetch_live_and_today_fixtures()
