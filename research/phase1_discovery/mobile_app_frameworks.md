# 📱 Mobile App Research Phase 1: Frameworks & Discovery

> **Objective:** Evaluate and standardize mobile app frameworks for Antigravity agent-driven prototyping.

---

## 📊 Framework Comparison Matrix

| Framework | Architecture | Agent State Sync | Development Velocity | PWA / Offline Support | Recommendation |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **React PWA (Vite)** | Web-native + Service Workers | High (Direct JSON polling / SSE / WS) | Instant (Hot Module Replacement) | Native Web PWA | ⭐ **Selected Standard** |
| **React Native (Expo)** | Native Mobile Runtime | Medium (Bridge API / Metro reload) | Fast | Web export available | Alternate for Native Mobile |
| **Flutter** | Dart Engine rendering | Medium (Custom Channel) | Medium | Web support available | Heavy runtime overhead |
| **Capacitor / Ionic** | WebView wrapper | High | Fast | Web PWA standard | Secondary wrapper choice |

---

## 🎯 Key Discovery Insights
1. **React PWA (Vite + React)** provides zero-build latency for live agent state modification ("Vibe Coding").
2. Bridge scripts like [`mobile_bridge.py`](file:///home/kizamladjanijebac/Documents/jude%20guard/judge-guard-core-master/src/antigravity_core/mobile_bridge.py) can update state asynchronously without restarting dev servers.
3. Service worker caching guarantees offline functionality while polling `/app_config.json` every 500ms when online.
