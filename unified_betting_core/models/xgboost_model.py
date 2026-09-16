"""
Tabular Form & Time-Decay Weighting Model (XGBoost / Regression Ensembling).
Weighs recent match performance higher than older fixtures.
"""

import logging
import math

import pandas as pd

logger = logging.getLogger("SharpBet.XGBoostModel")


class TimeDecayModel:
    def __init__(self, decay_rate: float = 0.005):
        """
        decay_rate: Exponential decay lambda.
        Matches from 180 days ago have significantly less weight than matches from 14 days ago.
        """
        self.decay_rate = decay_rate

    def calculate_form_rating(
        self, team_name: str, historical_df: pd.DataFrame
    ) -> dict[str, float]:
        """
        Calculates rolling offensive and defensive ratings using exponential time-decay.
        """
        if historical_df.empty:
            return {"attack_rating": 1.0, "defense_rating": 1.0}

        team_matches = historical_df[
            (historical_df["home_team"] == team_name)
            | (historical_df["away_team"] == team_name)
        ].copy()

        if team_matches.empty:
            return {"attack_rating": 1.0, "defense_rating": 1.0}

        # Calculate time difference weights (assuming row order represents chronological order)
        n = len(team_matches)
        weights = [math.exp(-self.decay_rate * (n - 1 - i)) for i in range(n)]
        sum_weights = sum(weights) or 1.0

        weighted_xg_scored = 0.0
        weighted_xg_conceded = 0.0

        for idx, (_, row) in enumerate(team_matches.iterrows()):
            w = weights[idx]
            if row["home_team"] == team_name:
                weighted_xg_scored += float(row.get("home_xg", 1.2)) * w
                weighted_xg_conceded += float(row.get("away_xg", 1.1)) * w
            else:
                weighted_xg_scored += float(row.get("away_xg", 1.1)) * w
                weighted_xg_conceded += float(row.get("home_xg", 1.2)) * w

        avg_scored = weighted_xg_scored / sum_weights
        avg_conceded = weighted_xg_conceded / sum_weights

        return {
            "attack_rating": round(avg_scored, 3),
            "defense_rating": round(avg_conceded, 3),
        }

    def adjust_match_xg(
        self,
        home_team: str,
        away_team: str,
        raw_home_xg: float,
        raw_away_xg: float,
        hist_df: pd.DataFrame,
    ) -> dict[str, float]:
        """
        Combines baseline xG with time-decay form ratings.
        """
        home_form = self.calculate_form_rating(home_team, hist_df)
        away_form = self.calculate_form_rating(away_team, hist_df)

        # Blend base xG with team attack and opponent defense form
        adj_home_xg = (
            (raw_home_xg * 0.6)
            + (home_form["attack_rating"] * 0.2)
            + (away_form["defense_rating"] * 0.2)
        )
        adj_away_xg = (
            (raw_away_xg * 0.6)
            + (away_form["attack_rating"] * 0.2)
            + (home_form["defense_rating"] * 0.2)
        )

        return {
            "home_xg": round(max(adj_home_xg, 0.2), 2),
            "away_xg": round(max(adj_away_xg, 0.2), 2),
        }
