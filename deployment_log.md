# Deployment Log - 2026-09-16T07:25:00.000000

## Target 1: Cloudflare Edge Worker (`my-worker/`) -> Real Production Deploy
- **Service Name:** `judge-guard-edge-agent`
- **Environment:** Production (`workers.dev`)
- **Cloudflare Account ID:** `8de5d0d9f4989519818901ee429bfd3f` (`kiza101288@gmail.com`)
- **Version ID:** `0029f1aa-99f3-4daf-b1d8-a57d46fa5974`
- **Live URL:** `https://judge-guard-edge-agent.kiza101288.workers.dev`
- **Secrets Injected:** `NOTION_API_KEY` (uploaded securely via `wrangler secret put`, zero leakage into git)
- **Runtime Components:**
  - Cloudflare Agents SDK + Durable Objects (`ContentOrchestratorAgent`, `JudgeGuardMcpAgent`)
  - SQLite Migration: `v1`
  - Streamable HTTP MCP Endpoint: `/mcp`
- **Live Health Check:**
  - `curl -i https://judge-guard-edge-agent.kiza101288.workers.dev/` -> **HTTP/2 200 OK**
  - Payload:
    ```json
    {
      "name": "JudgeGuard Edge Hub",
      "status": "OPERATIONAL",
      "runtime": "Cloudflare Workers + Durable Objects (agents-sdk)",
      "authority": "MASTER_ORCHESTRATION.md",
      "mcp": {
        "endpoint": "/mcp",
        "protocol": "2024-11-05",
        "transport": "Streamable HTTP"
      },
      "services": {
        "notionMcp": "https://mcp.notion.com/v1",
        "notebookLmMcp": "https://nlm-bridge.internal.net/mcp"
      }
    }
    ```
- **Deployment Status:** ✅ REAL LIVE PRODUCTION DEPLOYMENT COMPLETE & VERIFIED

---

## Target 2: Python Backend / Analytics Engine (`judge-guard-core-master`) -> Standalone Clean-Room Artifact
- **Package:** `packages/sharpbet_core/` (SharpBet Core v3.0.0)
- **Artifact:** `exports/dist/sharpbet_core_v3.0.0.zip` (48.74 MB, SHA-256: `1d714912da37968d7d8ea1e6e30ef78631080d19ffd32d52f0ecb6dc289dfa1b`)
- **Clean-Room Verification (`/tmp/sharpbet_clean_room_v3`):**
  - Gate 1 (Zero Git Artifacts): ✅ PASS
  - Gate 2 (Clean Dependency Isolation): ✅ PASS
  - Gate 3 (Clean-Room Test Suite Execution): ✅ PASS (16/16 tests passed)
  - Gate 4 (Walk-Forward OOS Engine Execution): ✅ PASS
  - Gate 5 (Deterministic Metric Reproduction): ✅ PASS (Calibration ECE = 3.79%, Brier = 0.5921)
  - Gate 6 (FastAPI REST Server Daemon Health): ✅ PASS (HTTP 200 on `/health`)
  - Gate 7 (Zero Hardcoded Secrets / Credentials): ✅ PASS
- **Release Verification Report:** `packages/sharpbet_core/RELEASE_EVIDENCE_REPORT.md`
- **Git State:** Pushed to GitHub `origin/master` (`kizabgd123/judge-guard-core-master`)
- **Status:** ✅ VERIFIED DISTRIBUTABLE ARTIFACT / RESEARCH-ONLY ENGINE (Market Alpha Gate: FAIL, Stake = €0.00)
