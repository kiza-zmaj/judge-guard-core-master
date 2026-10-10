#!/usr/bin/env python3
"""
Unit tests for NotebookLM Orchestrator Agent (nlm_orchestrator.py).
Tests notebook catalog resolution, titles, aliases, and active notebook binding.
"""

import unittest
from pathlib import Path

import nlm_orchestrator


class TestNLMOrchestrator(unittest.TestCase):
    """Test suite for nlm_orchestrator resolution logic and catalog integrity."""

    def test_catalog_structure(self):
        """Verify all entries in NOTEBOOK_CATALOG have required fields."""
        self.assertGreater(len(nlm_orchestrator.NOTEBOOK_CATALOG), 0)
        for item in nlm_orchestrator.NOTEBOOK_CATALOG:
            self.assertIn("alias", item)
            self.assertIn("title", item)
            self.assertIn("id", item)
            self.assertTrue(len(item["id"]) >= 32, f"Invalid UUID: {item['id']}")

    def test_fk_sava_resolution(self):
        """Ensure fk-sava-45 resolves via alias and full human title."""
        expected_id = "3d33925e-5929-445b-8870-25f3dc23bf2b"
        self.assertEqual(nlm_orchestrator.resolve_notebook_id("fk-sava-45"), expected_id)
        self.assertEqual(nlm_orchestrator.resolve_notebook_id("sava-45"), expected_id)
        self.assertEqual(nlm_orchestrator.resolve_notebook_id("FK Sava 45"), expected_id)
        self.assertEqual(nlm_orchestrator.get_notebook_title("fk-sava-45"), "FK Sava 45")
        self.assertEqual(nlm_orchestrator.get_notebook_title(expected_id), "FK Sava 45")

    def test_fine_tuning_resolution(self):
        """Ensure fine-tuning resolves via alias and full human title."""
        expected_id = "eeb2676d-bd7f-4e73-a29b-38c43b9359d1"
        self.assertEqual(nlm_orchestrator.resolve_notebook_id("fine-tuning"), expected_id)
        self.assertEqual(nlm_orchestrator.resolve_notebook_id("finetuning"), expected_id)
        self.assertEqual(nlm_orchestrator.resolve_notebook_id("Fine-Tuning & OpenWebUI 2026"), expected_id)
        self.assertEqual(nlm_orchestrator.get_notebook_title("fine-tuning"), "Fine-Tuning & OpenWebUI 2026")
        self.assertEqual(nlm_orchestrator.get_notebook_title(expected_id), "Fine-Tuning & OpenWebUI 2026")

    def test_active_and_research_resolution(self):
        """Ensure active and research keywords resolve to registered active notebook."""
        expected_active = nlm_orchestrator.get_active_notebook_id()
        self.assertEqual(nlm_orchestrator.resolve_notebook_id("active"), expected_active)
        self.assertEqual(nlm_orchestrator.resolve_notebook_id("current"), expected_active)
        self.assertEqual(nlm_orchestrator.resolve_notebook_id("research"), expected_active)

    def test_raw_uuid_passthrough(self):
        """Ensure unknown raw UUID passes through untouched."""
        raw_uuid = "12345678-abcd-1234-abcd-1234567890ab"
        self.assertEqual(nlm_orchestrator.resolve_notebook_id(raw_uuid), raw_uuid)
        self.assertEqual(nlm_orchestrator.get_notebook_title(raw_uuid), raw_uuid)


if __name__ == "__main__":
    unittest.main()
