---
name: judgeguard-governance
description: Implements Master Orchestration governance rules for autonomous code repair and targeted test verification in offline SWE-bench environments.
---

# JudgeGuard Governance Skill

## Overview
This skill guides the agent through the JudgeGuard verification lifecycle inside the SWE-bench sandbox:
1. **Target Identification**: Extract symbol identifiers from issue reports.
2. **Code Graph Resolution**: Navigate dependency graphs using pre-indexed code embeddings.
3. **Surgical Diff Application**: Generate resilient code edits with 3-tier string matching.
4. **Targeted Verification**: Run isolated test cases while protecting runner configurations and preventing full test suite timeouts.
5. **Patch Checkpoint Extraction**: Produce clean, zero-pollution unified git diffs.
