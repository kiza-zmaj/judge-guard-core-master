"""
Block-Bootstrap Confidence Intervals for SharpBet Core.

MOTIVATION (market-efficiency-lab / research standard):
  Standard bootstrap resamples individual bets as i.i.d., but same-round
  bets are correlated (shared referee pool, weather, scheduling fatigue).
  Block-bootstrap resamples entire matchday BLOCKS, preserving intra-block
  correlation and producing honest (wider) CIs.

  A 95% CI that does NOT contain zero is required evidence that ROI/CLV
  is distinguishable from random noise at statistical significance.

USAGE:
    bb = BlockBootstrap(n_bootstrap=10_000, block_unit="date")
    result = bb.compute_ci(bets_list, metric="roi_pct")
    print(result.ci_lower, result.mean_estimate, result.ci_upper)
"""

import logging
import math
import random
from dataclasses import dataclass
from typing import Any, Literal

import numpy as np

logger = logging.getLogger("SharpBet.BlockBootstrap")


@dataclass
class BootstrapResult:
    metric: str
    mean_estimate: float
    ci_lower: float
    ci_upper: float
    n_bootstrap: int
    n_blocks: int
    n_observations: int
    block_unit: str
    contains_zero: bool
    is_significant: bool  # CI does NOT contain zero
    p_value_approx: float  # fraction of bootstrap samples <= 0


class BlockBootstrap:
    """
    Block-Bootstrap resampler for bet-level time series.

    Supported metrics:
        'roi_pct'      — PnL / stakes * 100
        'fair_clv_pct' — mean fair CLV across settled bets
        'win_rate_pct' — win rate percentage
        'pnl'          — raw PnL sum

    Block units:
        'date'   — one block per unique match date (recommended)
        'week'   — one block per ISO week
        'month'  — one block per calendar month
    """

    def __init__(
        self,
        n_bootstrap: int = 10_000,
        confidence: float = 0.95,
        block_unit: Literal["date", "week", "month"] = "date",
        seed: int = 42,
    ):
        self.n_bootstrap = n_bootstrap
        self.confidence = confidence
        self.block_unit = block_unit
        self.seed = seed

    # ──────────────────────────────────────────────────────────────────────────

    def _get_block_key(self, bet: dict[str, Any]) -> str:
        date_str = str(bet.get("date", "unknown"))
        if self.block_unit == "date":
            return date_str[:10]  # YYYY-MM-DD
        elif self.block_unit == "week":
            try:
                import datetime
                d = datetime.date.fromisoformat(date_str[:10])
                iso = d.isocalendar()
                return f"{iso[0]}-W{iso[1]:02d}"
            except Exception:
                return date_str[:7]
        elif self.block_unit == "month":
            return date_str[:7]  # YYYY-MM
        return date_str[:10]

    def _compute_metric(self, bets: list[dict[str, Any]], metric: str) -> float:
        if not bets:
            return 0.0
        if metric == "roi_pct":
            total_stake = sum(b.get("stake", 0.0) for b in bets)
            total_pnl = sum(b.get("pnl", 0.0) for b in bets)
            return (total_pnl / total_stake * 100.0) if total_stake > 0 else 0.0
        elif metric == "fair_clv_pct":
            clvs = [
                b.get("fair_clv_pct") or b.get("fair_clv", 0.0) * 100.0
                for b in bets
                if b.get("fair_clv") is not None or b.get("fair_clv_pct") is not None
            ]
            return float(np.mean(clvs)) if clvs else 0.0
        elif metric == "win_rate_pct":
            wins = sum(1 for b in bets if b.get("is_win") or b.get("pnl", 0) > 0)
            return wins / len(bets) * 100.0
        elif metric == "pnl":
            return sum(b.get("pnl", 0.0) for b in bets)
        else:
            raise ValueError(f"Unknown metric: {metric}")

    # ──────────────────────────────────────────────────────────────────────────

    def compute_ci(
        self,
        bets: list[dict[str, Any]],
        metric: str = "roi_pct",
    ) -> BootstrapResult:
        """
        Compute block-bootstrap CI for the given metric.

        Args:
            bets: List of bet records. Each must have 'date', 'stake', 'pnl'.
                  For CLV metric also needs 'fair_clv' or 'fair_clv_pct'.
            metric: One of 'roi_pct', 'fair_clv_pct', 'win_rate_pct', 'pnl'.

        Returns:
            BootstrapResult with CI bounds and significance flags.
        """
        if not bets:
            return BootstrapResult(
                metric=metric,
                mean_estimate=0.0,
                ci_lower=0.0,
                ci_upper=0.0,
                n_bootstrap=self.n_bootstrap,
                n_blocks=0,
                n_observations=0,
                block_unit=self.block_unit,
                contains_zero=True,
                is_significant=False,
                p_value_approx=1.0,
            )

        # Group into blocks
        blocks: dict[str, list[dict[str, Any]]] = {}
        for bet in bets:
            key = self._get_block_key(bet)
            blocks.setdefault(key, []).append(bet)

        block_list = list(blocks.values())
        n_blocks = len(block_list)

        if n_blocks < 5:
            logger.warning(
                f"BlockBootstrap: only {n_blocks} blocks — "
                "CI may be unreliable. Increase sample size."
            )

        # Point estimate on full data
        point_estimate = self._compute_metric(bets, metric)

        # Bootstrap
        rng = random.Random(self.seed)
        bootstrap_samples: list[float] = []

        for _ in range(self.n_bootstrap):
            # Resample n_blocks blocks with replacement
            sampled_blocks = rng.choices(block_list, k=n_blocks)
            sampled_bets = [b for block in sampled_blocks for b in block]
            bootstrap_samples.append(self._compute_metric(sampled_bets, metric))

        samples_arr = np.array(bootstrap_samples)
        alpha = 1.0 - self.confidence
        ci_lower = float(np.percentile(samples_arr, alpha / 2 * 100))
        ci_upper = float(np.percentile(samples_arr, (1 - alpha / 2) * 100))

        # p-value approximation: fraction of bootstrap samples ≤ 0
        p_value = float(np.mean(samples_arr <= 0.0))
        contains_zero = ci_lower <= 0.0 <= ci_upper
        is_significant = not contains_zero

        logger.info(
            f"BlockBootstrap [{metric}]: estimate={point_estimate:.3f}, "
            f"CI=[{ci_lower:.3f}, {ci_upper:.3f}], "
            f"significant={is_significant}, p≈{p_value:.4f}, "
            f"blocks={n_blocks}, n={len(bets)}"
        )

        return BootstrapResult(
            metric=metric,
            mean_estimate=round(point_estimate, 4),
            ci_lower=round(ci_lower, 4),
            ci_upper=round(ci_upper, 4),
            n_bootstrap=self.n_bootstrap,
            n_blocks=n_blocks,
            n_observations=len(bets),
            block_unit=self.block_unit,
            contains_zero=contains_zero,
            is_significant=is_significant,
            p_value_approx=round(p_value, 4),
        )

    def compute_paired_ci(
        self,
        bets_model: list[dict[str, Any]],
        bets_baseline: list[dict[str, Any]],
        metric: str = "roi_pct",
    ) -> BootstrapResult:
        """
        Paired block-bootstrap: compute CI of (model metric - baseline metric)
        on the same set of matches.

        The paired approach gives SE ~10x smaller than marginal comparison
        because shared noise cancels (DeLong / Deotte principle).

        Args:
            bets_model: Bet records from the model strategy.
            bets_baseline: Bet records from the Pinnacle benchmark on identical matches.
            metric: Metric to compare.
        """
        # Align by match date
        def _group_by_date(b_list: list[dict[str, Any]]) -> dict[str, list]:
            g: dict[str, list] = {}
            for b in b_list:
                key = self._get_block_key(b)
                g.setdefault(key, []).append(b)
            return g

        g_model = _group_by_date(bets_model)
        g_base = _group_by_date(bets_baseline)
        common_dates = sorted(set(g_model.keys()) & set(g_base.keys()))

        if not common_dates:
            logger.warning("Paired bootstrap: no common dates between model and baseline.")
            return self.compute_ci([], metric)

        paired_diffs: list[float] = []
        rng = random.Random(self.seed)

        for _ in range(self.n_bootstrap):
            sampled_dates = rng.choices(common_dates, k=len(common_dates))
            m_bets = [b for d in sampled_dates for b in g_model.get(d, [])]
            b_bets = [b for d in sampled_dates for b in g_base.get(d, [])]
            diff = self._compute_metric(m_bets, metric) - self._compute_metric(b_bets, metric)
            paired_diffs.append(diff)

        # Point estimate
        m_all = [b for d in common_dates for b in g_model[d]]
        b_all = [b for d in common_dates for b in g_base[d]]
        point_diff = self._compute_metric(m_all, metric) - self._compute_metric(b_all, metric)

        diff_arr = np.array(paired_diffs)
        alpha = 1.0 - self.confidence
        ci_lower = float(np.percentile(diff_arr, alpha / 2 * 100))
        ci_upper = float(np.percentile(diff_arr, (1 - alpha / 2) * 100))
        p_value = float(np.mean(diff_arr <= 0.0))
        contains_zero = ci_lower <= 0.0 <= ci_upper

        logger.info(
            f"PairedBootstrap [{metric}]: diff={point_diff:.3f}, "
            f"CI=[{ci_lower:.3f}, {ci_upper:.3f}], p≈{p_value:.4f}"
        )

        return BootstrapResult(
            metric=f"paired_diff_{metric}",
            mean_estimate=round(point_diff, 4),
            ci_lower=round(ci_lower, 4),
            ci_upper=round(ci_upper, 4),
            n_bootstrap=self.n_bootstrap,
            n_blocks=len(common_dates),
            n_observations=len(m_all),
            block_unit=self.block_unit,
            contains_zero=contains_zero,
            is_significant=not contains_zero,
            p_value_approx=round(p_value, 4),
        )
