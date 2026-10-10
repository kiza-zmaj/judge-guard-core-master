import unittest
import os
import sys
import tempfile
import sqlite3

# Ensure repo root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.antigravity_core.telemetry import TelemetryTracker, calculate_cost
from src.antigravity_core.token_cleaner import TokenCleaner, estimate_tokens
from git_bolt_jules_gate import cmd_audit, cmd_badge


class TestBoltJulesTelemetry(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.tmp_dir, "test_research.db")
        self.tracker = TelemetryTracker(db_path=self.db_path)

    def test_record_and_summary_telemetry(self):
        # Record Bolt call — no thinking tokens (classic model)
        rec_bolt = self.tracker.record_call(
            agent="bolt",
            action="Git Staged Context Pruning",
            model="gemini-3.7-flash",
            prompt_tokens=500,
            completion_tokens=200,
            thinking_tokens=0,
            total_tokens=700,
            cached_tokens=1000,
            tokens_saved=3500,
            latency_ms=210.5
        )
        self.assertEqual(rec_bolt["agent"], "bolt")
        self.assertEqual(rec_bolt["tokens_saved"], 3500)
        self.assertGreater(rec_bolt["cost_estimate_usd"], 0)
        self.assertEqual(rec_bolt["thinking_tokens"], 0)

        # Record Jules call — no thinking tokens
        rec_jules = self.tracker.record_call(
            agent="jules",
            action="PR Maintenance Triage",
            model="gemini-3.7-flash",
            prompt_tokens=800,
            completion_tokens=400,
            thinking_tokens=0,
            total_tokens=1200,
            cached_tokens=2000,
            tokens_saved=5000,
            latency_ms=380.0
        )
        self.assertEqual(rec_jules["agent"], "jules")

        # Check summary
        summary = self.tracker.get_summary()
        self.assertEqual(summary["total_calls"], 2)
        self.assertEqual(summary["total_tokens"], 1900)
        self.assertEqual(summary["total_tokens_saved"], 8500)
        self.assertIn("bolt", summary["by_agent"])
        self.assertIn("jules", summary["by_agent"])

    def test_thinking_tokens_auto_resolution(self):
        """
        Verifies the exact 491-token arithmetic from the auditor's review:
          prompt=2546, completion=2, total=3039 → thinking_tokens = 3039 - (2546+2) = 491
        This is the Gemini Flash Thinking/reasoning budget.
        """
        rec = self.tracker.record_call(
            agent="gemini_client",
            action="generate_content",
            model="gemini-3.8-flash",
            prompt_tokens=2546,
            completion_tokens=2,
            # thinking_tokens NOT passed — auto-resolved from total
            total_tokens=3039,
            cached_tokens=0,
            tokens_saved=22,
            latency_ms=5555.2,
        )
        # Auto-resolved thinking = 3039 - (2546 + 2 + 0) = 491
        self.assertEqual(rec["thinking_tokens"], 491)
        # Arithmetic is clean
        self.assertEqual(
            rec["prompt_tokens"] + rec["completion_tokens"] + rec["thinking_tokens"],
            rec["total_tokens"]
        )
        # tokens_saved is an estimate from character heuristics (len/3.8)
        self.assertIsInstance(rec["tokens_saved"], int)

    def test_token_cleaner_filtering(self):
        files = [
            "src/antigravity_core/gemini_client.py",
            "local_py/local/lib/python3.14/dist-packages/googleapiclient/discovery_cache/documents/test.json",
            "tests/test_something.py",
            ".venv/lib/python3.12/site-packages/package.py",
            "package-lock.json",
            "README.md"
        ]
        clean_files, excluded_count = TokenCleaner.clean_file_paths(files)
        self.assertEqual(len(clean_files), 3)
        self.assertIn("src/antigravity_core/gemini_client.py", clean_files)
        self.assertIn("tests/test_something.py", clean_files)
        self.assertIn("README.md", clean_files)
        self.assertEqual(excluded_count, 3)

    def test_token_cleaner_diff_pruning(self):
        raw_diff = (
            "diff --git a/local_py/discovery_cache.json b/local_py/discovery_cache.json\n"
            "+ {\"massive_payload\": [1, 2, 3]}\n"
            "diff --git a/src/main.py b/src/main.py\n"
            "@@ -1,3 +1,4 @@\n"
            " def hello():\n"
            "+    return 'world'\n"
        )
        cleaned_diff, tokens_saved = TokenCleaner.clean_git_diff(raw_diff)
        self.assertIn("[Bolt/Jules Token Cleaner: skipped", cleaned_diff)
        self.assertIn("def hello()", cleaned_diff)
        self.assertGreater(tokens_saved, 0)

    def test_badge_formatting(self):
        badge = self.tracker.format_badge(
            agent="bolt",
            action="Test Action",
            total_tokens=1500,
            tokens_saved=4200,
            latency_ms=150.2,
            model="gemini-3.7-flash"
        )
        self.assertIn("Telemetry (BOLT)", badge)
        self.assertIn("1,500 tokens used", badge)
        # Badge labels savings as estimated (heuristic, not tokenizer-verified)
        self.assertIn("4,200 tokens saved (est)", badge)


if __name__ == "__main__":
    unittest.main()
