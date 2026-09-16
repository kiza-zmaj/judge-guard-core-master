Do NOT choose only one issue. Resolve all four issues end-to-end, in this exact order, and do not declare the project production-valid until every stage passes.

### PHASE 1 — ECE ANOMALY: HARD BLOCKER

Perform a forensic audit of `calculate_ece()` and every caller.

Determine exactly why the reported OOS ECE is `0.00%`.

Verify:

* bin construction
* bin boundaries
* inclusive/exclusive edge handling
* empty-bin behavior
* multiclass ECE implementation
* weighted aggregation
* probability normalization
* rounding
* whether ECE is calculated on raw, calibrated, validation, or already-fit predictions
* whether any calibration output is accidentally reused as ground truth
* whether the reported Maximum Calibration Error is calculated independently
* whether the same observations were used for calibration fitting and ECE evaluation

Create independent tests with manually verifiable expected results.

Generate an explicit reliability table:

`bin | count | mean_predicted_prob | empirical_frequency | abs_error`

Then independently recompute ECE from the persisted OOS predictions.

HARD RULE:

If ECE cannot be independently reproduced from untouched OOS predictions, the calibration gate MUST FAIL CLOSED.

Do not change thresholds merely to make the metric pass.

---

### PHASE 2 — REMOVE CIRCULAR CLV DEPENDENCY

Redesign CLV validation so it does NOT depend on `approved_bets`.

Create a historical candidate population using rules frozen before evaluating the historical period.

For every eligible historical candidate, persist:

* event ID
* prediction timestamp
* odds at decision time
* bookmaker/source
* closing odds
* model probability
* calibrated probability
* raw EV
* calibrated EV
* candidate/decision state
* CLV

Calculate CLV across the candidate population BEFORE current-bet approval.

The dependency must become:

`Historical Candidate Set`
→ `CLV Measurement`
→ `Market Alpha Evidence`
→ `Decision Gate`

NEVER:

`Approved Bet`
→ `CLV`
→ `Approval`

Explicitly test that CLV remains measurable when there are zero approved bets.

---

### PHASE 3 — MODULARIZE VALIDATION

Create independent production gates:

#### Gate A — CALIBRATION VALIDATION

Answers only:

“Are model probabilities calibrated out-of-sample?”

Use:

* OOS Brier
* OOS ECE
* Maximum Calibration Error
* reliability analysis
* sample-size threshold
* temporal drift

Do NOT use CLV or P&L as calibration metrics.

#### Gate B — MARKET ALPHA / CLV

Answers only:

“Does the strategy systematically beat the market reference?”

Use:

* CLV
* mean/median CLV
* sufficient sample size
* temporal robustness
* market reference definition
* confidence interval
* no future leakage

Do NOT call this a calibration result.

#### Gate C — ECONOMIC / P&L

Answers only:

“Does the predefined betting strategy generate positive OOS economic performance?”

Use:

* realized P&L
* ROI/yield
* turnover
* drawdown
* stake policy
* bankroll path
* confidence interval
* robustness across time periods

Do NOT tune the strategy thresholds after observing the OOS results.

---

### PHASE 4 — STATISTICAL RIGOR

Add uncertainty estimates for all material empirical metrics.

At minimum:

* ROI/yield confidence interval
* mean CLV confidence interval
* win-rate confidence interval
* calibrated probability uncertainty where applicable
* drawdown statistics
* sample sizes

Use statistically appropriate methods for the quantity being measured and document the assumptions.

Do not present point estimates without their uncertainty.

Do not interpret a confidence interval crossing zero as proof of edge.

---

### PHASE 5 — STRICT WALK-FORWARD INTEGRATION

Ensure the final historical experiment is genuinely chronological:

`PAST TRAIN`
→ `PAST CALIBRATION`
→ `OOS PREDICTION`
→ `REAL DECISION-TIME ODDS`
→ `CLV OBSERVED LATER`
→ `RESULT OBSERVED LATER`
→ `P&L`

No future observations may influence earlier predictions, calibration, threshold selection, or gate configuration.

Run explicit leakage tests.

---

### PHASE 6 — FINAL GOVERNANCE TAXONOMY

Use these independent statuses:

`RAW_EV`
`CALIBRATED_EV`
`CALIBRATION_PASS`
`MARKET_ALPHA_PASS`
`ECONOMIC_PASS`
`EMPIRICALLY_SUPPORTED_EV`
`EXECUTABLE_EV`

and rejection states:

`FAKE_EV`
`CALIBRATION_FAILED`
`MARKET_ALPHA_FAILED`
`ECONOMIC_VALIDATION_FAILED`
`INSUFFICIENT_EVIDENCE`
`DATA_DEGRADED`
`NO_EDGE`

`EMPIRICALLY_SUPPORTED_EV` is allowed ONLY when:

`Calibration Gate = PASS`
AND
`Market Alpha / CLV Gate = PASS`
AND
`Economic / P&L Gate = PASS`
AND
`Data Integrity = PASS`
AND
`Leakage Tests = PASS`

Otherwise:

`stake = €0.00`

FAIL CLOSED.

---

### PHASE 7 — EVIDENCE PACKAGE

Produce a final reproducible validation package containing:

1. raw OOS prediction dataset
2. calibration dataset
3. reliability table
4. ECE/Brier calculation output
5. historical candidate CLV dataset
6. CLV statistics + confidence intervals
7. historical P&L dataset
8. ROI/yield + confidence intervals
9. leakage-test results
10. gate-by-gate PASS/FAIL evidence
11. exact data timestamps
12. model/calibration version hashes
13. exact command to reproduce everything

Do not report “proof” unless the underlying artifact can be inspected and independently reproduced.

---

### FINAL RULE

Do NOT optimize the model to obtain PASS.

The objective is to determine the truth.

Possible valid final outcomes are:

`EMPIRICALLY_SUPPORTED_EV = PASS`

or

`EMPIRICALLY_SUPPORTED_EV = FAIL`

A FAIL backed by rigorous evidence is an acceptable and successful result.

A PASS without independently reproducible evidence is a system failure.
