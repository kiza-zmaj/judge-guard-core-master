# AWS Builder Mini-Challenge: Comprehensive Product Feedback

> **Project:** JudgeGuard Autonomous AI Governance & Alexa+ MCP Server  
> **Primary Repository:** [kiza-zmaj/judgeguard-alexa-mcp](https://github.com/kiza-zmaj/judgeguard-alexa-mcp)  
> **Author & Evaluator:** `kizabgd123` (GitHub Organization: `kiza-zmaj`)  
> **AWS Services Evaluated:** AWS Bedrock Runtime (`InvokeModel` API), Anthropic Claude 3.5 Sonnet (`anthropic.claude-3-5-sonnet-20241022-v2:0`), Amazon Titan Text Express (`amazon.titan-text-express-v1`).

---

## 1. Tool / Feature Evaluated: AWS Bedrock Runtime (`InvokeModel` API)

### A. What Worked Well
- **Model-Specific Payload Dispatch**: The repository implements model-specific request payload formatting for both Anthropic Claude 3.5 Sonnet (Bedrock Messages format) and Amazon Titan Text Express (`inputText`/`textGenerationConfig`). This allows cost and latency tiering: lightweight checks can target Amazon Titan, while deep semantic multi-turn safety reasoning can target Claude 3.5.
- **Structured JSON Output**: Both models can be prompted to return strict JSON verdicts conforming to JudgeGuard's `ActionVerdict` schema.
- **Deterministic Offline Fallback for CI & Local Development**: To ensure deterministic, reproducible test runs and offline development without recurring AWS API costs or quota blockers, the server includes a local simulated fallback mode when AWS credentials are not configured.
- **Security & IAM**: Native AWS IAM role-based authentication (`boto3.client('bedrock-runtime')`) avoids hardcoding static keys in source repositories.

### B. Execution Mode & Latency Observations
- **Offline Fallback Mode:** In local automated tests, policy evaluation runs instantaneously through the deterministic fallback engine.
- **Live AWS Bedrock Mode:** When configured with AWS credentials (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_DEFAULT_REGION`), requests are dispatched directly to the Bedrock Runtime endpoint. Live latency is governed by model warmup, region selection (`us-east-1` vs `us-west-2`), account concurrency quotas, and network round-trip time.

### C. Friction & Pain Points
1. **Heterogeneous Request Schemas across Foundation Models**: Unlike OpenAI-compatible endpoints, Bedrock's raw `InvokeModel` API requires fundamentally distinct body schemas for Claude (`{"anthropic_version": "...", "messages": [...]}`) versus Titan (`{"inputText": "...", "textGenerationConfig": {...}}`). Developers building multi-model routing must maintain separate JSON serialization logic per provider.
2. **Streaming Event Buffering with SSE/FastAPI**: When bridging Bedrock responses to Streamable HTTP MCP server-sent events, buffering between Bedrock's chunked response and the client transport requires explicit keepalive handling.
3. **Regional Model Quotas & Discovery**: Determining whether on-demand model access is already active for Claude vs. Titan across specific AWS regions can cause initial onboarding friction for hackathon builders without prior Bedrock quota allocations.

### D. Actionable Suggestions for the AWS Team
1. **First-Party Bedrock MCP Adapter**: Provide an official AWS Bedrock Model Context Protocol (MCP) server or transport adapter for Streamable HTTP (Spec 2025-11-25+) out-of-the-box.
2. **Unified Schema Helpers in Boto3**: Provide built-in request/response normalization helpers in the AWS SDK to ease multi-model dispatch between Claude, Titan, and Llama foundation models on Bedrock.
3. **Standardized Guardrails Output Schema**: Enable Bedrock Guardrails to return structured JSON-RPC 2.0 error payloads so client AI agents can negotiate safer alternative actions autonomously.
