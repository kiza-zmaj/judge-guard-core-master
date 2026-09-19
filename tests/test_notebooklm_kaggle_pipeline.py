#!/usr/bin/env python3
"""
Test Suite: NotebookLM + Kaggle CLI Closed-Loop Pipeline
=========================================================
Adheres 1:1 to tests/specs/notebooklm_kaggle_pipeline_spec.md
Authored under spec-test persona guidelines and AAA pattern.
"""

import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.kaggle_stream.nlm_rule_verifier import NLMRuleVerifier
from src.kaggle_stream.kaggle_cli_runner import KaggleCLIRunner
from src.kaggle_stream.closed_loop_pipeline import ClosedLoopPipeline


class TestNotebookLMKagglePipeline(unittest.TestCase):
    """
    Comprehensive verification suite testing the 5-phase NotebookLM & Kaggle CLI integration.
    """

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.competition_id = "test-football-analytics"
        self.notebook_id = "83fc213b-0684-4251-8980-42e0610a6742"

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    # ------------------------------------------------------------------------
    # NLM-01: NotebookLM Alias and UUID Resolution
    # ------------------------------------------------------------------------
    def test_NLM_01_notebook_resolution(self):
        """
        [NLM-01] Positive Test: Ensure notebook_id or alias initializes cleanly
        and falls back to standard environment defaults.
        """
        # Arrange
        custom_id = "custom-competition-uuid"
        
        # Act
        verifier_custom = NLMRuleVerifier(notebook_id=custom_id)
        verifier_default = NLMRuleVerifier()

        # Assert
        self.assertEqual(verifier_custom.notebook_id, custom_id)
        self.assertIsNotNone(verifier_default.notebook_id)

    # ------------------------------------------------------------------------
    # NLM-02: Rule and Metric Constraint Extraction
    # ------------------------------------------------------------------------
    @patch("subprocess.run")
    def test_NLM_02_rule_and_metric_constraint_query(self, mock_run):
        """
        [NLM-02] Positive / Mock Test: Query NotebookLM brain and extract grounded metric constraints.
        """
        # Arrange
        mock_proc = MagicMock()
        mock_proc.stdout = "The official evaluation metric is LogLoss. Missing values must be median-imputed."
        mock_run.return_value = mock_proc
        verifier = NLMRuleVerifier(notebook_id=self.notebook_id)

        # Act
        result = verifier.verify_metric_constraint(self.competition_id, "LogLoss")

        # Assert
        self.assertTrue(result["compliant"])
        self.assertEqual(result["metric_name"], "LogLoss")
        self.assertIn("LogLoss", result["grounded_response"])
        mock_run.assert_called_once()

    # ------------------------------------------------------------------------
    # KAG-01: Kaggle Credentials and Environment Verification
    # ------------------------------------------------------------------------
    def test_KAG_01_kaggle_credentials_environment(self):
        """
        [KAG-01] Security / State Test: Verify detection of valid ~/.kaggle/kaggle.json
        and proper error signaling when credentials are missing.
        """
        # Arrange: create mock valid kaggle.json
        valid_creds_dir = Path(self.test_dir) / ".kaggle"
        valid_creds_dir.mkdir()
        creds_file = valid_creds_dir / "kaggle.json"
        with open(creds_file, "w") as f:
            json.dump({"username": "kizabgd123", "key": "secret_token_123"}, f)

        # Act: Check valid environment
        runner_valid = KaggleCLIRunner(kaggle_config_dir=str(valid_creds_dir))
        res_valid = runner_valid.check_environment()

        # Act: Check missing environment
        empty_dir = Path(self.test_dir) / "empty"
        empty_dir.mkdir()
        runner_missing = KaggleCLIRunner(kaggle_config_dir=str(empty_dir))
        res_missing = runner_missing.check_environment()

        # Assert
        self.assertTrue(res_valid["ready"])
        self.assertEqual(res_valid["username"], "kizabgd123")
        self.assertFalse(res_missing["ready"])
        self.assertEqual(res_missing["status"], "MISSING_CREDENTIALS")

    # ------------------------------------------------------------------------
    # KAG-02: Kaggle CLI Data Download & Extraction
    # ------------------------------------------------------------------------
    @patch("subprocess.run")
    def test_KAG_02_kaggle_cli_data_download_extraction(self, mock_run):
        """
        [KAG-02] Integration / Mock Test: Verify download command structure and directory handling.
        """
        # Arrange
        mock_proc = MagicMock()
        mock_proc.stdout = "Downloading test-football-analytics.zip..."
        mock_run.return_value = mock_proc
        runner = KaggleCLIRunner()
        target_dir = Path(self.test_dir) / "data"

        # Act
        result = runner.download_competition_data(self.competition_id, str(target_dir))

        # Assert
        self.assertTrue(result["success"])
        self.assertEqual(result["competition_id"], self.competition_id)
        mock_run.assert_called_once()
        cmd_called = mock_run.call_args[0][0]
        self.assertIn("competitions", cmd_called)
        self.assertIn("download", cmd_called)
        self.assertIn(self.competition_id, cmd_called)

    # ------------------------------------------------------------------------
    # EDA-01: Data Integrity & Schema Validation
    # ------------------------------------------------------------------------
    def test_EDA_01_data_integrity_schema_validation(self):
        """
        [EDA-01] Functional Test: Validate submission schema against expected competition columns.
        """
        # Arrange
        verifier = NLMRuleVerifier()
        valid_cols = ["id", "target"]
        invalid_cols = ["feature1", "feature2"]

        # Act
        valid_check = verifier.verify_submission_schema(self.competition_id, valid_cols, row_count=100)
        invalid_check = verifier.verify_submission_schema(self.competition_id, invalid_cols, row_count=100)

        # Assert
        self.assertTrue(valid_check["compliant"])
        self.assertTrue(valid_check["valid_columns"])
        self.assertFalse(invalid_check["compliant"])
        self.assertFalse(invalid_check["valid_columns"])

    # ------------------------------------------------------------------------
    # CV-01: Local Cross-Validation Replicate
    # ------------------------------------------------------------------------
    def test_CV_01_local_cross_validation_replicate(self):
        """
        [CV-01] Math / Algorithmic Test: Verify deterministic out-of-sample CV score calculation.
        """
        # Arrange
        pipeline = ClosedLoopPipeline(competition_id=self.competition_id)
        y_true = [1, 0, 1, 1, 0]
        y_pred = [0.9, 0.1, 0.8, 0.95, 0.05]

        # Act
        # Squared error per item: (1-0.9)^2=0.01, (0-0.1)^2=0.01, (1-0.8)^2=0.04, (1-0.95)^2=0.0025, (0-0.05)^2=0.0025
        # Total = 0.065 / 5 = 0.013
        brier_score = pipeline.run_cv_experiment(y_true, y_pred)

        # Assert
        self.assertEqual(brier_score, 0.013)

    # ------------------------------------------------------------------------
    # SUB-01: Kaggle CLI Automated Prediction Submission
    # ------------------------------------------------------------------------
    @patch("subprocess.run")
    def test_SUB_01_kaggle_cli_automated_submission(self, mock_run):
        """
        [SUB-01] Positive / Mock Test: Ensure predictions file submission executes correctly.
        """
        # Arrange
        mock_proc = MagicMock()
        mock_proc.stdout = "Successfully submitted to test-football-analytics"
        mock_run.return_value = mock_proc
        runner = KaggleCLIRunner()
        
        # Create a dummy submission file
        sub_file = Path(self.test_dir) / "submission.csv"
        with open(sub_file, "w") as f:
            f.write("id,target\n1,0.85\n2,0.12\n")

        # Act
        result = runner.submit_prediction(
            competition_id=self.competition_id,
            file_path=str(sub_file),
            message="Test baseline submission"
        )

        # Assert
        self.assertTrue(result["success"])
        self.assertIn("Successfully submitted", result["output"])
        mock_run.assert_called_once()
        cmd_args = mock_run.call_args[0][0]
        self.assertIn("submit", cmd_args)
        self.assertIn(str(sub_file), cmd_args)

    # ------------------------------------------------------------------------
    # SUB-02: Submission Status Polling & Leaderboard Rank Extraction
    # ------------------------------------------------------------------------
    @patch("subprocess.run")
    def test_SUB_02_submission_status_polling_and_leaderboard(self, mock_run):
        """
        [SUB-02] Polling Test: Verify status loop polling terminates once scored.
        """
        # Arrange
        mock_proc = MagicMock()
        mock_proc.stdout = "fileName,date,description,status,publicScore\nsubmission.csv,2026-09-18,Test,complete,0.1542"
        mock_run.return_value = mock_proc
        runner = KaggleCLIRunner()

        # Act
        poll_res = runner.poll_submission_status(self.competition_id, max_retries=2, delay_sec=0.01)

        # Assert
        self.assertTrue(poll_res["completed"])
        self.assertEqual(poll_res["status"], "SCORED")

    # ------------------------------------------------------------------------
    # LOOP-01: Closed-Loop Hypothesis Gate — Approved Execution Flow
    # ------------------------------------------------------------------------
    @patch.object(KaggleCLIRunner, "submit_prediction")
    @patch.object(KaggleCLIRunner, "poll_submission_status")
    @patch.object(NLMRuleVerifier, "query_rule_constraint")
    def test_LOOP_01_closed_loop_hypothesis_gate_approved(self, mock_nlm, mock_poll, mock_submit):
        """
        [LOOP-01] E2E Positive Test: Rule-compliant hypothesis proceeds through CV,
        submission, and status evaluation.
        """
        # Arrange
        mock_nlm.return_value = {
            "success": True,
            "answer": "Only in-competition data is permitted. Target metric is LogLoss."
        }
        mock_submit.return_value = {"success": True, "file": "submission.csv"}
        mock_poll.return_value = {"status": "SCORED", "completed": True}

        pipeline = ClosedLoopPipeline(competition_id=self.competition_id)
        hypothesis = {
            "description": "Baseline LightGBM 5-fold CV",
            "uses_external_data": False,
            "metric_name": "LogLoss"
        }
        sub_file = Path(self.test_dir) / "submission.csv"
        sub_file.write_text("id,target\n1,0.5\n")

        # Act
        result = pipeline.execute_closed_loop_iteration(
            hypothesis=hypothesis,
            submission_file=str(sub_file),
            y_true=[1, 0],
            y_pred=[0.8, 0.2]
        )

        # Assert
        self.assertEqual(result["status"], "CYCLE_COMPLETE")
        self.assertTrue(result["submitted"])
        self.assertIsNotNone(result["cv_score"])
        mock_submit.assert_called_once()

    # ------------------------------------------------------------------------
    # LOOP-02: Closed-Loop Hypothesis Gate — Rule Violation Interception
    # ------------------------------------------------------------------------
    @patch.object(KaggleCLIRunner, "submit_prediction")
    @patch.object(NLMRuleVerifier, "query_rule_constraint")
    def test_LOOP_02_closed_loop_hypothesis_gate_violation_interception(self, mock_nlm, mock_submit):
        """
        [LOOP-02] E2E Security / Gate Test: Prohibited external data hypothesis is intercepted
        and halted BEFORE any submission call is dispatched.
        """
        # Arrange
        mock_nlm.return_value = {
            "success": True,
            "answer": "External data is prohibited by competition rules. Zero tolerance."
        }
        pipeline = ClosedLoopPipeline(competition_id=self.competition_id)
        invalid_hypothesis = {
            "description": "Pretrained LLM with external internet dataset",
            "uses_external_data": True,
            "metric_name": "LogLoss"
        }
        sub_file = Path(self.test_dir) / "submission.csv"
        sub_file.write_text("id,target\n1,0.5\n")

        # Act
        result = pipeline.execute_closed_loop_iteration(
            hypothesis=invalid_hypothesis,
            submission_file=str(sub_file)
        )

        # Assert
        self.assertEqual(result["status"], "BLOCKED")
        self.assertFalse(result["submitted"])
        self.assertIn("prohibited", result["reason"].lower())
        # CRITICAL SAFETY GATE: Submission MUST NOT be called!
        mock_submit.assert_not_called()


if __name__ == "__main__":
    unittest.main()
