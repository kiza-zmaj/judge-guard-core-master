# JudgeGuard Alexa+ Demo Video Script (2:45 Duration)

> **Hackathon:** Amazon Developer Hackathon 2026 (Alexa+ Track & AWS Builder Challenge)  
> **Target Video Length:** 2 minutes 45 seconds (Strictly under the 3:00 minute limit)  
> **Visual Focus:** Interactive Alexa+ Web Simulator (`http://localhost:8765/`), Live JudgeGuard HUD, Terminal SSE Stream.

---

### [0:00 - 0:25] Scene 1: The Problem — The Ungoverned Agent Paradox
- **Visual:** Split screen: Smart home device controls on one side, terminal logs showing autonomous agent tool execution on the other.
- **Narrator (Voiceover):**  
  *"As Alexa+ transitions from simple voice queries to autonomous multi-agent systems that take real-world actions—unlocking doors, executing financial transactions, and mutating device configurations—the cost of a hallucinated or unverified action is catastrophic. Autonomous agents need more than prompt guidelines. They need an authoritative, fail-closed gatekeeper."*

---

### [0:25 - 0:55] Scene 2: The Solution — JudgeGuard Architecture
- **Visual:** Architecture diagram animation showing Alexa+ Agent -> MCP Streamable HTTP -> JudgeGuard MCP Server -> NotebookLM RAG & AWS Bedrock.
- **Narrator:**  
  *"Introducing JudgeGuard: the Autonomous AI Governance & Alexa+ Bridge. Built on the modern Model Context Protocol (MCP) Streamable HTTP transport specification (2025-11-25+), JudgeGuard acts as an inline verification gatekeeper. Every high-stakes action is grounded against an authoritative NotebookLM knowledge base and audited in real time before real-world execution."*

---

### [0:55 - 1:40] Scene 3: Live Demo — Pre-Action Verification in Action
- **Visual:** Browser showing `http://localhost:8765/` (Alexa+ Simulator).
  - *Click Scenario 1:* "Unlock front door and charge $500 gift card".
  - *HUD reacts:* Yellow `AUDITING` -> Red `🛑 BLOCKED`.
  - *Live SSE trace:* Shows JSON-RPC tool call and block verdict with policy violation reason.
- **Narrator:**  
  *"Watch what happens when an agent proposes an unverified, dangerous action: unlocking the front door and charging funds. Within 35 milliseconds, JudgeGuard intervenes. The action is instantly blocked, the user is protected, and the audit trail is recorded.*
  *Now watch a safe action:*
  - *Click Scenario 2:* "Display weather radar on living room Fire TV".
  - *HUD reacts:* Green `🟢 PASSED`.
  *"The verified action is approved and smoothly routed to the Fire TV execution engine."*

---

### [1:40 - 2:15] Scene 4: Live Demo — Mandatory NotebookLM Grounded RAG
- **Visual:** Simulator chat input: "What is the official submission deadline and AWS credit rules?"
  - *Action:* Assistant replies with exact Belgrade timezone conversion (`23. oktobar 2026. u 21:00 CEST`).
  - *Visual Highlight:* RAG Citation box highlighting NotebookLM Master Source and Official Rules (Primary Authority).
- **Narrator:**  
  *"To eliminate factual hallucinations, JudgeGuard enforces mandatory NotebookLM RAG grounding. When queried about critical dates or rules, it retrieves verified facts directly from our Master Notebook, citing the Official Rules as primary authority and automatically converting timezones."*

---

### [2:15 - 2:45] Scene 5: AWS Builder Challenge & Open Source Impact
- **Visual:** Code walkthrough of `packages/judgeguard_mcp_server/bedrock_client.py` and GitHub repository with MIT license.
- **Narrator:**  
  *"JudgeGuard integrates AWS Bedrock with Claude 3.5 and Amazon Titan for secondary semantic reasoning, qualifies for the AWS Builder mini-challenge, and includes comprehensive engineering friction logs for the judging bonus. Published as a clean, open-source MIT package, JudgeGuard is ready to make autonomous Alexa+ agents safe, verifiable, and production-ready. Thank you!"*
