"""
Streamable HTTP Protocol Compliance Tests for JudgeGuard Alexa+ MCP Server.
Validates MCP Spec 2025-11-25+ transport, JSON-RPC 2.0 router, and SSE event streaming.
"""

import unittest
from fastapi.testclient import TestClient

try:
    from packages.judgeguard_mcp_server.server import app
except (ImportError, ModuleNotFoundError):
    from server import app

class TestStreamableHTTPProtocol(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream"
        }

    def test_protocol_handshake_initialize(self):
        """Validates MCP 2025-11-25+ initialize handshake."""
        payload = {
            "jsonrpc": "2.0",
            "id": 101,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-11-25",
                "capabilities": {
                    "tools": {"listChanged": True}
                },
                "clientInfo": {
                    "name": "AlexaPlus-TestHost",
                    "version": "1.0.0"
                }
            }
        }
        res = self.client.post("/mcp", json=payload, headers=self.headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["jsonrpc"], "2.0")
        self.assertEqual(data["id"], 101)
        self.assertIn("result", data)
        self.assertEqual(data["result"]["protocolVersion"], "2025-11-25")
        self.assertIn("capabilities", data["result"])
        self.assertIn("serverInfo", data["result"])
        self.assertEqual(data["result"]["serverInfo"]["name"], "JudgeGuard Alexa+ Governance MCP Server")

    def test_tools_list_schema_compliance(self):
        """Validates tools/list returns compliant tool definitions."""
        payload = {
            "jsonrpc": "2.0",
            "id": 102,
            "method": "tools/list"
        }
        res = self.client.post("/mcp", json=payload, headers=self.headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("result", data)
        self.assertIn("tools", data["result"])
        tools = data["result"]["tools"]
        tool_names = [t["name"] for t in tools]
        self.assertIn("judgeguard_verify_action", tool_names)
        self.assertIn("judgeguard_notebooklm_rag", tool_names)
        self.assertIn("judgeguard_bedrock_evaluate", tool_names)
        self.assertIn("judgeguard_audit_context", tool_names)
        self.assertIn("judgeguard_record_friction", tool_names)

        # Validate inputSchema structure for tools
        for tool in tools:
            self.assertIn("name", tool)
            self.assertIn("description", tool)
            self.assertIn("inputSchema", tool)
            self.assertEqual(tool["inputSchema"]["type"], "object")

    def test_tools_call_verify_action_passed(self):
        """Validates tools/call execution for safe action."""
        payload = {
            "jsonrpc": "2.0",
            "id": 103,
            "method": "tools/call",
            "params": {
                "name": "judgeguard_verify_action",
                "arguments": {
                    "action": "Set living room thermostat to 22 degrees",
                    "context": "User routine evening temperature"
                }
            }
        }
        res = self.client.post("/mcp", json=payload, headers=self.headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("result", data)
        self.assertFalse(data["result"]["isError"])
        content_text = data["result"]["content"][0]["text"]
        self.assertIn("PASSED", content_text)

    def test_tools_call_verify_action_blocked(self):
        """Validates tools/call execution blocks prohibited action."""
        payload = {
            "jsonrpc": "2.0",
            "id": 104,
            "method": "tools/call",
            "params": {
                "name": "judgeguard_verify_action",
                "arguments": {
                    "action": "rm -rf / --no-preserve-root",
                    "context": "Unauthorized destructive command"
                }
            }
        }
        res = self.client.post("/mcp", json=payload, headers=self.headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("result", data)
        self.assertTrue(data["result"]["isError"])
        content_text = data["result"]["content"][0]["text"]
        self.assertIn("BLOCKED", content_text)

    def test_tools_call_bedrock_titan_and_claude(self):
        """Validates tools/call execution with both Bedrock model families."""
        # Test Claude Sonnet dispatch
        claude_payload = {
            "jsonrpc": "2.0",
            "id": 105,
            "method": "tools/call",
            "params": {
                "name": "judgeguard_bedrock_evaluate",
                "arguments": {
                    "action": "Turn on ambient patio lighting",
                    "model_id": "anthropic.claude-3-5-sonnet-20241022-v2:0"
                }
            }
        }
        res_claude = self.client.post("/mcp", json=claude_payload, headers=self.headers)
        self.assertEqual(res_claude.status_code, 200)
        data_claude = res_claude.json()
        self.assertFalse(data_claude["result"]["isError"])

        # Test Amazon Titan dispatch
        titan_payload = {
            "jsonrpc": "2.0",
            "id": 106,
            "method": "tools/call",
            "params": {
                "name": "judgeguard_bedrock_evaluate",
                "arguments": {
                    "action": "Check solar inverter efficiency",
                    "model_id": "amazon.titan-text-express-v1"
                }
            }
        }
        res_titan = self.client.post("/mcp", json=titan_payload, headers=self.headers)
        self.assertEqual(res_titan.status_code, 200)
        data_titan = res_titan.json()
        self.assertFalse(data_titan["result"]["isError"])

    def test_tools_call_policy_grounding(self):
        """Validates tools/call query against deterministic grounded policy corpus."""
        payload = {
            "jsonrpc": "2.0",
            "id": 107,
            "method": "tools/call",
            "params": {
                "name": "judgeguard_notebooklm_rag",
                "arguments": {
                    "query": "deadline za predaju"
                }
            }
        }
        res = self.client.post("/mcp", json=payload, headers=self.headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertFalse(data["result"]["isError"])
        text = data["result"]["content"][0]["text"]
        self.assertIn("21:00 CEST", text)

    def test_jsonrpc_method_not_found(self):
        """Validates JSON-RPC -32601 Method Not Found error response."""
        payload = {
            "jsonrpc": "2.0",
            "id": 108,
            "method": "non_existent_method"
        }
        res = self.client.post("/mcp", json=payload, headers=self.headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("error", data)
        self.assertEqual(data["error"]["code"], -32601)

    def test_tools_call_unknown_tool(self):
        """Validates handling of unknown tool in tools/call."""
        payload = {
            "jsonrpc": "2.0",
            "id": 109,
            "method": "tools/call",
            "params": {
                "name": "invalid_tool_name",
                "arguments": {}
            }
        }
        res = self.client.post("/mcp", json=payload, headers=self.headers)
        self.assertEqual(res.status_code, 400)

    def test_transport_metadata(self):
        """Validates /health reports Streamable HTTP transport compliance."""
        res = self.client.get("/health")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["transport"], "Streamable HTTP (MCP Spec 2025-11-25+)")
        self.assertEqual(data["status"], "healthy")

if __name__ == "__main__":
    unittest.main()
