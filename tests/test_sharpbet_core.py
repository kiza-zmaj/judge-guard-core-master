"""
Comprehensive Automated Test Suite for SharpBet Core.
Covers:
1. Mathematical precision (Power & Multiplicative De-vig, Fair Odds, EV, Kelly, CLV)
2. Calibration diagnostics (Multi-class Brier Score, ECE, Reliability Binning, Temperature Scaling)
3. Data integrity & degraded state handling
4. Decision Gate fail-closed enforcement (Fake EV, Calibration Failure, Insufficient Evidence)
5. Zero Future Leakage Verification
"""

import math
import pytest
import numpy as np
import pandas as pd
from unified_betting_core.decision_engine.devig_engine import DevigEngine
from unified_betting_core.decision_engine.ev_calculator import EVCalculator
from unified_betting_core.decision_engine.kelly_criterion import KellyCriterion
from unified_betting_core.decision_engine.clv_calculator import CLVCalculator, CLVState
from unified_betting_core.decision_engine.empirical_gate import EmpiricalDecisionGate, DecisionStatus
from unified_betting_core.models.calibration import ModelCalibration, TemperatureScaler
from unified_betting_core.data_ingestion.real_data_provider import DataQualityState

# =====================================================================
# 1. MATHEMATICAL TESTS
# =====================================================================

def test_devig_overround():
    """Verify that bookmaker overround is accurately calculated."""
    odds = {"home": 1.90, "away": 1.90}
    inv_sum, margin = DevigEngine.calculate_overround(odds)
    assert round(inv_sum, 4) == 1.0526
    assert round(margin, 4) == 0.0526

def test_devig_power_and_fair_odds():
    """Verify that Power method de-vig sums to strictly 1.0 and strips vig."""
    odds = {"home": 2.10, "draw": 3.40, "away": 3.60}
    devig_probs = DevigEngine.devig_power(odds)
    assert round(sum(devig_probs.values()), 4) == 1.0
    fair_odds = DevigEngine.fair_odds(devig_probs)
    assert fair_odds["home"] > odds["home"]
    assert fair_odds["draw"] > odds["draw"]
    assert fair_odds["away"] > odds["away"]

def test_ev_calculation():
    """Verify mathematical EV formula: (p * odds) - 1.0."""
    calc = EVCalculator(min_edge=0.05)
    probs = {"home": 0.50, "draw": 0.25, "away": 0.25}
    odds = {"home_odds": 2.20, "draw_odds": 4.00, "away_odds": 4.00}
    evals = calc.evaluate_outcomes(probs, odds)

    home_eval = next(e for e in evals if e["outcome"] == "home")
    assert home_eval["edge"] == 0.10
    assert home_eval["edge_pct"] == 10.0
    assert home_eval["is_value_bet"] is True

def test_kelly_criterion_stake():
    """Verify Fractional Kelly staking formula and safety cap."""
    kelly = KellyCriterion(fraction=0.5, min_edge=0.05, max_bankroll_pct=0.10)
    stake = kelly.calculate_stake(0.55, 2.00, 1000.0)
    assert stake == 50.00

    huge_stake = kelly.calculate_stake(0.90, 2.00, 1000.0)
    assert huge_stake == 100.00  # Capped at 10%

def test_clv_calculation_real_vs_pending():
    """Verify that CLV handles retrospective settlement vs pending kickoff."""
    settled = CLVCalculator.calculate_clv(placed_odds=2.20, closing_odds=2.00)
    assert settled["state"] == CLVState.SETTLED.value
    assert settled["raw_clv_pct"] == 10.0
    assert settled["beat_closing"] is True

    pending = CLVCalculator.calculate_clv(placed_odds=2.20, closing_odds=None)
    assert pending["state"] == CLVState.PENDING_CLOSE.value
    assert pending["raw_clv"] is None
    assert pending["beat_closing"] is False

# =====================================================================
# 2. CALIBRATION TESTS
# =====================================================================

def test_brier_score_precision():
    """Verify multi-class Brier score calculation."""
    preds = [{"home": 1.0, "draw": 0.0, "away": 0.0}]
    actuals = ["home"]
    res = ModelCalibration.calculate_brier_score(preds, actuals)
    assert res["brier_score"] == 0.0

    wrong_preds = [{"home": 0.0, "draw": 1.0, "away": 0.0}]
    wrong_res = ModelCalibration.calculate_brier_score(wrong_preds, actuals)
    assert wrong_res["brier_score"] == 2.0

def test_ece_calculation():
    """Verify Expected Calibration Error (ECE)."""
    probs = [0.25] * 40 + [0.75] * 40
    labels = [1] * 10 + [0] * 30 + [1] * 30 + [0] * 10
    ece_res = ModelCalibration.calculate_ece(probs, labels, num_bins=2)
    assert ece_res["ece_pct"] == 0.0

def test_temperature_scaling_optimization():
    """Verify that TemperatureScaler optimizes cross-entropy on validation data."""
    scaler = TemperatureScaler(default_temp=1.0)
    preds = [
        {"home": 0.95, "draw": 0.03, "away": 0.02},
        {"home": 0.90, "draw": 0.05, "away": 0.05}
    ] * 20
    acts = (["home"] * 14 + ["draw"] * 3 + ["away"] * 3) * 2
    fitted_t = scaler.fit(preds, acts)
    assert fitted_t > 1.0
    scaled = scaler.scale({"home": 0.90, "draw": 0.05, "away": 0.05})
    assert scaled["home"] < 0.90

# =====================================================================
# 3. DECISION GATE & FAIL-CLOSED TESTS
# =====================================================================

def test_gate_rejects_fake_ev_model_delusion():
    """Verify that extreme tail divergence is rejected as FAKE_EV."""
    gate = EmpiricalDecisionGate(min_edge=0.05)
    result = gate.audit_bet(
        outcome="away",
        p_model=0.25,
        p_devig=0.089,
        best_odds=10.0,
        data_quality=DataQualityState.LIVE,
        out_of_sample_calibration_passed=True,
        historical_clv_demonstrated=True,
        historical_sample_size=200
    )
    assert result.status == DecisionStatus.FAKE_EV
    assert result.is_executable is False
    assert result.recommended_stake == 0.0

def test_gate_rejects_when_calibration_fails():
    """Verify that a positive EV candidate is blocked if out-of-sample calibration gate failed."""
    gate = EmpiricalDecisionGate(min_edge=0.05)
    # p_model=0.50, p_devig=0.45, best_odds=2.40 -> p_calib ~ 0.468 -> calibrated EV = +12.3%
    result = gate.audit_bet(
        outcome="home",
        p_model=0.50,
        p_devig=0.45,
        best_odds=2.40,
        data_quality=DataQualityState.LIVE,
        out_of_sample_calibration_passed=False, # Calibration Gate FAILED
        historical_clv_demonstrated=True,
        historical_sample_size=200
    )
    assert result.status == DecisionStatus.CALIBRATION_FAILED
    assert result.is_executable is False
    assert result.recommended_stake == 0.0

def test_gate_rejects_when_sample_size_insufficient():
    """Verify that insufficient historical sample size blocks execution."""
    gate = EmpiricalDecisionGate(min_edge=0.05)
    # p_model=0.50, p_devig=0.45, best_odds=2.40 -> Calibrated EV > 5%
    result = gate.audit_bet(
        outcome="home",
        p_model=0.50,
        p_devig=0.45,
        best_odds=2.40,
        data_quality=DataQualityState.LIVE,
        out_of_sample_calibration_passed=True,
        historical_clv_demonstrated=False, # Historical CLV proof missing
        historical_sample_size=30          # Insufficient sample (< 100)
    )
    assert result.status == DecisionStatus.INSUFFICIENT_EVIDENCE
    assert result.is_executable is False
    assert result.recommended_stake == 0.0

def test_gate_rejects_degraded_data():
    """Verify that degraded data quality blocks bet execution."""
    gate = EmpiricalDecisionGate(min_edge=0.05)
    result = gate.audit_bet(
        outcome="home",
        p_model=0.50,
        p_devig=0.40,
        best_odds=2.50,
        data_quality=DataQualityState.DEGRADED,
        out_of_sample_calibration_passed=True,
        historical_clv_demonstrated=True,
        historical_sample_size=200
    )
    assert result.status == DecisionStatus.DATA_DEGRADED
    assert result.is_executable is False
    assert result.recommended_stake == 0.0

def test_gate_allows_executable_ev_when_all_gates_pass():
    """Verify that when all empirical criteria are met, bet is approved."""
    gate = EmpiricalDecisionGate(min_edge=0.05)
    # p_model=0.50, p_devig=0.45, odds=2.40 -> Calibrated EV ~ +12.3%
    result = gate.audit_bet(
        outcome="home",
        p_model=0.50,
        p_devig=0.45,
        best_odds=2.40,
        data_quality=DataQualityState.LIVE,
        out_of_sample_calibration_passed=True,
        historical_clv_demonstrated=True,
        historical_sample_size=250
    )
    assert result.status == DecisionStatus.EXECUTABLE_EV
    assert result.is_executable is True
    assert result.is_empirically_supported is True

# =====================================================================
# 4. ZERO FUTURE LEAKAGE TEST
# =====================================================================

def test_zero_future_leakage_in_walk_forward_data():
    """Verify that historical matches are strictly monotonically sorted by date."""
    from unified_betting_core.data_ingestion.real_data_provider import RealDataProvider
    provider = RealDataProvider()
    df, state = provider.get_real_historical_dataset()
    assert not df.empty
    assert len(df) >= 380

    df["dt"] = pd.to_datetime(df["date"])
    assert df["dt"].is_monotonic_increasing


# =====================================================================
# 5. PAPER TRADING & BIAS STRESS TESTS (PHASE 0-8)
# =====================================================================

def test_paper_trading_logger_enforces_zero_stake(tmp_path):
    """Verify that PaperTradingLogger strictly records €0.00 stake in research mode."""
    from unified_betting_core.execution.paper_trading_logger import PaperTradingLogger
    log_file = tmp_path / "paper_test.jsonl"
    logger = PaperTradingLogger(log_path=str(log_file))

    entry = logger.log_bet_candidate(
        event_id="2026-09-20_Arsenal_Chelsea_home",
        match="Arsenal vs Chelsea",
        outcome="home",
        odds=2.10,
        prediction={"home": 0.52, "draw": 0.26, "away": 0.22},
        ev_pct=9.2,
        ece_at_time=3.79
    )

    assert entry["stake_recommended"] == 0.00
    assert entry["operational_mode"] == "PAPER_TRADING_RESEARCH_ONLY"
    assert entry["input_hash"] is not None

    logs = logger.read_all_logs()
    assert len(logs) == 1
    assert logs[0]["event_id"] == "2026-09-20_Arsenal_Chelsea_home"


def test_bias_stress_auditor_detects_tail_sensitivity():
    """Verify that BiasStressAuditor correctly identifies tail sensitivity when few bets flip ROI."""
    from unified_betting_core.validation.bias_analysis import BiasStressAuditor

    # Simulated 20 bets: 1 big outlier win (+50.0), 19 losses (-2.0 each = -38.0). Total PnL = +12.0
    mock_bets = [
        {"date": "2025-01-01", "match": "A vs B", "outcome": "away", "placed_odds": 6.0, "closing_odds": 4.0, "fair_clv": 0.35, "stake": 10.0, "pnl": 50.0}
    ] + [
        {"date": f"2025-01-{i:02d}", "match": f"T{i} vs T{i+1}", "outcome": "home", "placed_odds": 2.0, "closing_odds": 2.0, "fair_clv": 0.0, "stake": 2.0, "pnl": -2.0}
        for i in range(2, 21)
    ]

    audit = BiasStressAuditor.audit_bias_and_stress(mock_bets)
    assert audit["status"] == "COMPLETED"
    assert audit["is_tail_sensitive"] is True
    assert audit["roi_flip_k"] == 1  # Removing just the 1 top bet flips ROI negative
    assert "FAILED_STRESS_TEST" in audit["verdict"]


# =====================================================================
# 6. SHARPBET V10 CORE MODULE TESTS
# =====================================================================

def test_base_margin_model_residual_learning():
    """Verify BaseMarginModel fits residual over devigged market logit without lookahead."""
    from unified_betting_core.models.base_margin_model import BaseMarginModel

    model = BaseMarginModel(min_train_samples=10, edge_threshold=0.01)
    # Generate past records where home team wins frequently when form_delta is positive
    past_records = [
        {
            "p_market_home": 0.45,
            "p_market_draw": 0.28,
            "p_market_away": 0.27,
            "form_delta_home": 0.3,
            "actual_result": "home",
        }
        for _ in range(30)
    ]

    model.fit(past_records)
    assert model.is_fitted is True

    # Prediction
    pred = model.predict_match(
        p_market_devigged={"home": 0.45, "draw": 0.28, "away": 0.27},
        form_delta_home=0.3,
    )
    assert len(pred.predictions) == 3
    home_p = next(p for p in pred.predictions if p.outcome == "home")
    assert home_p.p_final > 0.45  # Model should recognize positive residual for home
    assert home_p.edge_vs_market > 0.0


def test_block_bootstrap_preserves_clusters():
    """Verify BlockBootstrap groups bets by date blocks and computes 95% CI."""
    from unified_betting_core.validation.block_bootstrap import BlockBootstrap

    # 30 bets across 10 distinct dates
    mock_bets = []
    for day in range(1, 11):
        d_str = f"2025-02-{day:02d}"
        for b_idx in range(3):
            mock_bets.append({
                "date": d_str,
                "stake": 10.0,
                "pnl": 5.0 if (day + b_idx) % 2 == 0 else -10.0,
                "fair_clv_pct": 2.5 if day % 2 == 0 else -1.0,
            })

    bb = BlockBootstrap(n_bootstrap=500, confidence=0.95, block_unit="date", seed=42)
    res_roi = bb.compute_ci(mock_bets, metric="roi_pct")
    assert res_roi.n_blocks == 10
    assert res_roi.ci_lower <= res_roi.mean_estimate <= res_roi.ci_upper

    res_clv = bb.compute_ci(mock_bets, metric="fair_clv_pct")
    assert res_clv.n_blocks == 10
    assert res_clv.ci_lower <= res_clv.mean_estimate <= res_clv.ci_upper


def test_segment_clv_auditor_breakdown():
    """Verify SegmentCLVAuditor segments bets by odds bucket, outcome, and league."""
    from unified_betting_core.validation.segment_clv_audit import SegmentCLVAuditor

    mock_bets = [
        {"date": "2025-01-01", "league": "EPL", "outcome": "home", "odds": 1.45, "stake": 10.0, "pnl": 4.5, "fair_clv_pct": 3.0, "is_win": True},
        {"date": "2025-01-02", "league": "EPL", "outcome": "draw", "odds": 3.40, "stake": 10.0, "pnl": -10.0, "fair_clv_pct": -2.0, "is_win": False},
        {"date": "2025-01-03", "league": "LaLiga", "outcome": "away", "odds": 2.20, "stake": 10.0, "pnl": 12.0, "fair_clv_pct": 4.0, "is_win": True},
    ]

    auditor = SegmentCLVAuditor()
    report = auditor.run_audit(mock_bets)
    assert report.total_bets_audited == 3
    assert len(report.segments_by_odds_bucket) >= 2
    assert len(report.segments_by_outcome) >= 2
    assert len(report.segments_by_league) >= 2

    r_dict = auditor.to_dict(report)
    assert "overall_fair_clv_pct" in r_dict
    assert "segments_by_odds_bucket" in r_dict


def test_paper_trading_ledger_integrity(tmp_path):
    """Verify PaperTradingLedger registers, settles, and verifies SHA-256 integrity."""
    from unified_betting_core.validation.paper_ledger import PaperTradingLedger

    ledger_file = tmp_path / "paper_ledger_test.jsonl"
    ledger = PaperTradingLedger(ledger_path=str(ledger_file))

    # Register bet
    entry_id = ledger.register_bet(
        match="Arsenal vs Chelsea",
        league="EPL",
        outcome="home",
        entry_odds=2.10,
        stake_units=0.01,
        kickoff_at="2026-09-25T15:00:00Z",
        model_edge_pct=4.5,
        p_model=0.50,
        p_market_devigged=0.45,
    )
    assert entry_id.startswith("PL-")

    # Settle bet
    settled = ledger.settle_bet(
        entry_id=entry_id,
        actual_result="home",
        closing_odds=2.00,
        fair_closing_odds=2.06,
    )
    assert settled.status == "SETTLED_WIN"
    assert settled.pnl_units > 0

    # Verify integrity
    integrity = ledger.verify_ledger_integrity()
    assert integrity["integrity_ok"] is True
    assert integrity["issues_found"] == 0
    assert integrity["total_entries"] == 1


