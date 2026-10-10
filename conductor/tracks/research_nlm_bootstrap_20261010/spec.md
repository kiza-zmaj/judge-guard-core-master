# Specification: Research Workspace Bootstrap with NLM & MCP Suite

## Overview
This track bootstraps an autonomous AI research environment with:
1. Native integration to Google NotebookLM (NLM) as the authoritative Grounding Source.
2. Full MCP server integration with `@modelcontextprotocol/server-sequential-thinking` for recursive hypotheses.
3. Automated startup verification script verifying MCP status, NotebookLM credentials/notebook access, and JudgeGuard safety compliance.
4. Clean export pipeline for research reports, audio summaries, and cited references.

## Functional Requirements
- **FR-1:** Provide a unified bootstrap script `bootstrap_workspace.py` that validates all required tooling:
  - Python 3.12 virtualenv and dependencies.
  - MCP configuration (`sequential-thinking`, `chrome-devtools-mcp`, `redis`).
  - NotebookLM connectivity (resolving notebook ID from `.cm/notebook_id` or alias).
- **FR-2:** Provide an interactive and programmatic research interface to query NotebookLM notebooks and extract grounded answers with citations.
- **FR-3:** Comply strictly with Master Orchestration (`GEMINI.md`, `master_orchestration.md`, `judge_guard.py`) — zero mocks, atomic task logging, and git checkpoints.
