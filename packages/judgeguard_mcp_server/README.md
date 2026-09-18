# 🛡️ JudgeGuard — Alexa+ MCP Governance Server

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python: 3.10+](https://img.shields.io/badge/Python-3.10%2B-brightgreen.svg)](https://www.python.org/)
[![MCP Spec: 2025-11-25](https://img.shields.io/badge/MCP-2025--11--25-orange.svg)](https://modelcontextprotocol.io/)
[![Track: Alexa+](https://img.shields.io/badge/Track-Alexa%2B-blueviolet.svg)](https://amazonappdev2026.devpost.com/)
[![AWS: Bedrock](https://img.shields.io/badge/AWS-Bedrock%20Claude%203.5%20%7C%20Titan-FF9900.svg)](https://aws.amazon.com/bedrock/)

**JudgeGuard** is an autonomous AI governance gatekeeper and safety bridge developed for the **Amazon Developer Hackathon 2026** ([amazonappdev2026.devpost.com](https://amazonappdev2026.devpost.com/)).

It implements a self-hosted **Model Context Protocol (MCP)** server over **Streamable HTTP (MCP Spec 2025-11-25+)** to safeguard Alexa+ agentic interactions, prevent unauthorized high-risk operations (e.g. unlocking doors, financial transactions, destructive commands), and provide verifiable policy grounding and deep semantic reasoning via **AWS Bedrock**.

---

## 🏆 Hackathon Tracks & Submission Mapping

| Track / Mini-Challenge | Implementation Details | Evidence & Links |
| :--- | :--- | :--- |
| **Primary Track: Alexa+** | **Plan A (Core):** Self-hosted MCP Server implementing MCP spec **2025-11-25+** via Streamable HTTP with runtime tool execution.<br>**Plan B (Visual Demo):** Custom **Alexa+ Experience Web Simulator** (`static/index.html`). | [`server.py`](server.py), [`test_protocol.py`](test_protocol.py), [`static/index.html`](static/index.html) |
| **AWS Builder Mini-Challenge** | Dual model support via **AWS Bedrock Runtime**: **Anthropic Claude 3.5 Sonnet** and **Amazon Titan Text Express** (`inputText`/`textGenerationConfig`). | [`bedrock_client.py`](bedrock_client.py), [`AWS_PRODUCT_FEEDBACK.md`](AWS_PRODUCT_FEEDBACK.md) |
| **Open Source Mini-Challenge** | **Additional Companion Open-Source Project:** [kiza-zmaj/judgeguard-policy-schema](https://github.com/kiza-zmaj/judgeguard-policy-schema) — standalone Pydantic v2 governance schema & rule evaluation engine under the MIT License. | [judgeguard-policy-schema](https://github.com/kiza-zmaj/judgeguard-policy-schema), [`pyproject.toml`](pyproject.toml) |

> **Clarifications for Judges:**  
> 1. **Transport Architecture:** The implementation uses Streamable HTTP JSON-RPC POST requests (`/mcp`) for all MCP protocol operations (`initialize`, `tools/list`, `tools/call`). The GET endpoint provides an SSE event stream for UI telemetry and asynchronous audit events.  
> 2. **Policy Grounding Lineage:** Google NotebookLM was utilized during the development phase as our research reference environment. For reproducible evaluation, the public server embeds a deterministic, verified local policy corpus derived from official hackathon rules, so judges do not require access to private notebooks or external credentials.  
> 3. **AWS Bedrock Dispatch:** The repository implements live AWS Bedrock dispatch for Claude 3.5 Sonnet and Amazon Titan Text Express, while automated tests and public evaluation use a deterministic fallback when AWS credentials are unavailable.
> 4. **Alexa+ Web Simulator:** The simulator (`http://127.0.0.1:8765/simulator`) is our custom demonstration web application created to showcase real-time agentic workflows and the JudgeGuard HUD. It is not Amazon's internal simulator.

---

## ⚡ Quickstart: Running & Testing

### 1. Clone & Setup Environment
```bash
git clone https://github.com/kiza-zmaj/judgeguard-alexa-mcp.git
cd judgeguard-alexa-mcp

python3 -m venv .venv
source .venv/bin/activate

pip install -e .
```

### 2. Start the MCP Server & Web Simulator
```bash
python3 server.py
```
The server starts on `http://127.0.0.1:8765` and serves both the Streamable HTTP MCP endpoint and the interactive Web Simulator.

### 3. Run Automated Verification Tests
```bash
python3 -m unittest test_server.py test_protocol.py
```
**Test Baseline & Conformance:**
- **Primary Server Tests:** `python3 -m unittest test_server.py test_protocol.py` (21 passed, 0 failures, 0 errors)
- **Companion Schema Tests:** `pytest tests/` in [`judgeguard-policy-schema`](https://github.com/kiza-zmaj/judgeguard-policy-schema) (6 passed, 0 failures)
- **Protocol Status:** MCP Streamable HTTP implementation with protocol-level regression tests
- **Live AWS Bedrock Execution:** Optional / environment-dependent (automated tests run against deterministic offline fallback when AWS credentials are not set)
- **Environment:** Python 3.12.3 on Linux x86_64 (`Linux 6.8.0-101-generic`)

---

## 🔌 MCP Streamable HTTP Protocol (Spec 2025-11-25+)

### 1. Initialize Handshake
```bash
curl -X POST http://127.0.0.1:8765/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
      "protocolVersion": "2025-11-25",
      "clientInfo": {"name": "AlexaPlusHost", "version": "1.0.0"}
    }
  }'
```

### 2. List Available Governance Tools (`tools/list`)
```bash
curl -X POST http://127.0.0.1:8765/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "id": 2, "method": "tools/list"}'
```

### 3. Execute Pre-Action Verification (`tools/call`)
```bash
curl -X POST http://127.0.0.1:8765/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 3,
    "method": "tools/call",
    "params": {
      "name": "judgeguard_verify_action",
      "arguments": {"action": "Unlock front door for delivery driver"}
    }
  }'
```

### 4. Evaluate Action with AWS Bedrock (Claude 3.5 Sonnet or Amazon Titan)
```bash
curl -X POST http://127.0.0.1:8765/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 4,
    "method": "tools/call",
    "params": {
      "name": "judgeguard_bedrock_evaluate",
      "arguments": {
        "action": "Adjust thermostat to 21 degrees",
        "model_id": "amazon.titan-text-express-v1"
      }
    }
  }'
```

---

## 📑 Hackathon Evidence & Reference Documents

- **Master Submission Checklist:** [`MASTER_SUBMISSION_CHECKLIST.md`](MASTER_SUBMISSION_CHECKLIST.md)
- **AWS Product Feedback:** [`AWS_PRODUCT_FEEDBACK.md`](AWS_PRODUCT_FEEDBACK.md) — Multi-model evaluation telemetry and feature requests.
- **Engineering Friction Logs:** [`HACKATHON_FRICTION_LOG.md`](HACKATHON_FRICTION_LOG.md) — 3 detailed technical logs documenting real challenges and solutions (for the 10% judging bonus).
- **Demo Video Script:** [`DEMO_VIDEO_SCRIPT.md`](DEMO_VIDEO_SCRIPT.md) — 2:45 walkthrough script formatted for YouTube/Vimeo public submission.
- **Open Source Companion Repo:** [`judgeguard-policy-schema`](https://github.com/kiza-zmaj/judgeguard-policy-schema) — Standalone policy definition library.

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
