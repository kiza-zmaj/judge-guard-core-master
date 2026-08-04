# ⚙️ Mobile App Research Phase 2: Integration & Tooling

> **Objective:** Analyze integration protocols and tooling between Python backend agents and React Mobile PWA.

---

## 🛠️ Architectural Tooling Stack

1. **State Store:** `src/mobile_app_pwa/public/app_config.json`
2. **Agent Bridge:** `src/antigravity_core/mobile_bridge.py`
3. **PWA Runtime:** React + Vite + Axios polling loop (500ms) with `visibilitychange` listener.
4. **Verification Engine:** `judge_guard.py` pushing live verdicts via `bridge.push_verdict()`.

---

## 🔄 Data Flow Protocol

```mermaid
sequenceDiagram
    participant Agent as Antigravity Agent
    participant Bridge as mobile_bridge.py
    participant File as app_config.json
    participant PWA as React PWA App
    participant Judge as judge_guard.py

    Agent->>Bridge: update_state({"title": "...", "theme": "dark"})
    Bridge->>File: Write JSON (Async Background Thread)
    Judge->>Bridge: push_verdict(action, status, reason)
    Bridge->>File: Write last_verdict to app_config.json
    PWA->>File: Poll GET /app_config.json?t=timestamp
    File-->>PWA: Return updated JSON
    PWA->>PWA: Render dynamic components & verdict card
```
