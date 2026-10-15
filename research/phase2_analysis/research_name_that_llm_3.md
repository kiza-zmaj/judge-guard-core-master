# Research: Record Name That LLM 3 Submissions Leaderboard Scores and Verification

**Date**: 2026-10-15

## 1. Executive Summary
This research documents the current implementation and status of the "Name That LLM 3" competition pipeline, submissions (Sub1 Fast Stylometric Baseline, Sub2 UltraBERT 5-Fold Deep Classifier, Sub3 Apex GM Hierarchical Blend, Sub4 Qwen3 Dual Fusion SOTA), and their leaderboard evaluation and verification mechanisms across `WORK_LOG.md`, `src/kaggle_stream/`, and research scripts.

## 2. Technical Context
- **Kaggle CLI Integration**: `src/kaggle_stream/kaggle_cli_runner.py` provides competition management, dataset download, automated submission (`submit_to_competition`), and leaderboard polling (`get_leaderboard_position`).
- **Submission Tracking**: Multiple iterations of submissions have been pushed and submitted, as documented in `WORK_LOG.md` (lines 643-695).
- **Verification Engine**: `judge_guard.py` enforces pre-execution validation and safety checks across all actions.

## 3. Findings & Analysis
- Submissions for Name That LLM 3 include:
  1. Sub1: Fast Stylometric Baseline
  2. Sub2: UltraBERT 5-Fold Deep Classifier
  3. Sub3: Apex GM Hierarchical Blend
  4. Sub4: Qwen3 Dual Fusion SOTA
- Leaderboard polling scripts and APIs (`kaggle_cli_runner.py:218`) query Kaggle CLI to extract public/private leaderboard positions and scores.
- Verification status is fully logged in `WORK_LOG.md` with recent git checkpoints.

## 4. Technical Constraints
- Kaggle API rate limits and competition submission quotas.
- Authentication credentials via `kaggle.json` required for live CLI interaction.
- Strict adherence to Layer 000 Ollama Gemma 4 ticket gates and JudgeGuard validation.

## 5. Architecture Documentation
- Follows the Antigravity Master Orchestration workflow (`MASTER_ORCHESTRATION.md`).
- Uses SQLite telemetry (`research.db`) and `git_bolt_jules_gate.py` for token auditing and badge generation.
