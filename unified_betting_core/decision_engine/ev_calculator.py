"""
Expected Value (+EV) Calculation & Value Bet Filtering.
Calculates edge over bookmaker odds.
"""

from typing import Dict, Any, List
from unified_betting_core.config import MIN_EDGE

class EVCalculator:
    def __init__(self, min_edge: float = MIN_EDGE):
        self.min_edge = min_edge

    def evaluate_outcomes(self, probs: Dict[str, float], odds: Dict[str, float]) -> List[Dict[str, Any]]:
        """
        Calculates EV for Home, Draw, Away outcomes.
        EV formula: (Model_Prob * Decimal_Odds) - 1
        Returns list of outcomes sorted by descending EV.
        """
        candidates = []
        outcomes = [
            ("home", probs.get("home", 0.0), odds.get("home_odds", 0.0)),
            ("draw", probs.get("draw", 0.0), odds.get("draw_odds", 0.0)),
            ("away", probs.get("away", 0.0), odds.get("away_odds", 0.0))
        ]

        for outcome, prob, decimal_odds in outcomes:
            if decimal_odds <= 1.0 or prob <= 0:
                continue

            implied_prob = 1.0 / decimal_odds
            edge = (prob * decimal_odds) - 1.0

            candidates.append({
                "outcome": outcome,
                "model_prob": round(prob, 4),
                "odds": round(decimal_odds, 2),
                "implied_prob": round(implied_prob, 4),
                "edge": round(edge, 4),
                "edge_pct": round(edge * 100, 2),
                "is_value_bet": edge >= self.min_edge
            })

        # Sort highest edge first
        candidates.sort(key=lambda x: x["edge"], reverse=True)
        return candidates

    def get_best_value_bet(self, probs: Dict[str, float], odds: Dict[str, float]) -> Dict[str, Any]:
        """Returns the single highest +EV bet if it exceeds min_edge, else None."""
        evals = self.evaluate_outcomes(probs, odds)
        if evals and evals[0]["is_value_bet"]:
            return evals[0]
        return {}
