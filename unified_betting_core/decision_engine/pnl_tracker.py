"""
Realized P&L Tracker, Bankroll Evolution & Quantitative Performance Metrics.
Tracks actual settled bets, ROI / Yield, Max Drawdown, Profit Factor,
and correlation between Closing Line Value (CLV) and Realized Profit.
"""

from typing import Any

import numpy as np

from unified_betting_core.config import DEFAULT_BANKROLL


class PnLTracker:
    """
    Tracks bankroll growth, settled bet metrics, and statistical validation of edge.
    """

    def __init__(self, initial_bankroll: float = DEFAULT_BANKROLL):
        self.initial_bankroll = initial_bankroll
        self.current_bankroll = initial_bankroll
        self.peak_bankroll = initial_bankroll
        self.bets: list[dict[str, Any]] = []
        self.equity_curve: list[dict[str, Any]] = [
            {"bet_num": 0, "bankroll": initial_bankroll, "pnl": 0.0}
        ]

    def record_bet(
        self,
        match: str,
        outcome: str,
        placed_odds: float,
        stake: float,
        actual_result: str,
        closing_odds: float | None = None,
        closing_fair_odds: float | None = None,
        date: str | None = None,
    ) -> dict[str, Any]:
        """
        Records and settles a single wager.
        Result is evaluated: 'won' if outcome matches actual_result, else 'lost'.
        """
        if stake <= 0 or placed_odds <= 1.0:
            return {}

        is_win = outcome.lower().strip() == actual_result.lower().strip()
        profit = (stake * placed_odds - stake) if is_win else -stake

        self.current_bankroll += profit
        self.peak_bankroll = max(self.peak_bankroll, self.current_bankroll)

        # CLV calculation if closing odds provided
        clv_info = {}
        if closing_odds and closing_odds > 1.0:
            raw_clv = (placed_odds / closing_odds) - 1.0
            fair_clv = (
                (placed_odds / closing_fair_odds) - 1.0
                if closing_fair_odds
                else raw_clv
            )
            clv_info = {
                "closing_odds": closing_odds,
                "raw_clv": round(raw_clv, 4),
                "fair_clv": round(fair_clv, 4),
            }

        bet_entry = {
            "bet_id": len(self.bets) + 1,
            "date": date or "N/A",
            "match": match,
            "outcome": outcome,
            "placed_odds": placed_odds,
            "stake": round(stake, 2),
            "actual_result": actual_result,
            "is_win": is_win,
            "pnl": round(profit, 2),
            "bankroll_after": round(self.current_bankroll, 2),
            **clv_info,
        }

        self.bets.append(bet_entry)
        self.equity_curve.append(
            {
                "bet_num": len(self.bets),
                "bankroll": round(self.current_bankroll, 2),
                "pnl": round(self.current_bankroll - self.initial_bankroll, 2),
            }
        )

        return bet_entry

    def get_summary_metrics(self) -> dict[str, Any]:
        """
        Generates full quantitative summary of performance.
        """
        if not self.bets:
            return {
                "initial_bankroll": self.initial_bankroll,
                "current_bankroll": self.current_bankroll,
                "total_bets": 0,
                "total_staked": 0.0,
                "net_profit": 0.0,
                "roi_yield_pct": 0.0,
                "win_rate_pct": 0.0,
                "max_drawdown_eur": 0.0,
                "max_drawdown_pct": 0.0,
                "profit_factor": 0.0,
                "clv_pnl_correlation": 0.0,
            }

        total_bets = len(self.bets)
        wins = sum(1 for b in self.bets if b["is_win"])
        win_rate = (wins / total_bets) * 100.0

        total_staked = sum(b["stake"] for b in self.bets)
        net_profit = self.current_bankroll - self.initial_bankroll
        roi_yield = (net_profit / max(total_staked, 1.0)) * 100.0

        gross_wins = sum(b["pnl"] for b in self.bets if b["pnl"] > 0)
        gross_losses = abs(sum(b["pnl"] for b in self.bets if b["pnl"] < 0))
        profit_factor = gross_wins / max(gross_losses, 0.01)

        # Max Drawdown computation
        peak = self.initial_bankroll
        max_dd_eur = 0.0
        max_dd_pct = 0.0

        for point in self.equity_curve:
            b_val = point["bankroll"]
            peak = max(peak, b_val)
            dd = peak - b_val
            dd_pct = (dd / peak) * 100.0 if peak > 0 else 0.0
            max_dd_eur = max(max_dd_eur, dd)
            max_dd_pct = max(max_dd_pct, dd_pct)

        # Correlation between CLV and individual bet return
        clv_list = []
        return_list = []
        for b in self.bets:
            if "raw_clv" in b:
                clv_list.append(b["raw_clv"])
                # return per unit staked: pnl / stake
                return_list.append(b["pnl"] / max(b["stake"], 0.01))

        clv_corr = 0.0
        if (
            len(clv_list) >= 5
            and np.std(clv_list) > 1e-6
            and np.std(return_list) > 1e-6
        ):
            clv_corr = float(np.corrcoef(clv_list, return_list)[0, 1])

        return {
            "initial_bankroll": round(self.initial_bankroll, 2),
            "current_bankroll": round(self.current_bankroll, 2),
            "total_bets": total_bets,
            "wins": wins,
            "losses": total_bets - wins,
            "win_rate_pct": round(win_rate, 2),
            "total_staked": round(total_staked, 2),
            "net_profit": round(net_profit, 2),
            "roi_yield_pct": round(roi_yield, 2),
            "max_drawdown_eur": round(max_dd_eur, 2),
            "max_drawdown_pct": round(max_dd_pct, 2),
            "profit_factor": round(profit_factor, 2),
            "clv_pnl_correlation": round(clv_corr, 3),
        }
