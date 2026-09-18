# Amazon Developer Hackathon 2026: Official Engineering Friction Log

> **Project:** JudgeGuard Autonomous AI Governance & Alexa+ MCP Bridge  
> **Bonus Category:** Engineering Friction Logging (Eligible for up to 10% judging bonus)  
> **Format:** Tool/API • Task Attempted • Steps Taken • Expected vs. Actual • Severity • Workaround • Actionable Suggestion

---

### Entry 1: Model Context Protocol (MCP) Streamable HTTP Transport Specification
- **Tool / API / SDK:** MCP Specification 2025-11-25+ (Streamable HTTP Transport)
- **Task Attempted:** Implementing real-time Server-Sent Events (SSE) streaming on `GET /mcp` alongside JSON-RPC 2.0 requests on `POST /mcp` in FastAPI.
- **Steps Taken:**
  1. Configured FastAPI route `GET /mcp` returning `StreamingResponse(..., media_type="text/event-stream")`.
  2. Subscribed async queue to broadcast tool execution events and verification verdicts.
  3. Sent JSON-RPC `POST /mcp` requests concurrently from web client.
- **Expected vs. Actual:**
  - *Expected:* Client receives instant event frames without blocking subsequent JSON-RPC calls.
  - *Actual:* Without proactive keepalive pings (`: ping\n\n`) every 15s, intermediate HTTP proxies and certain browser connections prematurely timed out or buffered the stream until buffer fill.
- **Severity:** Medium
- **Workaround Used:** Injected periodic keepalive comment lines (`yield ": ping\\n\\n"`) and configured `X-Accel-Buffering: no` response headers in `packages/judgeguard_mcp_server/server.py`.
- **Actionable Suggestion for Developer Platform:** Document the required HTTP buffering and keepalive headers explicitly in the official Alexa+ MCP Streamable HTTP developer quickstart.

---

### Entry 2: MCP JSON-RPC Error Handling for Tool Block Verdicts
- **Tool / API / SDK:** MCP Tool Execution Protocol (`tools/call`)
- **Task Attempted:** Communicating a governance block verdict (e.g. `BLOCKED` for dangerous physical actions) to the calling agent.
- **Steps Taken:** Returned a standard JSON-RPC response with `"isError": true` inside the tool result object.
- **Expected vs. Actual:**
  - *Expected:* Host agent should receive structured error content and understand the reason for denial.
  - *Actual:* Some LLM clients treated `"isError": true` as a transport crash rather than a graceful policy denial, attempting repeated infinite retries.
- **Severity:** Medium
- **Workaround Used:** Returned detailed JSON structure inside `content[0].text` with clear `approved: false` and `reason` fields, allowing the agent to negotiate an alternative or ask the user for confirmation.
- **Actionable Suggestion for Developer Platform:** Standardize an error taxonomy for agent tool denials (e.g. `POLICY_VIOLATION`, `CONFIRMATION_REQUIRED`, `INSUFFICIENT_PERMISSIONS`) in the MCP specification.

---

### Entry 3: AWS Bedrock Claude 3.5 Streaming Header Compatibility
- **Tool / API / SDK:** AWS Bedrock Runtime (`InvokeModelWithResponseStream`)
- **Task Attempted:** Streaming token-by-token reasoning traces from Bedrock Claude 3.5 Sonnet directly into the JudgeGuard SSE stream.
- **Steps Taken:** Iterated over the Bedrock event stream generator in Python asyncio worker.
- **Expected vs. Actual:**
  - *Expected:* Uniform token chunks forwarded immediately.
  - *Actual:* Bedrock stream yielded raw byte buffers with custom AWS event headers requiring binary deserialization before JSON conversion.
- **Severity:** Low
- **Workaround Used:** Decoupled the Bedrock evaluation into a dedicated client (`packages/judgeguard_mcp_server/bedrock_client.py`) that handles payload extraction cleanly.
- **Actionable Suggestion for Developer Platform:** Provide high-level asynchronous generators in the `boto3` SDK that yield parsed string chunks directly for modern Python async frameworks.
