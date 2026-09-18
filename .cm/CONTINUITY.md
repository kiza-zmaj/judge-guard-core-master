# Project Continuity & Working Memory: JudgeGuard Core

- **Active Goal**: Amazon Developer Hackathon 2026 - JudgeGuard Autonomous AI Governance & Alexa+ MCP Bridge
- **Current Phase**: Phase 1: Architecture & OpenSpec Setup
- **Working Context**:
  - Primary Track: Alexa+ (Self-hosted MCP Server, Streamable HTTP spec 2025-11-25+ & Simulated Web Experience)
  - Mandatory RAG & Data Engine: NotebookLM is the authoritative grounding and RAG engine
  - Mini-Challenges: AWS Builder (Bedrock integration) + Open Source (MIT package)
  - Master Reference: NotebookLM (UUID `82440dea-0a12-40a7-a249-0ba460f69611`) & Official Rules
  - Governance Authority: Pre-Action Verification Workflow enforced via `judge_guard.py`
- **Next Actions**:
  1. Task 1.3: Initialize MCP Server package structure (`packages/judgeguard-mcp-server/`)
  2. Task 2.1: Implement Streamable HTTP transport and JSON-RPC 2.0 router
  3. Task 2.2: Implement `judgeguard_verify_action` MCP tool
  4. Task 2.3: Implement `judgeguard_notebooklm_rag` mandatory RAG tool
