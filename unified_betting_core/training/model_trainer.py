"""
Unified Betting Core: Model Trainer & Calibration Engine.
Processes live match results against archived predictions, evaluates Brier score,
calibrates model temperature scaling, and feeds back into historical training datasets.
"""

import argparse
import csv
import json
import logging
import math
import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("SharpBet.ModelTrainer")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRAINING_DIR = os.path.join(BASE_DIR, "data", "training")
ARCHIVE_JSON = os.path.join(TRAINING_DIR, "placed_tickets_archive.json")
DATASET_CSV = os.path.join(TRAINING_DIR, "mozzart_training_dataset.csv")
MODELS_STORE = os.path.join(BASE_DIR, "models_store")
CALIBRATION_FILE = os.path.join(MODELS_STORE, "mozzart_calibration_weights.json")


def evaluate_selection_outcome(
    market_type: str,
    selection: str,
    home_goals: int,
    away_goals: int,
    ht_home_goals: int = 0,
    ht_away_goals: int = 0,
) -> int:
    """
    Evaluates whether a selection won (1) or lost (0) based on actual score and halftime score.
    """
    sel = selection.strip().upper()
    tot_goals = home_goals + away_goals
    tot_ht = ht_home_goals + ht_away_goals
    tot_sh = (home_goals - ht_home_goals) + (away_goals - ht_away_goals)

    if market_type == "1X2":
        if sel in ["1", "HOME"]:
            return 1 if home_goals > away_goals else 0
        elif sel in ["X", "DRAW"]:
            return 1 if home_goals == away_goals else 0
        elif sel in ["2", "AWAY"]:
            return 1 if away_goals > home_goals else 0

    elif market_type == "double_chance":
        if sel == "1X":
            return 1 if home_goals >= away_goals else 0
        elif sel == "12":
            return 1 if home_goals != away_goals else 0
        elif sel == "X2":
            return 1 if away_goals >= home_goals else 0

    elif market_type == "total_goals":
        if sel in ["2+", "VIŠE 1.5", "OVER 1.5"]:
            return 1 if tot_goals >= 2 else 0
        elif sel in ["0-2", "MANJE 2.5", "UNDER 2.5"]:
            return 1 if tot_goals <= 2 else 0
        elif sel in ["3+", "VIŠE 2.5", "OVER 2.5"]:
            return 1 if tot_goals >= 3 else 0
        elif sel in ["0-1", "UNDER 1.5"]:
            return 1 if tot_goals <= 1 else 0
        elif sel in ["4+", "OVER 3.5"]:
            return 1 if tot_goals >= 4 else 0

    elif market_type in ["halftime_goals", "first_half_goals", "prvo_poluvreme_golovi"]:
        if sel in ["I1+", "1+I", "OVER 0.5 HT", "I 1+"]:
            return 1 if tot_ht >= 1 else 0
        elif sel in ["I2+", "2+I", "OVER 1.5 HT", "I 2+"]:
            return 1 if tot_ht >= 2 else 0
        elif sel in ["I 0-1", "0-1 I", "UNDER 1.5 HT"]:
            return 1 if tot_ht <= 1 else 0
        elif sel in ["I 1-2", "1-2 I", "1-2"]:
            return 1 if 1 <= tot_ht <= 2 else 0

    elif market_type in ["second_half_goals", "drugo_poluvreme_golovi"]:
        if sel in ["II1+", "1+II", "OVER 0.5 2H", "II 1+"]:
            return 1 if tot_sh >= 1 else 0
        elif sel in ["II2+", "2+II", "OVER 1.5 2H", "II 2+"]:
            return 1 if tot_sh >= 2 else 0

    elif market_type in ["goals_both_halves", "golovi_oba_poluvremena"]:
        if sel in ["I1+&II1+", "1+I&1+II", "1+FH&1+SH"]:
            return 1 if (tot_ht >= 1 and tot_sh >= 1) else 0
        elif sel in ["I2+&II2+", "2+I&2+II", "2+FH&2+SH"]:
            return 1 if (tot_ht >= 2 and tot_sh >= 2) else 0
        elif sel in ["I1+&II2+", "1+I&2+II", "1+FH&2+SH"]:
            return 1 if (tot_ht >= 1 and tot_sh >= 2) else 0

    elif market_type in ["half_with_more_goals", "poluvreme_vise_golova"]:
        if sel in ["I<II", "2", "2H", "II"]:
            return 1 if tot_sh > tot_ht else 0
        elif sel in ["I=II", "X", "EQUAL", "="]:
            return 1 if tot_sh == tot_ht else 0
        elif sel in ["I>II", "1", "1H", "I"]:
            return 1 if tot_ht > tot_sh else 0

    elif market_type in ["combo_result_ht_goals", "mozzart_combinations"]:
        if sel in ["1&I1+", "1&1+I", "1&OV 0.5FH"]:
            return 1 if (home_goals > away_goals and tot_ht >= 1) else 0
        elif sel in ["2&I1+", "2&1+I", "2&OV 0.5FH"]:
            return 1 if (away_goals > home_goals and tot_ht >= 1) else 0
        elif sel in ["GG&I1+", "GG&1+I"]:
            return 1 if (home_goals >= 1 and away_goals >= 1 and tot_ht >= 1) else 0
        elif sel in ["1&I2+", "1&2+I"]:
            return 1 if (home_goals > away_goals and tot_ht >= 2) else 0

    elif market_type in ["both_teams_to_score", "btts"]:
        if sel in ["GG", "DA", "YES"]:
            return 1 if (home_goals >= 1 and away_goals >= 1) else 0
        elif sel in ["NG", "NE", "NO"]:
            return 1 if (home_goals == 0 or away_goals == 0) else 0

    raise ValueError(f"Unknown market_type '{market_type}' with selection '{selection}'")


class MozzartModelTrainer:
    def __init__(self):
        self.archive_path = ARCHIVE_JSON
        self.csv_path = DATASET_CSV
        self.data = self._load_archive()

    def _load_archive(self) -> Dict[str, Any]:
        if not os.path.exists(self.archive_path):
            raise FileNotFoundError(f"Archive file not found: {self.archive_path}")
        with open(self.archive_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save_archive(self):
        with open(self.archive_path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)
        self._sync_to_csv()

    def _sync_to_csv(self):
        csv_rows = []
        sample_id = 1
        for t in self.data.get("tickets", []):
            for leg in t.get("legs", []):
                csv_rows.append({
                    "sample_id": sample_id,
                    "ticket_id": t["ticket_id"],
                    "ticket_name": t.get("name", ""),
                    "match": leg["match"],
                    "home_team": leg["home_team"],
                    "away_team": leg["away_team"],
                    "league": leg["league"],
                    "start_time": leg["start_time"],
                    "market_type": leg["market_type"],
                    "selection": leg["selection"],
                    "odds": leg["odds"],
                    "p_model": leg["p_model"],
                    "implied_prob_devigged": leg.get("implied_prob_devigged", round(1.0 / leg["odds"], 4)),
                    "edge": leg.get("edge", 0.0),
                    "xg_home": leg.get("xg_home", 0.0),
                    "xg_away": leg.get("xg_away", 0.0),
                    "predicted_score": leg.get("predicted_score", ""),
                    "actual_score": leg.get("actual_score") or "",
                    "outcome_win": leg.get("outcome") if leg.get("outcome") is not None else "",
                    "status": "COMPLETED" if leg.get("outcome") is not None else "PENDING"
                })
                sample_id += 1

        if csv_rows:
            with open(self.csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=list(csv_rows[0].keys()))
                writer.writeheader()
                writer.writerows(csv_rows)

    def record_match_result(self, match_identifier: str, score_str: str):
        """
        Records the actual FT score for a match (e.g. "1-0" or "2-1").
        Updates all ticket legs containing this match.
        """
        score_parts = score_str.strip().split("-")
        if len(score_parts) != 2:
            raise ValueError(f"Invalid score format '{score_str}'. Expected format: 'H-A' (e.g. '2-0')")
        h_score, a_score = int(score_parts[0]), int(score_parts[1])

        updated_count = 0
        match_id_clean = match_identifier.lower().replace(" ", "").replace("-", "")

        for ticket in self.data.get("tickets", []):
            for leg in ticket.get("legs", []):
                leg_name = leg["match"].lower().replace(" ", "").replace("-", "")
                home_team = leg["home_team"].lower().replace(" ", "")
                away_team = leg["away_team"].lower().replace(" ", "")

                if (match_id_clean in leg_name) or (home_team in match_id_clean and away_team in match_id_clean):
                    leg["actual_score"] = f"{h_score}-{a_score}"
                    outcome = evaluate_selection_outcome(leg["market_type"], leg["selection"], h_score, a_score)
                    leg["outcome"] = outcome
                    updated_count += 1
                    logger.info(f"Updated leg '{leg['match']}' selection '{leg['selection']}': Score {h_score}-{a_score} -> Outcome: {'WIN' if outcome == 1 else 'LOSS'}")

            # Check ticket overall status
            all_finished = True
            has_loss = False
            for leg in ticket.get("legs", []):
                if leg.get("outcome") is None:
                    all_finished = False
                elif leg.get("outcome") == 0:
                    has_loss = True

            if has_loss:
                ticket["status"] = "LOST"
            elif all_finished:
                ticket["status"] = "WON"
            else:
                ticket["status"] = "IN_PROGRESS"

        self._save_archive()
        logger.info(f"Successfully recorded result for {updated_count} leg(s). Archive synchronized.")

    def calculate_metrics(self) -> Dict[str, Any]:
        """
        Calculates Brier score, log-loss, and calibration error across all evaluated predictions.
        """
        evaluated_legs = []
        for t in self.data.get("tickets", []):
            for leg in t.get("legs", []):
                if leg.get("outcome") is not None:
                    evaluated_legs.append(leg)

        if not evaluated_legs:
            return {
                "sample_count": 0,
                "status": "NO_COMPLETED_MATCHES_YET",
                "message": "All matches are currently PENDING. Record results to trigger training metrics."
            }

        brier_model_sum = 0.0
        brier_bookie_sum = 0.0
        log_loss_sum = 0.0
        wins = 0

        for leg in evaluated_legs:
            y = float(leg["outcome"])
            p_m = float(leg["p_model"])
            p_b = float(leg.get("implied_prob_devigged", 1.0 / leg["odds"]))

            brier_model_sum += (p_m - y) ** 2
            brier_bookie_sum += (p_b - y) ** 2

            # Log loss clipping
            p_clipped = min(max(p_m, 1e-6), 1.0 - 1e-6)
            log_loss_sum += -(y * math.log(p_clipped) + (1.0 - y) * math.log(1.0 - p_clipped))

            if y == 1.0:
                wins += 1

        n = len(evaluated_legs)
        brier_model = brier_model_sum / n
        brier_bookie = brier_bookie_sum / n
        log_loss = log_loss_sum / n
        win_rate = wins / n

        # Calibration delta: negative means model is sharper / better than bookie
        brier_skill_score = 1.0 - (brier_model / max(brier_bookie, 1e-6))

        metrics = {
            "sample_count": n,
            "win_rate": round(win_rate, 4),
            "brier_score_model": round(brier_model, 4),
            "brier_score_bookmaker": round(brier_bookie, 4),
            "brier_skill_score": round(brier_skill_score, 4),
            "log_loss": round(log_loss, 4),
            "model_beats_bookmaker": bool(brier_model < brier_bookie)
        }
        return metrics

    def train_calibration_layer(self) -> Dict[str, Any]:
        """
        Calibrates model output probabilities using empirical outcomes via temperature scaling.
        """
        metrics = self.calculate_metrics()
        if metrics.get("sample_count", 0) < 5:
            logger.info("Fewer than 5 completed samples; using default prior temperature T=1.00")
            calib_weights = {
                "temperature": 1.0,
                "fitted_samples": metrics.get("sample_count", 0),
                "last_trained_at": datetime.now().isoformat(),
                "metrics": metrics
            }
        else:
            # Optimize temperature T to minimize log loss on realized samples
            evaluated_legs = [
                leg for t in self.data.get("tickets", []) for leg in t.get("legs", [])
                if leg.get("outcome") is not None
            ]
            best_t = 1.0
            best_loss = 999.0

            for t_candidate in [x * 0.05 for x in range(14, 30)]:  # 0.70 to 1.45
                loss = 0.0
                for leg in evaluated_legs:
                    y = float(leg["outcome"])
                    logit = math.log(leg["p_model"] / (1.0 - leg["p_model"] + 1e-9))
                    scaled_logit = logit / t_candidate
                    p_scaled = 1.0 / (1.0 + math.exp(-scaled_logit))
                    p_clipped = min(max(p_scaled, 1e-6), 1.0 - 1e-6)
                    loss += -(y * math.log(p_clipped) + (1.0 - y) * math.log(1.0 - p_clipped))

                loss /= len(evaluated_legs)
                if loss < best_loss:
                    best_loss = loss
                    best_t = t_candidate

            calib_weights = {
                "temperature": round(best_t, 3),
                "fitted_samples": len(evaluated_legs),
                "optimal_loss": round(best_loss, 4),
                "last_trained_at": datetime.now().isoformat(),
                "metrics": metrics
            }

        os.makedirs(MODELS_STORE, exist_ok=True)
        with open(CALIBRATION_FILE, "w", encoding="utf-8") as f:
            json.dump(calib_weights, f, indent=2)
        logger.info(f"Saved calibration weights to {CALIBRATION_FILE}")
        return calib_weights

    def print_status_report(self):
        """
        Prints a detailed overview of all archived tickets, their legs, and model metrics.
        """
        print("\n" + "=" * 80)
        print("🎯 MOZZART BETTING CORE: ARHIVA TIKETA & TRENING PODACI")
        print("=" * 80)
        print(f"📁 Baza uplate: {self.archive_path}")
        print(f"📊 Dataset za obuku: {self.csv_path}")

        for i, ticket in enumerate(self.data.get("tickets", []), 1):
            print("\n" + "-" * 80)
            print(f"🎟️ TIKET #{i}: {ticket.get('name', 'N/A')} (Šifra: {ticket.get('ticket_id')})")
            print(f"⏰ Vreme: {ticket.get('timestamp')} | Status: {ticket.get('status')} | Max Isplata: {ticket.get('max_payout_rsd'):,.2f} RSD")
            print("-" * 80)
            print(f"{'#':<3} {'Vreme':<10} {'Meč':<35} {'Tip':<6} {'Kvota':<6} {'P(mod)':<8} {'Status':<10} {'Rezultat':<8}")
            print("-" * 80)

            for j, leg in enumerate(ticket.get("legs", []), 1):
                status_str = "⏳ ČEKA"
                if leg.get("outcome") == 1:
                    status_str = "✅ DOBITAN"
                elif leg.get("outcome") == 0:
                    status_str = "❌ PADA"

                score_str = leg.get("actual_score") or f"xG: {leg.get('predicted_score')}"
                print(f"{j:<3} {leg['start_time']:<10} {leg['match'][:34]:<35} {leg['selection']:<6} {leg['odds']:<6.2f} {leg['p_model']*100:<7.1f}% {status_str:<10} {score_str:<8}")

        metrics = self.calculate_metrics()
        print("\n" + "=" * 80)
        print("📈 METRIKE KALIBRACIJE I STATISTIKA ZA TRENING")
        print("=" * 80)
        if metrics.get("sample_count", 0) == 0:
            print("⏳ Trenutni status: Svi mečevi su u toku ili čekaju početak.")
            print("💡 Kako ažurirati rezultat meča kada se završi:")
            print("   python3 -m unified_betting_core.training.model_trainer --record-result \"Montana vs Hebar\" \"2-0\"")
        else:
            print(f"Obrađeno uzoraka: {metrics['sample_count']}")
            print(f"Procenat prolaza: {metrics['win_rate']*100:.1f}%")
            print(f"Brier Score (Model):    {metrics['brier_score_model']:.4f}")
            print(f"Brier Score (Kladionica): {metrics['brier_score_bookmaker']:.4f}")
            print(f"Brier Skill Score:      {metrics['brier_skill_score']:+.4f}")
            print(f"Log Loss:               {metrics['log_loss']:.4f}")
            print(f"Model bolji od kvota:   {'DA ✅' if metrics['model_beats_bookmaker'] else 'NE ❌'}")
        print("=" * 80 + "\n")


def main():
    parser = argparse.ArgumentParser(description="Mozzart Model Trainer and Ticket Archive Engine")
    parser.add_argument("--status", action="store_true", help="Print current status of tickets and calibration metrics")
    parser.add_argument("--record-result", nargs=2, metavar=("MATCH", "SCORE"), help="Record result for a match, e.g. --record-result 'Montana vs Hebar' '1-0'")
    parser.add_argument("--train", action="store_true", help="Train / calibrate model on all recorded match outcomes")
    args = parser.parse_args()

    trainer = MozzartModelTrainer()

    if args.record_result:
        match_id, score = args.record_result
        trainer.record_match_result(match_id, score)
        trainer.train_calibration_layer()
        trainer.print_status_report()
    elif args.train:
        trainer.train_calibration_layer()
        trainer.print_status_report()
    else:
        trainer.print_status_report()


if __name__ == "__main__":
    main()
