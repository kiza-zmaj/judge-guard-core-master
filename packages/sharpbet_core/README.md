# ⚽ SharpBet Core v3.0

> **Enterprise Quantitative Sports Betting & Walk-Forward Forensic Audit Engine**  
> *Deterministic Expected Value • Temperature Scaling Calibration • Pinnacle CLV Verification • Fail-Closed Risk Governance*

---

## 🎯 Executive Overview

**SharpBet Core** is a production-grade quantitative sports analytics and model validation engine engineered to bridge the gap between academic football modeling and institutional sports trading.

Unlike simplistic "tipster bots" or uncalibrated machine learning scripts, SharpBet Core implements a mathematically hardened **11-step decision pipeline** designed to eliminate lookahead bias, verify closing-line value (CLV) against sharp market makers (Pinnacle), and protect bankroll capital through an empirical fail-closed governance gate.

```
[1] Raw Poisson Probs  ──► [2] Model Fair Odds ──► [3] Power De-vig Market
        │
[4] Best Market Odds   ──► [5] Pinnacle Closing ──► [6] True CLV Benchmark
        │
[7] Calibrated EV      ──► [8] Kelly Criterion  ──► [9] Realized P&L
        │
[10] OOS Calibration   ──► [11] 3-Gate Decision Gate (Fail-Closed)
```

---

## 🔬 Core Differentiators & Mathematical Foundations

### 1. Zero-Lookahead Walk-Forward Engine
* **Historical Horizon:** Backtested across 1,140 real Premier League matches (3 complete seasons: 2022/23, 2023/24, 2024/25).
* **Burn-in & Out-of-Sample (OOS):** Strictly enforced chronological sequencing. The model uses a 380-match burn-in window and evaluates exactly 760 clean out-of-sample matches with zero data leakage.
* **Pre-Match Decision Integrity:** Candidate signals are filtered strictly before kickoff without peeking into future market movements.

### 2. Multi-Class Expected Calibration Error (ECE) & Temperature Scaling
* Predictions are decomposed using **One-vs-Rest (OvR)** binary reliability bins across Home, Draw, and Away outcomes.
* Rolling out-of-sample temperature scaling optimizes probability reliability:
  $$\text{Macro ECE} = 3.79\% \quad (\text{Threshold} \le 6.0\%)$$
  $$\text{Brier Score} = 0.5921 \quad (\text{Benchmark} \le 0.6500)$$

### 3. Institutional Market Alpha & Fair CLV (Closing Line Value)
* Integrates true kickoff closing odds from **Pinnacle (`PSCH`, `PSCD`, `PSCA`)** with documented fallbacks.
* Applies **Shin / Power De-vigging** to strip the bookmaker's overround before comparing against placed odds, ensuring true market alpha estimation rather than margin illusions.

### 4. Empirical 3-Gate Fail-Closed Governance
Every trade must pass three independent statistical gates before any capital allocation:
* **Gate A (Calibration):** $\text{ECE} \le 6.0\%$, $\text{Brier} \le 0.65$. *(PASS)*
* **Gate B (Market Alpha):** $\text{Mean Fair CLV} > 0.0\%$, $95\%\ \text{CI Lower} > -2.0\%$.
* **Gate C (Economic Significance):** $\text{ROI} > 0\%$, $95\%\ \text{CI Lower} \ge -2.0\%$, $\text{Min Bets} \ge 100$.
* **Fail-Closed Guarantee:** If any gate fails, the engine programmatically forces `STAKE = €0.00` and enters `RESEARCH_ONLY` mode, preventing catastrophic drawdown.

### 5. Leave-K-Out Tail Sensitivity & Stress Testing
* Automated bias auditor (`bias_analysis.py`) tests whether strategy ROI is driven by genuine statistical edge or outlier luck.
* Computes exact $K$-outlier flip points, ensuring strategy survivability under market regime shifts.

---

## 🚀 Quick Start

### 1. Local Python Installation
```bash
# Clone and navigate to package
cd packages/sharpbet_core

# Install isolated dependencies
pip install -r requirements.txt

# Run full Walk-Forward Backtest & Forensic Audit
python3 -m unified_betting_core.main --walk-forward
```

### 2. Running the REST API Server
```bash
python3 unified_betting_core/api/server.py
# Server listening on http://localhost:5001
```

### 3. Docker Deployment (One-Click)
```bash
docker-compose up --build -d
```

---

## 📡 REST API Specification

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Service status, pipeline version, and evidence taxonomy. |
| `GET` | `/api/fixtures` | Returns upcoming scheduled fixtures with team ratings. |
| `GET` | `/api/value-bets` | Evaluates active fixtures through the 11-step pipeline and returns calibrated +EV opportunities. |
| `GET` | `/api/audit-all` | Full forensic audit log of all screened matches with rejection reasons. |
| `POST` | `/api/walk-forward` | Triggers a fresh walk-forward simulation and returns Gate A/B/C verdicts. |

---

## 📦 Evidence Package (14 Forensic Artifacts)

Running the walk-forward engine automatically produces 14 cryptographic forensic artifacts in `data/evidence_package/`:
1. `oos_predictions.csv` — All 760 out-of-sample predictions and actual results.
2. `calibration_dataset.csv` — Raw vs. calibrated probabilities.
3. `reliability_table.csv` — Ten-bin reliability diagram values.
4. `ece_brier_output.json` — Quantified ECE, MCE, and Brier metrics.
5. `candidate_clv_dataset.csv` — Match-by-match CLV vs. Pinnacle closing lines.
6. `clv_statistics.json` — Mean, median, std error, and 95% CI of CLV.
7. `pnl_dataset.csv` — Complete ledger of placed stakes, returns, and cumulative bankroll.
8. `roi_statistics.json` — Turnover, net profit, yield, and max drawdown.
9. `leakage_test_results.json` — Pre-kickoff timestamp and isolation verification.
10. `gate_verdicts.json` — Formal verdicts for Gate A, Gate B, and Gate C.
11. `timestamps_audit.json` — Timing checks proving zero forward-looking data.
12. `bias_and_stress_test.json` — Leave-K-out tail analysis and Home/Draw/Away asymmetry.
13. `reproduce_command.sh` — Exact bash script to reproduce the entire run.
14. `version_hashes.json` — Cryptographic SHA-256 integrity checksums for every artifact.

---

## 📄 License & Commercial Rights
Copyright (c) 2026. All rights reserved. Commercial deployment and resale licenses available.
