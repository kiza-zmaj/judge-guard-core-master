"""
Feature Engineering for SharpBet v11.
Based on SharpBet Core v5 architecture (NotebookLM verified):
- Dixon-Coles rho correction (rho=-0.11) for low-score joint distribution
- Dynamic Elo: HFA=+65, K=24, goal-margin multiplier G
- Time-causal rolling stats (5 & 10 match windows, strict shift(1))
- Prior utility injection for base_margin = logit(p_prior)
"""
import logging
import math
from typing import Any
import numpy as np
import pandas as pd

logger = logging.getLogger("SharpBet.FeatureBuilder")

DEFAULT_ELO = 1500.0
ELO_K = 24.0        # From SharpBet v5 spec
ELO_HFA = 65.0      # Home Field Advantage in Elo points
RHO = -0.11         # Dixon-Coles low-score correction


def _elo_expected(r_home: float, r_away: float) -> float:
    """Expected score for home vs away (with HFA applied)."""
    return 1.0 / (1.0 + 10.0 ** ((r_away - (r_home + ELO_HFA)) / 400.0))


def _goal_margin_multiplier(hg: int, ag: int) -> float:
    """G multiplier per SharpBet v5 spec."""
    delta = abs(hg - ag)
    if delta <= 1:
        return 1.0
    elif delta == 2:
        return 1.5
    else:
        return (1.75 + delta) / 3.0


def _update_elo(r_home: float, r_away: float, hg: int, ag: int):
    if hg > ag:
        s_h, s_a = 1.0, 0.0
    elif hg < ag:
        s_h, s_a = 0.0, 1.0
    else:
        s_h, s_a = 0.5, 0.5
    G = _goal_margin_multiplier(hg, ag)
    e_h = _elo_expected(r_home, r_away)
    e_a = 1.0 - e_h
    new_h = r_home + ELO_K * G * (s_h - e_h)
    new_a = r_away + ELO_K * G * (s_a - e_a)
    return round(new_h, 2), round(new_a, 2)


def _dixon_coles_home_draw_away(lam_h: float, lam_a: float) -> tuple:
    """
    Compute P(Home), P(Draw), P(Away) via Dixon-Coles bivariate correction.
    rho = -0.11 (negative covariance for low-score events).
    """
    max_goals = 8
    p_home = p_draw = p_away = 0.0
    for x in range(max_goals + 1):
        for y in range(max_goals + 1):
            # Dixon-Coles tau correction
            if x == 0 and y == 0:
                tau = 1.0 - lam_h * lam_a * RHO
            elif x == 0 and y == 1:
                tau = 1.0 + lam_h * RHO
            elif x == 1 and y == 0:
                tau = 1.0 + lam_a * RHO
            elif x == 1 and y == 1:
                tau = 1.0 - RHO
            else:
                tau = 1.0
            p_xy = (tau
                    * (lam_h ** x * math.exp(-lam_h) / math.factorial(x))
                    * (lam_a ** y * math.exp(-lam_a) / math.factorial(y)))
            if x > y:
                p_home += p_xy
            elif x == y:
                p_draw += p_xy
            else:
                p_away += p_xy
    total = p_home + p_draw + p_away
    if total < 1e-9:
        return 0.45, 0.27, 0.28
    return round(p_home / total, 5), round(p_draw / total, 5), round(p_away / total, 5)


DERBY_PAIRS = set([
    frozenset(["manchester utd", "manchester city"]),
    frozenset(["arsenal", "tottenham"]),
    frozenset(["liverpool", "everton"]),
    frozenset(["chelsea", "tottenham"]),
    frozenset(["chelsea", "arsenal"]),
    frozenset(["newcastle", "sunderland"]),
    frozenset(["west ham", "millwall"]),
])


class FeatureBuilder:
    """
    Builds 13 strictly pre-match features for SharpBet v11.
    Zero lookahead: all features computed from past matches only.
    """
    def __init__(self, form_window: int = 5, long_window: int = 10):
        self.form_window = form_window
        self.long_window = long_window

    def build(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return df
        df = df.copy()
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").reset_index(drop=True)

        elo: dict[str, float] = {}
        last_date: dict[str, Any] = {}
        history: dict[str, list] = {}

        rows_out = []
        for idx, row in df.iterrows():
            h = str(row["home_team"]).lower().strip()
            a = str(row["away_team"]).lower().strip()
            dt = row["date"]

            # Elo (pre-match, includes HFA)
            elo_h = elo.get(h, DEFAULT_ELO)
            elo_a = elo.get(a, DEFAULT_ELO)
            elo_diff = elo_h - elo_a  # positive = home stronger (excl HFA)

            def _rolling(team, key, window):
                vals = history.get(f"{team}__{key}", [])
                return float(np.mean(vals[-window:])) if vals else None

            # Form: points per game (5 and 10)
            h5 = _rolling(h, "pts", self.form_window) or 1.0
            a5 = _rolling(a, "pts", self.form_window) or 1.0
            h10 = _rolling(h, "pts", self.long_window) or 1.0
            a10 = _rolling(a, "pts", self.long_window) or 1.0

            # Goals
            h_scored_5 = _rolling(h, "scored", self.form_window) or 1.45
            h_conc_5 = _rolling(h, "conceded", self.form_window) or 1.35
            a_scored_5 = _rolling(a, "scored", self.form_window) or 1.20
            a_conc_5 = _rolling(a, "conceded", self.form_window) or 1.45

            # Poisson lambda (attack * opponent_defense / league_avg)
            lam_h = max((h_scored_5 + a_conc_5) / 2.0, 0.3)
            lam_a = max((a_scored_5 + h_conc_5) / 2.0, 0.2)

            # Dixon-Coles probabilities
            dc_home, dc_draw, dc_away = _dixon_coles_home_draw_away(lam_h, lam_a)

            # H2H
            h2h_key = f"h2h__{min(h,a)}__{max(h,a)}"
            h2h_list = history.get(h2h_key, [])
            h2h_home_rate = float(np.mean(h2h_list[-5:])) if h2h_list else 0.45

            # Rest days
            days_h = int((dt - last_date[h]).days) if h in last_date else 14
            days_a = int((dt - last_date[a]).days) if a in last_date else 14

            # Prior utility (SharpBet v5 formula)
            # utility = a1*(lam_h - lam_a) + a2*(elo_diff/400) + a3*delta_rest
            utility = (
                0.6 * (lam_h - lam_a)
                + 0.4 * (elo_diff / 400.0)
                + 0.1 * ((min(days_h, 30) - min(days_a, 30)) / 30.0)
            )
            p_prior_home = 1.0 / (1.0 + math.exp(-utility))

            # Derby
            derby = 1 if frozenset([h, a]) in DERBY_PAIRS else 0

            # Season week
            season_val = str(row.get("season", "2324"))
            try:
                s_year = int("20" + season_val[:2])
            except:
                s_year = 2023
            s_start = pd.Timestamp(f"{s_year}-08-01")
            s_week = max(1, int((dt - s_start).days // 7))

            feat = {
                "elo_home": elo_h,
                "elo_away": elo_a,
                "elo_diff": round(elo_diff, 2),
                "form_home_5": round(h5, 4),
                "form_away_5": round(a5, 4),
                "form_diff_5": round(h5 - a5, 4),
                "pts_diff_last10": round(h10 - a10, 4),
                "lam_home": round(lam_h, 4),
                "lam_away": round(lam_a, 4),
                "dc_prob_home": dc_home,
                "dc_prob_draw": dc_draw,
                "dc_prob_away": dc_away,
                "h2h_home_rate": round(h2h_home_rate, 4),
                "goals_scored_avg_5": round(h_scored_5, 4),
                "goals_conceded_avg_5": round(h_conc_5, 4),
                "days_since_last_home": min(days_h, 90),
                "days_since_last_away": min(days_a, 90),
                "rest_diff": min(days_h, 30) - min(days_a, 30),
                "is_derby": derby,
                "season_week": s_week,
                "utility_prior": round(utility, 5),
                "p_prior_home": round(p_prior_home, 5),
            }
            rows_out.append({**dict(row), **feat})

            # --- UPDATE STATE AFTER recording (zero lookahead) ---
            hg = int(row.get("home_goals", 0))
            ag = int(row.get("away_goals", 0))
            new_elo_h, new_elo_a = _update_elo(elo_h, elo_a, hg, ag)
            elo[h] = new_elo_h
            elo[a] = new_elo_a
            h_pts = 3 if hg > ag else (1 if hg == ag else 0)
            a_pts = 3 if ag > hg else (1 if hg == ag else 0)
            for team, pts, scored, conceded in [
                (h, h_pts, hg, ag), (a, a_pts, ag, hg)
            ]:
                history.setdefault(f"{team}__pts", []).append(pts)
                history.setdefault(f"{team}__scored", []).append(scored)
                history.setdefault(f"{team}__conceded", []).append(conceded)
            # H2H: 1=home win, 0=draw, -1=away win
            h2h_val = 1 if hg > ag else (0 if hg == ag else -1)
            history.setdefault(h2h_key, []).append(h2h_val)
            last_date[h] = dt
            last_date[a] = dt

        return pd.DataFrame(rows_out)

    def get_feature_names(self) -> list:
        return [
            "elo_home", "elo_away", "elo_diff",
            "form_home_5", "form_away_5", "form_diff_5", "pts_diff_last10",
            "lam_home", "lam_away",
            "dc_prob_home", "dc_prob_draw", "dc_prob_away",
            "h2h_home_rate",
            "goals_scored_avg_5", "goals_conceded_avg_5",
            "days_since_last_home", "days_since_last_away", "rest_diff",
            "is_derby", "season_week",
            "utility_prior", "p_prior_home",
        ]
