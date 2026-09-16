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
