"""
Kelly Criterion Money Management & Bankroll Allocation.
Enforces fractional Kelly betting (Half-Kelly) and maximum exposure caps.
"""

import logging
from typing import Any

from unified_betting_core.config import (
    DEFAULT_BANKROLL,
    KELLY_FRACTION,
    MAX_BANKROLL_PCT,
    MIN_EDGE,
)

logger = logging.getLogger("SharpBet.KellyCriterion")


class KellyCriterion:
    def __init__(
        self,
        fraction: float = KELLY_FRACTION,
        min_edge: float = MIN_EDGE,
        max_bankroll_pct: float = MAX_BANKROLL_PCT,
    ):
        self.fraction = fraction
        self.min_edge = min_edge
        self.max_bankroll_pct = max_bankroll_pct

    def calculate_stake(
        self, model_prob: float, market_odds: float, bankroll: float = DEFAULT_BANKROLL
    ) -> float:
        """
        Calculates optimal stake using Fractional Kelly Criterion.

        Formula:
            b = market_odds - 1 (net profit per unit)
            q = 1 - model_prob
            edge = (b * p) - q = (p * market_odds) - 1
            f* = edge / b
            stake = f* * fraction * bankroll
        """
        if market_odds <= 1.0 or model_prob <= 0.0 or bankroll <= 0.0:
            return 0.0

        b = market_odds - 1.0
        edge = (model_prob * market_odds) - 1.0

        if edge <= self.min_edge:
            return 0.0

        kelly_full = edge / b
        stake = kelly_full * self.fraction * bankroll

        # Safety cap: Never risk more than max_bankroll_pct on a single wager
        max_allowed_stake = bankroll * self.max_bankroll_pct
        final_stake = min(stake, max_allowed_stake)

        return round(max(final_stake, 0.0), 2)

    def allocate_portfolio(
        self, value_bets: list[dict[str, Any]], bankroll: float = DEFAULT_BANKROLL
    ) -> list[dict[str, Any]]:
        """
        Allocates stakes across multiple value bets simultaneously.
        Enforces total portfolio exposure cap (e.g., max 30% of bankroll across concurrent wagers).
        """
        allocated = []
        total_staked = 0.0
        portfolio_cap = bankroll * 0.35  # Max 35% total portfolio risk

        for bet in value_bets:
            prob = bet.get("model_prob", 0.0)
            odds = bet.get("odds", 0.0)

            stake = self.calculate_stake(prob, odds, bankroll)
            if stake > 0:
                if total_staked + stake > portfolio_cap:
                    # Scaled down to fit within remaining portfolio limit
                    remaining = max(portfolio_cap - total_staked, 0.0)
                    stake = round(remaining, 2)

                if stake > 0:
                    total_staked += stake
                    bet_copy = dict(bet)
                    bet_copy["stake"] = stake
                    bet_copy["bankroll_pct"] = round((stake / bankroll) * 100, 2)
                    allocated.append(bet_copy)

        return allocated
