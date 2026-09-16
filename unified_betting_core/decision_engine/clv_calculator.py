"""
Closing Line Value (CLV) Calculator & Market Efficiency Benchmark for SharpBet Core.
Compares recommended/placed odds against real market closing odds and zero-vig closing odds.
Beating the closing line (CLV > 0) is the definitive statistical proof of positive expectancy.
NO SIMULATION OR GUESSED CLOSING ODDS ALLOWED IN REAL EVALUATION.
"""

import math
from enum import Enum
from typing import Any

import numpy as np


class CLVState(Enum):
    SETTLED = "SETTLED"  # Real closing line observed and verified
    PENDING_CLOSE = (
        "PENDING_CLOSE"  # Fixture has not closed; closing odds not yet available
    )
    MISSING_DATA = "MISSING_DATA"  # Closing line data could not be obtained from source


class CLVCalculator:
    """
    Calculates and aggregates Closing Line Value (CLV).

    Formulas:
    1. Raw CLV: (Placed_Odds / Closing_Odds) - 1.0
    2. Fair CLV (Zero-Vig): (Placed_Odds / Fair_Closing_Odds) - 1.0
       where Fair_Closing_Odds = 1.0 / P_closing_devig
    """

    @staticmethod
    def calculate_clv(
        placed_odds: float,
        closing_odds: float | None = None,
        closing_fair_odds: float | None = None,
    ) -> dict[str, Any]:
        """
        Calculates CLV metrics for a single wager.
        If closing odds are not available (e.g. upcoming fixture), marks state as PENDING_CLOSE.
        """
        if placed_odds <= 1.0:
            return {
                "state": CLVState.MISSING_DATA.value,
                "raw_clv": None,
                "raw_clv_pct": None,
                "fair_clv": None,
                "fair_clv_pct": None,
                "beat_closing": False,
                "note": "Invalid placed odds",
            }

        if closing_odds is None or closing_odds <= 1.01:
            return {
                "state": CLVState.PENDING_CLOSE.value,
                "placed_odds": round(placed_odds, 3),
                "closing_odds": None,
                "closing_fair_odds": None,
                "raw_clv": None,
                "raw_clv_pct": None,
                "fair_clv": None,
                "fair_clv_pct": None,
                "beat_closing": False,
                "note": "Closing odds pending kickoff",
            }

        # Raw CLV vs bookmaker closing line
        raw_clv = (placed_odds / closing_odds) - 1.0

        # Fair CLV vs zero-vig closing price
        if closing_fair_odds and closing_fair_odds > 1.0:
            fair_clv = (placed_odds / closing_fair_odds) - 1.0
        else:
            # Approximate fair closing odds by removing ~3.5% bookmaker overround
            approx_fair = closing_odds * 1.035
            fair_clv = (placed_odds / approx_fair) - 1.0

        return {
            "state": CLVState.SETTLED.value,
            "placed_odds": round(placed_odds, 3),
            "closing_odds": round(closing_odds, 3),
            "closing_fair_odds": round(
                closing_fair_odds if closing_fair_odds else (closing_odds * 1.035), 3
            ),
            "raw_clv": round(raw_clv, 4),
            "raw_clv_pct": round(raw_clv * 100, 2),
            "fair_clv": round(fair_clv, 4),
            "fair_clv_pct": round(fair_clv * 100, 2),
            "beat_closing": raw_clv > 0.0,
            "note": "Verified against real closing line",
        }

    @staticmethod
    def evaluate_portfolio_clv(bets: list[dict[str, Any]]) -> dict[str, Any]:
        """
        Aggregates CLV performance across a portfolio of placed bets with real closing prices.
        Computes mean, median, beat-closing rate, sample size, and 95% confidence interval.
        """
        if not bets:
            return {
                "total_bets": 0,
                "settled_closing_bets": 0,
                "pending_closing_bets": 0,
                "avg_raw_clv_pct": 0.0,
                "median_raw_clv_pct": 0.0,
                "avg_fair_clv_pct": 0.0,
                "beat_closing_rate_pct": 0.0,
                "clv_std_error_pct": 0.0,
                "ci_95_lower_pct": 0.0,
                "ci_95_upper_pct": 0.0,
                "expected_roi_from_clv_pct": 0.0,
                "has_demonstrated_clv_edge": False,
            }

        raw_clvs = []
        fair_clvs = []
        beat_count = 0
        pending_count = 0

        for bet in bets:
            placed = bet.get("odds", bet.get("placed_odds", 0.0))
            closing = bet.get("closing_odds", None)
            closing_fair = bet.get("closing_fair_odds", None)

            if closing is None or float(closing) <= 1.01:
                pending_count += 1
                continue

            metrics = CLVCalculator.calculate_clv(placed, float(closing), closing_fair)
            if metrics["state"] == CLVState.SETTLED.value:
                raw_clvs.append(metrics["raw_clv"])
                fair_clvs.append(metrics["fair_clv"])
                if metrics["beat_closing"]:
                    beat_count += 1

        n_settled = len(raw_clvs)
        if n_settled == 0:
            return {
                "total_bets": len(bets),
                "settled_closing_bets": 0,
                "pending_closing_bets": pending_count,
                "avg_raw_clv_pct": 0.0,
                "median_raw_clv_pct": 0.0,
                "avg_fair_clv_pct": 0.0,
                "beat_closing_rate_pct": 0.0,
                "clv_std_error_pct": 0.0,
                "ci_95_lower_pct": 0.0,
                "ci_95_upper_pct": 0.0,
                "expected_roi_from_clv_pct": 0.0,
                "has_demonstrated_clv_edge": False,
            }

        raw_np = np.array(raw_clvs)
        fair_np = np.array(fair_clvs)

        avg_raw = float(np.mean(raw_np))
        median_raw = float(np.median(raw_np))
        avg_fair = float(np.mean(fair_np))
        beat_rate = (beat_count / n_settled) * 100.0

        # Standard error and 95% CI
        std_err = (
            float(np.std(raw_np, ddof=1) / math.sqrt(n_settled))
            if n_settled > 1
            else 0.0
        )
        ci_lower = avg_raw - (1.96 * std_err)
        ci_upper = avg_raw + (1.96 * std_err)

        # Has edge only if sample is meaningful (>=50) and mean CLV is positive
        has_clv_edge = (n_settled >= 50) and (avg_raw > 0.0)

        return {
            "total_bets": len(bets),
            "settled_closing_bets": n_settled,
            "pending_closing_bets": pending_count,
            "avg_raw_clv_pct": round(avg_raw * 100, 2),
            "median_raw_clv_pct": round(median_raw * 100, 2),
            "avg_fair_clv_pct": round(avg_fair * 100, 2),
            "beat_closing_rate_pct": round(beat_rate, 2),
            "clv_std_error_pct": round(std_err * 100, 3),
            "ci_95_lower_pct": round(ci_lower * 100, 2),
            "ci_95_upper_pct": round(ci_upper * 100, 2),
            "expected_roi_from_clv_pct": round(avg_fair * 100, 2),
            "has_demonstrated_clv_edge": has_clv_edge,
        }
