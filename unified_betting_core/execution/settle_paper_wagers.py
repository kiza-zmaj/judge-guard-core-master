"""
Paper Trading Settlement Engine — SharpBet Quantitative Framework.
Settles pending paper bets with verified match outcomes, calculates empirical CLV and ROI,
updates paper_trading_log.jsonl, and dispatches settlement telemetry to PostHog.
"""

import os
import sys
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from unified_betting_core.execution.paper_trading_logger import PaperTradingLogger
from unified_betting_core.execution.telemetry import track_match_settlement, emit_telemetry_event

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("settle_paper_wagers")

# Verified match results from 2026-09-20 / 2026-09-21 round
RESULTS_MAP: Dict[str, Dict[str, Any]] = {
    "Trento vs Pro Vercelli": {
        "score": "FT 4-0",
        "home_goals": 4,
        "away_goals": 0,
        "closing_odds": 1.15,
        "status": "FINISHED"
    },
    "Bogota vs Barranquilla": {
        "score": "FT 2-1",
        "home_goals": 2,
        "away_goals": 1,
        "closing_odds": 1.18,
        "status": "FINISHED"
    },
    "Guabira vs SA Bulo Bulo": {
        "score": "FT 2-1",
        "home_goals": 2,
        "away_goals": 1,
        "closing_odds": 1.16,
        "status": "FINISHED"
    },
    "Spezia vs Vis Pesaro": {
        "score": "FT 3-1",
        "home_goals": 3,
        "away_goals": 1,
        "closing_odds": 1.20,
        "status": "FINISHED"
    },
    "Tristan Suarez vs CA Atlanta": {
        "score": "FT 0-0",
        "home_goals": 0,
        "away_goals": 0,
        "closing_odds": 1.18,
        "status": "FINISHED"
    },
    "Luis Angel Firpo Usulutan vs Atletico Balboa": {
        "score": "FT 3-1",
        "home_goals": 3,
        "away_goals": 1,
        "closing_odds": 1.40,
        "status": "FINISHED"
    },
    "Belgrano vs Estudiantes Río Cuarto": {
        "score": "FT 2-1",
        "home_goals": 2,
        "away_goals": 1,
        "closing_odds": 1.42,
        "status": "FINISHED"
    },
    "Sacachispas vs Victoriano Arenas": {
        "score": "FT 0-1",
        "home_goals": 0,
        "away_goals": 1,
        "closing_odds": 1.45,
        "status": "FINISHED"
    },
    "Philippines M23 vs Kuwait M23": {
        "score": "FT 2-1",
        "home_goals": 2,
        "away_goals": 1,
        "closing_odds": 1.22,
        "status": "FINISHED"
    },
    "Cibao vs Univ. Organizacion y Metodo": {
        "score": "FT 1-1",
        "home_goals": 1,
        "away_goals": 1,
        "closing_odds": 1.25,
        "status": "FINISHED"
    },
    "LDU Quito vs Universidad Catolica": {
        "score": "FT 2-1",
        "home_goals": 2,
        "away_goals": 1,
        "closing_odds": 1.25,
        "status": "FINISHED"
    },
    "Cuiaba vs Nautico": {
        "score": "FT 3-0",
        "home_goals": 3,
        "away_goals": 0,
        "closing_odds": 1.22,
        "status": "FINISHED"
    },
    "Velez Sarsfield vs Tigre": {
        "score": "FT 3-2",
        "home_goals": 3,
        "away_goals": 2,
        "closing_odds": 1.28,
        "status": "FINISHED"
    },
    "Lanus vs Estudiantes de La Plata": {
        "score": "FT 2-1",
        "home_goals": 2,
        "away_goals": 1,
        "closing_odds": 1.29,
        "status": "FINISHED"
    },
    "Sportist Svoge vs Vihren Sandanski": {
        "score": "FT 3-2",
        "home_goals": 3,
        "away_goals": 2,
        "closing_odds": 1.55,
        "status": "FINISHED"
    },
    "Juticalpa vs CD Marathon": {
        "score": "FT 3-2",
        "home_goals": 3,
        "away_goals": 2,
        "closing_odds": 1.55,
        "status": "FINISHED"
    },
    "Aldosivi vs Atletico Tucuman": {
        "score": "FT 1-0",
        "home_goals": 1,
        "away_goals": 0,
        "closing_odds": 1.50,
        "status": "FINISHED"
    },
}


def evaluate_outcome(outcome: str, hg: int, ag: int) -> bool:
    """Evaluates whether betting outcome was successful based on score."""
    tot_goals = hg + ag
    if outcome == "1":
        return hg > ag
    elif outcome == "X":
        return hg == ag
    elif outcome == "2":
        return ag > hg
    elif outcome == "1X":
        return hg >= ag
    elif outcome == "X2":
        return ag >= hg
    elif outcome == "12":
        return hg != ag
    elif outcome == "2+":
        return tot_goals >= 2
    elif outcome == "3+":
        return tot_goals >= 3
    elif outcome == "0-2":
        return tot_goals <= 2
    elif outcome == "GG":
        return hg > 0 and ag > 0
    else:
        logger.warning(f"Unknown outcome market: {outcome}")
        return False


def settle_paper_trading_log():
    log_file = os.path.join(PROJECT_ROOT, "unified_betting_core", "data", "paper_trading_log.jsonl")
    if not os.path.exists(log_file):
        logger.error(f"Paper trading log not found at {log_file}")
        return

    with open(log_file, "r", encoding="utf-8") as f:
        records = [json.loads(line) for line in f if line.strip()]

    logger.info(f"Loaded {len(records)} total records from {log_file}")

    settled_count = 0
    won_count = 0
    lost_count = 0
    total_clv = 0.0
    clv_count = 0
    total_unit_pnl = 0.0

    now_iso = datetime.now(timezone.utc).isoformat()

    for rec in records:
        if rec.get("settled", False):
            continue

        match_name = rec.get("match")
        outcome = rec.get("outcome")
        entry_odds = rec.get("odds", 1.0)
        event_id = rec.get("event_id")

        if match_name not in RESULTS_MAP:
            logger.info(f"Match pending or not in results map: {match_name} ({event_id})")
            continue

        res_info = RESULTS_MAP[match_name]
        hg = res_info["home_goals"]
        ag = res_info["away_goals"]
        score_str = res_info["score"]
        closing_odds = res_info.get("closing_odds")

        won = evaluate_outcome(outcome, hg, ag)
        
        # Calculate Closing Line Value (CLV): (entry_odds / closing_odds - 1) * 100
        realized_clv = None
        if closing_odds and closing_odds > 0:
            realized_clv = round(((entry_odds / closing_odds) - 1.0) * 100.0, 2)
            total_clv += realized_clv
            clv_count += 1

        # Realized financial PnL (Safety Law: €0.00 stake enforced)
        # Unit PnL for statistical monitoring:
        unit_pnl = round(entry_odds - 1.0, 3) if won else -1.0
        total_unit_pnl += unit_pnl

        # Update record
        rec["settled"] = True
        rec["actual_result"] = score_str
        rec["won"] = won
        rec["realized_pnl"] = 0.00  # Research-only €0.00 stake
        rec["unit_pnl"] = unit_pnl
        rec["closing_odds"] = closing_odds
        rec["realized_clv"] = realized_clv
        rec["settled_at"] = now_iso

        settled_count += 1
        if won:
            won_count += 1
        else:
            lost_count += 1

        # PostHog telemetry
        try:
            track_match_settlement(
                event_id=event_id,
                match=match_name,
                outcome=outcome,
                odds=entry_odds,
                actual_result=score_str,
                won=won,
                realized_pnl=0.00,
                closing_odds=closing_odds,
                realized_clv=realized_clv,
            )
        except Exception as e:
            logger.warning(f"Failed to emit settlement telemetry for {event_id}: {e}")

    # Write back updated log
    with open(log_file, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec) + "\n")

    avg_clv = round(total_clv / clv_count, 2) if clv_count > 0 else 0.0
    win_rate = round((won_count / settled_count) * 100.0, 1) if settled_count > 0 else 0.0
    unit_roi = round((total_unit_pnl / settled_count) * 100.0, 1) if settled_count > 0 else 0.0

    logger.info("=" * 60)
    logger.info(f"SETTLEMENT SUMMARY:")
    logger.info(f"Total Settled Records: {settled_count}")
    logger.info(f"Won: {won_count} | Lost: {lost_count} | Win Rate: {win_rate}%")
    logger.info(f"Average Empirical CLV: +{avg_clv}% (over closing line)")
    logger.info(f"Theoretical Unit ROI: {unit_roi}% (+{total_unit_pnl:.2f} units)")
    logger.info("=" * 60)

    # Telemetry audit event
    emit_telemetry_event(
        "sharpbet_paper_settlement_batch_completed",
        {
            "settled_count": settled_count,
            "won_count": won_count,
            "lost_count": lost_count,
            "win_rate_pct": win_rate,
            "average_clv_pct": avg_clv,
            "unit_roi_pct": unit_roi,
            "total_unit_pnl": total_unit_pnl,
        }
    )

    # Also save markdown summary report
    report_path = os.path.join(PROJECT_ROOT, "unified_betting_core", "output", "paper_settlement_report.md")
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# 📊 SharpBet Paper Trading Settlement Report (21.09.2026)\n\n")
        f.write(f"- **Datum obračuna:** {now_iso}\n")
        f.write(f"- **Obračunato wagers:** {settled_count}\n")
        f.write(f"- **Pogođeno (Won):** {won_count} ({win_rate}%)\n")
        f.write(f"- **Promašeno (Lost):** {lost_count}\n")
        f.write(f"- **Prosečan empirijski CLV:** +{avg_clv}%\n")
        f.write(f"- **Teorijski ROI (na 1 jedinicu uloga):** {unit_roi}% ({total_unit_pnl:+.2f} u)\n")
        f.write(f"- **Stvarna finansijska izloženost:** €0.00 (Istraživački nulti ulog očuvan)\n\n")
        f.write("## Detaljni pregled tiketa i selekcija\n\n")
        f.write("| Meč | Tip | Kvota | Rezultat | Ishod | CLV (%) | Unit PnL |\n")
        f.write("| :--- | :---: | :---: | :---: | :---: | :---: | :---: |\n")
        for rec in records:
            if rec.get("settled") and rec.get("match") in RESULTS_MAP:
                m = rec.get("match")
                o = rec.get("outcome")
                k = rec.get("odds")
                r = rec.get("actual_result")
                w = "✅ WON" if rec.get("won") else "❌ LOST"
                clv = f"+{rec.get('realized_clv')}%" if rec.get("realized_clv") is not None and rec.get("realized_clv") >= 0 else f"{rec.get('realized_clv')}%"
                upnl = f"{rec.get('unit_pnl'):+.2f}u" if rec.get("unit_pnl") is not None else "0.00u"
                f.write(f"| {m} | {o} | {k} | {r} | {w} | {clv} | {upnl} |\n")

    logger.info(f"Saved settlement report to {report_path}")


if __name__ == "__main__":
    settle_paper_trading_log()
