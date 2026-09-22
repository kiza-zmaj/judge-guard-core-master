#!/usr/bin/env python3
"""
SharpBet Core — Automated Paper Trading Execution & Ticket Generation Runner
Phase: Paper Trading & Live Monitoring
Authority: MASTER_ORCHESTRATION.md & JudgeGuard Governance

Executes:
1. Ingestion of Mozzart matches and markets.
2. Dixon-Coles Bivariate Goal Modeling & Power De-vigging.
3. 5-Strategy Mathematical Ticket Construction (Zicer, Value, Goals, Night, System 4/6).
4. Immutable Append-Only Audit Logging via PaperTradingLogger (STAKE = €0.00).
5. PostHog EU Cloud Telemetry Dispatch for Real-Time Observability.
"""

import os
import sys
import json
import logging
from datetime import datetime, timezone

# Add root directory to sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from unified_betting_core.execution.mozzart_ticket_generator import (
    MozzartQuantitativeEngine,
    generate_markdown_report,
)
from unified_betting_core.execution.paper_trading_logger import PaperTradingLogger
from unified_betting_core.execution.telemetry import (
    emit_telemetry_event,
    track_paper_bet_logged,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("SharpBetPaperRunner")


def run_cycle():
    logger.info("=" * 75)
    logger.info("🛡️ SHARPBET CORE — EXECUTING REAL-TIME PAPER TRADING CYCLE")
    logger.info("=" * 75)

    mecevi_file = "/home/kizamladjanijebac/Downloads/mozzart_fudbal_mecevi_2026-09-20.csv"
    marketi_file = "/home/kizamladjanijebac/Downloads/mozzart_fudbal_marketi_2026-09-20.csv"

    if not os.path.exists(mecevi_file) or not os.path.exists(marketi_file):
        raise FileNotFoundError(f"Missing Mozzart data feeds: {mecevi_file} / {marketi_file}")

    # 1. Initialize Engine & Evaluate Markets
    logger.info("📊 Step 1: Fitting Dixon-Coles Bivariate Poisson Engine across fixtures...")
    engine = MozzartQuantitativeEngine(mecevi_file, marketi_file)
    eval_res = engine.evaluate_all()
    logger.info(f"   Evaluated {len(eval_res['matches'])} matches and {len(eval_res['bets'])} betting markets.")

    # 2. Build 5 Institutional Tickets
    logger.info("🎯 Step 2: Assembling 5 Institutional Mathematical Tickets...")
    ticket_res = engine.build_tickets(eval_res)
    tickets = ticket_res["tickets"]
    logger.info(f"   Constructed {len(tickets)} tickets successfully.")

    # 3. Log All Unique Selections to PaperTradingLogger (STAKE = €0.00)
    logger.info("🔒 Step 3: Enforcing Paper Trading Safety Law (Stake = €0.00) & Audit Trail...")
    paper_logger = PaperTradingLogger()

    logged_bets = []
    seen_event_outcomes = set()

    for t in tickets:
        ticket_name = t["ticket_name"]
        strategy = t["strategy"]
        for s in t["selections"]:
            event_key = f"{s['match_id']}_{s['code']}"
            if event_key in seen_event_outcomes:
                continue
            seen_event_outcomes.add(event_key)

            pred_dict = {
                "p_calibrated": round(float(s["p_calibrated"]), 4),
                "p_model": round(float(s["p_model"]), 4),
                "p_devig": round(float(s["p_devig"]), 4),
                "predicted_score": s.get("predicted_score", "1-1"),
                "ticket_source": ticket_name,
                "strategy": strategy,
            }

            ev_pct = round(float(s["raw_ev_pct"]), 2)

            entry = paper_logger.log_bet_candidate(
                event_id=f"MOZ_{s['match_id']}_{s['code']}",
                match=f"{s['domacin']} vs {s['gost']}",
                outcome=s["code"],
                odds=float(s["odds"]),
                prediction=pred_dict,
                ev_pct=ev_pct,
                ece_at_time=0.038,  # Calibrated macro ECE from Gate A
                bookmaker="MozzartBet",
                model_version="SharpBet-DixonColes-v17.0",
                data_status="LIVE_PARSED",
                is_executable=True,
                raw_input_data={
                    "match_id": s["match_id"],
                    "takmicenje": s["takmicenje"],
                    "vreme": s["vreme"],
                    "odds": s["odds"],
                    "selection_desc": s["selection_desc"],
                },
            )
            logged_bets.append(entry)

    logger.info(f"   Appended {len(logged_bets)} unique candidate wagers to paper_trading_log.jsonl.")

    # 4. Save JSON and Markdown Reports
    output_dir = os.path.join(PROJECT_ROOT, "unified_betting_core", "output")
    os.makedirs(output_dir, exist_ok=True)
    out_json_path = os.path.join(output_dir, "mozzart_tickets.json")
    out_md_path = os.path.join(output_dir, "mozzart_tiketi_izvestaj.md")

    with open(out_json_path, "w", encoding="utf-8") as f:
        json.dump(ticket_res, f, ensure_ascii=False, indent=2)

    generate_markdown_report(ticket_res, out_md_path)
    logger.info(f"📄 Markdown Report generated: {out_md_path}")
    logger.info(f"💾 JSON Ticket Artifact generated: {out_json_path}")

    # 5. Emit Summary Event to PostHog
    emit_telemetry_event(
        event_name="sharpbet_paper_cycle_completed",
        properties={
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tickets_generated": len(tickets),
            "unique_bets_logged": len(logged_bets),
            "sample_ticket_names": [t["ticket_name"] for t in tickets],
            "total_odds_list": [t["total_odds"] for t in tickets],
            "operational_mode": "PAPER_TRADING_RESEARCH_ONLY",
            "audit_file": paper_logger.log_path,
        },
    )

    logger.info("🚀 Telemetry cycle complete. All events dispatched to PostHog.")
    logger.info("=" * 75)

    return {
        "status": "SUCCESS",
        "tickets_count": len(tickets),
        "logged_bets_count": len(logged_bets),
        "tickets": tickets,
    }


if __name__ == "__main__":
    run_cycle()
