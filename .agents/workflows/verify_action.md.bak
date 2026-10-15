---
name: verify_action
description: Run full Master Orchestration verification workflow with Ollama Gemma 4 ticket check, JudgeGuard, and Git checkpoint.
---

# Verify Action Workflow

1. Ensure the active task is reflected in `TICKET.md`.
2. Run pre-action verification:
   ```bash
   ./gemini_cli.sh "$ACTION"
   ```
3. Check status in `WORK_LOG.md`.
4. Inspect git commit checkpoint:
   ```bash
   git log -n 1 --oneline
   ```
