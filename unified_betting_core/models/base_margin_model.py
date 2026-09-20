"""
Base-Margin GBDT Model for SharpBet Core.

PRINCIPLE (Deotte / S6E9 Lesson):
  Instead of teaching a GBDT to estimate P(home|features) from scratch,
  we initialize each tree with:
      base_score = logit(p_market_devigged)

  This forces the ensemble to learn ONLY the residual:
      delta = logit(p_true) - logit(p_market)

  i.e., "Where does the market misprice relative to form, injuries, schedule?"

  A model that cannot beat `base_margin = 0` (the market) produces no edge.
  If the residual delta is consistently > 0 in OOS, that is genuine alpha.

ZERO-LEAKAGE GUARANTEE:
  - `fit()` is called only on strictly past data (before the fold boundary).
  - `predict_residual()` is called on OOS rows only.
  - Closing odds are NEVER passed to fit() or predict_residual().
"""

import logging
import math
from dataclasses import dataclass, field
from typing import Any

import numpy as np

logger = logging.getLogger("SharpBet.BaseMarginModel")


def _logit(p: float) -> float:
    """Safe logit. Clips p to [1e-6, 1 - 1e-6]."""
    p = max(min(p, 1 - 1e-6), 1e-6)
    return math.log(p / (1 - p))


def _sigmoid(x: float) -> float:
    """Inverse logit."""
    return 1.0 / (1.0 + math.exp(-x))


@dataclass
class BaseMarginPrediction:
    """
    Per-outcome base-margin model output.

    Fields:
        outcome: 'home' | 'draw' | 'away'
        p_market_devigged: de-vigged opening market probability (anchor)
        logit_market: logit(p_market_devigged) — the base margin
        residual_delta: learned residual in logit space (positive = model > market)
        p_final: sigmoid(logit_market + residual_delta) — final blended probability
        edge_vs_market: p_final - p_market_devigged (positive edge signal)
        is_positive_edge: True if edge_vs_market > threshold
    """

    outcome: str
    p_market_devigged: float
    logit_market: float
    residual_delta: float
    p_final: float
    edge_vs_market: float
    is_positive_edge: bool


@dataclass
class MatchBaseMarginResult:
    """Full prediction for one match (home/draw/away)."""

    match_id: str
    predictions: list[BaseMarginPrediction] = field(default_factory=list)
    best_edge_outcome: str = ""
    best_edge_value: float = 0.0
    model_version: str = "base_margin_v1"


class BaseMarginModel:
    """
    Lightweight form-based residual estimator anchored to market log-odds.

    Without a real GBDT library dependency (xgboost/lightgbm are optional),
    this class implements the same mathematical contract:

        residual_logit = f(form_features) — learned from past window
        p_final = sigmoid(logit_market + residual_logit)

    The residual f() is estimated via weighted least-squares on past matches
    (a linear approximation of the first GBDT split), which is sufficient to
    demonstrate positive or negative delta vs market.

    To upgrade: swap `_fit_linear_residual` for an LGBMClassifier trained
    with `init_score=logit_market_array` on the training fold.
    """

    def __init__(
        self,
        min_train_samples: int = 60,
        edge_threshold: float = 0.015,
        decay_rate: float = 0.004,
    ):
        self.min_train_samples = min_train_samples
        self.edge_threshold = edge_threshold
        self.decay_rate = decay_rate

        # Fitted parameters per outcome
        self._residual_bias: dict[str, float] = {"home": 0.0, "draw": 0.0, "away": 0.0}
        self._residual_form_weights: dict[str, float] = {
            "home": 0.0,
            "draw": 0.0,
            "away": 0.0,
        }
        self.is_fitted = False
        self.n_train_samples = 0

    # ──────────────────────────────────────────────────────────────────────────
    # FIT: Call strictly on past window data (before fold boundary)
    # ──────────────────────────────────────────────────────────────────────────

    def fit(
        self,
        past_records: list[dict[str, Any]],
    ) -> "BaseMarginModel":
        """
        Fit the residual model on strictly historical records.

        Each record must contain:
            p_market_home, p_market_draw, p_market_away   — devigged opening odds
            form_delta_home                                — home form advantage signal [-1, 1]
            actual_result                                  — 'home'|'draw'|'away'

        Residual target: logit(p_outcome_empirical) - logit(p_market_outcome)

        We use a simple weighted mean (exponential time-decay by record index)
        as the bias term, and a form-weighted gradient for the form coefficient.
        """
        if len(past_records) < self.min_train_samples:
            logger.debug(
                f"BaseMarginModel: insufficient train samples "
                f"({len(past_records)} < {self.min_train_samples}). Using defaults."
            )
            self.is_fitted = True
            return self

        outcomes = ["home", "draw", "away"]
        n = len(past_records)
        weights = np.array(
            [math.exp(-self.decay_rate * (n - 1 - i)) for i in range(n)]
        )
        weights /= weights.sum()

        for outcome in outcomes:
            residuals = []
            form_signals = []
            w_list = []

            for i, rec in enumerate(past_records):
                actual = str(rec.get("actual_result", "")).lower().strip()
                p_mkt = float(rec.get(f"p_market_{outcome}", 0.333))
                form_delta = float(rec.get("form_delta_home", 0.0))

                if outcome == "away":
                    form_signal = -form_delta
                elif outcome == "draw":
                    form_signal = -abs(form_delta) * 0.5
                else:
                    form_signal = form_delta

                # Empirical outcome: 1 if actual == outcome else 0
                p_empirical = 1.0 if actual == outcome else 0.0
                # Smooth with market prior to avoid log(0): Laplace smoothing
                p_empirical_smooth = (
                    p_empirical * 0.85 + p_mkt * 0.15
                )

                logit_mkt = _logit(p_mkt)
                logit_emp = _logit(p_empirical_smooth)
                residual = logit_emp - logit_mkt

                residuals.append(residual)
                form_signals.append(form_signal)
                w_list.append(weights[i])

            r_arr = np.array(residuals)
            f_arr = np.array(form_signals)
            w_arr = np.array(w_list)

            # Weighted bias
            self._residual_bias[outcome] = float(np.average(r_arr, weights=w_arr))

            # Weighted form coefficient (cov/var)
            w_mean_r = np.average(r_arr, weights=w_arr)
            w_mean_f = np.average(f_arr, weights=w_arr)
            cov = float(np.average((r_arr - w_mean_r) * (f_arr - w_mean_f), weights=w_arr))
            var_f = float(np.average((f_arr - w_mean_f) ** 2, weights=w_arr))
            self._residual_form_weights[outcome] = cov / var_f if var_f > 1e-8 else 0.0

        self.is_fitted = True
        self.n_train_samples = n
        logger.debug(
            f"BaseMarginModel fitted on {n} samples. "
            f"Biases: {self._residual_bias}"
        )
        return self

    # ──────────────────────────────────────────────────────────────────────────
    # PREDICT: Call only on OOS rows
    # ──────────────────────────────────────────────────────────────────────────

    def predict_match(
        self,
        p_market_devigged: dict[str, float],
        form_delta_home: float = 0.0,
    ) -> MatchBaseMarginResult:
        """
        Predict residual-adjusted probabilities for a single match.

        Args:
            p_market_devigged: {'home': float, 'draw': float, 'away': float}
                               De-vigged opening market probabilities (sum ≈ 1.0).
                               MUST be computed from entry odds ONLY (not closing).
            form_delta_home: Signed form advantage for home team.
                             Positive → home team in better form.
                             Range: [-1.0, 1.0].

        Returns:
            MatchBaseMarginResult with per-outcome edge vs market.
        """
        outcomes = ["home", "draw", "away"]
        form_signals = {
            "home": form_delta_home,
            "draw": -abs(form_delta_home) * 0.5,
            "away": -form_delta_home,
        }

        predictions = []
        for outcome in outcomes:
            p_mkt = max(float(p_market_devigged.get(outcome, 0.333)), 1e-6)
            logit_mkt = _logit(p_mkt)

            if self.is_fitted:
                bias = self._residual_bias.get(outcome, 0.0)
                form_w = self._residual_form_weights.get(outcome, 0.0)
                form_sig = form_signals[outcome]
                residual_delta = bias + form_w * form_sig
                # Clip residual to ±0.5 logit units to prevent overconfidence
                residual_delta = max(min(residual_delta, 0.5), -0.5)
            else:
                residual_delta = 0.0

            logit_final = logit_mkt + residual_delta
            p_final = _sigmoid(logit_final)
            edge = p_final - p_mkt

            predictions.append(
                BaseMarginPrediction(
                    outcome=outcome,
                    p_market_devigged=round(p_mkt, 5),
                    logit_market=round(logit_mkt, 5),
                    residual_delta=round(residual_delta, 5),
                    p_final=round(p_final, 5),
                    edge_vs_market=round(edge, 5),
                    is_positive_edge=edge > self.edge_threshold,
                )
            )

        # Best edge outcome
        best = max(predictions, key=lambda x: x.edge_vs_market)

        return MatchBaseMarginResult(
            match_id="",
            predictions=predictions,
            best_edge_outcome=best.outcome if best.is_positive_edge else "",
            best_edge_value=round(best.edge_vs_market, 5),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_fitted": self.is_fitted,
            "n_train_samples": self.n_train_samples,
            "edge_threshold": self.edge_threshold,
            "residual_bias": self._residual_bias,
            "residual_form_weights": self._residual_form_weights,
        }
