"""
Model Calibration & Probability Diagnostics for SharpBet Core.
Gate A: Are model probabilities calibrated out-of-sample?

FIXED: ECE is now calculated over ALL OOS predictions (multiclass OvR),
not over the empty 'selected_bets' list that caused ECE=0.00%.

Strictly separates training, calibration, and out-of-sample evaluation.
"""

import math
import numpy as np
from scipy.optimize import minimize_scalar
from dataclasses import dataclass
from typing import Dict, Any, List, Tuple, Optional

@dataclass
class CalibrationGateVerdict:
    passed: bool
    brier_score: float
    # ECE is Optional[float] — None means EMPTY_INPUT, not a valid measurement
    ece_pct: Optional[float]
    mce_pct: Optional[float]
    sample_size: int
    is_drift_detected: bool
    status: str
    failure_reasons: List[str]
    reliability_table: List[Dict[str, Any]]


class TemperatureScaler:
    """
    Platt-style Temperature Scaling for multi-class probabilities (Home/Draw/Away).
    MUST be fitted strictly on PAST window data only — never on OOS evaluation data.
    """
    def __init__(self, default_temp: float = 1.05):
        self.temperature = default_temp
        self.is_fitted = False

    def fit(self, prob_distributions: List[Dict[str, float]], actual_results: List[str]) -> float:
        if len(prob_distributions) < 30 or len(prob_distributions) != len(actual_results):
            return self.temperature

        outcomes = ["home", "draw", "away"]
        probs_array = []
        labels_array = []

        for p_dict, act in zip(prob_distributions, actual_results):
            act_clean = act.lower().strip()
            if act_clean not in outcomes:
                continue
            probs_array.append([max(p_dict.get(o, 0.0), 1e-6) for o in outcomes])
            labels_array.append(outcomes.index(act_clean))

        if len(labels_array) < 30:
            return self.temperature

        probs_np = np.array(probs_array)
        labels_np = np.array(labels_array)

        def nll(temp):
            if temp <= 0.1 or temp > 5.0:
                return 1e9
            logits = np.log(probs_np) / temp
            exp_logits = np.exp(logits - np.max(logits, axis=1, keepdims=True))
            softmax_probs = exp_logits / np.sum(exp_logits, axis=1, keepdims=True)
            return -np.mean(np.log(softmax_probs[np.arange(len(labels_np)), labels_np] + 1e-12))

        res = minimize_scalar(nll, bounds=(0.5, 3.0), method="bounded")
        if res.success:
            self.temperature = round(float(res.x), 4)
            self.is_fitted = True

        return self.temperature

    def scale(self, probs: Dict[str, float]) -> Dict[str, float]:
        outcomes = ["home", "draw", "away"]
        logits = [math.log(max(probs.get(o, 0.0), 1e-6)) / self.temperature for o in outcomes]
        max_l = max(logits)
        exp_l = [math.exp(l - max_l) for l in logits]
        sum_exp = sum(exp_l)
        return {outcomes[i]: round(exp_l[i] / sum_exp, 4) for i in range(len(outcomes))}


class ModelCalibration:
    """
    Gate A: Out-of-sample calibration assessment.
    ECE is measured over ALL OOS multiclass predictions (one-vs-rest per outcome),
    NOT over a subset of approved bets (which would cause circular dependency and
    produce ECE=0.00% when no bets are approved).
    """

    @staticmethod
    def calculate_brier_score(
        predictions: List[Dict[str, float]],
        actuals: List[str]
    ) -> Dict[str, Any]:
        """
        Multi-class Brier Score: BS = (1/N) * sum_i sum_k (p_ik - y_ik)^2
        Baseline (uniform 33/33/33) = 0.667. Lower is better.
        Returns sample_size=0 and score=0.6667 for empty/invalid input.
        """
        if not predictions or not actuals or len(predictions) != len(actuals):
            return {"brier_score": 0.6667, "sample_size": 0, "error": "EMPTY_OR_MISMATCHED_INPUT"}

        outcomes = ["home", "draw", "away"]
        total_sq_error = 0.0
        n = len(predictions)
        per_outcome = {"home": 0.0, "draw": 0.0, "away": 0.0}

        for p_dict, actual in zip(predictions, actuals):
            act = actual.lower().strip()
            for o in outcomes:
                p = p_dict.get(o, 0.0)
                y = 1.0 if act == o else 0.0
                err = (p - y) ** 2
                total_sq_error += err
                per_outcome[o] += err

        brier = total_sq_error / n
        return {
            "brier_score": round(brier, 5),
            "brier_home": round(per_outcome["home"] / n, 5),
            "brier_draw": round(per_outcome["draw"] / n, 5),
            "brier_away": round(per_outcome["away"] / n, 5),
            "sample_size": n
        }

    @staticmethod
    def calculate_ece(
        predicted_probs: List[float],
        true_labels: List[int],
        num_bins: int = 10
    ) -> Dict[str, Any]:
        """
        Binary ECE for a single outcome class (use as part of multiclass OvR).
        Returns ece=None (not 0.0) for empty input — distinguishes missing data
        from a legitimate perfect calibration measurement.

        ECE = sum_m (|B_m| / N) * |acc(B_m) - conf(B_m)|
        """
        # CRITICAL FIX: Empty input returns None, never 0.0
        if not predicted_probs or len(predicted_probs) != len(true_labels):
            return {
                "ece": None,
                "ece_pct": None,
                "mce": None,
                "mce_pct": None,
                "bins": [],
                "sample_size": 0,
                "error": "EMPTY_INPUT — ECE not measurable"
            }

        probs = np.array(predicted_probs, dtype=float)
        labels = np.array(true_labels, dtype=float)
        n = len(probs)

        bin_boundaries = np.linspace(0, 1, num_bins + 1)
        ece = 0.0
        mce = 0.0
        bin_details = []

        for i in range(num_bins):
            lo = bin_boundaries[i]
            hi = bin_boundaries[i + 1]
            in_bin = (probs >= lo) & (probs < hi) if i < num_bins - 1 else (probs >= lo) & (probs <= hi)
            bin_size = int(np.sum(in_bin))

            if bin_size > 0:
                acc = float(np.mean(labels[in_bin]))
                conf = float(np.mean(probs[in_bin]))
                gap = abs(acc - conf)
                ece += (bin_size / n) * gap
                mce = max(mce, gap)
                bin_details.append({
                    "bin_range": f"{lo:.2f}-{hi:.2f}",
                    "count": bin_size,
                    "mean_predicted_prob": round(conf, 4),
                    "empirical_frequency": round(acc, 4),
                    "abs_error": round(gap, 4)
                })

        return {
            "ece": round(float(ece), 4),
            "ece_pct": round(float(ece) * 100, 2),
            "mce": round(float(mce), 4),
            "mce_pct": round(float(mce) * 100, 2),
            "bins": bin_details,
            "sample_size": n
        }

    @staticmethod
    def calculate_multiclass_ece(
        predicted_distributions: List[Dict[str, float]],
        actual_results: List[str],
        outcomes: List[str] = None,
        num_bins: int = 10
    ) -> Dict[str, Any]:
        """
        Multiclass ECE via One-vs-Rest (OvR) decomposition.
        For each outcome class, treats it as a binary problem and computes ECE.
        Final ECE = macro-average over classes.

        This is the correct method for 3-outcome football prediction:
        - Uses ALL OOS predictions (no selection bias)
        - Does NOT require approved bets to exist
        - Breaks the circular dependency with CLV/approval gates
        """
        if outcomes is None:
            outcomes = ["home", "draw", "away"]

        if not predicted_distributions or not actual_results:
            return {
                "ece_multiclass": None,
                "ece_pct": None,
                "per_class_ece": {},
                "bins_per_class": {},
                "sample_size": 0,
                "error": "EMPTY_INPUT — ECE not measurable"
            }

        per_class_results = {}
        ece_values = []

        for outcome in outcomes:
            probs = [d.get(outcome, 0.0) for d in predicted_distributions]
            labels = [1 if r.lower().strip() == outcome else 0 for r in actual_results]
            result = ModelCalibration.calculate_ece(probs, labels, num_bins=num_bins)
            per_class_results[outcome] = result
            if result.get("ece") is not None:
                ece_values.append(result["ece"])

        if not ece_values:
            return {
                "ece_multiclass": None,
                "ece_pct": None,
                "per_class_ece": per_class_results,
                "sample_size": len(predicted_distributions),
                "error": "ECE_COMPUTATION_FAILED"
            }

        macro_ece = float(np.mean(ece_values))
        return {
            "ece_multiclass": round(macro_ece, 4),
            "ece_pct": round(macro_ece * 100, 2),
            "per_class_ece": {
                o: {
                    "ece_pct": per_class_results[o].get("ece_pct"),
                    "mce_pct": per_class_results[o].get("mce_pct"),
                    "sample_size": per_class_results[o].get("sample_size", 0)
                }
                for o in outcomes
            },
            "bins_per_class": {o: per_class_results[o].get("bins", []) for o in outcomes},
            "sample_size": len(predicted_distributions)
        }

    @staticmethod
    def produce_reliability_table(
        predicted_distributions: List[Dict[str, float]],
        actual_results: List[str],
        outcome: str = "home",
        num_bins: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Returns an inspectable reliability table for a single outcome class.
        Format: bin | count | mean_predicted_prob | empirical_frequency | abs_error
        Suitable for Phase 7 evidence package output.
        """
        probs = [d.get(outcome, 0.0) for d in predicted_distributions]
        labels = [1 if r.lower().strip() == outcome else 0 for r in actual_results]
        result = ModelCalibration.calculate_ece(probs, labels, num_bins=num_bins)
        return result.get("bins", [])

    @classmethod
    def evaluate_out_of_sample_gate(
        cls,
        predicted_prob_distributions: List[Dict[str, float]],
        actual_results: List[str],
        min_sample_size: int = 100,
        max_ece_pct: float = 6.0,
        max_brier: float = 0.65
    ) -> CalibrationGateVerdict:
        """
        GATE A: CALIBRATION GATE.
        Answers only: "Are model probabilities calibrated out-of-sample?"

        Takes ALL OOS predicted distributions and ALL actual results.
        Does NOT take selected_probabilities or selected_binary_labels —
        that caused the circular dependency and ECE=0.00% bug.

        Fails closed on:
        - Insufficient sample size
        - ECE > max_ece_pct
        - Brier > max_brier
        - Temporal calibration drift
        """
        n = len(predicted_prob_distributions)
        failure_reasons = []

        # 1. Sample size
        if n < min_sample_size:
            failure_reasons.append(
                f"Insufficient OOS sample: {n} matches (minimum: {min_sample_size})."
            )

        # 2. Brier Score
        brier_metrics = cls.calculate_brier_score(predicted_prob_distributions, actual_results)
        brier = brier_metrics.get("brier_score", 1.0)
        if brier > max_brier:
            failure_reasons.append(
                f"Brier {brier:.4f} > threshold {max_brier:.4f}."
            )

        # 3. Multiclass ECE (OvR) — over ALL OOS predictions
        ece_metrics = cls.calculate_multiclass_ece(
            predicted_prob_distributions, actual_results, num_bins=8
        )
        ece_pct = ece_metrics.get("ece_pct")
        mce_pct = None

        if ece_pct is None:
            failure_reasons.append("ECE could not be computed — empty OOS prediction set.")
        elif ece_pct > max_ece_pct:
            failure_reasons.append(
                f"ECE {ece_pct:.2f}% > threshold {max_ece_pct:.2f}%."
            )

        # MCE: worst class
        per_class = ece_metrics.get("per_class_ece", {})
        mce_values = [v.get("mce_pct") for v in per_class.values() if v.get("mce_pct") is not None]
        if mce_values:
            mce_pct = round(max(mce_values), 2)

        # 4. Temporal drift
        is_drift = False
        if n >= 60:
            mid = n // 2
            h1 = cls.calculate_multiclass_ece(
                predicted_prob_distributions[:mid], actual_results[:mid], num_bins=8
            )
            h2 = cls.calculate_multiclass_ece(
                predicted_prob_distributions[mid:], actual_results[mid:], num_bins=8
            )
            e1 = h1.get("ece_pct") or 0.0
            e2 = h2.get("ece_pct") or 0.0
            drift = abs(e2 - e1)
            if drift > 4.5:
                is_drift = True
                failure_reasons.append(
                    f"Calibration drift: ECE diverged {drift:.2f}% between halves ({e1:.1f}% → {e2:.1f}%)."
                )

        # 5. Reliability table (home class for inspectability)
        reliability_table = cls.produce_reliability_table(
            predicted_prob_distributions, actual_results, outcome="home", num_bins=8
        )

        passed = len(failure_reasons) == 0
        return CalibrationGateVerdict(
            passed=passed,
            brier_score=brier,
            ece_pct=ece_pct,
            mce_pct=mce_pct,
            sample_size=n,
            is_drift_detected=is_drift,
            status="CALIBRATION_PASS" if passed else "CALIBRATION_FAILED",
            failure_reasons=failure_reasons,
            reliability_table=reliability_table
        )
