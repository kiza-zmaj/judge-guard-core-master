# 🏛️ JudgeGuard Master Orchestration: Universal Agent Blueprint & Starter Kit

> **Target Audience:** Any AI Agent (Gemini, Claude, GPT-4, Cursor, Bolt, Jules, Windsurf) or Human Engineer.  
> **Mandate:** 100% Reproducible, zero-mock, production-grade safety, token gating, and master orchestration.  
> **Authority:** `MASTER_ORCHESTRATION.md` & `judge_guard.py`.

---

## 🚀 Quick Start: 1-Command Bootstrap for Any New Repository

If you are an AI agent setting up a brand new project or GitHub repository, choose one of the following methods:

### Method A: Automated Export via Packager Script (Fastest)

From the `judge-guard-core-master` workspace:

```bash
# Export the complete ecosystem to any new repository directory with git initialized:
python3 scripts/judgeguard_packager.py export --target /path/to/my-new-repo --name "My Project Name" --init-git

# Verify compliance:
python3 scripts/judgeguard_packager.py verify --target /path/to/my-new-repo
```

### Method B: Extract the Portable Starter Kit Archive

A self-contained archive is pre-built at:
`exports/judgeguard-starter-kit.tar.gz`

To install it into a new project:

```bash
# 1. Create and enter your new project folder:
mkdir -p /path/to/new-repo && cd /path/to/new-repo

# 2. Extract the archive:
tar -xzf /path/to/judge-guard-core-master/exports/judgeguard-starter-kit.tar.gz --strip-components=1

# 3. Initialize Python environment:
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-judgeguard.txt

# 4. Initialize Git & First Checkpoint:
git init
git config user.name "JudgeGuard Agent"
git config user.email "agent@judgeguard.local"
git add .
git commit -m "checkpoint: Initialize JudgeGuard Master Orchestration"

# 5. Verify the gates:
python3 git_bolt_jules_gate.py audit
pytest tests/test_bolt_jules_telemetry.py
```

### Method C: Connecting to a New GitHub Repository

```bash
# In your newly initialized repository:
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/YOUR_NEW_REPO.git
git push -u origin main
```

*(Note: `.env` and `research.db` are automatically ignored by `.gitignore` to prevent any secret or telemetry database leakage).*

---

## 📂 Core File Manifest (What Every JudgeGuard Repo Must Have)

```text
├── .agents/
│   ├── rules/
│   │   ├── mandatory.md                     # Pre & Post Action 7-step rules
│   │   └── master_orchestration.md          # 9 Immutable Laws definition
│   ├── skills/
│   │   └── verify-action/
│   │       └── SKILL.md                     # Native Antigravity verification skill
│   └── workflows/
│       └── verify_action.md                 # Agent slash command workflow
├── src/
│   └── antigravity_core/
│       ├── __init__.py
│       ├── ticket_verifier.py               # Ollama Cloud Gemma 4 Gatekeeper
│       ├── token_cleaner.py                 # Context bloat pruner & diff cleaner
│       ├── telemetry.py                     # SQLite research.db metrics recorder
│       ├── judge_flow.py                    # Multi-turn Gemini judging engine
│       └── gemini_client.py                 # Multi-key failover LLM client
├── tests/
│   └── test_bolt_jules_telemetry.py         # Verification test suite (8 tests)
├── scripts/
│   ├── codex_log_cleaner.py                 # Memory & crash log garbage collector
│   └── judgeguard_packager.py               # Blueprint exporter & verifier
├── MASTER_ORCHESTRATION.md                  # Universal source of truth
├── GEMINI.md                                # Directives for Antigravity & Gemini agents
├── BOLT.md                                  # Directives for Bolt.new & WebContainers
├── AGENTS.md                                # Base agent directives
├── judge_guard.py                           # 4-Layer safety & semantic drift engine
├── git_bolt_jules_gate.py                   # Token cleaner audit & telemetry badge CLI
├── gemini_cli.sh                            # 7-step execution wrapper (Gemini)
├── qwen_cli.sh                              # 7-step execution wrapper (Qwen)
├── TICKET.md                                # Current active work ticket
├── WORK_LOG.md                              # Mandatory task journal (<= 5 open tasks)
├── requirements-judgeguard.txt              # Core dependencies
├── .env.example                             # Environment variable template
└── .gitignore                               # Token-clean optimized ignore rules
```

---

## 🏛️ The 9 Immutable Laws

These 9 laws apply identically to **every** AI agent across **all** environments (Antigravity IDE, Bolt.new, Cursor, CLI, etc.):

1. **User Sovereignty:** The USER is the ultimate authority. No action without user approval.
2. **JudgeGuard is Mandatory:** Every major action must pass `judge_guard.py` before execution.
3. **TICKET.md Required:** Work ticket must be created/updated before running verification.
4. **Layer 000 Ticket Gate:** Ollama Cloud Gemma 4 verifies tickets before launch AND approves completion before ticket closure.
5. **Git Checkpoint After Success:** Every successful action MUST create a git commit (`checkpoint: [ACTION]`) and log the SHA to `WORK_LOG.md`.
6. **Atomic Task Chunking:** Maximum 5 open tasks in `WORK_LOG.md` at any time.
7. **No Mocks, No Simulations:** 100% production mode only. Zero fake simulation code.
8. **Model Lock:** Antigravity model changes require passcode `0012`.
9. **No Sudo, No Privilege Escalation:** Hard block in Layer 00 on `sudo`, `rm -rf /`, `chmod -R 777`.

---

## 🧹 Token Cleaning & Context Reduction Protocol

To prevent context overflow, LLM confusion, and massive API token waste:

1. **Forbidden Context Ingestion:**
   Agents must NEVER load into LLM context:
   - `local_py/**` (contains discovery cache JSONs exceeding context limits)
   - `.venv/**`, `node_modules/**`, `dist/**`, `build/**`
   - `.git/**`, `.cache/**`, `exports/**`, `*.log`
2. **Surgical Diff Generation:**
   - Propose changes as targeted replacement blocks (`replace_file_content`).
   - Do NOT rewrite or echo unmodified lines or entire multi-thousand-line files.
3. **Automated Token Audit:**
   - Verify staged files before committing:
     ```bash
     python3 git_bolt_jules_gate.py audit
     ```
   - Generate token-compressed diffs:
     ```bash
     python3 git_bolt_jules_gate.py clean-diff
     ```

---

## 📊 Telemetry & Observability

All operations are recorded to maintain full auditability:

1. **SQLite Metrics:** Every call logs `prompt_tokens`, `completion_tokens`, `total_tokens`, `cached_tokens`, `tokens_saved`, `latency_ms`, and `cost_estimate_usd` in `research.db`.
2. **Telemetry Badges:** Every Git checkpoint commit automatically attaches a badge to `WORK_LOG.md`:
   ```bash
   python3 git_bolt_jules_gate.py badge --agent gemini --action "[ACTION]"
   ```
   > 📊 **Telemetry (GEMINI)**: 22,136 tokens used | ⚡ ~51,122 tokens saved (est) | ⏱️ 391.5ms | 🤖 `gemini-3.7-flash`
3. **Live Dashboard:** Review cumulative metrics anytime:
   ```bash
   python3 git_bolt_jules_gate.py telemetry
   ```

---

## 🔄 The 7-Step Verification Workflow

Whenever an agent performs work, it runs either:

```bash
./gemini_cli.sh "[ACTION_NAME]" "[OPTIONAL_COMMAND]"
```
or
```bash
./qwen_cli.sh "[ACTION_NAME]" "[OPTIONAL_COMMAND]"
```

This single execution automatically handles:
1. **Ticket Synchronization:** Syncs `TICKET.md` via `ticket_verifier.py create`.
2. **Work Log Inscription:** Appends `🟡 Starting [ACTION]` to `WORK_LOG.md`.
3. **Pre-Action Multi-Layer Gate:**
   - Layer 00: Blocks dangerous commands (`sudo`, `rm -rf`).
   - Layer 000: Verifies ticket admission with Ollama Cloud Gemma 4.
   - Layer 0: Enforces Atomic Task Chunking (<= 5 open tasks).
   - Layer 3: Verifies alignment with Project Essence (no semantic drift).
4. **Command Execution:** Executes tests, build, or script (if provided).
5. **Post-Action Ticket Closure Gate:** Verifies completion evidence with Gemma 4 (`COMPLETION_APPROVED`).
6. **Token Cleaner Audit & Git Checkpoint:**
   - Runs `git_bolt_jules_gate.py audit` to ensure staged files contain zero token bloat.
   - Commits: `git commit -m "checkpoint: [ACTION]"`.
   - Logs commit SHA and Telemetry Badge to `WORK_LOG.md`.
7. **Cleanup:** Runs `scripts/codex_log_cleaner.py` to prune ephemeral caches.

---

## 🤖 Instructions for AI Agents Implementing This Blueprint

If you are an AI assistant tasked with setting up this system in a new project:

1. **Verify Workspace Roots:** Check if git is initialized. If not, run `git init`.
2. **Unpack or Copy Files:** Use `scripts/judgeguard_packager.py export` or copy all files listed in the manifest above.
3. **Make Scripts Executable:** Ensure `chmod +x judge_guard.py git_bolt_jules_gate.py gemini_cli.sh qwen_cli.sh`.
4. **Run Compliance Verification:** Run `python3 scripts/judgeguard_packager.py verify --target .` to ensure 100% adherence.
5. **Run Test Suite:** Run `pytest tests/test_bolt_jules_telemetry.py`.
6. **Initialize Work Log:** Verify `WORK_LOG.md` has the initial checkpoint recorded.
7. **Present Status to User:** Show the verified clean audit and initial commit SHA.
