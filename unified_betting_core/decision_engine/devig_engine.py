"""
De-vigging Engine & Fair Odds Calculator.
Strips bookmaker margin (vig / overround) to extract the market's true implied probability.
Supports Multiplicative and Power / Logarithmic de-vig methods.
"""

import math

from scipy.optimize import brentq


class DevigEngine:
    @staticmethod
    def calculate_overround(odds_dict: dict[str, float]) -> tuple[float, float]:
        """
        Calculates total implied probability (sum of inverses) and bookmaker overround / margin.
        Example: 1.95 / 1.95 -> sum = 1.0256 -> margin = 2.56%
        """
        valid_odds = [v for v in odds_dict.values() if v > 1.0]
        if not valid_odds:
            return 0.0, 0.0

        inv_sum = sum(1.0 / o for o in valid_odds)
        margin = inv_sum - 1.0
        return round(inv_sum, 5), round(margin, 5)

    @staticmethod
    def devig_multiplicative(odds_dict: dict[str, float]) -> dict[str, float]:
        """
        Basic proportional de-vig: P_i = (1 / O_i) / sum(1 / O_j).
        Fast, but assumes bookmaker spreads vig equally across all outcomes.
        """
        inv_sum, _ = DevigEngine.calculate_overround(odds_dict)
        if inv_sum <= 0:
            return {k: 0.0 for k in odds_dict}

        devigged = {}
        for outcome, odds in odds_dict.items():
            if odds > 1.0:
                p = (1.0 / odds) / inv_sum
                devigged[outcome] = round(p, 5)
            else:
                devigged[outcome] = 0.0
        return devigged

    @staticmethod
    def devig_power(odds_dict: dict[str, float]) -> dict[str, float]:
        """
        Power Method / Logarithmic De-vig (Standard in Sharp Sports Analytics).
        Solves for exponent k such that sum((1 / O_i)^k) = 1.0.
        Correctly accounts for the favorite-longshot bias (vig is concentrated on underdogs).
        """
        valid_items = [(k, v) for k, v in odds_dict.items() if v > 1.0]
        if not valid_items:
            return {k: 0.0 for k in odds_dict}

        inv_odds = [1.0 / o for _, o in valid_items]

        # Target function: f(k) = sum(inv_odds^k) - 1 = 0
        def f(k):
            return sum(math.pow(p, k) for p in inv_odds) - 1.0

        try:
            # k is typically between 1.0 and 4.0 for normal margins
            k_star = brentq(f, 0.5, 6.0)
        except (ValueError, RuntimeError):
            # Fallback to multiplicative if solver fails
            return DevigEngine.devig_multiplicative(odds_dict)

        devigged = {}
        total = 0.0
        for outcome, odds in valid_items:
            p = math.pow(1.0 / odds, k_star)
            devigged[outcome] = p
            total += p

        # Normalize to strictly 1.0
        return {k: round(v / total, 5) for k, v in devigged.items()}

    @staticmethod
    def fair_odds(devig_probs: dict[str, float]) -> dict[str, float]:
        """
        Converts true de-vigged probabilities into fair (zero-vig) decimal odds.
        Fair Odds = 1 / P_true
        """
        fair = {}
        for outcome, p in devig_probs.items():
            if p > 0.0001:
                fair[outcome] = round(1.0 / p, 3)
            else:
                fair[outcome] = 999.0
        return fair
