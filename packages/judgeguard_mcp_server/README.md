# JudgeGuard Alexa+ MCP Server

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![MCP Spec](https://img.shields.io/badge/MCP-2025--11--25+-blue.svg)](https://modelcontextprotocol.io/)
[![RAG Engine](https://img.shields.io/badge/RAG-NotebookLM-brightgreen.svg)](https://notebook.google.com/)

Autonomous AI Governance & Pre-Action Verification Bridge for **Alexa+** and agentic systems, built for the **Amazon Developer Hackathon 2026**.

## Features

- **Streamable HTTP Transport (MCP Spec 2025-11-25+)**: Full Server-Sent Events (SSE) streaming and JSON-RPC 2.0 router.
- **Mandatory NotebookLM RAG (`judgeguard_notebooklm_rag`)**: Authoritative grounding against NotebookLM knowledge bases (`82440dea-0a12-40a7-a249-0ba460f69611`) with cited source attribution.
- **Pre-Action Verification (`judgeguard_verify_action`)**: Autonomous evaluation of high-stakes actions before real-world execution.
- **Hallucination & Factual Consistency Audit (`judgeguard_audit_context`)**: Real-time checking of agent responses against verified ground truth.
- **Friction Log Generator (`judgeguard_record_friction`)**: Structured engineering telemetry formatted for the hackathon's **10% judging bonus**.

## Quickstart

### 1. Installation
```bash
pip install -e packages/judgeguard_mcp_server
```

### 2. Run MCP Server
```bash
python3 packages/judgeguard_mcp_server/server.py
```
Server starts on `http://localhost:8765`.

### 3. Verification & JSON-RPC Example

#### Initialize:
```bash
curl -X POST http://localhost:8765/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "id": 1, "method": "initialize"}'
```

#### Query Mandatory NotebookLM RAG:
```bash
curl -X POST http://localhost:8765/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/call",
    "params": {
      "name": "judgeguard_notebooklm_rag",
      "arguments": {"query": "Koji je tačan deadline za predaju po vremenu u Beogradu?"}
    }
  }'
```

#### Pre-Action Verification:
```bash
curl -X POST http://localhost:8765/mcp \
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

#### Listen to Streamable HTTP SSE Stream:
```bash
curl -N http://localhost:8765/mcp
```
