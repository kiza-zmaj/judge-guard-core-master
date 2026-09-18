# Project Continuity & Working Memory: JudgeGuard Core

- **Active Goal**: Amazon Developer Hackathon 2026 - JudgeGuard Autonomous AI Governance & Alexa+ MCP Bridge
- **Current Phase**: Phase 3: Alexa+ Experience Web Simulator
- **Working Context**:
  - Primary Track: Alexa+ (Self-hosted MCP Server, Streamable HTTP spec 2025-11-25+ & Simulated Web Experience)
  - Mandatory RAG & Data Engine: NotebookLM is the authoritative grounding and RAG engine (Notebook UUID `82440dea-0a12-40a7-a249-0ba460f69611`)
  - Mini-Challenges: AWS Builder (Bedrock integration) + Open Source (MIT package)
  - Master Reference: NotebookLM & Official Rules (Primary Authority)
  - Governance Authority: Pre-Action Verification Workflow enforced via `judge_guard.py`

## Key Decisions
- [Decision]: Adopted MCP Streamable HTTP transport (Spec 2025-11-25+) with Server-Sent Events (SSE) on `/mcp` and JSON-RPC 2.0 router — scope: `module:packages/judgeguard_mcp_server`
- [Decision]: NotebookLM established as mandatory grounded RAG engine (`judgeguard_notebooklm_rag` & `judgeguard_audit_context`) to eliminate LLM hallucinations — scope: `global`
- [Decision]: Auto-generating Hackathon Friction Logs (`judgeguard_record_friction`) directly to JSONL to capture the 10% judging bonus — scope: `module:packages/judgeguard_mcp_server`

## Mistakes & Learnings
- **What Failed**: `await queue.put(payload)` in `broadcast_event` could stall if an SSE client disconnects or slows down.
- **How to Prevent**: Use `queue.put_nowait(payload)` and immediately purge dead queues upon exception.
- **Scope**: `file:packages/judgeguard_mcp_server/server.py`

## Completed Phases
- [x] Phase 1: OpenSpec Architecture, Core Schemas & Package Setup
- [x] Phase 2: Streamable HTTP MCP Server Implementation & Unit Tests (7/7 passing)
- [x] Code Review: /cm-code-review passed, `.cm/handoff/review.json` emitted
- [x] NotebookLM Sync: 2 Notes created and 2 Sources indexed in notebook `82440dea-0a12-40a7-a249-0ba460f69611`

## Next Actions
1. Phase 3.1: Build lightweight, high-aesthetic Web Simulator interface (Vanilla CSS + HTML5 + JS)
2. Phase 3.2: Implement simulated Alexa+ voice/text assistant with multi-turn context
3. Phase 3.3: Connect simulator to JudgeGuard MCP Server via live JSON-RPC & SSE stream
4. Phase 3.4: Implement visual JudgeGuard Verdict HUD (🟢 PASSED, 🛑 BLOCKED, 🟡 AUDITING)
