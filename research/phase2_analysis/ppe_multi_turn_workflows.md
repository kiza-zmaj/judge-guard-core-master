# 🧠 PPE Architecture: Multi-Turn Workflow Management Analysis

> **Focus:** Declarative YAML Scripting (`.ai.yaml`), Multi-Turn Control, and Plan-Execute-Verify Cycle.
> **Engine:** Programmable Prompt Engine (PPE)
> **Verification:** JudgeGuard v2.1 Compliance

---

## 🏛️ PPE Architecture Overview

The **Programmable Prompt Engine (PPE)** shifts prompt engineering from static strings to **executable, declarative scripts** stored as `.ai.yaml` files. PPE encapsulates multi-turn agentic conversations, prompt templates, system instructions, and deterministic control logic into local-first, version-controlled artifacts.

```python
# PPE Multi-Turn Workflow Management Configuration
PPE_ARCHITECTURE_COMPONENTS = {
    "scripting_engine": "Declarative YAML-based language (.ai.yaml)",
    "turn_management": {
        "separators": ["---", "***"], # Triple dashes or asterisks manage dialogue turns
        "auto_invocation": "autoRunLLMIfPromptAvailable: true", # Triggers LLM automatically at prompt segments
        "context_state": "Local-first persistence for execution history"
    },
    "control_flow_instructions": {
        "built_in_logic": ["$if", "$set", "$echo", "$while"], # Turing-complete control flow
        "agent_tools": {
            "interaction": "[[@input]]", # Interactive user prompts
            "filesystem": "[[@file]]", # OS/file interaction
            "composition": "[[@agent_name(params)]]" # Nested agent calls
        }
    }
}
```

---

## 📋 The 4 Key Architectural Pillars

### 1. Role of YAML Scripts (`.ai.yaml`)
- **Declarative Structure:** Encapsulates prompt headers, variables, tool permissions, and model parameters (`temperature`, `top_p`) in a clean YAML schema.
- **Local-First Persistence:** Preserves session state locally across agent invocations without relying on third-party cloud state servers.

### 2. Multi-Turn Separation & Auto-Execution
- **Turn Separators (`---` / `***`):** Explicitly delimits dialogue turns, defining boundaries between User, Assistant, and System frames.
- **`autoRunLLMIfPromptAvailable: true`:** Enables autonomous chain-of-thought progression across turns without waiting for manual user intervention after every step.

### 3. Control Flow & Turing-Complete Directives
- **Directives (`$if`, `$set`, `$while`, `$echo`):** Enables dynamic branching, variable mutation, and conditional loops directly inside the prompt template.
- **Agent Tools Integration:**
  - `[[@input]]`: Direct human-in-the-loop parameter injection.
  - `[[@file]]`: Automatic workspace file reading/writing.
  - `[[@agent_name(params)]]`: Compositional subagent invocation.

### 4. Plan-Execute-Verify Pattern

```python
EXECUTION_WORKFLOW_PATTERN = {
    "step_1_planning": "Planning Script requests structured JSON/YAML plan from LLM",
    "step_2_execution": "Execution Script iterates through items using $while or sequential agent calls",
    "step_3_verification": "Verification Script uses $if conditions or 'Critic' agents to validate state"
}
```

- **Planning Phase:** Generates structured execution graph.
- **Execution Phase:** Iterates through tasks using `$while` loops and subagent calls.
- **Verification Phase:** Evaluates outputs against `JudgeGuard` rules and `$if` assertions before finalization.

---

## 🏁 Summary

PPE architecture manages multi-turn workflows by treating prompts as executable scripts rather than static strings. It uses a unique **Script Composition** model where separate scripts handle planning, execution, and verification in a deterministic loop. This enables local-first, offline agentic behavior with complex logic embedded directly in the dialogue flow.
