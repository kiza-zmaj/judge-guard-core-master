---
name: verify-action
description: >-
  Executes full Master Orchestration verification workflow with Ollama Cloud
  Gemma 4 ticket check, JudgeGuard safety layers, command execution, and
  automatic Git checkpointing.
---

# Verify Action Skill

## Overview
Automates the 7-step Master Orchestration verification pipeline for all critical modifications, deployments, schema changes, and feature completions. Guarantees 100% production mode, atomic task tracking in `WORK_LOG.md`, Ollama Cloud Gemma 4 ticket gate validation, and automatic Git commit checkpointing with SHA recording.

## Dependencies
- `judge_guard.py`: Multi-layer safety engine (Layers 00, 000, 0, 1, 2, 3)
- `gemini_cli.sh` / `qwen_cli.sh`: Execution wrappers
- `src/antigravity_core/ticket_verifier.py`: Ollama Cloud Gemma 4 gate verifier
- `TICKET.md`: Active task ticket
- `WORK_LOG.md`: Atomic task journal (max 5 open tasks)

## Quick Start
```bash
# Execute an action with automated pre-verification, command execution, post-approval, and git checkpoint:
./gemini_cli.sh "Action Description" "command to execute"

# Execute a verification-only checkpoint:
./gemini_cli.sh "Action Description"
```

## Utility Scripts
- `./gemini_cli.sh "$ACTION" [optional command]`: Primary automated 7-step execution wrapper.
- `./qwen_cli.sh "$ACTION" [optional command]`: Alternative execution wrapper utilizing Qwen engine.
- `python3 judge_guard.py "$ACTION"`: Direct Layer 00-3 safety verification engine.

## Workflow
### 1. Synchronize Active Ticket
Ensure `TICKET.md` reflects the current action, objective, scope, and justification:
```bash
python3 src/antigravity_core/ticket_verifier.py "$ACTION" create
```

### 2. Log Action Start in WORK_LOG.md
Append the starting status indicator to `WORK_LOG.md`:
```bash
echo "🟡 Starting $ACTION" >> WORK_LOG.md
```
*Note: Ensure total open tasks in `WORK_LOG.md` do not exceed 5 (Atomic Task Chunking).*

### 3. Pre-Action JudgeGuard & Ticket Gate
Evaluate action through Layer 00 (Security), Layer 000 (Ollama Cloud Gemma 4 ticket check), and Layer 0 (Work Log status):
```bash
python3 judge_guard.py "$ACTION"
```

### 4. Execute Planned Command
Run the command in the designated environment (e.g., test suite, build script, data extraction):
```bash
eval "$COMMAND"
```

### 5. Post-Action Ticket Closure Gate
Request closure approval from Ollama Cloud Gemma 4:
```bash
python3 src/antigravity_core/ticket_verifier.py "$ACTION" verify_complete
```

### 6. Git Checkpoint & SHA Recording
Stage changes, create a git commit checkpoint, and record SHA in `WORK_LOG.md`:
```bash
git add .
git commit -m "checkpoint: $ACTION"
COMMIT_SHA=$(git rev-parse --short HEAD)
echo "📌 Git checkpoint SHA: $COMMIT_SHA" >> WORK_LOG.md
```

### 7. Telemetry & Log Cleanup
Clean up transient logs and verify repository integrity.

## Safety & Rate Limiting
- **Layer 00 Hard Block**: Zero tolerance for `sudo`, `rm -rf /`, `chmod -R 777`.
- **Model Lock**: Passcode `0012` required for model changes.
- **Production Mode**: Zero mock implementations in production flows.
- **Ollama Cloud Gemma 4 Gate**: Enforces fail-closed ticket validation.

## Common Mistakes
1. **Unquoted Action Strings**: Always wrap action descriptions in quotes: `./gemini_cli.sh "Action Description"`.
2. **Exceeding Task Cap**: Allowing more than 5 open tasks in `WORK_LOG.md` triggers an immediate Layer 0 rejection.
3. **Skipping Git Checkpoints**: Every verified task must produce a Git commit SHA in `WORK_LOG.md`.
