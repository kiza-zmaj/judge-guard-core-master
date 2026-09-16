"""
Poisson Distribution Probability Engine for Football Match Outcomes.
Simulates goal probabilities to derive 1X2, Over/Under, and BTTS probabilities.
"""

import os
import pickle
import logging
from scipy.stats import poisson
from typing import Dict, Any, Optional
from unified_betting_core.config import MODELS_STORE_DIR

logger = logging.getLogger("SharpBet.PoissonModel")

def dixon_coles_tau(x: int, y: int, h_xg: float, a_xg: float, rho: float = -0.11) -> float:
    """
    Dixon-Coles bivariate adjustment factor tau for low scores:
    Adjusts probability mass for (0,0), (1,0), (0,1), and (1,1) to correct for
    empirical low-score dependence and draw underestimation in independent Poisson models.
    """
    if x == 0 and y == 0:
        return max(1.0 - (h_xg * a_xg * rho), 0.0)
    elif x == 0 and y == 1:
        return max(1.0 + (h_xg * rho), 0.0)
    elif x == 1 and y == 0:
        return max(1.0 + (a_xg * rho), 0.0)
    elif x == 1 and y == 1:
        return max(1.0 - rho, 0.0)
    return 1.0


class SimplePoissonModel:
    """Trained weights container from historical matches."""
    pass

class _PoissonUnpickler(pickle.Unpickler):
    def find_class(self, module, name):
        if name == "SimplePoissonModel":
            return SimplePoissonModel
        return super().find_class(module, name)

class PoissonEngine:
    def __init__(self, model_path: Optional[str] = None):
        self.max_goals = 10
        self.model_path = model_path or os.path.join(str(MODELS_STORE_DIR), "poisson_model.pkl")
        self.external_model = None
        self._try_load_pickle()

    def _try_load_pickle(self):
        """Loads trained pickled model weights if present."""
        if os.path.exists(self.model_path):
            try:
                with open(self.model_path, "rb") as f:
                    self.external_model = _PoissonUnpickler(f).load()
                logger.info(f"Loaded trained Poisson model from {self.model_path}")
            except Exception as e:
                logger.warning(f"Could not unpickle {self.model_path}: {e}. Using direct Poisson PMF simulation.")

    def predict_match(self, home_team: str, away_team: str, home_xg: float, away_xg: float) -> Dict[str, float]:
        """
        Calculates probabilities for match outcomes given home and away expected goals.
        Includes Dixon-Coles low-score bivariate correlation correction.
        """
        # If external model implements predict_match, we can invoke it
        if self.external_model and hasattr(self.external_model, "predict_match"):
            try:
                return self.external_model.predict_match(home_team, away_team, home_xg, away_xg)
            except Exception:
                pass

        # Direct mathematical simulation using Poisson PMF with Dixon-Coles adjustment
        h_xg = float(home_xg)
        if h_xg > 8.0:
            h_xg = h_xg / 38.0 # Normalize season aggregate to single match
        a_xg = float(away_xg)
        if a_xg > 8.0:
            a_xg = a_xg / 38.0 # Normalize season aggregate to single match

        h_xg = max(round(h_xg, 2), 0.2)
        a_xg = max(round(a_xg, 2), 0.2)

        home_probs = [poisson.pmf(i, h_xg) for i in range(self.max_goals)]
        away_probs = [poisson.pmf(i, a_xg) for i in range(self.max_goals)]

        prob_home = 0.0
        prob_draw = 0.0
        prob_away = 0.0
        prob_over_2_5 = 0.0
        prob_btts = 0.0

        best_score_prob = -1.0
        best_score = "1-1"

        for h in range(self.max_goals):
            for a in range(self.max_goals):
                tau = dixon_coles_tau(h, a, h_xg, a_xg)
                p = home_probs[h] * away_probs[a] * tau

                if h > a:
                    prob_home += p
                elif h == a:
                    prob_draw += p
                else:
                    prob_away += p

                if (h + a) > 2.5:
                    prob_over_2_5 += p

                if h > 0 and a > 0:
                    prob_btts += p

                if p > best_score_prob:
                    best_score_prob = p
                    best_score = f"{h}-{a}"

        # Normalize 1X2 sum to strictly 1.0
        total_1x2 = prob_home + prob_draw + prob_away
        if total_1x2 > 0:
            prob_home /= total_1x2
            prob_draw /= total_1x2
            prob_away /= total_1x2

        return {
            "home": round(prob_home, 4),
            "draw": round(prob_draw, 4),
            "away": round(prob_away, 4),
            "over_2_5": round(prob_over_2_5, 4),
            "under_2_5": round(1.0 - prob_over_2_5, 4),
            "btts": round(prob_btts, 4),
            "predicted_score": best_score,
            "home_xg": h_xg,
            "away_xg": a_xg
        }

    def predict_in_play(
        self,
        home_team: str,
        away_team: str,
        current_home_score: int,
        current_away_score: int,
        elapsed_minutes: float,
        home_xg: float,
        away_xg: float
    ) -> Dict[str, Any]:
        """
        Calculates in-play probabilities for match outcomes conditioning on current score and elapsed time.
        Models remaining goals using Poisson with remaining expected goals adjusted for remaining time.
        """
        # Fraction of regular 90 minutes remaining
        remaining_ratio = max(0.05, min(1.0, (90.0 - float(elapsed_minutes)) / 90.0))

        h_xg = float(home_xg)
        if h_xg > 8.0:
            h_xg = h_xg / 38.0
        a_xg = float(away_xg)
        if a_xg > 8.0:
            a_xg = a_xg / 38.0

        h_xg = max(round(h_xg, 2), 0.2)
        a_xg = max(round(a_xg, 2), 0.2)

        # Remaining expected goals
        rem_home_xg = max(0.01, h_xg * remaining_ratio)
        rem_away_xg = max(0.01, a_xg * remaining_ratio)

        home_probs = [poisson.pmf(i, rem_home_xg) for i in range(self.max_goals)]
        away_probs = [poisson.pmf(i, rem_away_xg) for i in range(self.max_goals)]

        prob_home = 0.0
        prob_draw = 0.0
        prob_away = 0.0
        prob_over_2_5 = 0.0
        prob_btts = 0.0

        best_score_prob = -1.0
        best_score = f"{current_home_score}-{current_away_score}"

        for h in range(self.max_goals):
            for a in range(self.max_goals):
                p = home_probs[h] * away_probs[a]
                final_h = current_home_score + h
                final_a = current_away_score + a

                if final_h > final_a:
                    prob_home += p
                elif final_h == final_a:
                    prob_draw += p
                else:
                    prob_away += p

                if (final_h + final_a) > 2.5:
                    prob_over_2_5 += p

                if final_h > 0 and final_a > 0:
                    prob_btts += p

                if p > best_score_prob:
                    best_score_prob = p
                    best_score = f"{final_h}-{final_a}"

        total_1x2 = prob_home + prob_draw + prob_away
        if total_1x2 > 0:
            prob_home /= total_1x2
            prob_draw /= total_1x2
            prob_away /= total_1x2

        return {
            "home": round(prob_home, 4),
            "draw": round(prob_draw, 4),
            "away": round(prob_away, 4),
            "over_2_5": round(prob_over_2_5, 4),
            "under_2_5": round(1.0 - prob_over_2_5, 4),
            "btts": round(prob_btts, 4),
            "predicted_score": best_score,
            "home_xg": rem_home_xg,
            "away_xg": rem_away_xg,
            "in_play": True,
            "current_score": f"{current_home_score}-{current_away_score}",
            "elapsed_minutes": elapsed_minutes
        }

