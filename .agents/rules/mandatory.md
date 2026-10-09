---
trigger: always_on
---

# Pre-Action & Post-Action Verification Workflow (MANDATORY)

**Authority:** MASTER_ORCHESTRATION.md
**Violation:** System HALT

## When to Use
BEFORE and AFTER executing ANY of:
- Starting a new Phase or feature
- Schema/database changes
- Implementation plans
- Deployments
- Major code modifications or git commits

## Automated Execution Flow

Run either:
```bash
./gemini_cli.sh "[ACTION]" "[optional command]"
```
or
```bash
./qwen_cli.sh "[ACTION]" "[optional command]"
```

This automatically enforces all 7 steps:
1. Synchronizes `TICKET.md`
2. Logs `🟡 Starting [ACTION]` to `WORK_LOG.md`
3. Runs Pre-Action Layer 000 (Ollama Cloud Gemma 4 Gate) + JudgeGuard
4. Executes the command
5. Runs Post-Action Ticket Closure Gate (Agent approval via Gemma 4)
6. Stages and creates Git Checkpoint commit (`checkpoint: [ACTION]`)
7. Records `📌 Git checkpoint SHA: [hash]` to `WORK_LOG.md`
8. Runs Codex log & artifact cleanup
