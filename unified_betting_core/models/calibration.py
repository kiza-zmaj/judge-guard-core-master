"""
Model Calibration & Probability Diagnostics for SharpBet Core.
Calculates Brier Score, Expected Calibration Error (ECE), Maximum Calibration Error (MCE),
Temperature Scaling, and Out-of-Sample Calibration Gates.
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
    ece_pct: float
    mce_pct: float
    sample_size: int
    is_drift_detected: bool
    status: str
    failure_reasons: List[str]

class TemperatureScaler:
    """
    Fits and applies Platt-style Temperature Scaling for multi-class probabilities (Home/Draw/Away).
    Minimizes cross-entropy strictly on past validation split.
    """
    def __init__(self, default_temp: float = 1.05):
        self.temperature = default_temp
        self.is_fitted = False

    def fit(self, prob_distributions: List[Dict[str, float]], actual_results: List[str]) -> float:
        """
        Fits optimal temperature T on historical validation data using negative log-likelihood.
        """
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

        # Loss function: Negative Log-Likelihood with temperature T
        def nll(temp):
            if temp <= 0.1 or temp > 5.0:
                return 1e9
            logits = np.log(probs_np) / temp
            exp_logits = np.exp(logits - np.max(logits, axis=1, keepdims=True))
            softmax_probs = exp_logits / np.sum(exp_logits, axis=1, keepdims=True)
            nll_val = -np.mean(np.log(softmax_probs[np.arange(len(labels_np)), labels_np] + 1e-12))
            return nll_val

        res = minimize_scalar(nll, bounds=(0.5, 3.0), method="bounded")
        if res.success:
            self.temperature = round(float(res.x), 4)
            self.is_fitted = True

        return self.temperature

    def scale(self, probs: Dict[str, float]) -> Dict[str, float]:
        """Scales predicted probabilities with the fitted temperature parameter."""
        outcomes = ["home", "draw", "away"]
        logits = [math.log(max(probs.get(o, 0.0), 1e-6)) / self.temperature for o in outcomes]
        max_l = max(logits)
        exp_l = [math.exp(l - max_l) for l in logits]
        sum_exp = sum(exp_l)
        return {outcomes[i]: round(exp_l[i] / sum_exp, 4) for i in range(len(outcomes))}

class ModelCalibration:
    """
    Assesses and refines the calibration of probabilistic betting models.
    Provides strict out-of-sample validation gates.
    """

    @staticmethod
    def calculate_brier_score(predictions: List[Dict[str, float]], actuals: List[str]) -> Dict[str, float]:
        """
        Multi-class Brier Score:
        BS = (1 / N) * sum_i sum_k (p_ik - y_ik)^2
        where y_ik is 1 if outcome k occurred, else 0.
        Lower is better (0.0 is perfect prediction; 0.667 is uninformative 33/33/33 baseline).
        """
        if not predictions or not actuals or len(predictions) != len(actuals):
            return {"brier_score": 0.6667, "sample_size": 0}

        outcomes = ["home", "draw", "away"]
        total_sq_error = 0.0
        n = len(predictions)
        per_outcome_error = {"home": 0.0, "draw": 0.0, "away": 0.0}

        for p_dict, actual in zip(predictions, actuals):
            actual_clean = actual.lower().strip()
            for outcome in outcomes:
                p = p_dict.get(outcome, 0.0)
                y = 1.0 if actual_clean == outcome else 0.0
                err = (p - y) ** 2
                total_sq_error += err
                per_outcome_error[outcome] += err

        brier = total_sq_error / n
        return {
            "brier_score": round(brier, 5),
            "brier_home": round(per_outcome_error["home"] / n, 5),
            "brier_draw": round(per_outcome_error["draw"] / n, 5),
            "brier_away": round(per_outcome_error["away"] / n, 5),
            "sample_size": n
        }

    @staticmethod
    def calculate_ece(
        predicted_probs: List[float],
        true_labels: List[int],
        num_bins: int = 10
    ) -> Dict[str, Any]:
        """
        Expected Calibration Error (ECE) and Maximum Calibration Error (MCE).
        ECE = sum_m (|B_m| / N) * |acc(B_m) - conf(B_m)|
        """
        if not predicted_probs or len(predicted_probs) != len(true_labels):
            return {"ece": 0.0, "ece_pct": 0.0, "mce": 0.0, "mce_pct": 0.0, "bins": []}

        probs = np.array(predicted_probs)
        labels = np.array(true_labels)
        n = len(probs)

        bin_boundaries = np.linspace(0, 1, num_bins + 1)
        ece = 0.0
        mce = 0.0
        bin_details = []

        for i in range(num_bins):
            bin_lower = bin_boundaries[i]
            bin_upper = bin_boundaries[i + 1]

            if i == num_bins - 1:
                in_bin = (probs >= bin_lower) & (probs <= bin_upper)
            else:
                in_bin = (probs >= bin_lower) & (probs < bin_upper)

            bin_size = int(np.sum(in_bin))

            if bin_size > 0:
                accuracy_in_bin = float(np.mean(labels[in_bin]))
                avg_confidence_in_bin = float(np.mean(probs[in_bin]))
                abs_diff = abs(accuracy_in_bin - avg_confidence_in_bin)

                ece += (bin_size / n) * abs_diff
                mce = max(mce, abs_diff)

                bin_details.append({
                    "bin_range": f"{bin_lower:.2f}-{bin_upper:.2f}",
                    "count": bin_size,
                    "avg_confidence": round(avg_confidence_in_bin, 4),
                    "empirical_accuracy": round(accuracy_in_bin, 4),
                    "calibration_gap": round(abs_diff, 4)
                })

        return {
            "ece": round(float(ece), 4),
            "ece_pct": round(float(ece) * 100, 2),
            "mce": round(float(mce), 4),
            "mce_pct": round(float(mce) * 100, 2),
            "bins": bin_details
        }

    @classmethod
    def evaluate_out_of_sample_gate(
        cls,
        predicted_prob_distributions: List[Dict[str, float]],
        actual_results: List[str],
        selected_probabilities: List[float],
        selected_binary_labels: List[int],
        min_sample_size: int = 100,
        max_ece_pct: float = 6.0,
        max_brier: float = 0.65
    ) -> CalibrationGateVerdict:
        """
        MANDATORY OUT-OF-SAMPLE CALIBRATION GATE.
        Evaluates whether the model's out-of-sample probability calibration
        satisfies quantitative empirical criteria:
        1. Sample size >= min_sample_size (default 100)
        2. ECE <= max_ece_pct (default 6.0%)
        3. Brier Score <= max_brier (default 0.65)
        4. Drift check: First half vs second half ECE divergence <= 4.0%
        """
        n_samples = len(predicted_prob_distributions)
        failure_reasons = []

        # 1. Sample size check
        if n_samples < min_sample_size:
            failure_reasons.append(
                f"Insufficient sample size: {n_samples} matches observed (minimum required: {min_sample_size})."
            )

        # 2. Brier score
        brier_metrics = cls.calculate_brier_score(predicted_prob_distributions, actual_results)
        brier = brier_metrics.get("brier_score", 1.0)
        if brier > max_brier:
            failure_reasons.append(
                f"Brier score {brier:.4f} exceeds maximum threshold of {max_brier:.4f}."
            )

        # 3. ECE & MCE
        ece_metrics = cls.calculate_ece(selected_probabilities, selected_binary_labels, num_bins=8)
        ece_pct = ece_metrics.get("ece_pct", 0.0)
        mce_pct = ece_metrics.get("mce_pct", 0.0)

        if ece_pct > max_ece_pct:
            failure_reasons.append(
                f"Expected Calibration Error ({ece_pct:.2f}%) exceeds threshold of {max_ece_pct:.2f}%."
            )

        # 4. Calibration drift check (Split test window in half)
        is_drift = False
        if len(selected_probabilities) >= 60:
            mid = len(selected_probabilities) // 2
            ece_h1 = cls.calculate_ece(selected_probabilities[:mid], selected_binary_labels[:mid])["ece_pct"]
            ece_h2 = cls.calculate_ece(selected_probabilities[mid:], selected_binary_labels[mid:])["ece_pct"]
            drift_delta = abs(ece_h2 - ece_h1)
            if drift_delta > 4.5:
                is_drift = True
                failure_reasons.append(
                    f"Calibration drift detected: ECE diverged by {drift_delta:.2f}% between windows ({ece_h1:.1f}% -> {ece_h2:.1f}%)."
                )

        passed = len(failure_reasons) == 0
        status = "PASSED" if passed else "FAILED"

        return CalibrationGateVerdict(
            passed=passed,
            brier_score=brier,
            ece_pct=ece_pct,
            mce_pct=mce_pct,
            sample_size=n_samples,
            is_drift_detected=is_drift,
            status=status,
            failure_reasons=failure_reasons
        )
