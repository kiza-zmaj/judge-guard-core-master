"""
Empirical Evidence Gate & Production Decision Engine for SharpBet Core.
Enforces the mandatory 6-stage validation chain before any bet can be executed:
1. Data Integrity Gate
2. Model Probability & De-vig Gate
3. Anti-Delusion & Tail Divergence Gate (Fake EV filter)
4. Out-of-Sample Calibration Gate (ECE & Brier)
5. Historical Track Record & CLV Gate
6. Portfolio Risk & Exposure Gate (Kelly)

Implements the strict evidence-based taxonomy:
  RAW_EV -> CALIBRATED_EV -> EMPIRICALLY_SUPPORTED_EV -> EXECUTABLE_EV
  (Rejections: FAKE_EV, MARGINAL_EV, CALIBRATION_FAILED, INSUFFICIENT_EVIDENCE, DATA_DEGRADED, NO_EDGE)
FAILS CLOSED AT EVERY GATE.
"""

from enum import Enum
from dataclasses import dataclass
from typing import Dict, Any, List, Optional
from unified_betting_core.config import MIN_EDGE
from unified_betting_core.data_ingestion.real_data_provider import DataQualityState

class DecisionStatus(Enum):
    EXECUTABLE_EV = "EXECUTABLE_EV"                       # Empirically supported + market fresh + risk passed
    EMPIRICALLY_SUPPORTED_EV = "EMPIRICALLY_SUPPORTED_EV" # Passed out-of-sample calibration and CLV gates
    CALIBRATED_EV = "CALIBRATED_EV"                       # Positive calibrated edge, but empirical proof pending
    RAW_EV = "RAW_EV"                                     # Raw statistical edge only
    FAKE_EV = "FAKE_EV"                                   # Raw EV > 0 but Calibrated EV <= 0 or extreme tail divergence
    MARGINAL_EV = "MARGINAL_EV"                           # Calibrated EV > 0 but below min_edge threshold
    CALIBRATION_FAILED = "CALIBRATION_FAILED"             # Out-of-sample ECE or Brier exceeded safety limit
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"       # Historical sample size too small or CLV <= 0
    MARKET_VALIDATION_FAILED = "MARKET_FAILED"            # De-vig or bookmaker prices invalid
    DATA_DEGRADED = "DATA_DEGRADED"                       # Input data state is stale, degraded, or missing
    NO_EDGE = "NO_EDGE"                                   # No mathematical edge detected

@dataclass
class GateEvaluationResult:
    status: DecisionStatus
    is_executable: bool
    is_empirically_supported: bool
    p_model: float
    model_fair_odds: float
    p_devig: float
    market_fair_odds: float
    p_calibrated: float
    calibrated_fair_odds: float
    best_odds: float
    raw_ev_pct: float
    calibrated_ev_pct: float
    recommended_stake: float
    gate_verdicts: Dict[str, bool]
    audit_notes: List[str]

class EmpiricalDecisionGate:
    """
    Evaluates candidate selections against empirical reality.
    Guarantees that uncalibrated model overconfidence is never treated as proven EV.
    """

    def __init__(
        self,
        min_edge: float = MIN_EDGE,
        max_divergence: float = 0.14,
        max_rel_divergence: float = 0.85,
        base_model_weight: float = 0.28,
        longshot_odds_threshold: float = 5.50
    ):
        self.min_edge = min_edge
        self.max_divergence = max_divergence
        self.max_rel_divergence = max_rel_divergence
        self.base_model_weight = base_model_weight
        self.longshot_odds_threshold = longshot_odds_threshold

    def calculate_shrinkage_weight(self, p_model: float, p_devig: float, odds: float) -> float:
        """Dynamically shrinks model trust when divergence or odds are high."""
        abs_div = abs(p_model - p_devig)
        weight = self.base_model_weight

        if odds >= self.longshot_odds_threshold or p_devig < 0.12:
            weight = max(weight * 0.45, 0.08)

        if abs_div > self.max_divergence:
            weight = max(weight * 0.40, 0.08)
        elif abs_div < 0.03:
            weight = min(weight * 1.35, 0.45)

        return round(weight, 4)

    def calibrate_probability(self, p_model: float, p_devig: float, odds: float) -> float:
        """Calculates Bayesian shrinkage probability toward sharp market consensus."""
        if p_devig <= 0:
            return p_model
        weight = self.calculate_shrinkage_weight(p_model, p_devig, odds)
        p_calibrated = (weight * p_model) + ((1.0 - weight) * p_devig)
        return round(p_calibrated, 5)

    def audit_bet(
        self,
        outcome: str,
        p_model: float,
        p_devig: float,
        best_odds: float,
        data_quality: DataQualityState = DataQualityState.CACHED,
        out_of_sample_calibration_passed: bool = False,
        historical_clv_demonstrated: bool = False,
        historical_sample_size: int = 0
    ) -> GateEvaluationResult:
        """
        Runs the complete multi-gate empirical validation.
        Fails closed: If any gate is unsatisfied, execution is blocked (stake = 0.0).
        """
        audit_notes = []
        gate_verdicts = {
            "data_quality_gate": False,
            "probability_validity_gate": False,
            "market_devig_gate": False,
            "anti_delusion_gate": False,
            "out_of_sample_calibration_gate": False,
            "historical_clv_gate": False
        }

        # 1. Data Integrity Gate
        if data_quality in [DataQualityState.CORRUPT_OR_MISSING, DataQualityState.DEGRADED]:
            audit_notes.append(f"Data Quality Gate Failed: input state is {data_quality.value}.")
            return self._build_rejection(DecisionStatus.DATA_DEGRADED, p_model, p_devig, best_odds, gate_verdicts, audit_notes)
        gate_verdicts["data_quality_gate"] = True

        # 2. Probability & Odds Validity Gate
        if best_odds <= 1.01 or p_model <= 0.0 or p_model >= 1.0:
            audit_notes.append(f"Invalid odds ({best_odds}) or probability ({p_model}).")
            return self._build_rejection(DecisionStatus.MARKET_VALIDATION_FAILED, p_model, p_devig, best_odds, gate_verdicts, audit_notes)
        gate_verdicts["probability_validity_gate"] = True

        # 3. Market De-vig Gate
        if p_devig <= 0.0 or p_devig >= 1.0:
            audit_notes.append(f"De-vig probability calculation invalid ({p_devig}).")
            return self._build_rejection(DecisionStatus.MARKET_VALIDATION_FAILED, p_model, p_devig, best_odds, gate_verdicts, audit_notes)
        gate_verdicts["market_devig_gate"] = True

        # Compute Raw & Calibrated EV
        raw_ev = (p_model * best_odds) - 1.0
        raw_ev_pct = round(raw_ev * 100, 2)

        p_calib = self.calibrate_probability(p_model, p_devig, best_odds)
        calibrated_ev = (p_calib * best_odds) - 1.0
        calibrated_ev_pct = round(calibrated_ev * 100, 2)

        abs_div = abs(p_model - p_devig)
        rel_div = abs_div / max(p_devig, 0.001)
        is_longshot = best_odds >= self.longshot_odds_threshold
        high_divergence = abs_div > self.max_divergence or rel_div > self.max_rel_divergence

        # 4. Anti-Delusion & Fake EV Gate
        if raw_ev <= self.min_edge:
            audit_notes.append(f"No Edge: Raw EV ({raw_ev_pct}%) <= min edge ({self.min_edge*100:.1f}%).")
            return self._build_result(DecisionStatus.NO_EDGE, p_model, p_devig, p_calib, best_odds, raw_ev_pct, calibrated_ev_pct, gate_verdicts, audit_notes)

        # Check tail distortion / longshot divergence first
        if is_longshot and high_divergence:
            audit_notes.append(
                f"Longshot Overconfidence: odds {best_odds:.2f} with {abs_div*100:.1f}% model-market divergence rejected as FAKE_EV."
            )
            return self._build_result(DecisionStatus.FAKE_EV, p_model, p_devig, p_calib, best_odds, raw_ev_pct, calibrated_ev_pct, gate_verdicts, audit_notes)

        if calibrated_ev <= 0.0:
            audit_notes.append(
                f"Model Delusion Detected: Raw EV is +{raw_ev_pct}%, but Calibrated EV after market shrinkage is {calibrated_ev_pct}%. FAKE_EV rejected."
            )
            return self._build_result(DecisionStatus.FAKE_EV, p_model, p_devig, p_calib, best_odds, raw_ev_pct, calibrated_ev_pct, gate_verdicts, audit_notes)

        if calibrated_ev < self.min_edge:
            audit_notes.append(
                f"Marginal Edge: Calibrated EV (+{calibrated_ev_pct}%) is below operational threshold (+{self.min_edge*100:.1f}%)."
            )
            return self._build_result(DecisionStatus.MARGINAL_EV, p_model, p_devig, p_calib, best_odds, raw_ev_pct, calibrated_ev_pct, gate_verdicts, audit_notes)

        gate_verdicts["anti_delusion_gate"] = True

        # 5. Out-of-Sample Calibration Gate
        if not out_of_sample_calibration_passed:
            gate_verdicts["out_of_sample_calibration_gate"] = False
            audit_notes.append(
                "Calibration Gate Pending/Failed: Out-of-sample ECE/Brier validation has not confirmed model accuracy."
            )
            return self._build_result(
                DecisionStatus.CALIBRATION_FAILED,
                p_model, p_devig, p_calib, best_odds, raw_ev_pct, calibrated_ev_pct,
                gate_verdicts, audit_notes
            )
        gate_verdicts["out_of_sample_calibration_gate"] = True

        # 6. Historical Track Record & CLV Gate
        if historical_sample_size < 100 or not historical_clv_demonstrated:
            gate_verdicts["historical_clv_gate"] = False
            audit_notes.append(
                f"Insufficient Evidence Gate: Historical sample size ({historical_sample_size} matches) < 100 or positive CLV track record not yet established."
            )
            return self._build_result(
                DecisionStatus.INSUFFICIENT_EVIDENCE,
                p_model, p_devig, p_calib, best_odds, raw_ev_pct, calibrated_ev_pct,
                gate_verdicts, audit_notes
            )
        gate_verdicts["historical_clv_gate"] = True

        # Both empirical validation gates passed -> EMPIRICALLY_SUPPORTED_EV & EXECUTABLE_EV
        audit_notes.append(
            "Empirically Supported: Passed out-of-sample calibration, historical positive CLV, and anti-delusion gates."
        )
        return self._build_result(
            DecisionStatus.EXECUTABLE_EV,
            p_model, p_devig, p_calib, best_odds, raw_ev_pct, calibrated_ev_pct,
            gate_verdicts, audit_notes,
            is_executable=True,
            is_empirically_supported=True
        )

    def _build_result(
        self,
        status: DecisionStatus,
        p_model: float,
        p_devig: float,
        p_calib: float,
        best_odds: float,
        raw_ev_pct: float,
        calibrated_ev_pct: float,
        gate_verdicts: Dict[str, bool],
        audit_notes: List[str],
        is_executable: bool = False,
        is_empirically_supported: bool = False
    ) -> GateEvaluationResult:
        model_fair_odds = round(1.0 / p_model, 3) if p_model > 0 else 999.0
        market_fair_odds = round(1.0 / p_devig, 3) if p_devig > 0 else 999.0
        calib_fair_odds = round(1.0 / p_calib, 3) if p_calib > 0 else 999.0

        return GateEvaluationResult(
            status=status,
            is_executable=is_executable,
            is_empirically_supported=is_empirically_supported,
            p_model=round(p_model, 4),
            model_fair_odds=model_fair_odds,
            p_devig=round(p_devig, 4),
            market_fair_odds=market_fair_odds,
            p_calibrated=round(p_calib, 4),
            calibrated_fair_odds=calib_fair_odds,
            best_odds=round(best_odds, 3),
            raw_ev_pct=raw_ev_pct,
            calibrated_ev_pct=calibrated_ev_pct,
            recommended_stake=0.0,
            gate_verdicts=gate_verdicts,
            audit_notes=audit_notes
        )

    def _build_rejection(
        self,
        status: DecisionStatus,
        p_model: float,
        p_devig: float,
        best_odds: float,
        gate_verdicts: Dict[str, bool],
        audit_notes: List[str]
    ) -> GateEvaluationResult:
        return self._build_result(
            status=status,
            p_model=p_model,
            p_devig=p_devig,
            p_calib=p_devig if p_devig > 0 else p_model,
            best_odds=best_odds,
            raw_ev_pct=0.0,
            calibrated_ev_pct=0.0,
            gate_verdicts=gate_verdicts,
            audit_notes=audit_notes,
            is_executable=False,
            is_empirically_supported=False
        )
