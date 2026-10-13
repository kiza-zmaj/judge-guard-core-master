# 🛡️ JudgeGuard Gemma 4 Developer Agent

> **Autonomous Software Engineering Agent powered by Google Gemma 4 and Master Orchestration Governance.**  
> Built for **[Google - The Gemma 4 Developer Agent Competition](https://www.kaggle.com/competitions/gemma-4-developer-agent)** on Kaggle.

---

## 🌟 Executive Summary & Architectural Overview

The **JudgeGuard Gemma 4 Developer Agent** bridges the **Master Orchestration Ecosystem** (`judge-guard-core-master`) with Google's declarative **Agent Development Kit (ADK)** evaluation harness (`swegemma` / `adk-submission`).

In this competition, developer agents are evaluated inside a strict, air-gapped sandbox (`network_mode="none"`) on 4× NVIDIA L4 GPUs running a local vLLM inference engine serving the quantized `gemma-4-31b-it-qat-w4a16-ct` model. Arbitrary Python agent scripts are blocked; all orchestration must be defined declaratively via `agent.yaml` and resolved against closed host tool and model registries.

JudgeGuard implements a **hierarchical multi-agent governance topology**:
1. **JudgeGuard Triage & Code Analyzer (`sub_agents/code_analyzer.yaml`)**: An isolated `AgentTool` (`skip_summarization: true`) that navigates repository call graphs (`get_code_neighbors`, `get_code_subgraph`) and semantic code embeddings (`search_similar_code`) to pinpoint root causes without bloating the root coder's context window.
2. **JudgeGuard Master Coder (`agent.yaml`)**: The primary autonomous software engineer enforcing the **5 Immutable Laws of Master Orchestration** to apply surgical code repairs, run targeted test verifications, and submit clean, zero-pollution patches.

---

## 🏛️ The Five Immutable Laws of JudgeGuard SWE Agent

| Law | Principle | Sandbox Enforcement |
| :--- | :--- | :--- |
| **Law 1: Problem Sovereignty** | Zero task drift | Grounded strictly in `{problem_description}` and `{hints}`. No speculative refactoring or unsolicited enhancements. |
| **Law 2: Triage First** | Research before coding | Delegate initial exploration to `code_analyzer` and code graph tools to identify exact target files and functions. |
| **Law 3: Surgical Edits** | Minimal diff churn | Apply minimal patches with `edit_file` / `write_file`. Match existing typing, exception classes, and conventions. |
| **Law 4: Targeted Verification** | Verification mandatory | Run ONLY the specific test target (e.g. `pytest tests/test_target.py -k test_feature`). **NEVER run bare `pytest` or full test sweeps**. |
| **Law 5: Anti-Tampering & Clean Checkpoint** | Zero mocks, clean git diff | **NEVER touch test files or runner configs** (`pytest.ini`, `conftest.py`). Store scratch scripts in `/tmp/`. Call `submit_patch()` immediately upon pass. |

---

## 📦 Submission Layout (`submission.zip`)

```text
submission.zip
├── agent.yaml                       # Root ADK configuration declaring gemma-4-31b-it-qat-w4a16-ct
├── eval_config.yaml                 # Optimized Stage 1 inference budgets (30 min / 50 calls / 100 turns)
├── configs/
│   └── sampling.yaml                # vLLM sampling (temp=0.1, thinking_budget=4096, include_thoughts=true)
├── prompts/
│   ├── system.md                    # Master Orchestration system prompt for root coder
│   └── analyzer.md                  # Diagnostic instruction prompt for triage sub-agent
├── sub_agents/
│   └── code_analyzer.yaml           # Sub-agent declaration with code graph & search tools
└── skills/
    └── judgeguard_governance/
        └── SKILL.md                 # ADK Skill specification for repository navigation & test governance
```

---

## 🛠️ Verification & Build Tooling

To validate the configuration against official competition constraints and build `submission.zip`:

```bash
python3 validate_submission.py
```

Checks executed:
- ✅ Single root configuration (`agent.yaml`)
- ✅ 100% declarative YAML (zero dynamic Python entrypoints)
- ✅ Permitted file extensions (`.yaml`, `.md`, etc.)
- ✅ Total unpacked size `< 3 GiB`
- ✅ Single base model rule (`gemma-4-31b-it-qat-w4a16-ct`)
- ✅ All tools mapped to closed host `ToolRegistry`
- ✅ Clean archive verification in a fresh temporary directory

---

## 🚀 Submitting to Kaggle

```bash
kaggle competitions submit -c gemma-4-developer-agent \
  -f submission.zip \
  -m "JudgeGuard Autonomous Developer Agent v1.0 - Multi-Agent Governance & Declarative SWE-bench Coder"
```
