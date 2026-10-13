# WORK TICKET
**Action:** Implement Screen Recording Wrapper for Antigravity Agent (agy-screen-recorder)
**Objective:** Build a production-grade Python CLI application that: (1) starts ffmpeg x11grab screen recording, (2) launches an `agy` agent with a given topic via `--print` mode, (3) waits for agent completion, (4) stops recording, (5) writes JSONL audit log, (6) verifies outputs, (7) writes final.txt status.
**Scope:** /home/testovinovi/DEV hacktoons/agy-screen-recorder
**Justification:** User /goal directive — Antigravity Task Prompt for Screen Recording Wrapper. JudgeGuard roles: Runner, ScreenRecorder, Logger, Verifier.
**Status:** OPEN
**Enforcement:** Non-destructive execution, zero mocks, zero fake simulations, 100% production mode. ffmpeg x11grab verified working on :0. agy CLI at ~/.local/bin/agy verified present.
