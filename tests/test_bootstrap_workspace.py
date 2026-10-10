#!/usr/bin/env python3
"""
Test Suite: Bootstrap Workspace & NLM Grounding Telemetry
=========================================================
Tests for bootstrap_workspace.py diagnostics, NLM query bridge,
artifact extraction, and SQLite telemetry integration.
"""

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

import bootstrap_workspace


class TestBootstrapWorkspace(unittest.TestCase):
    """Test suite for research workspace bootstrap diagnostics and bridge."""

    def test_check_python_environment(self):
        """Ensure python environment check returns version and prefix."""
        result = bootstrap_workspace.check_python_environment()
        self.assertIn("python_version", result)
        self.assertIn("in_venv", result)
        self.assertIn("status", result)

    def test_check_mcp_servers(self):
        """Ensure MCP server config check inspects configured servers."""
        result = bootstrap_workspace.check_mcp_servers()
        self.assertIn("servers", result)
        self.assertIn("sequential_thinking_configured", result)
        self.assertTrue(result["sequential_thinking_configured"])

    def test_check_notebooklm(self):
        """Ensure NotebookLM status returns registered notebook id."""
        result = bootstrap_workspace.check_notebooklm()
        self.assertIn("notebook_id", result)
        self.assertIn("orchestrator_script_present", result)
        self.assertTrue(result["orchestrator_script_present"])

    def test_check_conductor_workspace(self):
        """Ensure conductor directory check verifies tracks registry."""
        result = bootstrap_workspace.check_conductor_workspace()
        self.assertTrue(result["conductor_initialized"])
        self.assertTrue(result["tracks_file_present"])
        self.assertEqual(result["status"], "INITIALIZED")

    def test_check_orchestration_safety(self):
        """Ensure Master Orchestration safety check validates JudgeGuard, Ticket, and WorkLog."""
        result = bootstrap_workspace.check_orchestration_safety()
        self.assertTrue(result["judge_guard_present"])
        self.assertTrue(result["ticket_present"])
        self.assertTrue(result["work_log_present"])
        self.assertEqual(result["status"], "ACTIVE")

    def test_extract_research_artifacts(self):
        """Ensure research artifact extraction writes summary markdown to output dir."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            res = bootstrap_workspace.extract_research_artifacts(tmp_dir)
            self.assertEqual(res["status"], "SUCCESS")
            self.assertEqual(len(res["artifacts"]), 1)
            summary_path = Path(res["artifacts"][0])
            self.assertTrue(summary_path.exists())
            self.assertIn("Grounded Research Summary", summary_path.read_text(encoding="utf-8"))

    def test_query_notebooklm_with_telemetry(self):
        """Ensure query_notebooklm executes query and writes telemetry record."""
        question = "What is the primary evaluation metric?"
        result = bootstrap_workspace.query_notebooklm(question, record_telemetry=True)
        self.assertEqual(result["question"], question)
        self.assertTrue(result["telemetry_recorded"])
        self.assertIn("telemetry_details", result)
        self.assertIn("result", result)
        self.assertTrue(result["result"]["success"])


if __name__ == "__main__":
    unittest.main()
