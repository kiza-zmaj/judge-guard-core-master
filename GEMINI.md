# GEMINI.md — Project Antigravity Master Orchestration
# Loaded automatically in Antigravity IDE for judge-guard-core-master.

trigger: always_on

## 🏛️ Immutable Laws (MASTER_ORCHESTRATION.md)

1. **User Sovereignty:** The USER is the ultimate authority. No action without user approval.
2. **JudgeGuard is Mandatory:** Every major action must pass `judge_guard.py` before execution.
3. **TICKET.md Required:** Work ticket must be created/updated before running verification.
4. **Layer 000 Ticket Gate:** Ollama Cloud Gemma 4 verifies tickets before launch AND approves completion before ticket closure.
5. **Git Checkpoint After Success:** Every successful action MUST create a git commit (`checkpoint: [ACTION]`) and log the SHA to `WORK_LOG.md`.
6. **Atomic Task Chunking:** Maximum 5 open tasks in `WORK_LOG.md` at any time.
7. **No Mocks, No Simulations:** 100% production mode only.
8. **Model Lock:** Antigravity model changes require passcode `0012`.
9. **No Sudo, No Privilege Escalation:** Hard block in Layer 00 on `sudo`, `rm -rf /`, `chmod -R 777`.

## 🔄 Verification Workflow

```bash
# 1. Update WORK_LOG.md
echo "🟡 Starting [ACTION]" >> WORK_LOG.md

# 2. Pre-Action Verification (Layer 000 Ollama Gemma 4 + JudgeGuard)
./gemini_cli.sh "[ACTION]"

# 3. Post-Action Verification & Checkpoint is automatic:
# - Ollama Gemma 4 COMPLETION_APPROVED
# - git commit -m "checkpoint: [ACTION]"
# - SHA logged to WORK_LOG.md
```

## Key Files
- `judge_guard.py` — Multi-layer safety engine
- `gemini_cli.sh` — Automated 7-step execution wrapper
- `qwen_cli.sh` — Qwen execution wrapper
- `TICKET.md` — Current active ticket
- `WORK_LOG.md` — Mandatory task log
- `MASTER_ORCHESTRATION.md` — Source of truth
