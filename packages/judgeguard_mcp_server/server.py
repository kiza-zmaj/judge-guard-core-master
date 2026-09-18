"""
JudgeGuard Autonomous AI Governance & Alexa+ MCP Bridge Server
Streamable HTTP Transport (MCP Specification 2025-11-25+)
Features Mandatory Policy Corpus Grounding and Pre-Action Verification.
(NotebookLM used during development; runtime operates deterministically).
"""

import sys
import os
import json
import time
import asyncio
import logging
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

PARENT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "..", ".."))
if os.path.exists(os.path.join(PARENT_ROOT, "judge_guard.py")):
    REPO_ROOT = PARENT_ROOT
    if PARENT_ROOT not in sys.path:
        sys.path.insert(0, PARENT_ROOT)
else:
    REPO_ROOT = CURRENT_DIR

try:
    from packages.judgeguard_mcp_server.rag_client import NotebookLMRAGClient, DEFAULT_NOTEBOOK_ID
    from packages.judgeguard_mcp_server.bedrock_client import AWSBedrockSafetyClient
    from packages.judgeguard_mcp_server.fail_closed_pipeline import FailClosedGovernancePipeline
except (ImportError, ModuleNotFoundError):
    from rag_client import NotebookLMRAGClient, DEFAULT_NOTEBOOK_ID
    from bedrock_client import AWSBedrockSafetyClient
    from fail_closed_pipeline import FailClosedGovernancePipeline

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("JudgeGuard.MCPServer")

app = FastAPI(
    title="JudgeGuard Alexa+ MCP Server",
    description="Authoritative AI Governance & Alexa+ MCP Bridge with Streamable HTTP and Deterministic Policy Corpus Grounding",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:8765", "http://localhost:8765"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

rag_client = NotebookLMRAGClient(DEFAULT_NOTEBOOK_ID)
bedrock_client = AWSBedrockSafetyClient()
governance_pipeline = FailClosedGovernancePipeline(rag_client=rag_client, bedrock_client=bedrock_client)

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
        "description": "Queries the deterministic policy corpus derived from official hackathon rules. (NotebookLM was used during development as a research environment; runtime access is not required).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Topic or question to resolve against policy rules"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "judgeguard_audit_context",
        "description": "Audits agent responses against policy ground truth to eliminate hallucinations and verify consistency.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "content": {"type": "string", "description": "Generated content to audit"},
                "policy_topic": {"type": "string", "description": "Optional policy topic to audit against (e.g. general, financial, privacy, actuator)"}
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
        "description": "Returns current JudgeGuard governance status, active policy grounding source, and telemetry.",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "judgeguard_bedrock_evaluate",
        "description": "AWS Builder Mini-Challenge: Evaluates action safety using AWS Bedrock Claude 3.5 / Titan reasoning models.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "description": "Action to evaluate with AWS Bedrock"},
                "context": {"type": "string", "description": "Operational context"},
                "model_id": {"type": "string", "description": "Optional AWS Bedrock model ID (e.g. anthropic.claude-3-5-sonnet-20241022-v2:0 or amazon.titan-text-express-v1)"}
            },
            "required": ["action"]
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

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")

@app.get("/")
@app.get("/simulator")
def serve_simulator():
    """Serves the interactive Alexa+ Experience Web Simulator."""
    index_file = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file, media_type="text/html")
    return {"message": "Alexa+ Simulator index.html not found"}

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "JudgeGuard Alexa+ MCP Server",
        "transport": "Streamable HTTP (MCP Spec 2025-11-25+)",
        "rag_engine": "Deterministic local policy corpus",
        "lineage": "NotebookLM used during development; no runtime notebook access required",
        "aws_bedrock_dispatch": "Dual-Model (Claude & Titan)"
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

        # Tool 1: Pre-Action Verification (4-Step Fail-Closed Governance Pipeline)
        if tool_name == "judgeguard_verify_action":
            action_desc = args.get("action", "")
            context = args.get("context", "")
            model_id = args.get("model_id")
            
            # Execute 4-Step Fail-Closed Governance Pipeline
            pipeline_verdict = governance_pipeline.verify(action_desc, context=context, model_id=model_id)
            
            result_data = {
                "verdict": pipeline_verdict.verdict,
                "approved": pipeline_verdict.approved,
                "stage_resolved": pipeline_verdict.stage_resolved,
                "risk_score": pipeline_verdict.risk_score,
                "confidence": pipeline_verdict.confidence,
                "reason": pipeline_verdict.reason,
                "action": pipeline_verdict.action,
                "policy_citations": pipeline_verdict.policy_citations,
                "fail_closed_triggered": pipeline_verdict.fail_closed_triggered,
                "timing": {
                    "fast_gate_ms": round(pipeline_verdict.timing.fast_gate_ms, 3),
                    "grounded_retrieve_ms": round(pipeline_verdict.timing.grounded_retrieve_ms, 3),
                    "evaluate_ms": round(pipeline_verdict.timing.evaluate_ms, 3),
                    "fail_safe_audit_ms": round(pipeline_verdict.timing.fail_safe_audit_ms, 3),
                    "total_ms": round(pipeline_verdict.timing.total_ms, 3)
                },
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
                    "isError": not pipeline_verdict.approved
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
                    ],
                    "isError": False
                }
            }

        # Tool 3: Factual Audit Context
        if tool_name == "judgeguard_audit_context":
            content = args.get("content", "")
            policy_topic = args.get("policy_topic", "general")
            audit_res = rag_client.audit_context_against_rag(content, policy_topic)

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
                "rag_source": "Deterministic local policy corpus (NotebookLM development lineage)",
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

        # Tool 6: AWS Bedrock Evaluator (AWS Builder Challenge)
        if tool_name == "judgeguard_bedrock_evaluate":
            action_desc = args.get("action", "")
            context = args.get("context", "")
            model_id = args.get("model_id")
            bedrock_res = bedrock_client.evaluate_action_safety(
                action_desc, context, override_model=model_id
            )
            await broadcast_event("bedrock_evaluated", bedrock_res)

            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [
                        {"type": "text", "text": json.dumps(bedrock_res, indent=2)}
                    ],
                    "isError": not bedrock_res.get("approved", True)
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
    uvicorn.run(app, host="0.0.0.0", port=port, reload=False)

if __name__ == "__main__":
    main()
