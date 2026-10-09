# AGENTS.md — Antigravity Agent Directives

trigger: always_on

## Mandate
You are an autonomous agent operating within the **JudgeGuard Master Orchestration** ecosystem.
All operations must strictly conform to `/home/testovinovi/judge-guard-core-master/MASTER_ORCHESTRATION.md`.

## Mandatory Operating Rules
1. Never bypass JudgeGuard verification (`judge_guard.py`).
2. Always keep `WORK_LOG.md` up-to-date with active task status.
3. Keep open tasks in `WORK_LOG.md` at or below 5 (Atomic Task Chunking).
4. Tickets in `TICKET.md` must be approved by Ollama Cloud Gemma 4 before starting and at completion.
5. Every completed task must produce a Git commit with SHA recorded in `WORK_LOG.md`.
6. Zero mock implementations, zero fake simulation code.
7. Never execute `sudo`, `rm -rf /`, or permission changes (`chmod -R 777`).
