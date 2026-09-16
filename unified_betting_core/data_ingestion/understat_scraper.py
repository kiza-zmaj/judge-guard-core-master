"""
Understat xG Scraper & Historical Fallback Loader.
Extracts expected goals (xG) and expected goals against (xGA) per team.
"""

import logging
import os

import pandas as pd

from unified_betting_core.config import DATA_DIR, DEFAULT_LEAGUE, DEFAULT_SEASON

logger = logging.getLogger("SharpBet.Understat")


class UnderstatScraper:
    def __init__(self, data_dir: str | None = None):
        self.data_dir = data_dir or str(DATA_DIR)
        self.team_stats: dict[str, dict[str, float]] = {}

    def get_team_stats(self) -> dict[str, dict[str, float]]:
        """Returns the dictionary of loaded or scraped team xG stats."""
        if not self.team_stats:
            self.load_or_scrape()
        return self.team_stats

    def load_or_scrape(self) -> dict[str, dict[str, float]]:
        """
        Attempts to scrape live stats from Understat.
        Falls back seamlessly to local historical dataset if network is unavailable.
        """
        try:
            return self._scrape_live()
        except Exception as e:
            logger.warning(
                f"Live Understat scraping unavailable ({e}). Falling back to local historical data."
            )
            return self._load_from_local()

    def _scrape_live(self) -> dict[str, dict[str, float]]:
        import asyncio

        import aiohttp
        from understat import Understat

        async def _fetch():
            async with aiohttp.ClientSession() as session:
                understat = Understat(session)
                teams = await understat.get_teams(DEFAULT_LEAGUE, DEFAULT_SEASON)
                stats = {}
                for team in teams:
                    name = team.get("title")
                    history = team.get("history", [])
                    if history:
                        total_xg = sum(float(m.get("xG", 0)) for m in history)
                        total_xga = sum(float(m.get("xGA", 0)) for m in history)
                        matches_count = max(len(history), 1)
                        stats[name] = {
                            "xG": round(total_xg / matches_count, 3),
                            "xGA": round(total_xga / matches_count, 3),
                            "total_xG": round(total_xg, 2),
                            "total_xGA": round(total_xga, 2),
                            "matches": matches_count,
                        }
                return stats

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        stats = loop.run_until_complete(_fetch())
        self.team_stats = stats
        logger.info(f"Scraped live Understat data for {len(stats)} teams.")
        return stats

    def _load_from_local(self) -> dict[str, dict[str, float]]:
        """Computes aggregate xG & xGA per match from historical_matches.csv."""
        hist_path = os.path.join(self.data_dir, "historical_matches.csv")
        if not os.path.exists(hist_path):
            logger.error(f"Historical dataset not found at {hist_path}")
            return {}

        df = pd.read_csv(hist_path)
        stats: dict[str, dict[str, float]] = {}

        for _, row in df.iterrows():
            home = str(row.get("home_team", "")).strip()
            away = str(row.get("away_team", "")).strip()
            h_xg = float(row.get("home_xg", 1.3))
            a_xg = float(row.get("away_xg", 1.1))

            if home not in stats:
                stats[home] = {"xG_sum": 0.0, "xGA_sum": 0.0, "count": 0}
            stats[home]["xG_sum"] += h_xg
            stats[home]["xGA_sum"] += a_xg
            stats[home]["count"] += 1

            if away not in stats:
                stats[away] = {"xG_sum": 0.0, "xGA_sum": 0.0, "count": 0}
            stats[away]["xG_sum"] += a_xg
            stats[away]["xGA_sum"] += h_xg
            stats[away]["count"] += 1

        res = {}
        for team, data in stats.items():
            cnt = max(data["count"], 1)
            res[team] = {
                "xG": round(data["xG_sum"] / cnt, 3),
                "xGA": round(data["xGA_sum"] / cnt, 3),
                "total_xG": round(data["xG_sum"], 2),
                "total_xGA": round(data["xGA_sum"], 2),
                "matches": cnt,
            }

        self.team_stats = res
        logger.info(f"Loaded aggregate stats from local cache for {len(res)} teams.")
        return res
