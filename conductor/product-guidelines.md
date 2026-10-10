# Product Guidelines

## Core Principles
1. **Zero Mocks, 100% Production Mode:** All research and execution components operate against real APIs, actual artifacts, or strictly validated schemas.
2. **NotebookLM as Single Source of Truth:** Empirical assertions must trace back to grounded notebook citations.
3. **Atomic Task Chunking:** Never maintain more than 5 open tasks simultaneously.
4. **Git Checkpoints & Auditing:** Every verified operation produces a deterministic Git commit logged to `WORK_LOG.md`.
5. **Fail-Closed Security:** Never bypass JudgeGuard gates or Layer 00 safety checks.
