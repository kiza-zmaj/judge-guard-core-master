#!/usr/bin/env python3
"""
Closed Loop Pipeline: NotebookLM + Kaggle CLI
=============================================
End-to-end integration orchestrating NotebookLM consultation (Source of Truth)
and Kaggle CLI automated execution across all 5 competition phases.
"""

import logging
import os
from typing import Dict, Any, List, Optional
from pathlib import Path

from src.kaggle_stream.nlm_rule_verifier import NLMRuleVerifier
from src.kaggle_stream.kaggle_cli_runner import KaggleCLIRunner

logger = logging.getLogger(__name__)

class ClosedLoopPipeline:
    """
    Orchestrates the hypothesis -> verification -> execution -> submission -> evaluation cycle.
    """
    def __init__(
        self,
        competition_id: str,
        notebook_id: Optional[str] = None,
        verifier: Optional[NLMRuleVerifier] = None,
        runner: Optional[KaggleCLIRunner] = None
    ):
        self.competition_id = competition_id
        self.verifier = verifier or NLMRuleVerifier(notebook_id=notebook_id)
        self.runner = runner or KaggleCLIRunner()
        self.history: List[Dict[str, Any]] = []

    def verify_hypothesis_safety(self, hypothesis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Gate 1: Verify the proposed hypothesis against competition rules grounded in NotebookLM.
        """
        uses_external = hypothesis.get("uses_external_data", False)
        ext_check = self.verifier.verify_external_data_rules(self.competition_id, uses_external)
        
        if not ext_check["compliant"]:
            return {
                "approved": False,
                "reason": ext_check["reason"],
                "phase": "RULE_VERIFICATION_FAILED"
            }

        target_metric = hypothesis.get("metric_name", "LogLoss")
        metric_check = self.verifier.verify_metric_constraint(self.competition_id, target_metric)

        return {
            "approved": True,
            "metric_check": metric_check,
            "ext_check": ext_check,
            "phase": "RULE_VERIFICATION_APPROVED"
        }

    def run_cv_experiment(self, y_true: List[int], y_pred: List[float]) -> float:
        """
        Calculate local Cross-Validation score out-of-sample (Brier / MSE / LogLoss equivalent).
        """
        if not y_true or not y_pred or len(y_true) != len(y_pred):
            raise ValueError("Mismatched or empty labels/predictions in CV computation.")
        
        # Simple deterministic Brier Score calculation
        brier = sum((yt - yp) ** 2 for yt, yp in zip(y_true, y_pred)) / len(y_true)
        return round(brier, 6)

    def execute_closed_loop_iteration(
        self,
        hypothesis: Dict[str, Any],
        submission_file: str,
        y_true: Optional[List[int]] = None,
        y_pred: Optional[List[float]] = None
    ) -> Dict[str, Any]:
        """
        Execute full closed-loop step:
        1. Consult NotebookLM rules
        2. If approved -> run local CV
        3. Submit via Kaggle CLI
        4. Poll submission and update loop history
        """
        # Step 1: NotebookLM Rule Check
        safety_eval = self.verify_hypothesis_safety(hypothesis)
        if not safety_eval["approved"]:
            logger.warning(f"🛑 ClosedLoop: Hypothesis blocked by NotebookLM rules: {safety_eval['reason']}")
            record = {
                "hypothesis": hypothesis,
                "status": "BLOCKED",
                "reason": safety_eval["reason"],
                "submitted": False
            }
            self.history.append(record)
            return record

        # Step 2: Local CV Evaluation
        cv_score = None
        if y_true and y_pred:
            cv_score = self.run_cv_experiment(y_true, y_pred)

        # Step 3: Kaggle CLI Submission
        desc = hypothesis.get("description", "Automated Closed-Loop Pipeline Submission")
        sub_res = self.runner.submit_prediction(self.competition_id, submission_file, desc)
        
        if not sub_res["success"]:
            record = {
                "hypothesis": hypothesis,
                "status": "SUBMISSION_FAILED",
                "error": sub_res.get("error"),
                "cv_score": cv_score,
                "submitted": False
            }
            self.history.append(record)
            return record

        # Step 4: Status Polling
        poll_res = self.runner.poll_submission_status(self.competition_id, max_retries=3, delay_sec=0.1)

        record = {
            "hypothesis": hypothesis,
            "status": "CYCLE_COMPLETE",
            "cv_score": cv_score,
            "submission_id": sub_res.get("file"),
            "polling_status": poll_res.get("status"),
            "submitted": True
        }
        self.history.append(record)
        return record
