"""
Test Suite for Mozzart Quantitative Ticket Pipeline & Paper Trading Integration.
Enforces institutional rules derived from NotebookLM sources and JudgeGuard safety.
"""

import os
import sys
import unittest
import tempfile
import json
import pandas as pd
import numpy as np

# Ensure project root in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from unified_betting_core.execution.mozzart_ticket_generator import MozzartQuantitativeEngine
from unified_betting_core.execution.paper_trading_logger import PaperTradingLogger


class TestMozzartTicketPipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mecevi_file = "/home/kizamladjanijebac/Downloads/mozzart_fudbal_mecevi_2026-09-20.csv"
        cls.marketi_file = "/home/kizamladjanijebac/Downloads/mozzart_fudbal_marketi_2026-09-20.csv"
        assert os.path.exists(cls.mecevi_file), f"Missing {cls.mecevi_file}"
        assert os.path.exists(cls.marketi_file), f"Missing {cls.marketi_file}"
        cls.engine = MozzartQuantitativeEngine(cls.mecevi_file, cls.marketi_file)

    def test_01_evaluate_all_produces_bets(self):
        eval_res = self.engine.evaluate_all()
        self.assertIn("bets", eval_res)
        self.assertIn("matches", eval_res)
        bets = eval_res["bets"]
        self.assertGreater(len(bets), 50, "Expected at least 50 evaluated candidate betting markets")
        for b in bets[:50]:
            self.assertTrue(0.0 <= b["p_calibrated"] <= 1.0)
            self.assertGreaterEqual(b["odds"], 1.0)

    def test_02_build_tickets_produces_expected_strategies(self):
        eval_res = self.engine.evaluate_all()
        ticket_res = self.engine.build_tickets(eval_res)
        self.assertIn("tickets", ticket_res)
        tickets = ticket_res["tickets"]
        self.assertGreaterEqual(len(tickets), 5, "Expected at least 5 generated tickets")

        names = [t["ticket_name"].upper() for t in tickets]
        self.assertTrue(any("BANKERI" in n or "SIGURICA" in n for n in names))
        self.assertTrue(any("VALUE" in n for n in names))
        self.assertTrue(any("GOLOVI" in n for n in names))
        self.assertTrue(any("NOĆNI" in n or "NOCNI" in n for n in names))
        self.assertTrue(any("SISTEM" in n for n in names))

        for t in tickets:
            self.assertGreater(t["num_legs"], 0)
            self.assertGreater(t["total_odds"], 1.0)
            self.assertGreater(t["joint_probability_pct"], 0.0)
            self.assertGreater(t["recommended_stake_eur"], 0.0)

    def test_03_paper_trading_logger_enforces_zero_stake(self):
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            logger = PaperTradingLogger(log_path=tmp_path)
            entry = logger.log_bet_candidate(
                event_id="TEST_MATCH_001",
                match="Arsenal vs Chelsea",
                outcome="1",
                odds=2.10,
                prediction={"1": 0.52, "X": 0.26, "2": 0.22},
                ev_pct=9.2,
                ece_at_time=0.035,
                is_executable=True
            )
            self.assertEqual(entry["stake_recommended"], 0.00, "Safety Law: Paper trading stake must strictly be €0.00")
            self.assertEqual(entry["operational_mode"], "PAPER_TRADING_RESEARCH_ONLY")

            logs = logger.read_all_logs()
            self.assertEqual(len(logs), 1)
            self.assertEqual(logs[0]["event_id"], "TEST_MATCH_001")
            self.assertEqual(logs[0]["stake_recommended"], 0.00)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)


if __name__ == "__main__":
    unittest.main()
