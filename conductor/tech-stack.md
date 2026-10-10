# Technology Stack

## Runtime & Languages
- **Python:** 3.12+ (Antigravity Virtual Environment `.venv`)
- **Node.js / npm:** v20+ for MCP servers (`@modelcontextprotocol/server-*`)
- **Shell:** Bash (Master Orchestration Wrappers)

## Core Frameworks & MCP Protocols
- **Model Context Protocol (MCP):**
  - `sequential-thinking`: Complex recursive hypothesis generation and dynamic reasoning
  - `chrome-devtools-mcp`: Browser automation, audit capture, and DOM inspection
  - `redis`: High-speed ephemeral cache and state synchronization
  - `github-mcp-server`: Repository automation and audit verification
- **NotebookLM (NLM) Suite:**
  - `nlm_orchestrator.py` & `nlm` CLI: Autonomous query, artifact retrieval, audio overview download
  - UUID Registry: `.cm/notebook_id` (`8774fd5f-d8af-4ec8-aef1-0ae81eed0902`)
- **JudgeGuard Master Orchestration:**
  - `judge_guard.py`: Multi-layer safety engine (Layer 00 to Layer 3)
  - `gemini_cli.sh` / `qwen_cli.sh`: 7-step execution & checkpoint wrapper
  - Telemetry & Token Cleaner: Token reduction, arithmetic reconciliation, and SQLite tracking
