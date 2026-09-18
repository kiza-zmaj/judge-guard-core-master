# 🛡️ JudgeGuard Core — Autonomous AI Governance & Safety Platform

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python: 3.12+](https://img.shields.io/badge/Python-3.12%2B-brightgreen.svg)](https://www.python.org/)
[![MCP Spec: 2025-11-25](https://img.shields.io/badge/MCP-2025--11--25-orange.svg)](https://modelcontextprotocol.io/)

JudgeGuard is an autonomous AI governance gatekeeper and multi-layer verification engine that enforces deterministic safety constraints, semantic intent drift detection, and pre-action permission checks before any tool, shell command, or API call is executed.

---

## 🚀 Amazon Developer Hackathon 2026 Submission

> **Standalone Hackathon Repository:** [https://github.com/kizabgd123/judgeguard-alexa-mcp](https://github.com/kizabgd123/judgeguard-alexa-mcp)  
> **Primary Track:** Alexa+ (Self-Hosted MCP Streamable HTTP Server + Web Simulator)  
> **Mini-Challenges:** AWS Builder Challenge (Bedrock Runtime) + Open Source Challenge (MIT License)  
> **Package Directory:** [`packages/judgeguard_mcp_server/`](packages/judgeguard_mcp_server/)  
> **Master Submission Checklist:** [`MASTER_SUBMISSION_CHECKLIST.md`](MASTER_SUBMISSION_CHECKLIST.md)

JudgeGuard has been ported and extended as a native **Model Context Protocol (MCP)** server implementing the **2025-11-25+ Streamable HTTP** specification for the Amazon Alexa+ ecosystem.

### Key Hackathon Components:
- **Streamable HTTP MCP Server (`packages/judgeguard_mcp_server/server.py`):** JSON-RPC 2.0 over HTTP POST with SSE event streaming (`protocolVersion: 2025-11-25`).
- **AWS Bedrock Reasoning (`packages/judgeguard_mcp_server/bedrock_client.py`):** Multi-model risk analysis using Claude 3.5 Sonnet and Amazon Titan Express.
- **NotebookLM RAG Grounding (`packages/judgeguard_mcp_server/rag_client.py`):** Authoritative rules and knowledge retrieval from NotebookLM (`82440dea-0a12-40a7-a249-0ba460f69611`).
- **Alexa+ Experience Web Simulator (`packages/judgeguard_mcp_server/static/index.html`):** Interactive demonstration web application with real-time SSE stream and HUD.
- **Unit & Protocol Tests (`packages/judgeguard_mcp_server/test_server.py`):** 10/10 synchronous unit tests passing in 0.051s.

---

## ⚡ Quick Start: Running the Alexa+ MCP Server

```bash
# 1. Clone repository
git clone https://github.com/kizabgd123/judge-guard-core-master.git
cd judge-guard-core-master

# 2. Set up virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt
pip install -e packages/judgeguard_mcp_server/

# 4. Run MCP Server & Web Simulator (port 8765)
python3 packages/judgeguard_mcp_server/server.py

# 5. Open Simulator in browser
# http://127.0.0.1:8765/
```

To run the verification test suite:
```bash
python3 -m unittest packages/judgeguard_mcp_server/test_server.py
```

---

## 🏗️ JudgeGuard Architecture & Verification Layers

```
User Voice / Action
        ↓
Alexa+ Host / AI Agent
        ↓ (MCP Streamable HTTP: tools/call)
┌────────────────────────────────────────────────────────┐
│             JudgeGuard Governance Gateway              │
│                                                        │
│  Layer 00: Destructive & Dangerous Shell Filter        │
│  Layer 01: Role & Tool Boundary Enforcement            │
│  Layer 02: Google NotebookLM RAG Policy Grounding      │
│  Layer 03: AWS Bedrock Claude 3.5 / Titan Reasoning   │
└────────────────────────────────────────────────────────┘
        ↓
    VERDICT
   ├── APPROVED  → Execute tool & emit audit event to SSE stream
   └── BLOCKED   → Terminate action safely & log incident
```

---

## 📁 Repository Layout

```
judge-guard-core-master/
├── LICENSE                                # Root MIT License
├── MASTER_SUBMISSION_CHECKLIST.md         # Master submission audit & verification checklist
├── judge_guard.py                         # Core 3-layer CLI verification gatekeeper
├── packages/
│   └── judgeguard_mcp_server/             # Alexa+ MCP Streamable HTTP package
│       ├── server.py                      # FastAPI Streamable HTTP MCP server
│       ├── bedrock_client.py              # AWS Bedrock runtime client
│       ├── rag_client.py                  # NotebookLM RAG integration
│       ├── test_server.py                 # Automated unit tests (10/10 passing)
│       ├── static/index.html              # Alexa+ Experience Web Simulator
│       ├── pyproject.toml                 # Package definition
│       ├── LICENSE                        # MIT License
│       ├── AWS_PRODUCT_FEEDBACK.md        # Formatted feedback for Devpost
│       ├── HACKATHON_FRICTION_LOG.md      # Detailed friction logs for bonus
│       └── DEMO_VIDEO_SCRIPT.md           # 2:45 video demo script
└── src/antigravity_core/                  # Governance runtime libraries
```

---

## 📄 License

This project is open source and available under the terms of the [MIT License](LICENSE).
