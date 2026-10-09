# MASTER_ORCHESTRATION.md

**Authority:** This document is the IMMUTABLE LAW of the Antigravity System.
**Version:** 2.0
**Status:** ACTIVE

---

## 🏛️ Immutable Laws

These laws CANNOT be overridden by any agent, user, or tool:

### Law 1: User Sovereignty

The USER is the ultimate authority. No agent may take actions that the user has not approved.

### Law 2: No Destructive Operations Without Verification

Any action involving deletion, system modification, or irreversible changes MUST pass JudgeGuard verification.

### Law 3: Research First

Before implementing any feature, validate assumptions through research. No guessing.

### Law 4: Transparency

All agent thoughts, actions, and verdicts MUST be logged and visible to the user.

### Law 5: Modularity & Clean Architecture

Code must follow the plugin-based architecture. No monolithic solutions.

### Law 6: Work Log Mandatory

WORK_LOG.md must be updated BEFORE and AFTER every major action.

### Law 7: Security Enforcement

No `sudo`, `rm -rf /`, `rm -rf /*`, or `chmod -R 777` operations are permitted under any circumstances.

### Law 8: Quality Standards

All code must be reviewed before merging. No "make it work" PRs without verifiable criteria.

---

## 🛡️ JudgeGuard Verification Rules

### Phase Rules

- **Phase 0-1 (Research):** ONLY browser/read tools allowed. No shell commands for research.
- **Phase 2+ (Execution):** Shell commands permitted AFTER JudgeGuard approval.

### Essence Check

Actions must not deviate more than 20% from Project Essence (see PROJECT_ESSENCE in judge_guard.py).

### Dangerous Command Blacklist

- `sudo` (privilege escalation)
- `rm -rf /` (root deletion)
- `rm -rf /*` (root deletion variant)
- `chmod -R 777` (world-writable)

---

## 📋 Project Essence

**Goal:** Build an autonomous, self-improving AI agent system (Antigravity).

**Core Values:**

1. User Control — User is ultimate authority
2. Safety — No destructive actions without verification
3. Quality — High standards for code and documentation
4. Transparency — Stream thoughts and actions to user
5. Modularity — Clean, plugin-based architecture
6. Research First — Validate before coding

---

## 🔄 Verification Workflow

Before ANY major action:

1. `echo "🟡 Starting [ACTION]" >> WORK_LOG.md`
2. `PYTHONPATH=. .venv/bin/python3 judge_guard.py "Start [ACTION]"`
3. If EXIT 0 → proceed. If EXIT 1 → STOP.
4. Execute action.
5. `echo "✅ Completed [ACTION]" >> WORK_LOG.md`
6. `PYTHONPATH=. .venv/bin/python3 judge_guard.py "Verify [ACTION] Complete"`
7. `git add . && git commit -m "checkpoint: [ACTION]"`

---

## ⚛️ Atomic Task Chunking Rule

**Derived from:** Phase 2 Forensic Analysis — Verification Churn pattern.

- **MAX_TASKS_PER_TRACK = 5** — No agent may open more than 5 concurrent `🟡 Starting` tasks.
- Before starting any new track, all open tasks must be either `✅ Completed` or `⚠️ Abandoned`.
- JudgeGuard Layer 0.0 enforces this rule automatically before any action is approved.
- Stale open tasks from crashed sessions must be explicitly marked `⚠️ Abandoned` before new work begins.

---

## 🔥 Firebase MCP Fallback Rule

**Derived from:** Phase 2 Forensic Analysis — External Packaging Breakage pattern.

- The `firebase-mcp-server` MCP resource `ui://core/deploy/mcp-app.html` is **broken** (upstream ENOENT).
- **DO NOT** block on or retry MCP resource reads from `firebase-mcp-server`.
- **ALWAYS** use native Firebase CLI for all deployment operations:
  ```bash
  npx -y firebase-tools@latest deploy
  npx -y firebase-tools@latest deploy --only hosting
  npx -y firebase-tools@latest deploy --only functions
  ```
- MCP tools from `firebase-mcp-server` may still be used for non-resource operations (auth, project listing).

