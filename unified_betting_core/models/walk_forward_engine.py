"""
Chronological Walk-Forward Backtest & Three-Gate Validation Engine for SharpBet Core.

Strictly decouples:
  1. Candidate Signal Generation (Candidate Warehouse)
  2. Gate A: Out-of-Sample Calibration (ECE & Brier across ALL OOS predictions)
  3. Gate B: Market Alpha / CLV (across ALL historical candidates, NOT approved bets)
  4. Gate C: Economic P&L (frozen strategy simulation, ROI with 95% CI)
  5. Governance Decision: EMPIRICALLY_SUPPORTED_EV = A AND B AND C

ELIMINATES THE CIRCULAR DEPENDENCY:
  Candidate Set -> CLV Measurement -> Market Alpha Evidence -> Decision Gate
"""

import math
import logging
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional, Tuple

from unified_betting_core.config import DEFAULT_BANKROLL, MIN_EDGE
from unified_betting_core.data_ingestion.real_data_provider import RealDataProvider, DataQualityState
from unified_betting_core.models.poisson_model import PoissonEngine
from unified_betting_core.models.calibration import ModelCalibration, TemperatureScaler
from unified_betting_core.decision_engine.devig_engine import DevigEngine
from unified_betting_core.decision_engine.clv_calculator import CLVCalculator, CLVState
from unified_betting_core.decision_engine.empirical_gate import (
    EmpiricalDecisionGate,
    GateAResult,
    GateBResult,
    GateCResult,
    ThreeGateVerdict,
    CalibrationStatus,
    MarketAlphaStatus,
    EconomicStatus,
    FinalStatus,
    evaluate_three_gate_verdict
)
from unified_betting_core.decision_engine.kelly_criterion import KellyCriterion
from unified_betting_core.decision_engine.pnl_tracker import PnLTracker
from unified_betting_core.validation.evidence_package import EvidencePackageGenerator

logger = logging.getLogger("SharpBet.WalkForward")


class WalkForwardEngine:
    """
    Executes chronological walk-forward out-of-sample validation.
    Enforces zero-lookahead, independent three-gate evaluation, and reproducible evidence.
    """

    def __init__(
        self,
        bankroll: float = DEFAULT_BANKROLL,
        burn_in_matches: int = 380,  # Season 1 for burn-in
        calib_window: int = 150       # Rolling past window for temperature scaling
    ):
        self.initial_bankroll = bankroll
        self.burn_in_matches = burn_in_matches
        self.calib_window = calib_window
        self.data_provider = RealDataProvider()

    def run_walk_forward(self, force_refresh_data: bool = False, generate_evidence: bool = True) -> Dict[str, Any]:
        """
        Executes the chronological walk-forward loop and evaluates the 3 independent gates.
        """
        df, data_state = self.data_provider.get_real_historical_dataset(force_refresh=force_refresh_data)
        if df.empty or len(df) <= self.burn_in_matches:
            logger.error(f"Insufficient real data for walk-forward: {len(df)} matches found.")
            return {"status": "FAILED", "error": "Insufficient real match data"}

        logger.info(f"Starting Walk-Forward on {len(df)} real matches (Burn-in: {self.burn_in_matches}, OOS: {len(df)-self.burn_in_matches}).")

        # Strict chronological ordering
        df["dt"] = pd.to_datetime(df["date"])
        df = df.sort_values(by=["dt"]).reset_index(drop=True)

        poisson_engine = PoissonEngine()
        empirical_gate = EmpiricalDecisionGate(min_edge=MIN_EDGE)
        kelly = KellyCriterion()

        # OOS tracking containers for Gate A (ALL OOS matches)
        oos_prob_distributions: List[Dict[str, float]] = []
        oos_actual_results: List[str] = []
        oos_match_dates: List[str] = []

        # Candidate Warehouse for Gate B (ALL candidate signals across all matches)
        candidate_warehouse: List[Dict[str, Any]] = []

        # Rolling past history for zero-leakage calibration fitting
        past_raw_dists: List[Dict[str, float]] = []
        past_actuals: List[str] = []

        # Rejection tracking
        rejections_counts = {
            "FAKE_EV": 0,
            "MARGINAL_EV": 0,
            "CALIBRATION_FAILED": 0,
            "MARKET_ALPHA_FAILED": 0,
            "ECONOMIC_VALIDATION_FAILED": 0,
            "INSUFFICIENT_EVIDENCE": 0,
            "NO_EDGE": 0
        }

        # Audit & diagnostics
        all_match_evaluations: List[Dict[str, Any]] = []
        last_observed_date = None

        # ─────────────────────────────────────────────────────────────────────
        # PASS 1: CHRONOLOGICAL WALK-FORWARD PREDICTION & CANDIDATE GENERATION
        # ─────────────────────────────────────────────────────────────────────
        for idx, row in df.iterrows():
            current_date = row["dt"]
            if last_observed_date is not None and current_date < last_observed_date:
                raise ValueError(f"Data Leakage: matches not chronological at index {idx} ({current_date} < {last_observed_date})")
            last_observed_date = current_date

            home_team = row["home_team"]
            away_team = row["away_team"]
            actual_result = str(row["result"]).strip()
            match_title = f"{home_team} vs {away_team}"

            # 1. Pre-match Poisson Model Prediction
            h_xg = float(row.get("home_xg", 1.4))
            a_xg = float(row.get("away_xg", 1.1))
            raw_model_probs = poisson_engine.predict_match(home_team, away_team, h_xg, a_xg)

            # In burn-in: collect history only, no betting decisions
            if idx < self.burn_in_matches:
                past_raw_dists.append(raw_model_probs)
                past_actuals.append(actual_result)
                continue

            # 2. Out-of-Sample Calibration (Temperature Scaling fit on strictly past window)
            recent_dists = past_raw_dists[-self.calib_window:]
            recent_acts = past_actuals[-self.calib_window:]
            temp_scaler = TemperatureScaler()
            temp_scaler.fit(recent_dists, recent_acts)
            calibrated_model_probs = temp_scaler.scale(raw_model_probs)

            oos_prob_distributions.append(calibrated_model_probs)
            oos_actual_results.append(actual_result)
            oos_match_dates.append(str(row["date"]))

            # 3. Real Pre-Match Opening Market Odds & De-vig
            odds_dict = {
                "home": float(row["home_odds"]),
                "draw": float(row["draw_odds"]),
                "away": float(row["away_odds"])
            }
            devig_probs = DevigEngine.devig_power(odds_dict)

            # 4. Real Pinnacle Closing Odds for retrospective CLV
            closing_odds_dict = {
                "home": float(row["closing_home_odds"]),
                "draw": float(row["closing_draw_odds"]),
                "away": float(row["closing_away_odds"])
            }
            closing_devig = DevigEngine.devig_power(closing_odds_dict)
            fair_closing_odds = DevigEngine.fair_odds(closing_devig)

            # 5. Evaluate all outcomes into Candidate Warehouse
            for outcome in ["home", "draw", "away"]:
                p_mod = calibrated_model_probs.get(outcome, 0.0)
                p_dvg = devig_probs.get(outcome, 0.0)
                b_odds = odds_dict[outcome]
                c_odds = closing_odds_dict[outcome]
                c_fair_odds = fair_closing_odds.get(outcome, c_odds * 1.035)

                # Per-bet anti-delusion check
                gate_eval = empirical_gate.audit_bet(
                    outcome=outcome,
                    p_model=p_mod,
                    p_devig=p_dvg,
                    best_odds=b_odds,
                    data_quality=data_state
                )

                # Tally rejection
                st_val = gate_eval.status.value
                if st_val in rejections_counts:
                    rejections_counts[st_val] += 1

                # Retrospective CLV (known only after kickoff)
                clv_metric = CLVCalculator.calculate_clv(
                    placed_odds=b_odds,
                    closing_odds=c_odds,
                    closing_fair_odds=c_fair_odds
                )

                is_win = (outcome.lower() == actual_result.lower())

                candidate_record = {
                    "event_id": f"{row['date']}_{home_team}_{away_team}_{outcome}",
                    "date": str(row["date"]),
                    "match": match_title,
                    "outcome": outcome,
                    "odds": b_odds,
                    "closing_odds": c_odds,
                    "closing_fair_odds": round(c_fair_odds, 3),
                    "p_model": round(p_mod, 4),
                    "p_devig": round(p_dvg, 4),
                    "p_calibrated": gate_eval.p_calibrated,
                    "raw_ev_pct": gate_eval.raw_ev_pct,
                    "calibrated_ev_pct": gate_eval.calibrated_ev_pct,
                    "status": gate_eval.status.value,
                    "actual_result": actual_result,
                    "is_win": is_win,
                    "raw_clv": clv_metric.get("raw_clv"),
                    "raw_clv_pct": clv_metric.get("raw_clv_pct"),
                    "fair_clv": clv_metric.get("fair_clv"),
                    "fair_clv_pct": clv_metric.get("fair_clv_pct"),
                    "beat_closing": clv_metric.get("beat_closing", False),
                    # Candidate signal: PRE-MATCH DETERMINATION (strictly before kickoff)
                    # Candidate signal is generated when model identifies positive calibrated EV
                    # and odds are within tradeable range (<= 4.0), WITHOUT ANY LOOKAHEAD to closing lines.
                    "is_candidate_signal": (
                        (gate_eval.status.value in ["CALIBRATED_EV", "EXECUTABLE_EV"] or gate_eval.calibrated_ev_pct >= 1.0)
                        and (b_odds <= 4.0)
                    )
                }
                candidate_warehouse.append(candidate_record)

            all_match_evaluations.append({
                "date": str(row["date"]),
                "match": match_title,
                "result": actual_result,
                "model_probs": calibrated_model_probs,
                "market_odds": odds_dict,
                "closing_odds": closing_odds_dict
            })

            # Append to rolling past history
            past_raw_dists.append(raw_model_probs)
            past_actuals.append(actual_result)

        # ─────────────────────────────────────────────────────────────────────
        # GATE A: OUT-OF-SAMPLE CALIBRATION VALIDATION
        # Evaluated across ALL OOS predictions (Multiclass OvR)
        # ─────────────────────────────────────────────────────────────────────
        gate_a_verdict = ModelCalibration.evaluate_out_of_sample_gate(
            oos_prob_distributions,
            oos_actual_results,
            min_sample_size=100,
            max_ece_pct=6.0,
            max_brier=0.65
        )

        gate_a = GateAResult(
            status=CalibrationStatus.CALIBRATION_PASS if gate_a_verdict.passed else CalibrationStatus.CALIBRATION_FAILED,
            passed=gate_a_verdict.passed,
            brier_score=gate_a_verdict.brier_score,
            ece_pct=gate_a_verdict.ece_pct,
            mce_pct=gate_a_verdict.mce_pct,
            sample_size=gate_a_verdict.sample_size,
            drift_detected=gate_a_verdict.is_drift_detected,
            failure_reasons=gate_a_verdict.failure_reasons,
            reliability_table=gate_a_verdict.reliability_table
        )

        # ─────────────────────────────────────────────────────────────────────
        # GATE B: MARKET ALPHA / CLV VALIDATION
        # Evaluated across ALL historical candidate signals (DECOUPLED FROM APPROVAL)
        # ─────────────────────────────────────────────────────────────────────
        candidate_signals = [c for c in candidate_warehouse if c["is_candidate_signal"]]
        # Gate B uses fair_clv (de-vigged Pinnacle closing) to avoid margin compression artifacts.
        # raw_clv is retained in output for diagnostics only.
        settled_candidates_clv = [c for c in candidate_signals if c["fair_clv"] is not None]

        gate_b_failures = []
        if len(settled_candidates_clv) < 30:
            gate_b_failures.append(f"Insufficient candidate signals with closing odds: {len(settled_candidates_clv)} (min 30).")

        raw_clvs = [c["raw_clv"] for c in settled_candidates_clv if c["raw_clv"] is not None]
        fair_clvs = [c["fair_clv"] for c in settled_candidates_clv]

        if fair_clvs:
            # Primary Gate B metric: fair_clv (de-vigged, unbiased)
            fair_arr = np.array(fair_clvs)
            mean_raw_clv = float(np.mean(fair_arr))   # naming kept for downstream compat
            median_raw_clv = float(np.median(fair_arr))
            std_err_clv = float(np.std(fair_arr, ddof=1) / math.sqrt(len(fair_arr))) if len(fair_arr) > 1 else 0.0
            ci_clv_lower = mean_raw_clv - (1.96 * std_err_clv)
            ci_clv_upper = mean_raw_clv + (1.96 * std_err_clv)
            avg_fair_clv = mean_raw_clv  # same array
            beat_rate = (sum(1 for c in settled_candidates_clv if c["beat_closing"]) / len(settled_candidates_clv)) * 100.0

            if mean_raw_clv <= 0.0:
                gate_b_failures.append(f"Mean fair CLV is non-positive ({mean_raw_clv*100:.2f}%). Strategy fails to beat fair closing line.")
            if ci_clv_upper <= 0.0:
                gate_b_failures.append(f"Upper 95% CI of fair CLV ({ci_clv_upper*100:.2f}%) is non-positive.")
        else:
            mean_raw_clv = 0.0
            median_raw_clv = 0.0
            avg_fair_clv = 0.0
            ci_clv_lower = 0.0
            ci_clv_upper = 0.0
            beat_rate = 0.0
            gate_b_failures.append("Zero candidate signals generated.")

        gate_b_passed = (len(gate_b_failures) == 0)
        gate_b = GateBResult(
            status=MarketAlphaStatus.MARKET_ALPHA_PASS if gate_b_passed else MarketAlphaStatus.MARKET_ALPHA_FAILED,
            passed=gate_b_passed,
            candidate_count=len(candidate_signals),
            settled_count=len(settled_candidates_clv),
            avg_raw_clv_pct=round(mean_raw_clv * 100, 2),
            avg_fair_clv_pct=round(avg_fair_clv * 100, 2),
            beat_closing_rate_pct=round(beat_rate, 2),
            ci_95_lower_pct=round(ci_clv_lower * 100, 2),
            ci_95_upper_pct=round(ci_clv_upper * 100, 2),
            failure_reasons=gate_b_failures
        )

        # ─────────────────────────────────────────────────────────────────────
        # GATE C: ECONOMIC / P&L VALIDATION
        # Executes predefined frozen strategy simulation (Kelly sizing on top candidate per match)
        # ─────────────────────────────────────────────────────────────────────
        pnl_tracker = PnLTracker(initial_bankroll=self.initial_bankroll)
        placed_bets: List[Dict[str, Any]] = []

        # Group candidates by match and pick best PRE-MATCH EV candidate per match (No CLV lookahead)
        candidates_by_match: Dict[str, List[Dict[str, Any]]] = {}
        for c in candidate_signals:
            m_key = f"{c['date']}_{c['match']}"
            candidates_by_match.setdefault(m_key, []).append(c)

        for m_key, match_cands in candidates_by_match.items():
            # Pre-match decision: choose candidate with highest calibrated EV (strictly pre-kickoff)
            best_cand = max(match_cands, key=lambda x: (x.get("calibrated_ev_pct") or 0.0))
            # Safe proportional unit stake (1.0% bankroll) for empirical evidence gate
            stake = round(pnl_tracker.current_bankroll * 0.01, 2)
            if stake > 0:
                bet_rec = pnl_tracker.record_bet(
                    match=best_cand["match"],
                    outcome=best_cand["outcome"],
                    placed_odds=best_cand["odds"],
                    stake=stake,
                    actual_result=best_cand["actual_result"],
                    closing_odds=best_cand["closing_odds"],
                    closing_fair_odds=best_cand["closing_fair_odds"],
                    date=best_cand["date"]
                )
                placed_bets.append(bet_rec)

        pnl_summary = pnl_tracker.get_summary_metrics()
        gate_c_failures = []

        total_bets = pnl_summary["total_bets"]
        roi_pct = pnl_summary["roi_yield_pct"]
        max_dd_pct = pnl_summary["max_drawdown_pct"]

        # Gate C Thresholds (Frozen pre-evaluation, as specified in approved implementation plan)
        GATE_C_CI_LOWER_FLOOR = -2.0   # Lower 95% CI bound must not be worse than -2.0%
        GATE_C_MIN_BETS = 100          # Statistical sample size requirement
        GATE_C_MAX_DRAWDOWN = 35.0

        # Confidence interval for ROI
        if total_bets >= 10:
            returns = [(b["pnl"] / max(b["stake"], 0.01)) for b in pnl_tracker.bets]
            ret_std_err = float(np.std(returns, ddof=1) / math.sqrt(total_bets))
            roi_ci_lower = roi_pct - (1.96 * ret_std_err * 100.0)
            roi_ci_upper = roi_pct + (1.96 * ret_std_err * 100.0)
        else:
            roi_ci_lower = roi_pct
            roi_ci_upper = roi_pct

        if total_bets < GATE_C_MIN_BETS:
            gate_c_failures.append(f"Insufficient total bets for economic significance: {total_bets} (min {GATE_C_MIN_BETS}).")
        if roi_pct <= 0.0:
            gate_c_failures.append(f"Realized ROI is non-positive ({roi_pct:.2f}%).")
        if roi_ci_lower < GATE_C_CI_LOWER_FLOOR:
            gate_c_failures.append(
                f"ROI 95% CI lower bound ({roi_ci_lower:.2f}%) is below safety floor ({GATE_C_CI_LOWER_FLOOR:.2f}%). "
                f"Statistical edge cannot be distinguished from random noise."
            )
        if max_dd_pct > GATE_C_MAX_DRAWDOWN:
            gate_c_failures.append(f"Maximum drawdown ({max_dd_pct:.2f}%) exceeds safety threshold of {GATE_C_MAX_DRAWDOWN:.2f}%.")

        # Per-outcome P&L breakdown
        pnl_by_outcome = {}
        for out in ["home", "draw", "away"]:
            out_bets = [b for b in pnl_tracker.bets if b["outcome"].lower() == out]
            out_count = len(out_bets)
            out_pnl = sum(b["pnl"] for b in out_bets)
            out_stakes = sum(b["stake"] for b in out_bets)
            out_roi = (out_pnl / out_stakes * 100.0) if out_stakes > 0 else 0.0
            out_wins = sum(1 for b in out_bets if b.get("is_win") or (b["pnl"] > 0))
            pnl_by_outcome[out] = {
                "bets": out_count,
                "wins": out_wins,
                "win_rate_pct": round(out_wins / max(out_count, 1) * 100.0, 2),
                "total_pnl": round(out_pnl, 2),
                "total_stakes": round(out_stakes, 2),
                "roi_pct": round(out_roi, 2)
            }

        gate_c_passed = (len(gate_c_failures) == 0)
        gate_c = GateCResult(
            status=EconomicStatus.ECONOMIC_PASS if gate_c_passed else EconomicStatus.ECONOMIC_VALIDATION_FAILED,
            passed=gate_c_passed,
            total_bets=total_bets,
            roi_pct=roi_pct,
            yield_pct=roi_pct,
            roi_ci_lower_pct=round(roi_ci_lower, 2),
            roi_ci_upper_pct=round(roi_ci_upper, 2),
            max_drawdown_pct=max_dd_pct,
            final_bankroll=pnl_summary["current_bankroll"],
            failure_reasons=gate_c_failures,
            pnl_by_outcome=pnl_by_outcome
        )

        # ─────────────────────────────────────────────────────────────────────
        # FINAL THREE-GATE VERDICT
        # ─────────────────────────────────────────────────────────────────────
        three_gate = evaluate_three_gate_verdict(gate_a, gate_b, gate_c)

        # Backward-compatible structures for ConsoleReporter
        calib_dict = {
            "brier_score": gate_a.brier_score,
            "ece_pct": gate_a.ece_pct,
            "mce_pct": gate_a.mce_pct,
            "sample_size": gate_a.sample_size,
            "is_drift_detected": gate_a.drift_detected
        }

        clv_dict = {
            "avg_fair_clv_pct": gate_b.avg_fair_clv_pct,   # PRIMARY: de-vigged, unbiased
            "avg_raw_clv_pct": gate_b.avg_raw_clv_pct,     # DIAGNOSTIC: margin-biased (informational only)
            "median_fair_clv_pct": round(median_raw_clv * 100, 2) if fair_clvs else 0.0,
            "beat_closing_rate_pct": gate_b.beat_closing_rate_pct,
            "ci_95_lower_pct": gate_b.ci_95_lower_pct,
            "ci_95_upper_pct": gate_b.ci_95_upper_pct,
            "candidate_count": gate_b.candidate_count
        }

        result = {
            "status": "COMPLETED",
            "three_gate_verdict": three_gate.to_dict(),
            "has_empirical_proof": three_gate.is_empirically_supported,
            "final_governance_status": three_gate.final_status.value,
            "gate_a": three_gate.to_dict()["gate_a"],
            "gate_b": three_gate.to_dict()["gate_b"],
            "gate_c": three_gate.to_dict()["gate_c"],
            "calibration_metrics": calib_dict,
            "clv_metrics": clv_dict,
            "pnl_metrics": pnl_summary,
            "rejections_summary": rejections_counts,
            "total_matches_evaluated": len(df),
            "out_of_sample_matches": len(oos_actual_results),
            "data_quality_state": data_state.value,
            "candidate_signals_count": len(candidate_signals),
            "placed_bets_count": len(placed_bets),
            "candidate_warehouse": candidate_warehouse,
            "oos_predictions": [
                {
                    "date": oos_match_dates[i],
                    "actual": oos_actual_results[i],
                    **oos_prob_distributions[i]
                }
                for i in range(len(oos_actual_results))
            ],
            "reliability_table": gate_a.reliability_table,
            "placed_bets": placed_bets
        }

        # Automatically generate Phase 7 evidence package
        if generate_evidence:
            try:
                pkg_gen = EvidencePackageGenerator()
                paths = pkg_gen.generate_package(result, df)
                result["evidence_package_paths"] = paths
                logger.info(f"Phase 7 Evidence Package successfully generated in {pkg_gen.output_dir}")
            except Exception as e:
                logger.error(f"Error generating evidence package: {e}")

        return result
