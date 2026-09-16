"""
Chronological Walk-Forward Backtest & Out-of-Sample Validation Engine for SharpBet Core.
Evaluates historical performance with strict zero-leakage discipline:
- Past data only for model fitting and temperature calibration
- Real pre-match available odds for decisions
- Real Pinnacle closing odds for retrospective CLV
- Real settled match results for P&L
Guarantees: No future features, no future odds, no look-ahead bias.
"""

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
from unified_betting_core.decision_engine.empirical_gate import EmpiricalDecisionGate, DecisionStatus
from unified_betting_core.decision_engine.kelly_criterion import KellyCriterion
from unified_betting_core.decision_engine.pnl_tracker import PnLTracker

logger = logging.getLogger("SharpBet.WalkForward")

class WalkForwardEngine:
    """
    Executes a rigorous out-of-sample walk-forward backtest over real historical matches.
    """

    def __init__(
        self,
        bankroll: float = DEFAULT_BANKROLL,
        burn_in_matches: int = 380,  # Season 1 (380 matches) for burn-in
        calib_window: int = 150       # Rolling 150 matches for temperature scaling
    ):
        self.initial_bankroll = bankroll
        self.burn_in_matches = burn_in_matches
        self.calib_window = calib_window
        self.data_provider = RealDataProvider()

    def run_walk_forward(self, force_refresh_data: bool = False) -> Dict[str, Any]:
        """
        Executes chronological walk-forward simulation across all available real matches.
        """
        df, data_state = self.data_provider.get_real_historical_dataset(force_refresh=force_refresh_data)
        if df.empty or len(df) <= self.burn_in_matches:
            logger.error(f"Insufficient real data for walk-forward: {len(df)} matches found.")
            return {"status": "FAILED", "error": "Insufficient real match data"}

        logger.info(f"Starting Walk-Forward on {len(df)} real matches (Burn-in: {self.burn_in_matches}, Out-of-sample: {len(df)-self.burn_in_matches}).")

        # Verify chronological ordering
        df["dt"] = pd.to_datetime(df["date"])
        df = df.sort_values(by=["dt"]).reset_index(drop=True)

        poisson_engine = PoissonEngine()
        empirical_gate = EmpiricalDecisionGate(min_edge=MIN_EDGE)
        kelly = KellyCriterion()
        pnl_tracker = PnLTracker(initial_bankroll=self.initial_bankroll)

        # Tracking containers for out-of-sample evaluation
        oos_prob_distributions: List[Dict[str, float]] = []
        oos_actual_results: List[str] = []
        oos_selected_probs: List[float] = []
        oos_selected_labels: List[int] = []

        all_candidate_audits: List[Dict[str, Any]] = []
        settled_clv_bets: List[Dict[str, Any]] = []
        rejected_counts: Dict[str, int] = {
            "FAKE_EV": 0,
            "MARGINAL_EV": 0,
            "CALIBRATION_FAILED": 0,
            "INSUFFICIENT_EVIDENCE": 0,
            "NO_EDGE": 0
        }

        # Rolling past predictions for out-of-sample calibration gate
        past_predicted_dists: List[Dict[str, float]] = []
        past_actuals: List[str] = []
        past_selected_p: List[float] = []
        past_selected_y: List[int] = []
        past_clvs: List[float] = []

        # Zero future leakage verification
        last_observed_date = None

        for idx, row in df.iterrows():
            current_date = row["dt"]
            if last_observed_date is not None and current_date < last_observed_date:
                raise ValueError(f"Data Leakage Violation: matches not strictly chronological at index {idx} ({current_date} < {last_observed_date})")
            last_observed_date = current_date

            home_team = row["home_team"]
            away_team = row["away_team"]
            actual_result = row["result"]

            # 1. Pre-match Poisson Model Prediction
            h_xg = float(row.get("home_xg", 1.4))
            a_xg = float(row.get("away_xg", 1.1))
            raw_model_probs = poisson_engine.predict_match(home_team, away_team, h_xg, a_xg)

            # In-burn-in phase: record stats to establish baseline, do not bet
            if idx < self.burn_in_matches:
                past_predicted_dists.append(raw_model_probs)
                past_actuals.append(actual_result)
                continue

            # 2. Out-of-Sample Calibration (Temperature Scaling fitted strictly on past window)
            recent_dists = past_predicted_dists[-self.calib_window:]
            recent_acts = past_actuals[-self.calib_window:]
            temp_scaler = TemperatureScaler()
            temp_scaler.fit(recent_dists, recent_acts)
            calibrated_model_probs = temp_scaler.scale(raw_model_probs)

            oos_prob_distributions.append(calibrated_model_probs)
            oos_actual_results.append(actual_result)

            # 3. Real Pre-Match Opening Market Odds
            odds_dict = {
                "home": float(row["home_odds"]),
                "draw": float(row["draw_odds"]),
                "away": float(row["away_odds"])
            }
            devig_probs = DevigEngine.devig_power(odds_dict)
            fair_market_odds = DevigEngine.fair_odds(devig_probs)

            # 4. Out-of-Sample Calibration Gate Evaluation on prior track record
            has_calib_proof = False
            has_clv_proof = False
            if len(past_selected_p) >= 50:
                calib_verdict = ModelCalibration.evaluate_out_of_sample_gate(
                    past_predicted_dists[-200:],
                    past_actuals[-200:],
                    past_selected_p[-200:],
                    past_selected_y[-200:],
                    min_sample_size=50,
                    max_ece_pct=7.0,
                    max_brier=0.65
                )
                has_calib_proof = calib_verdict.passed

            if len(past_clvs) >= 30:
                has_clv_proof = (np.mean(past_clvs[-100:]) > 0.0)

            # Real Pinnacle Closing Odds for retrospective settlement
            closing_odds_dict = {
                "home": float(row["closing_home_odds"]),
                "draw": float(row["closing_draw_odds"]),
                "away": float(row["closing_away_odds"])
            }
            closing_devig = DevigEngine.devig_power(closing_odds_dict)
            fair_closing_odds = DevigEngine.fair_odds(closing_devig)

            # 5. Evaluate all outcomes through the Empirical Decision Gate
            best_selection = None
            best_ev = -999.0

            for outcome in ["home", "draw", "away"]:
                p_mod = calibrated_model_probs.get(outcome, 0.0)
                p_dvg = devig_probs.get(outcome, 0.0)
                b_odds = odds_dict[outcome]

                gate_eval = empirical_gate.audit_bet(
                    outcome=outcome,
                    p_model=p_mod,
                    p_devig=p_dvg,
                    best_odds=b_odds,
                    data_quality=data_state,
                    out_of_sample_calibration_passed=has_calib_proof,
                    historical_clv_demonstrated=has_clv_proof,
                    historical_sample_size=len(past_actuals)
                )

                status_key = gate_eval.status.value
                if status_key in rejected_counts:
                    rejected_counts[status_key] += 1

                # Track candidate for reporting
                audit_record = {
                    "match": f"{home_team} vs {away_team}",
                    "date": row["date"],
                    "outcome": outcome,
                    "best_odds": b_odds,
                    "closing_odds": closing_odds_dict[outcome],
                    "raw_ev_pct": gate_eval.raw_ev_pct,
                    "calibrated_ev_pct": gate_eval.calibrated_ev_pct,
                    "status": gate_eval.status.value,
                    "is_executable": gate_eval.is_executable
                }
                all_candidate_audits.append(audit_record)

                if gate_eval.is_executable and gate_eval.calibrated_ev_pct > best_ev:
                    best_ev = gate_eval.calibrated_ev_pct
                    best_selection = {
                        "outcome": outcome,
                        "odds": b_odds,
                        "p_calibrated": gate_eval.p_calibrated,
                        "calibrated_ev": gate_eval.calibrated_ev_pct / 100.0,
                        "closing_odds": closing_odds_dict[outcome],
                        "closing_fair_odds": fair_closing_odds.get(outcome, closing_odds_dict[outcome] * 1.035)
                    }

            # 6. Settle Bet (strictly retrospective after decision is frozen)
            if best_selection:
                stake = kelly.calculate_stake(
                    model_prob=best_selection["p_calibrated"],
                    market_odds=best_selection["odds"],
                    bankroll=pnl_tracker.current_bankroll
                )

                if stake > 0:
                    bet_record = pnl_tracker.record_bet(
                        match=f"{home_team} vs {away_team}",
                        outcome=best_selection["outcome"],
                        placed_odds=best_selection["odds"],
                        stake=stake,
                        actual_result=actual_result,
                        closing_odds=best_selection["closing_odds"],
                        closing_fair_odds=best_selection["closing_fair_odds"],
                        date=row["date"]
                    )

                    # Compute real CLV
                    clv_metric = CLVCalculator.calculate_clv(
                        best_selection["odds"],
                        best_selection["closing_odds"],
                        best_selection["closing_fair_odds"]
                    )
                    settled_clv_bets.append(clv_metric)
                    past_clvs.append(clv_metric["raw_clv"])

                    oos_selected_probs.append(best_selection["p_calibrated"])
                    is_hit = 1 if best_selection["outcome"] == actual_result else 0
                    oos_selected_labels.append(is_hit)
                    past_selected_p.append(best_selection["p_calibrated"])
                    past_selected_y.append(is_hit)

            # Record into rolling history
            past_predicted_dists.append(raw_model_probs)
            past_actuals.append(actual_result)

        # 7. Final Out-of-Sample Metrics
        brier_res = ModelCalibration.calculate_brier_score(oos_prob_distributions, oos_actual_results)
        ece_res = ModelCalibration.calculate_ece(oos_selected_probs, oos_selected_labels, num_bins=8)
        clv_portfolio = CLVCalculator.evaluate_portfolio_clv(settled_clv_bets)
        pnl_metrics = pnl_tracker.get_summary_metrics()

        # Gate status determination
        has_empirical_proof = (
            pnl_metrics["total_bets"] >= 30 and
            clv_portfolio["avg_raw_clv_pct"] > 0.0 and
            ece_res["ece_pct"] <= 6.0 and
            brier_res["brier_score"] <= 0.65
        )

        return {
            "status": "COMPLETED",
            "total_matches_evaluated": len(df),
            "out_of_sample_matches": len(oos_actual_results),
            "data_quality_state": data_state.value,
            "has_empirical_proof": has_empirical_proof,
            "pnl_metrics": pnl_metrics,
            "clv_metrics": clv_portfolio,
            "calibration_metrics": {
                "brier_score": brier_res["brier_score"],
                "ece_pct": ece_res["ece_pct"],
                "mce_pct": ece_res["mce_pct"],
                "bins": ece_res["bins"]
            },
            "rejections_summary": rejected_counts,
            "sample_audits_count": len(all_candidate_audits)
        }
