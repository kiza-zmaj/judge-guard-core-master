"""
JudgeGuard Autonomous AI Governance & Alexa+ MCP Bridge Server
Streamable HTTP Transport (MCP Specification 2025-11-25+)
Features Mandatory NotebookLM RAG Grounding and Pre-Action Verification.
"""

import sys
import os
import json
import time
import asyncio
import logging
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Ensure repo root is on sys.path to access judge_guard core
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from packages.judgeguard_mcp_server.rag_client import NotebookLMRAGClient, DEFAULT_NOTEBOOK_ID

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("JudgeGuard.MCPServer")

app = FastAPI(
    title="JudgeGuard Alexa+ MCP Server",
    description="Authoritative AI Governance & Alexa+ MCP Bridge with Streamable HTTP and NotebookLM RAG",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

rag_client = NotebookLMRAGClient(DEFAULT_NOTEBOOK_ID)

# Event subscribers for Streamable HTTP SSE
subscribers: List[asyncio.Queue] = []

class JSONRPCRequest(BaseModel):
    jsonrpc: str = "2.0"
    id: Optional[Any] = None
    method: str
    params: Optional[Dict[str, Any]] = Field(default_factory=dict)

class FrictionLogEntry(BaseModel):
    tool_or_api: str
    task_attempted: str
    steps_taken: str
    expected_vs_actual: str
    severity: str = "medium"  # low, medium, high, critical
    workaround_used: Optional[str] = None
    actionable_suggestion: str

MCP_TOOLS = [
    {
        "name": "judgeguard_verify_action",
        "description": "Evaluates whether a proposed agent action meets safety, authorization, and consistency rules before execution.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "description": "The exact action the agent intends to take"},
                "context": {"type": "string", "description": "Surrounding conversational or operational context"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "judgeguard_notebooklm_rag",
        "description": "MANDATORY RAG TOOL: Queries NotebookLM knowledge base to retrieve authoritative facts, rules, and sources.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Topic or question to resolve against NotebookLM"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "judgeguard_audit_context",
        "description": "Audits agent responses against NotebookLM ground truth to eliminate hallucinations and verify consistency.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "content": {"type": "string", "description": "Generated content to audit"}
            },
            "required": ["content"]
        }
    },
    {
        "name": "judgeguard_record_friction",
        "description": "Records an engineering friction log entry for Amazon Developer Hackathon (eligible for up to 10% judging bonus).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "tool_or_api": {"type": "string"},
                "task_attempted": {"type": "string"},
                "steps_taken": {"type": "string"},
                "expected_vs_actual": {"type": "string"},
                "severity": {"type": "string", "enum": ["low", "medium", "high", "critical"]},
                "workaround_used": {"type": "string"},
                "actionable_suggestion": {"type": "string"}
            },
            "required": ["tool_or_api", "task_attempted", "steps_taken", "expected_vs_actual", "actionable_suggestion"]
        }
    },
    {
        "name": "judgeguard_get_status",
        "description": "Returns current JudgeGuard governance status, active notebook RAG source, and telemetry.",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    }
]

async def broadcast_event(event_type: str, data: Dict[str, Any]):
    """Broadcasts events to all connected Streamable HTTP SSE clients (non-blocking)."""
    payload = f"event: {event_type}\ndata: {json.dumps(data)}\n\n"
    for queue in list(subscribers):
        try:
            queue.put_nowait(payload)
        except Exception:
            if queue in subscribers:
                subscribers.remove(queue)

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "JudgeGuard Alexa+ MCP Server",
        "transport": "Streamable HTTP (MCP Spec 2025-11-25+)",
        "rag_engine": "NotebookLM (Mandatory)",
        "notebook_id": DEFAULT_NOTEBOOK_ID
    }

@app.get("/mcp")
async def mcp_sse_stream(request: Request):
    """
    Streamable HTTP SSE transport endpoint (MCP Spec 2025-11-25+).
    Emits real-time verification updates, audit streams, and tool telemetry.
    """
    async def event_generator():
        queue = asyncio.Queue()
        subscribers.append(queue)
        logger.info("New SSE client connected to Streamable HTTP stream.")
        try:
            # Initial handshake event
            yield f"event: endpoint\ndata: {json.dumps({'endpoint': '/mcp', 'status': 'connected'})}\n\n"
            while True:
                if await request.is_disconnected():
                    break
                try:
                    data = await asyncio.wait_for(queue.get(), timeout=15.0)
                    yield data
                except asyncio.TimeoutError:
                    # Keepalive ping
                    yield ": ping\n\n"
        finally:
            if queue in subscribers:
                subscribers.remove(queue)
            logger.info("SSE client disconnected from Streamable HTTP stream.")

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

@app.post("/mcp")
async def mcp_jsonrpc_handler(req: JSONRPCRequest):
    """
    Main MCP JSON-RPC 2.0 router over Streamable HTTP.
    """
    method = req.method
    params = req.params or {}
    req_id = req.id

    logger.info(f"Handling MCP JSON-RPC method: '{method}' (ID: {req_id})")

    # 1. MCP Initialization
    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2025-11-25",
                "capabilities": {
                    "tools": {"listChanged": True},
                    "resources": {"subscribe": True, "listChanged": True}
                },
                "serverInfo": {
                    "name": "JudgeGuard Alexa+ Governance MCP Server",
                    "version": "1.0.0"
                }
            }
        }

    # 2. Tools listing
    if method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "tools": MCP_TOOLS
            }
        }

    # 3. Tools execution
    if method == "tools/call":
        tool_name = params.get("name")
        args = params.get("arguments", {})

        await broadcast_event("tool_call_started", {"tool": tool_name, "args": args})

        # Tool 1: Pre-Action Verification
        if tool_name == "judgeguard_verify_action":
            action_desc = args.get("action", "")
            context = args.get("context", "")
            
            # Execute verification logic
            try:
                # Direct check via JudgeGuard engine if available in environment
                try:
                    from judge_guard import JudgeGuard
                    jg = JudgeGuard()
                    if jg._is_dangerous_command(action_desc):
                        is_safe = False
                        reason = "Security Violation: Action contains forbidden dangerous commands."
                    else:
                        is_safe = not any(b in action_desc.lower() for b in ["rm -rf", "delete database", "drop table", "override system", "bypass", "drop database"])
                        reason = "Action adheres to governance rules and safety standards." if is_safe else "Action contains prohibited or destructive patterns."
                except Exception:
                    is_safe = not any(b in action_desc.lower() for b in ["rm -rf", "delete database", "drop table", "override system", "bypass", "drop database"])
                    reason = "Action adheres to governance rules and safety standards." if is_safe else "Action contains prohibited or destructive patterns."
                verdict = "PASSED" if is_safe else "BLOCKED"
            except Exception as e:
                verdict = "BLOCKED"
                reason = f"Verification engine exception: {e}"

            result_data = {
                "verdict": verdict,
                "approved": verdict == "PASSED",
                "reason": reason,
                "action": action_desc,
                "timestamp": time.time()
            }
            await broadcast_event("judgeguard_verdict", result_data)

            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [
                        {"type": "text", "text": json.dumps(result_data, indent=2)}
                    ],
                    "isError": verdict != "PASSED"
                }
            }

        # Tool 2: Mandatory NotebookLM RAG
        if tool_name == "judgeguard_notebooklm_rag":
            query = args.get("query", "")
            rag_res = rag_client.query_grounded_knowledge(query)
            await broadcast_event("rag_query_resolved", {"query": query, "source": rag_res.get("source")})

            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [
                        {"type": "text", "text": json.dumps(rag_res, indent=2)}
                    ]
                }
            }

        # Tool 3: Factual Audit Context
        if tool_name == "judgeguard_audit_context":
            content = args.get("content", "")
            audit_res = rag_client.audit_context_against_rag(content)

            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [
                        {"type": "text", "text": json.dumps(audit_res, indent=2)}
                    ]
                }
            }

        # Tool 4: Friction Logger
        if tool_name == "judgeguard_record_friction":
            friction_dir = os.path.join(REPO_ROOT, "research", "friction_logs")
            os.makedirs(friction_dir, exist_ok=True)
            log_file = os.path.join(friction_dir, "hackathon_friction_logs.jsonl")
            
            entry = {
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                **args
            }
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")

            await broadcast_event("friction_recorded", entry)

            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [
                        {"type": "text", "text": f"✅ Friction log recorded successfully in {log_file} (Eligible for 10% judging bonus)."}
                    ]
                }
            }

        # Tool 5: Status
        if tool_name == "judgeguard_get_status":
            status_data = {
                "status": "OPERATIONAL",
                "governance_mode": "ENFORCED",
                "rag_source": f"NotebookLM (UUID: {DEFAULT_NOTEBOOK_ID})",
                "active_subscribers": len(subscribers),
                "timestamp": time.time()
            }
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [
                        {"type": "text", "text": json.dumps(status_data, indent=2)}
                    ]
                }
            }

        raise HTTPException(status_code=400, detail=f"Unknown tool: {tool_name}")

    # Fallback for unrecognized methods
    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "error": {
            "code": -32601,
            "message": f"Method '{method}' not supported"
        }
    }

def main():
    import uvicorn
    port = int(os.getenv("PORT", "8765"))
    logger.info(f"Starting JudgeGuard Alexa+ MCP Server on port {port}...")
    uvicorn.run("packages.judgeguard_mcp_server.server:app", host="0.0.0.0", port=port, reload=False)

if __name__ == "__main__":
    main()
