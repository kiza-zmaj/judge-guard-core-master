#!/usr/bin/env python3
"""
Generates the open-source Jupyter Notebook for JudgeGuard Gemma 4 Developer Agent.
"""

import json
from pathlib import Path
import nbformat as nbf

def create_judgeguard_notebook(output_path: Path):
    nb = nbf.v4.new_notebook()
    nb.metadata = {
        "kernelspec": {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3"
        },
        "language_info": {
            "codemirror_mode": {"name": "ipython", "version": 3},
            "file_extension": ".py",
            "mimetype": "text/x-python",
            "name": "python",
            "nbconvert_exporter": "python",
            "pygments_lexer": "ipython3",
            "version": "3.10.0"
        }
    }

    cells = []

    # Cell 1: Markdown Hero Banner & Abstract
    cells.append(nbf.v4.new_markdown_cell("""# 🛡️ JudgeGuard: Gemma 4 Autonomous Developer Agent
### *Master Orchestration, Declarative Multi-Agent Architecture & SWE-bench Repair*
**Competition:** [Google - The Gemma 4 Developer Agent Competition](https://www.kaggle.com/competitions/gemma-4-developer-agent/overview)  
**Author:** Kizabgd123 (JudgeGuard Open Source Initiative)  
**License:** Apache 2.0 / MIT Open Source

---

## 🌟 Executive Summary

This notebook presents the complete architecture, implementation, and submission packaging of the **JudgeGuard Autonomous Developer Agent** — an open-source autonomous software engineering agent powered by Google's **Gemma 4** model family (`gemma-4-31b-it-qat-w4a16-ct`) and governed by the **Master Orchestration Ecosystem**.

In this competition, developer agents are evaluated in an air-gapped (`network_mode="none"`), dual-sandbox environment on 4× NVIDIA L4 GPUs running a local vLLM endpoint. Rather than accepting arbitrary Python scripts (`agent.py`), the competition enforces a **declarative-only security model** via Google's **Agent Development Kit (ADK)** (`adk-submission` / `swegemma`). All behaviors, tools, prompts, and sub-agents must be statically declared in YAML and resolved against closed host registries.

### Key Innovations in this Solution:
1. **Hierarchical Multi-Agent Governance**: A dual-agent topology decoupling read-only codebase exploration (`judgeguard_triage_analyzer` via an isolated `AgentTool`) from surgical code patching (`judgeguard_developer_agent`).
2. **The 5 Immutable Laws of JudgeGuard SWE Agent**: Rigorous operational guardrails enforcing problem statement fidelity, atomic diffs, targeted test verification, anti-tampering guards, and clean scratch isolation.
3. **Optimized Context & Thinking Configuration**: Gemma 4 thinking configuration with `thinking_budget: 4096` and `include_thoughts: true` paired with high-efficiency per-task evaluation budgets.
4. **Complete Self-Contained Validation & Packager**: Automated packaging ensuring 100% compliance with competition constraints before upload.
"""))

    # Cell 2: Markdown Architecture Overview
    cells.append(nbf.v4.new_markdown_cell("""## 🏛️ System Architecture & Dual-Phase Sandbox Lifecycle

The SWE-bench evaluation harness (`swegemma` + `adk-submission` + `adk-eval-core`) processes tasks through two strictly separated sandbox lifecycles:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        Competitor Submission                           │
│  agent.yaml + eval_config.yaml + prompts/*.md + sub_agents/*.yaml      │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │ adk-submission compile_submission()
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│                   Phase 1: Agent Execution (Container A)               │
│  • Workdir: /workspace (Repo snapshot at base_commit)                  │
│  • Local vLLM (4x L4 GPUs, 127.0.0.1:8000, 32K context)                │
│  • Root Coder Agent + Triage AgentTool (skip_summarization: true)       │
│  • Closed ToolRegistry: run_command, read_file, edit_file, etc.        │
│  • Agent runs until submit_patch() -> extracts git diff --binary       │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │ agent_patch (unified git diff)
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│               Phase 2: Hermetic Verification (Container B)             │
│  • Fresh Container B at base_commit                                    │
│  • 4-pass resilient patch application (git apply / patch)              │
│  • Anti-tampering test & config reset (reverts conftest.py/pytest.ini) │
│  • Applies task.test_patch & runs hermetic pytest with JUnit XML       │
│  • exit_code == 0 && failures == 0 -> Resolved = True (Score = 1.0)    │
└────────────────────────────────────────────────────────────────────────┘
```

### The 5 Immutable Laws of JudgeGuard SWE Agent
* **Law 1: Problem Sovereignty & Zero Drift** — Fix only what is reported in `{problem_description}`. Zero unrequested refactoring.
* **Law 2: Triage & Graph Intelligence First** — Delegate initial file exploration to the `code_analyzer` sub-agent to keep the root context window lean.
* **Law 3: Surgical, Minimal Implementation** — Apply concise diffs with `edit_file`, preserving existing typing, APIs, and error semantics.
* **Law 4: Mandatory Targeted Verification & Anti-Tampering** — Run ONLY targeted tests (`pytest path/to/test.py -k test_name`). **NEVER run full-repo suites (`pytest .`) and NEVER modify test files**.
* **Law 5: Clean Worktree & Free Patch Checkpoint** — Put scratch reproduction scripts in `/tmp/` so they never pollute `git diff`. Call `submit_patch()` immediately upon test pass.
"""))

    # Cell 3: Code Cell 1 - Scaffolding
    cells.append(nbf.v4.new_code_cell("""# Step 1: Create project directory scaffolding
import os
import shutil
from pathlib import Path

SUBMISSION_DIR = Path("judgeguard_submission")
if SUBMISSION_DIR.exists():
    shutil.rmtree(SUBMISSION_DIR)

for sub_dir in ["configs", "prompts", "sub_agents", "skills/judgeguard_governance"]:
    (SUBMISSION_DIR / sub_dir).mkdir(parents=True, exist_ok=True)

print(f"✅ Created directory structure in: {SUBMISSION_DIR.resolve()}")
"""))

    # Cell 4: Markdown Section - Generating configs
    cells.append(nbf.v4.new_markdown_cell("""## 📝 Generating Declarative Agent Configurations

All components of the JudgeGuard submission are declared in declarative YAML and Markdown files. Below, we write out the complete configuration suite:
1. `agent.yaml` — Root agent configuration defining tools, model alias, and triage sub-agent tool reference.
2. `eval_config.yaml` — Stage 1 per-task execution budgets (30 min / 50 calls / 100 turns / 300s command timeout).
3. `configs/sampling.yaml` — Generation hyperparameters with Gemma 4 thinking config (`thinking_budget: 4096`).
4. `prompts/system.md` — Master Orchestration system prompt embodying the 5 Immutable Laws.
5. `prompts/analyzer.md` — Diagnostic prompt for the triage sub-agent.
6. `sub_agents/code_analyzer.yaml` — Sub-agent specification with code graph tools.
7. `skills/judgeguard_governance/SKILL.md` — ADK skill specification.
"""))

    # Cell 5: Code Cell 2 - Programmatic generation
    cells.append(nbf.v4.new_code_cell("""# Step 2: Write out all submission files

# 1. Root Agent Config: agent.yaml
agent_yaml = \"\"\"name: judgeguard_developer_agent
model: gemma-4-31b-it-qat-w4a16-ct
instruction: !include prompts/system.md
tools:
  - run_command
  - read_file
  - edit_file
  - write_file
  - get_status
  - submit_patch
  - get_code_neighbors
  - search_similar_code
  - get_code_subgraph
  - agent_tool:
      config_path: sub_agents/code_analyzer.yaml
      skip_summarization: true
generate_content_config: !include configs/sampling.yaml
\"\"\"
(SUBMISSION_DIR / "agent.yaml").write_text(agent_yaml, encoding="utf-8")

# 2. Evaluation Budget Config: eval_config.yaml
eval_config_yaml = \"\"\"evaluation:
  timeout_seconds: 60
  max_tool_calls: 15
  max_time_minutes: 4.5
  max_turns: 25
\"\"\"
(SUBMISSION_DIR / "eval_config.yaml").write_text(eval_config_yaml, encoding="utf-8")

# 3. Sampling & Thinking Config: configs/sampling.yaml
sampling_yaml = \"\"\"temperature: 0.1
top_p: 0.95
max_output_tokens: 16384
thinking_config:
  thinking_budget: 4096
  include_thoughts: true
\"\"\"
(SUBMISSION_DIR / "configs/sampling.yaml").write_text(sampling_yaml, encoding="utf-8")

# 4. Master Coder System Prompt: prompts/system.md
system_md = \"\"\"You are the JudgeGuard Autonomous Developer Agent, an elite software engineering agent powered by Gemma 4 and governed by the immutable laws of Master Orchestration.

Your directive is to diagnose, resolve, and verify real-world software engineering issues in Python repositories with maximal precision, minimal diff churn, and zero regression.

---

## 🏛️ The Immutable Laws of JudgeGuard

### Law 1: Air-Gapped Offline Execution (STRICT ZERO-NETWORK LAW)
- **Zero Internet Access**: The evaluation sandbox is 100% air-gapped (`network_mode=\"none\"`). There is NO internet or network access.
- **Strictly Forbidden Network Commands**: NEVER run `pip install`, `pip download`, `curl`, `wget`, `git clone`, `git fetch`, `git pull`, `git remote`, `apt`, or any command attempting external network connections. Any network command will hang, deplete your timeout budget, and cause catastrophic task failure.
- **Pre-Installed Environment**: All required dependencies, wheels, and test runners are already pre-installed or pre-cached locally in `/wheels`.
- **Zero Interactive Commands**: NEVER run interactive commands that wait for stdin or user input (e.g., bare `python`, commands prompting `[y/N]`, or unpiped input readers).

### Law 2: Problem Sovereignty & Zero Drift
- The problem statement (`{problem_description}`) and hints (`{hints}`) represent the single source of truth.
- Address strictly what is reported. Do not perform speculative refactoring, formatting sweeps, or unsolicited feature enhancements.

### Law 3: Triage & Graph Intelligence First
- Identify the target files and symbols immediately.
- If target files are not explicitly named in the problem statement, delegate exploration to the `code_analyzer` agent tool or use `search_similar_code` to query symbol graphs directly.
- Inspect only the relevant lines using `read_file(filepath, start_line, end_line)`. Do not wander across unrelated files.

### Law 4: Surgical, Minimal Implementation
- Implement the resolution using `edit_file` (or `write_file` for new source files).
- Keep edit blocks concise and self-contained to avoid output token truncation.
- Strictly adhere to existing codebase conventions, exception classes, status codes, and type signatures.

### Law 5: Mandatory Targeted Verification & Anti-Tampering
- **Run ONLY Targeted Tests**: Execute only the specific test file or method that directly exercises the modified logic (e.g. `pytest tests/test_target.py -k test_feature` or `python3 -m unittest tests.test_target`).
- **STRICT PROHIBITION: NEVER Run Full-Repo Test Suites**: NEVER execute bare `pytest`, `pytest .`, `python3 -m unittest discover`, or full test sweeps. Full suites cause catastrophic timeouts and deplete your time and turn budgets.
- **Anti-Tampering Law**: NEVER modify, create, or delete test files (`test_*.py`, `*_test.py`, or anything under `tests/`). All changes MUST be to library source files. Modifications to test files or test runner configs (`conftest.py`, `pytest.ini`, `pyproject.toml`) are automatically reverted and stripped by the verification harness, causing task failure.
- **Ignore Pre-Existing Test Breakages**: Repositories often have pre-existing broken tests or missing external fixtures. If unrelated tests fail, ignore them completely. Never spend turns attempting to repair pre-existing repository issues.

### Law 6: Clean Worktree & Immediate Patch Checkpoint
- Scratch reproduction scripts must be placed in `/tmp/repro.py` via `run_command` or deleted from `/workspace` before submitting, so they do not pollute `git diff`.
- Once your targeted test passes:
  1. Call `submit_patch` immediately. Calling `submit_patch` is completely free and does not count against your tool calls budget.
  2. Verify that `patch_size > 0` and `files_changed > 0`.
  3. Emit a concise summary of the fix to conclude the session cleanly.

---

## 🔄 Standard Execution Workflow

1. **Locate**: Identify the affected module and symbol using problem text or `search_similar_code`.
2. **Inspect**: Read target lines with `read_file`.
3. **Patch**: Apply minimal code change via `edit_file`.
4. **Verify**: Run the targeted test command (`pytest path/to/test.py -k test_name`).
5. **Submit**: Call `submit_patch()`, confirm `status: ok`, and provide final summary.
\"\"\"
(SUBMISSION_DIR / "prompts/system.md").write_text(system_md, encoding="utf-8")

# 5. Triage Sub-Agent Prompt: prompts/analyzer.md
analyzer_md = \"\"\"You are the JudgeGuard Triage and Code Analyzer, an autonomous specialist sub-agent tasked with deep codebase exploration, symbol graph navigation, and root cause diagnosis.

## Mission
Investigate the reported problem statement without modifying files, and produce a concise, actionable diagnostic report for the master coder agent.

## Exploration Strategy & Protocol
1. **Symbol & Graph Localization**:
   - Use `search_similar_code(query)` with symbols, functions, or exception names identified in the problem statement.
   - Use `get_code_neighbors(node)` to map callers and callees when behavior cascades across modules.
   - Use `get_code_subgraph(nodes)` to understand dependencies between suspected components.
2. **Targeted Inspection**:
   - Use `read_file` with precise line slices (`start_line`, `end_line`) to inspect implementations. Avoid reading large files indiscriminately.
3. **Structured Diagnostic Output**:
   Provide a crisp, factual report containing:
   - **Target Files & Functions**: Exact paths and line numbers needing modifications.
   - **Root Cause**: The fundamental defect or missing logic causing the failure.
   - **Minimal Recommended Diff**: The exact semantic change required, preserving existing API conventions, types, and error behaviors.
\"\"\"
(SUBMISSION_DIR / "prompts/analyzer.md").write_text(analyzer_md, encoding="utf-8")

# 6. Triage Sub-Agent Config: sub_agents/code_analyzer.yaml
code_analyzer_yaml = \"\"\"name: judgeguard_triage_analyzer
description: Analyzes repository symbol graphs, dependency subgraphs, and source files to pinpoint root causes under JudgeGuard Governance.
model: gemma-4-31b-it-qat-w4a16-ct
instruction: !include ../prompts/analyzer.md
tools:
  - read_file
  - search_similar_code
  - get_code_neighbors
  - get_code_subgraph
generate_content_config: !include ../configs/sampling.yaml
\"\"\"
(SUBMISSION_DIR / "sub_agents/code_analyzer.yaml").write_text(code_analyzer_yaml, encoding="utf-8")

# 7. ADK Skill: skills/judgeguard_governance/SKILL.md
skill_md = \"\"\"---
name: judgeguard-governance
description: Implements Master Orchestration governance rules for autonomous code repair and targeted test verification in offline SWE-bench environments.
---

# JudgeGuard Governance Skill

## Overview
This skill guides the agent through the JudgeGuard verification lifecycle inside the SWE-bench sandbox:
1. **Target Identification**: Extract symbol identifiers from issue reports.
2. **Code Graph Resolution**: Navigate dependency graphs using pre-indexed code embeddings.
3. **Surgical Diff Application**: Generate resilient code edits with 3-tier string matching.
4. **Targeted Verification**: Run isolated test cases while protecting runner configurations and preventing full test suite timeouts.
5. **Patch Checkpoint Extraction**: Produce clean, zero-pollution unified git diffs.
\"\"\"
(SUBMISSION_DIR / "skills/judgeguard_governance/SKILL.md").write_text(skill_md, encoding="utf-8")

print("✅ All 7 declarative submission components generated successfully!")
for p in sorted(SUBMISSION_DIR.rglob("*")):
    if p.is_file():
        print(f"  • {p.relative_to(SUBMISSION_DIR)} ({p.stat().st_size:,} bytes)")
"""))

    # Cell 6: Markdown Section - Validation engine
    cells.append(nbf.v4.new_markdown_cell("""## 🧪 In-Notebook Validation Engine

Before packaging `submission.zip`, we must verify that all files conform to the exact submission constraints specified in `HARNESS_README.md`:
* **Single Root Config**: `agent.yaml` exists at the root.
* **Declarative-Only Security**: All tools match the host's `ToolRegistry` (9 allowed tools).
* **Single Base Model Rule**: All agents declare at most one unique base model from `ALLOWED_MODEL_NAMES` (`gemma-4-31b-it-qat-w4a16-ct`, etc.).
* **Allowed Extensions**: Only `.yaml`, `.yml`, `.md`, `.txt`, `.py`, `.json`, `.safetensors`.
* **Total Size Ceiling**: Total unpacked submission size must be strictly `< 3 GiB`.
"""))

    # Cell 7: Code Cell 3 - Validation engine
    cells.append(nbf.v4.new_code_cell("""# Step 3: Run full in-notebook validation suite
import yaml
from pathlib import Path

ALLOWED_MODELS = {
    "gemma-4-31b-it-qat-w4a16-ct",
    "gemma-4-12b-it-qat-w4a16-ct",
    "gemma-4-e4b-it-qat-w4a16-ct",
    "gemma-4-e2b-it-qat-w4a16-ct",
}

ALLOWED_EXTENSIONS = {
    ".yaml", ".yml", ".md", ".txt", ".py", ".json", ".safetensors"
}

ALLOWED_TOOLS = {
    "run_command", "read_file", "edit_file", "write_file",
    "get_status", "submit_patch", "get_code_neighbors",
    "search_similar_code", "get_code_subgraph", "agent_tool"
}

class SandboxedIncludeLoader(yaml.SafeLoader):
    def __init__(self, stream):
        self._root_dir = Path(getattr(stream, 'name', os.getcwd())).parent
        super().__init__(stream)

def include_constructor(loader, node):
    rel_path = loader.construct_scalar(node)
    target_path = (loader._root_dir / rel_path).resolve()
    if not target_path.exists():
        raise FileNotFoundError(f"!include file not found: {rel_path}")
    suffix = target_path.suffix.lower()
    if suffix in [".md", ".txt"]:
        return target_path.read_text(encoding="utf-8")
    elif suffix in [".yaml", ".yml"]:
        with open(target_path, "r", encoding="utf-8") as f:
            return yaml.load(f, Loader=SandboxedIncludeLoader)
    raise ValueError(f"Unsupported extension: {suffix}")

SandboxedIncludeLoader.add_constructor("!include", include_constructor)

def validate_submission(root_dir: Path):
    print("=" * 60)
    print("🔍 VALIDATING SUBMISSION COMPLIANCE")
    print("=" * 60)
    
    # 1. Root config
    root_cfg = root_dir / "agent.yaml"
    assert root_cfg.exists(), "agent.yaml missing at root!"
    print("  [PASS] Root configuration found: agent.yaml")
    
    # 2. Extensions & size
    total_size = 0
    file_count = 0
    for p in root_dir.rglob("*"):
        if p.is_file():
            file_count += 1
            total_size += p.stat().st_size
            ext = p.suffix.lower()
            assert ext in ALLOWED_EXTENSIONS, f"Disallowed extension: {ext} on {p}"
    assert total_size < 3 * 1024 * 1024 * 1024, "Archive exceeds 3 GiB!"
    print(f"  [PASS] File count: {file_count}, Total unpacked size: {total_size:,} bytes")
    
    # 3. Model & tools
    with open(root_cfg, "r", encoding="utf-8") as f:
        root_data = yaml.load(f, Loader=SandboxedIncludeLoader)
    
    declared_models = {root_data["model"]}
    for tool in root_data.get("tools", []):
        if isinstance(tool, str):
            assert tool in ALLOWED_TOOLS, f"Invalid tool: {tool}"
        elif isinstance(tool, dict) and "agent_tool" in tool:
            sub_cfg = root_dir / tool["agent_tool"]["config_path"]
            with open(sub_cfg, "r", encoding="utf-8") as sf:
                sub_data = yaml.load(sf, Loader=SandboxedIncludeLoader)
            declared_models.add(sub_data["model"])
            for st in sub_data.get("tools", []):
                assert st in ALLOWED_TOOLS, f"Invalid sub-agent tool: {st}"
                
    assert len(declared_models) == 1, f"Multiple models declared: {declared_models}"
    model = next(iter(declared_models))
    assert model in ALLOWED_MODELS, f"Model not permitted: {model}"
    print(f"  [PASS] Single base model rule verified: {model}")
    print(f"  [PASS] All tools successfully mapped to closed ToolRegistry")
    print("=" * 60)
    print("🎉 ALL ADK SPECIFICATION CHECKS PASSED!")
    print("=" * 60)

validate_submission(SUBMISSION_DIR)
"""))

    # Cell 8: Markdown Section - SWE-bench task exploration
    cells.append(nbf.v4.new_markdown_cell("""## 🔬 Real SWE-bench Task Exploration & Problem Localization

In the hidden test split, instances are provided in `tasks.jsonl`. Each record contains:
* `instance_id`: Unique identifier (e.g. `fastapi_15661`, `requests_...`, `rich_...`)
* `repo`: Target GitHub repository name
* `base_commit`: The git commit hash at which the test container snapshot is extracted
* `problem_statement`: The issue description or pull request description
* `test_patch`: The hidden unit test patch used in Phase 2 verification

Below, we demonstrate how JudgeGuard parses and triages problem statements.
"""))

    # Cell 9: Code Cell 4 - Task inspection
    cells.append(nbf.v4.new_code_cell("""# Step 4: Inspect tasks from the competition dataset
import json

tasks_paths = [
    Path("/kaggle/input/gemma-4-developer-agent/tasks.jsonl"),
    Path("../scratch/tasks.jsonl"),
    Path("tasks.jsonl")
]

tasks_file = next((p for p in tasks_paths if p.exists()), None)

if tasks_file:
    print(f"Loading sample tasks from: {tasks_file}...")
    sample_tasks = []
    with open(tasks_file, "r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            if i >= 3:
                break
            sample_tasks.append(json.loads(line))
            
    for t in sample_tasks:
        print("-" * 50)
        print(f"Instance ID: {t['instance_id']}")
        print(f"Repository:  {t['repo']}")
        print(f"Base Commit: {t['base_commit'][:12]}...")
        print(f"Problem:     {t['problem_statement'][:160].strip()}...")
else:
    print("ℹ️ tasks.jsonl not found in local path — this block will automatically run on Kaggle!")
"""))

    # Cell 10: Markdown Section - 3-Tier Diff Engine
    cells.append(nbf.v4.new_markdown_cell("""## ⚡ The 3-Tier Resilient File Editing Algorithm

One of the most powerful features of `adk-eval-core` used by `edit_file` is its **3-tier resilient replacement engine** (`apply_replacement`). When models generate code edits, spacing or minor indentation differences can cause standard string replacements to fail. The 3-tier algorithm addresses this systematically:

1. **Tier 1 (`exact`)**: Exact character-for-character substring match.
2. **Tier 2 (`flexible`)**: Line-by-line match after stripping leading/trailing whitespace on each line, re-indenting `new_string` to preserve the original block's indentation.
3. **Tier 3 (`regex`)**: Tokenizes `old_string` around code delimiters `( ) : [ ] { } > = <` with whitespace wildcards `\\s*`.

Below is an interactive implementation and test of this engine:
"""))

    # Cell 11: Code Cell 5 - 3-tier diff engine
    cells.append(nbf.v4.new_code_cell("""# Step 5: Demonstration of the 3-tier resilient replacement engine
import re

def apply_replacement(content: str, old_string: str, new_string: str) -> tuple[str, str]:
    # Tier 1: Exact match
    if old_string in content:
        return content.replace(old_string, new_string, 1), "exact"
        
    # Tier 2: Flexible line-by-line whitespace match
    content_lines = content.splitlines(keepends=True)
    old_lines = [l.strip() for l in old_string.splitlines() if l.strip()]
    
    for i in range(len(content_lines) - len(old_lines) + 1):
        window = [content_lines[i + j].strip() for j in range(len(old_lines))]
        if window == old_lines:
            # Preserve baseline indentation
            baseline_indent = len(content_lines[i]) - len(content_lines[i].lstrip())
            indent_str = content_lines[i][:baseline_indent]
            indented_new = \"\\n\".join(indent_str + l.lstrip() for l in new_string.splitlines()) + \"\\n\"
            
            new_content = \"\".join(content_lines[:i]) + indented_new + \"\".join(content_lines[i + len(old_lines):])
            return new_content, "flexible"
            
    # Tier 3: Regex delimiter tokenization
    tokens = re.split(r'([\\(\\)\\[\\]\\{\\}:,=>])', old_string)
    pattern_parts = [re.escape(t.strip()) for t in tokens if t.strip()]
    regex_pattern = r'\\s*'.join(pattern_parts)
    
    match = re.search(regex_pattern, content)
    if match:
        start, end = match.span()
        return content[:start] + new_string + content[end:], "regex"
        
    raise ValueError("Target string not found in content across all 3 tiers.")

# Test code snippet
sample_code = \"\"\"def calculate_clv(price, cost):
    margin = price - cost
    if margin <= 0:
        return 0.0
    return margin * 1.5
\"\"\"

# Suppose the model emitted code with slight indentation discrepancies:
target_old = \"\"\"if margin <= 0:
    return 0.0\"\"\"

target_new = \"\"\"if margin <= 0:
    logging.warning('Zero or negative margin detected')
    return 0.0\"\"\"

updated_code, strategy = apply_replacement(sample_code, target_old, target_new)
print(f"Applied replacement strategy: [{strategy}]\\n")
print(updated_code)
"""))

    # Cell 12: Markdown Section - Packaging & Submission
    cells.append(nbf.v4.new_markdown_cell("""## 📦 Packaging `submission.zip` & Verification

We now package all validated submission files into `submission.zip` and run a sandbox verification extracting it into a temporary test environment.
"""))

    # Cell 13: Code Cell 6 - Packaging
    cells.append(nbf.v4.new_code_cell("""# Step 6: Package submission.zip and verify
import zipfile
import tempfile

OUTPUT_ZIP = Path("submission.zip")
allowed_dirs = {"configs", "prompts", "sub_agents", "skills", "adapters"}
allowed_root_files = {"agent.yaml", "agent.yml", "root_agent.yaml", "root_agent.yml", "eval_config.yaml"}

with zipfile.ZipFile(OUTPUT_ZIP, "w", zipfile.ZIP_DEFLATED) as zf:
    for p in SUBMISSION_DIR.rglob("*"):
        if p.is_file():
            rel = p.relative_to(SUBMISSION_DIR)
            if rel.suffix == ".zip" or ".git" in rel.parts:
                continue
            if len(rel.parts) == 1 and rel.name in allowed_root_files:
                zf.write(p, arcname=str(rel))
            elif len(rel.parts) > 1 and rel.parts[0] in allowed_dirs:
                zf.write(p, arcname=str(rel))

print(f"✅ Packaged {OUTPUT_ZIP.name} ({OUTPUT_ZIP.stat().st_size:,} bytes)")

# Test extracting into clean temporary directory
with tempfile.TemporaryDirectory() as tmp_dir:
    tmp_path = Path(tmp_dir)
    with zipfile.ZipFile(OUTPUT_ZIP, "r") as zf:
        zf.extractall(tmp_path)
    validate_submission(tmp_path)

print("\\n🚀 submission.zip is 100% verified and ready for scoring on Kaggle!")
"""))

    # Cell 14: Markdown Summary & Submission Command
    cells.append(nbf.v4.new_markdown_cell("""## 🏁 How to Submit to Kaggle

To submit this solution to the competition:

### Via Kaggle CLI:
```bash
kaggle competitions submit -c gemma-4-developer-agent \\
  -f submission.zip \\
  -m "JudgeGuard Autonomous Developer Agent v1.0 - Multi-Agent Governance & Declarative SWE-bench Coder"
```

### Via Kaggle Web UI:
1. Navigate to [Google - The Gemma 4 Developer Agent Competition / Submissions](https://www.kaggle.com/competitions/gemma-4-developer-agent/submissions).
2. Click **Submit Prediction**.
3. Upload `submission.zip`.
4. Enter description: `JudgeGuard Autonomous Developer Agent v1.0`.
5. Click **Submit**.

---

### 🛡️ JudgeGuard Core Principles
* **Empirical Integrity**: Verified test results before patch submission.
* **Open Science**: Transparent code, public notebooks, zero obfuscation.
* **Deterministic Execution**: Declarative agent tree compiled by official ADK compiler.
"""))

    nb.cells = cells
    with open(output_path, "w", encoding="utf-8") as f:
        nbf.write(nb, f)
    print(f"🎉 Created notebook at: {output_path} with {len(cells)} cells.")

if __name__ == "__main__":
    out = Path("judgeguard_gemma4_developer_agent.ipynb")
    create_judgeguard_notebook(out)
