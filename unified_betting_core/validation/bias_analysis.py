"""
Bias & Stress Testing Module for SharpBet Core.

Audits model predictions and economic performance for:
1. Per-outcome bias (Home / Draw / Away structural asymmetry)
2. Outlier dependency & tail sensitivity (Leave-K-Out analysis)
3. Flip threshold: number of top winning bets whose removal flips aggregate ROI negative
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List


class BiasStressAuditor:
    """
    Executes quantitative bias and stress audits on historical betting records.
    """

    @staticmethod
    def audit_bias_and_stress(placed_bets: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Runs comprehensive bias and sensitivity audit on placed bets.
        """
        if not placed_bets:
            return {
                "status": "EMPTY",
                "verdict": "NO_BETS_TO_AUDIT",
                "is_tail_sensitive": True,
                "is_away_biased": False
            }

        df = pd.DataFrame(placed_bets)
        total_bets = len(df)
        total_stakes = float(df["stake"].sum())
        total_pnl = float(df["pnl"].sum())
        baseline_roi = float(total_pnl / total_stakes * 100.0) if total_stakes > 0 else 0.0

        # 1. Per-Outcome Structural Breakdown
        outcome_breakdown = {}
        for out in ["home", "draw", "away"]:
            sub = df[df["outcome"].str.lower() == out]
            n_sub = len(sub)
            stakes_sub = float(sub["stake"].sum())
            pnl_sub = float(sub["pnl"].sum())
            roi_sub = float(pnl_sub / stakes_sub * 100.0) if stakes_sub > 0 else 0.0
            wins_sub = int((sub["pnl"] > 0).sum())
            win_rate = float(wins_sub / n_sub * 100.0) if n_sub > 0 else 0.0
            outcome_breakdown[out] = {
                "bet_count": n_sub,
                "bet_share_pct": round(n_sub / max(total_bets, 1) * 100.0, 2),
                "wins": wins_sub,
                "win_rate_pct": round(win_rate, 2),
                "total_stakes": round(stakes_sub, 2),
                "total_pnl": round(pnl_sub, 2),
                "roi_pct": round(roi_sub, 2)
            }

        # 2. Top Outliers by Realized P&L
        sorted_by_pnl = df.sort_values(by="pnl", ascending=False)
        top_5_outliers = []
        for _, b in sorted_by_pnl.head(5).iterrows():
            top_5_outliers.append({
                "date": str(b.get("date")),
                "match": str(b.get("match")),
                "outcome": str(b.get("outcome")),
                "placed_odds": float(b.get("placed_odds", 0.0)),
                "closing_odds": float(b.get("closing_odds", 0.0)),
                "fair_clv": float(b.get("fair_clv", 0.0)) if b.get("fair_clv") is not None else None,
                "stake": round(float(b.get("stake", 0.0)), 2),
                "pnl": round(float(b.get("pnl", 0.0)), 2)
            })

        # 3. Leave-K-Out Sensitivity Analysis
        leave_k_out = {}
        flip_k = None
        for k in range(1, min(6, total_bets)):
            sub_k = sorted_by_pnl.iloc[k:]
            pnl_k = float(sub_k["pnl"].sum())
            stakes_k = float(sub_k["stake"].sum())
            roi_k = float(pnl_k / stakes_k * 100.0) if stakes_k > 0 else 0.0
            leave_k_out[f"leave_{k}_out"] = {
                "excluded_top_bets": k,
                "remaining_bets": len(sub_k),
                "remaining_pnl": round(pnl_k, 2),
                "remaining_stakes": round(stakes_k, 2),
                "remaining_roi_pct": round(roi_k, 2)
            }
            if roi_k <= 0.0 and flip_k is None:
                flip_k = k

        # 4. Asymmetry and Tail Dependency Metrics
        away_share = outcome_breakdown.get("away", {}).get("bet_share_pct", 0.0)
        away_pnl = outcome_breakdown.get("away", {}).get("total_pnl", 0.0)
        home_pnl = outcome_breakdown.get("home", {}).get("total_pnl", 0.0)
        draw_pnl = outcome_breakdown.get("draw", {}).get("total_pnl", 0.0)

        is_away_biased = away_share > 50.0 or (away_pnl > 0 and home_pnl < 0 and draw_pnl < 0)
        is_tail_sensitive = (flip_k is not None and flip_k <= 5)

        if is_tail_sensitive:
            verdict = f"FAILED_STRESS_TEST (Tail sensitive: removing top {flip_k} bets flips ROI negative)"
        elif is_away_biased:
            verdict = "WARNING_AWAY_BIASED (Edge heavily concentrated in away bets)"
        else:
            verdict = "BALANCED_AND_ROBUST"

        return {
            "status": "COMPLETED",
            "verdict": verdict,
            "total_bets": total_bets,
            "baseline_pnl": round(total_pnl, 2),
            "baseline_roi_pct": round(baseline_roi, 2),
            "is_tail_sensitive": is_tail_sensitive,
            "roi_flip_k": flip_k,
            "is_away_biased": is_away_biased,
            "outcome_breakdown": outcome_breakdown,
            "top_5_outliers": top_5_outliers,
            "leave_k_out_sensitivity": leave_k_out,
            "audit_summary": (
                f"Baseline ROI: {baseline_roi:.2f}% across {total_bets} bets. "
                f"Removing top {flip_k or '>5'} bets flips aggregate ROI negative. "
                f"Away bets account for {away_share:.1f}% of volume and €{away_pnl:.2f} P&L "
                f"while Home bets lost €{abs(home_pnl):.2f}."
            )
        }
