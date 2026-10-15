# RSNA Knee Sub4 v2: Push Apex Grandmaster V14 DualRaptor Anti-Tie Kernel Implementation Plan

## Overview
Implement and push the Apex Grandmaster V14 DualRaptor Anti-Tie Kernel for RSNA Knee Sub4 v2, incorporating anti-tie ranking calibration, dual raptor ensembling, and strict JudgeGuard/Ollama verification.

## Scope Definition (CRITICAL)
### In Scope
- Configure and package the RSNA Knee Sub4 v2 kernel (`Apex Grandmaster V14 DualRaptor Anti-Tie`).
- Run pre-action verification via JudgeGuard and Layer 000 Ollama Gemma 4.
- Push kernel to Kaggle/remote deployment target.
- Create git checkpoint and log telemetry.
### Out of Scope (DO NOT TOUCH)
- Unrelated datasets or non-RSNA competitions.
- Refactoring core platform packages outside the submission path.

## Current State Analysis
- Research approved (`research/phase2_analysis/research_rsna_knee_v2_2026-10-15.md`, `research/phase2_analysis/research_review.md`).
- Pipeline patterns established in `research/kaggle_s6e9/`.

## Implementation Phases
### Phase 1: Kernel Configuration & Calibration
- **Goal**: Prepare DualRaptor anti-tie ranking calibration script and metadata.
- **Steps**:
  1. [ ] Validate configuration parameters for V14 DualRaptor ensemble.
  2. [ ] Run local dry-run check on metadata scoring.
- **Verification**: `python3 research/kaggle_s6e9/run_s6e9_pipeline.py` or equivalent check.

### Phase 2: Submission & Verification
- **Goal**: Execute Layer 000 safety gate and push kernel.
- **Steps**:
  1. [ ] Execute pre-action verification via `./gemini_cli.sh`.
  2. [ ] Submit kernel and verify success.
  3. [ ] Create git checkpoint commit `checkpoint: Push RSNA Knee Sub4 v2 Apex Grandmaster V14 DualRaptor Kernel`.
- **Verification**: `git status`, `git log -n 1`, telemetry badge logging.
