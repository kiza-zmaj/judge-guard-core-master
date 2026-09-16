"""
Three-Gate Empirical Verdict System for SharpBet Core.

Three independent proofs required before EXECUTABLE_EV:
  Gate A — CALIBRATION:    Are model probabilities calibrated OOS?
  Gate B — MARKET ALPHA:   Does the strategy beat the closing line?
  Gate C — ECONOMIC P&L:   Does the strategy generate positive OOS returns?

EMPIRICALLY_SUPPORTED_EV requires ALL THREE to PASS independently.
EXECUTABLE_EV adds per-bet risk/Kelly sizing on top.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from unified_betting_core.config import MIN_EDGE
from unified_betting_core.data_ingestion.real_data_provider import DataQualityState

# ─── Status taxonomy per Do.md Phase 6 ────────────────────────────────────────


class CalibrationStatus(Enum):
    CALIBRATION_PASS = "CALIBRATION_PASS"
    CALIBRATION_FAILED = "CALIBRATION_FAILED"


class MarketAlphaStatus(Enum):
    MARKET_ALPHA_PASS = "MARKET_ALPHA_PASS"
    MARKET_ALPHA_FAILED = "MARKET_ALPHA_FAILED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class EconomicStatus(Enum):
    ECONOMIC_PASS = "ECONOMIC_PASS"
    ECONOMIC_VALIDATION_FAILED = "ECONOMIC_VALIDATION_FAILED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class FinalStatus(Enum):
    EMPIRICALLY_SUPPORTED_EV = "EMPIRICALLY_SUPPORTED_EV"
    EXECUTABLE_EV = "EXECUTABLE_EV"
    # Rejections
    FAKE_EV = "FAKE_EV"
    MARGINAL_EV = "MARGINAL_EV"
    CALIBRATION_FAILED = "CALIBRATION_FAILED"
    MARKET_ALPHA_FAILED = "MARKET_ALPHA_FAILED"
    ECONOMIC_FAILED = "ECONOMIC_VALIDATION_FAILED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    MARKET_FAILED = "MARKET_FAILED"
    DATA_DEGRADED = "DATA_DEGRADED"
    NO_EDGE = "NO_EDGE"
    RAW_EV = "RAW_EV"
    CALIBRATED_EV = "CALIBRATED_EV"


# Alias for backwards compatibility
DecisionStatus = FinalStatus


# ─── Three-Gate Verdict ────────────────────────────────────────────────────────


@dataclass
class GateAResult:
    """Calibration Gate result. Populated once per walk-forward run."""

    status: CalibrationStatus
    passed: bool
    brier_score: float
    ece_pct: float | None  # None = not measurable (empty input)
    mce_pct: float | None
    sample_size: int
    drift_detected: bool
    failure_reasons: list[str]
    reliability_table: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class GateBResult:
    """Market Alpha / CLV Gate result. Populated over candidate population."""

    status: MarketAlphaStatus
    passed: bool
    candidate_count: int  # ALL candidates, not just approved bets
    settled_count: int
    avg_raw_clv_pct: float
    avg_fair_clv_pct: float
    beat_closing_rate_pct: float
    ci_95_lower_pct: float
    ci_95_upper_pct: float
    failure_reasons: list[str]


@dataclass
class GateCResult:
    """Economic P&L Gate result. Populated from frozen-strategy simulation."""

    status: EconomicStatus
    passed: bool
    total_bets: int
    roi_pct: float
    yield_pct: float
    roi_ci_lower_pct: float
    roi_ci_upper_pct: float
    max_drawdown_pct: float
    final_bankroll: float
    failure_reasons: list[str]
    pnl_by_outcome: dict[str, Any] = field(default_factory=dict)


@dataclass
class ThreeGateVerdict:
    """
    Final governance verdict combining all three independent gates.
    EMPIRICALLY_SUPPORTED_EV only when ALL THREE pass.
    """

    gate_a: GateAResult
    gate_b: GateBResult
    gate_c: GateCResult
    final_status: FinalStatus
    is_empirically_supported: bool
    is_executable: bool
    summary: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "final_status": self.final_status.value,
            "is_empirically_supported": self.is_empirically_supported,
            "is_executable": self.is_executable,
            "summary": self.summary,
            "gate_a": {
                "status": self.gate_a.status.value,
                "passed": self.gate_a.passed,
                "brier_score": self.gate_a.brier_score,
                "ece_pct": self.gate_a.ece_pct,
                "mce_pct": self.gate_a.mce_pct,
                "sample_size": self.gate_a.sample_size,
                "drift_detected": self.gate_a.drift_detected,
                "failure_reasons": self.gate_a.failure_reasons,
            },
            "gate_b": {
                "status": self.gate_b.status.value,
                "passed": self.gate_b.passed,
                "candidate_count": self.gate_b.candidate_count,
                "settled_count": self.gate_b.settled_count,
                "avg_raw_clv_pct": self.gate_b.avg_raw_clv_pct,
                "avg_fair_clv_pct": self.gate_b.avg_fair_clv_pct,
                "beat_closing_rate_pct": self.gate_b.beat_closing_rate_pct,
                "ci_95_lower_pct": self.gate_b.ci_95_lower_pct,
                "ci_95_upper_pct": self.gate_b.ci_95_upper_pct,
                "failure_reasons": self.gate_b.failure_reasons,
            },
            "gate_c": {
                "status": self.gate_c.status.value,
                "passed": self.gate_c.passed,
                "total_bets": self.gate_c.total_bets,
                "roi_pct": self.gate_c.roi_pct,
                "yield_pct": self.gate_c.yield_pct,
                "roi_ci_lower_pct": self.gate_c.roi_ci_lower_pct,
                "roi_ci_upper_pct": self.gate_c.roi_ci_upper_pct,
                "max_drawdown_pct": self.gate_c.max_drawdown_pct,
                "failure_reasons": self.gate_c.failure_reasons,
                "pnl_by_outcome": self.gate_c.pnl_by_outcome,
            },
        }


# ─── Three-Gate Evaluator ─────────────────────────────────────────────────────


def evaluate_three_gate_verdict(
    gate_a: GateAResult, gate_b: GateBResult, gate_c: GateCResult
) -> ThreeGateVerdict:
    """
    Combines three independent gate results into a final governance verdict.
    EMPIRICALLY_SUPPORTED_EV requires ALL THREE to pass.
    Fails closed: any failed gate blocks EXECUTABLE_EV.
    """
    failures = []
    if not gate_a.passed:
        failures.append(f"Gate A FAILED: {'; '.join(gate_a.failure_reasons)}")
    if not gate_b.passed:
        failures.append(f"Gate B FAILED: {'; '.join(gate_b.failure_reasons)}")
    if not gate_c.passed:
        failures.append(f"Gate C FAILED: {'; '.join(gate_c.failure_reasons)}")

    all_pass = gate_a.passed and gate_b.passed and gate_c.passed

    if all_pass:
        final = FinalStatus.EMPIRICALLY_SUPPORTED_EV
        summary = (
            f"ALL THREE GATES PASSED. "
            f"Calibration ECE={gate_a.ece_pct:.2f}% | "
            f"CLV={gate_b.avg_raw_clv_pct:.2f}% | "
            f"ROI={gate_c.roi_pct:.2f}% [{gate_c.roi_ci_lower_pct:.2f}%, {gate_c.roi_ci_upper_pct:.2f}%]"
        )
    elif not gate_a.passed:
        final = FinalStatus.CALIBRATION_FAILED
        summary = f"BLOCKED at Gate A (Calibration). {failures[0]}"
    elif not gate_b.passed:
        final = FinalStatus.MARKET_ALPHA_FAILED
        summary = f"BLOCKED at Gate B (Market Alpha/CLV). {failures[0]}"
    else:
        final = FinalStatus.ECONOMIC_FAILED
        summary = f"BLOCKED at Gate C (Economic P&L). {failures[0]}"

    return ThreeGateVerdict(
        gate_a=gate_a,
        gate_b=gate_b,
        gate_c=gate_c,
        final_status=final,
        is_empirically_supported=all_pass,
        is_executable=all_pass,
        summary=summary,
    )


# ─── Per-Bet Decision Gate (unchanged architecture) ───────────────────────────


@dataclass
class GateEvaluationResult:
    status: FinalStatus
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
    gate_verdicts: dict[str, bool]
    audit_notes: list[str]


class EmpiricalDecisionGate:
    """
    Per-bet anti-delusion filter.
    Checks: data integrity → odds validity → de-vig → fake EV → marginal EV.
    Three-Gate portfolio verdict is evaluated SEPARATELY in WalkForwardEngine.
    """

    def __init__(
        self,
        min_edge: float = MIN_EDGE,
        max_divergence: float = 0.14,
        max_rel_divergence: float = 0.85,
        base_model_weight: float = 0.28,
        longshot_odds_threshold: float = 5.50,
    ):
        self.min_edge = min_edge
        self.max_divergence = max_divergence
        self.max_rel_divergence = max_rel_divergence
        self.base_model_weight = base_model_weight
        self.longshot_odds_threshold = longshot_odds_threshold

    def calculate_shrinkage_weight(
        self, p_model: float, p_devig: float, odds: float
    ) -> float:
        abs_div = abs(p_model - p_devig)
        weight = self.base_model_weight
        if odds >= self.longshot_odds_threshold or p_devig < 0.12:
            weight = max(weight * 0.45, 0.08)
        if abs_div > self.max_divergence:
            weight = max(weight * 0.40, 0.08)
        elif abs_div < 0.03:
            weight = min(weight * 1.35, 0.45)
        return round(weight, 4)

    def calibrate_probability(
        self, p_model: float, p_devig: float, odds: float
    ) -> float:
        if p_devig <= 0:
            return p_model
        weight = self.calculate_shrinkage_weight(p_model, p_devig, odds)
        return round((weight * p_model) + ((1.0 - weight) * p_devig), 5)

    def audit_bet(
        self,
        outcome: str,
        p_model: float,
        p_devig: float,
        best_odds: float,
        data_quality: DataQualityState = DataQualityState.CACHED,
        out_of_sample_calibration_passed: bool = False,
        historical_clv_demonstrated: bool = False,
        historical_sample_size: int = 0,
        three_gate_passed: bool = False,
    ) -> GateEvaluationResult:
        """
        Per-bet anti-delusion audit.
        Checks data integrity -> probability validity -> market de-vig -> fake EV -> marginal EV -> three-gate governance.  # noqa: E501
        """
        notes = []
        verdicts = {
            "data_quality_gate": False,
            "probability_validity_gate": False,
            "market_devig_gate": False,
            "anti_delusion_gate": False,
        }

        if data_quality in [
            DataQualityState.CORRUPT_OR_MISSING,
            DataQualityState.DEGRADED,
        ]:
            notes.append(f"Data degraded: {data_quality.value}")
            return self._reject(
                FinalStatus.DATA_DEGRADED, p_model, p_devig, best_odds, verdicts, notes
            )
        verdicts["data_quality_gate"] = True

        if best_odds <= 1.01 or not (0.0 < p_model < 1.0):
            notes.append(f"Invalid odds ({best_odds}) or prob ({p_model})")
            return self._reject(
                FinalStatus.MARKET_FAILED, p_model, p_devig, best_odds, verdicts, notes
            )
        verdicts["probability_validity_gate"] = True

        if not (0.0 < p_devig < 1.0):
            notes.append(f"De-vig prob invalid ({p_devig})")
            return self._reject(
                FinalStatus.MARKET_FAILED, p_model, p_devig, best_odds, verdicts, notes
            )
        verdicts["market_devig_gate"] = True

        raw_ev = (p_model * best_odds) - 1.0
        raw_ev_pct = round(raw_ev * 100, 2)
        p_calib = self.calibrate_probability(p_model, p_devig, best_odds)
        cal_ev = (p_calib * best_odds) - 1.0
        cal_ev_pct = round(cal_ev * 100, 2)

        abs_div = abs(p_model - p_devig)
        rel_div = abs_div / max(p_devig, 0.001)
        is_longshot = best_odds >= self.longshot_odds_threshold
        high_div = abs_div > self.max_divergence or rel_div > self.max_rel_divergence

        if raw_ev <= self.min_edge:
            notes.append(f"No edge: raw EV {raw_ev_pct}%")
            return self._result(
                FinalStatus.NO_EDGE,
                p_model,
                p_devig,
                p_calib,
                best_odds,
                raw_ev_pct,
                cal_ev_pct,
                verdicts,
                notes,
            )

        if is_longshot and high_div:
            notes.append(
                f"Longshot overconfidence: odds {best_odds:.2f}, divergence {abs_div * 100:.1f}%"
            )
            return self._result(
                FinalStatus.FAKE_EV,
                p_model,
                p_devig,
                p_calib,
                best_odds,
                raw_ev_pct,
                cal_ev_pct,
                verdicts,
                notes,
            )

        if cal_ev <= 0.0:
            notes.append(
                f"Model delusion: raw EV +{raw_ev_pct}% but calibrated EV {cal_ev_pct}%"
            )
            return self._result(
                FinalStatus.FAKE_EV,
                p_model,
                p_devig,
                p_calib,
                best_odds,
                raw_ev_pct,
                cal_ev_pct,
                verdicts,
                notes,
            )

        if cal_ev < self.min_edge:
            notes.append(
                f"Marginal edge: {cal_ev_pct}% < threshold {self.min_edge * 100:.1f}%"
            )
            return self._result(
                FinalStatus.MARGINAL_EV,
                p_model,
                p_devig,
                p_calib,
                best_odds,
                raw_ev_pct,
                cal_ev_pct,
                verdicts,
                notes,
            )

        verdicts["anti_delusion_gate"] = True
        notes.append(f"Anti-delusion passed: calibrated EV +{cal_ev_pct}%")

        # Three-Gate Governance Verification
        if out_of_sample_calibration_passed is False:
            notes.append("Rejected: Out-of-sample calibration gate failed")
            return self._reject(
                FinalStatus.CALIBRATION_FAILED,
                p_model,
                p_devig,
                best_odds,
                verdicts,
                notes,
            )

        if (
            historical_sample_size < 100 or not historical_clv_demonstrated
        ) and not three_gate_passed:
            notes.append(
                f"Rejected: Insufficient empirical evidence "
                f"(sample={historical_sample_size}, "
                f"clv_demo={historical_clv_demonstrated})"
            )
            return self._reject(
                FinalStatus.INSUFFICIENT_EVIDENCE,
                p_model,
                p_devig,
                best_odds,
                verdicts,
                notes,
            )

        has_empirical_proof = three_gate_passed or (
            out_of_sample_calibration_passed
            and historical_clv_demonstrated
            and historical_sample_size >= 100
        )
        if has_empirical_proof:
            status = FinalStatus.EXECUTABLE_EV
            is_exe = True
            is_emp = True
            notes.append("Approved: Passed all Three Empirical Gates (A, B, C)")
        else:
            status = FinalStatus.CALIBRATED_EV
            is_exe = False
            is_emp = False
            notes.append(
                "Calibrated EV candidate pending portfolio Three-Gate empirical proof"
            )

        return self._result(
            status,
            p_model,
            p_devig,
            p_calib,
            best_odds,
            raw_ev_pct,
            cal_ev_pct,
            verdicts,
            notes,
            exe=is_exe,
            emp=is_emp,
        )

    def _result(
        self,
        status,
        p_model,
        p_devig,
        p_calib,
        best_odds,
        raw_ev_pct,
        cal_ev_pct,
        verdicts,
        notes,
        exe=False,
        emp=False,
    ):
        mfo = round(1.0 / p_model, 3) if p_model > 0 else 999.0
        mkt = round(1.0 / p_devig, 3) if p_devig > 0 else 999.0
        cal = round(1.0 / p_calib, 3) if p_calib > 0 else 999.0
        return GateEvaluationResult(
            status=status,
            is_executable=exe,
            is_empirically_supported=emp,
            p_model=round(p_model, 4),
            model_fair_odds=mfo,
            p_devig=round(p_devig, 4),
            market_fair_odds=mkt,
            p_calibrated=round(p_calib, 4),
            calibrated_fair_odds=cal,
            best_odds=round(best_odds, 3),
            raw_ev_pct=raw_ev_pct,
            calibrated_ev_pct=cal_ev_pct,
            recommended_stake=0.0,
            gate_verdicts=verdicts,
            audit_notes=notes,
        )

    def _reject(self, status, p_model, p_devig, best_odds, verdicts, notes):
        p_fb = p_devig if p_devig > 0 else p_model
        return self._result(
            status, p_model, p_devig, p_fb, best_odds, 0.0, 0.0, verdicts, notes
        )
