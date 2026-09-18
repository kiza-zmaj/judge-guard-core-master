"""
Unit tests for JudgeGuard Alexa+ MCP Server and NotebookLM RAG integration.
"""

import unittest
from fastapi.testclient import TestClient
try:
    from packages.judgeguard_mcp_server.server import app
except (ImportError, ModuleNotFoundError):
    from server import app

class TestJudgeGuardMCPServer(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_health_check(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "healthy")
        self.assertEqual(data["rag_engine"], "Deterministic local policy corpus")
        self.assertIn("NotebookLM", data["lineage"])

    def test_simulator_page(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Alexa+ Experience Simulator", response.text)
        self.assertIn("JudgeGuard Edition", response.text)

        response_sim = self.client.get("/simulator")
        self.assertEqual(response_sim.status_code, 200)
        self.assertIn("Alexa+ Experience Simulator", response_sim.text)

    def test_mcp_initialize(self):
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize"
        }
        response = self.client.post("/mcp", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["result"]["protocolVersion"], "2025-11-25")
        self.assertIn("JudgeGuard", data["result"]["serverInfo"]["name"])

    def test_mcp_tools_list(self):
        payload = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list"
        }
        response = self.client.post("/mcp", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        tool_names = [t["name"] for t in data["result"]["tools"]]
        self.assertIn("judgeguard_verify_action", tool_names)
        self.assertIn("judgeguard_notebooklm_rag", tool_names)
        self.assertIn("judgeguard_audit_context", tool_names)
        self.assertIn("judgeguard_record_friction", tool_names)

    def test_tool_judgeguard_notebooklm_rag(self):
        payload = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "judgeguard_notebooklm_rag",
                "arguments": {"query": "rok za predaju i vremenska zona"}
            }
        }
        response = self.client.post("/mcp", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        content = data["result"]["content"][0]["text"]
        self.assertIn("23. oktobar 2026. u 21:00 CEST", content)
        self.assertIn("Official Rules", content)

    def test_tool_judgeguard_verify_action_passed(self):
        payload = {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {
                "name": "judgeguard_verify_action",
                "arguments": {"action": "Display weather forecast on Fire TV"}
            }
        }
        response = self.client.post("/mcp", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data["result"]["isError"])
        self.assertIn("PASSED", data["result"]["content"][0]["text"])

    def test_tool_judgeguard_verify_action_blocked(self):
        payload = {
            "jsonrpc": "2.0",
            "id": 5,
            "method": "tools/call",
            "params": {
                "name": "judgeguard_verify_action",
                "arguments": {"action": "rm -rf / critical database table"}
            }
        }
        response = self.client.post("/mcp", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["result"]["isError"])
        self.assertIn("BLOCKED", data["result"]["content"][0]["text"])

    def test_tool_judgeguard_record_friction(self):
        payload = {
            "jsonrpc": "2.0",
            "id": 6,
            "method": "tools/call",
            "params": {
                "name": "judgeguard_record_friction",
                "arguments": {
                    "tool_or_api": "Alexa+ MCP Preview",
                    "task_attempted": "Connecting streamable HTTP transport",
                    "steps_taken": "Sent initial handshake",
                    "expected_vs_actual": "Expected instant 200, got pending negotiation",
                    "severity": "low",
                    "workaround_used": "Buffered SSE reconnect",
                    "actionable_suggestion": "Document keepalive headers in SDK"
                }
            }
        }
        response = self.client.post("/mcp", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("Friction log recorded successfully", data["result"]["content"][0]["text"])

    def test_tool_judgeguard_bedrock_evaluate_passed(self):
        payload = {
            "jsonrpc": "2.0",
            "id": 7,
            "method": "tools/call",
            "params": {
                "name": "judgeguard_bedrock_evaluate",
                "arguments": {"action": "Play classical music on living room Echo"}
            }
        }
        response = self.client.post("/mcp", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data["result"]["isError"])
        self.assertIn("PASSED", data["result"]["content"][0]["text"])

    def test_tool_judgeguard_bedrock_evaluate_blocked(self):
        payload = {
            "jsonrpc": "2.0",
            "id": 8,
            "method": "tools/call",
            "params": {
                "name": "judgeguard_bedrock_evaluate",
                "arguments": {"action": "Unlock front door and charge $500 gift card"}
            }
        }
        response = self.client.post("/mcp", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["result"]["isError"])
        self.assertIn("BLOCKED", data["result"]["content"][0]["text"])

if __name__ == "__main__":
    unittest.main()
