# NotebookLM + Kaggle CLI Closed-Loop Pipeline: Unit & Integration Test Cases

## Test File
`tests/test_notebooklm_kaggle_pipeline.py`

## Test Purpose
Verify the end-to-end integration and robustness of the NotebookLM-grounded Kaggle CLI system. The system enforces NotebookLM as the authoritative **Single Source of Truth (SISTEM ZA PROVERU)** for competition rules, metric definitions, and data integrity constraints, while leveraging Kaggle CLI as the **Execution Engine (AKCIONI MOTOR)** for dataset retrieval, local cross-validation, automated submission, and leaderboard polling.

## Test Cases Overview

| Case ID | Feature Description | Test Type | Focus Area |
| :--- | :--- | :--- | :--- |
| **NLM-01** | NotebookLM Source of Truth notebook/alias resolution | Positive Test | Valid UUID & alias resolution |
| **NLM-02** | NotebookLM rule & metric constraint query parsing | Positive / Mock | Factual extraction of rules & metric limits |
| **KAG-01** | Kaggle credentials and environment verification | Security / State | Detection of `kaggle.json` & permissions |
| **KAG-02** | Kaggle CLI dataset download and archive extraction | Integration / Mock | Subprocess handling for `competitions download` |
| **EDA-01** | Data integrity, shape verification, and anomaly detection | Functional / Logic | Null-handling, column validation against schema |
| **CV-01** | Leak-free local Cross-Validation evaluation | Algorithmic / Math | Replicated metric computation out-of-sample |
| **SUB-01** | Kaggle CLI automated prediction submission | Positive / Mock | Formatted call to `competitions submit` |
| **SUB-02** | Submission status polling & Leaderboard rank extraction | Async / Polling | Resilient polling & JSON score extraction |
| **LOOP-01** | Closed-Loop Hypothesis Gate — Approved Execution Flow | E2E Positive | Complete pass through NLM -> CV -> Submit |
| **LOOP-02** | Closed-Loop Hypothesis Gate — Rule Violation Interception | E2E Security / Gate | Block submission when hypothesis breaks rules |

---

## Detailed Test Steps

### NLM-01: NotebookLM Alias and UUID Resolution
**Test Purpose**: Ensure that competition or topic aliases correctly map to valid NotebookLM UUIDs, and unknown aliases raise explicit descriptive errors.

**Test Data Preparation**:
- Mock alias table with `"kaggle-challenge": "83fc213b-0684-4251-8980-42e0610a6742"`.

**Test Steps**:
1. Call `resolve_notebook_id("kaggle-challenge")`.
2. Verify resolved UUID matches expected alias value.
3. Call `resolve_notebook_id("unknown-random-alias")` with strict validation.
4. Verify fallback/handling behavior.

**Expected Results**:
- Alias resolves to UUID format.
- Direct UUID strings pass through untouched.

---

### NLM-02: Rule and Metric Constraint Extraction
**Test Purpose**: Verify that `NLMRuleVerifier.query_rule_constraint()` correctly formats queries to the NotebookLM orchestrator and parses grounded constraints (e.g. evaluation metric, missing value rules, external data bans).

**Test Data Preparation**:
- Mock `nlm_orchestrator.query_notebook` response returning structured metric guidance.

**Test Steps**:
1. Arrange mocked NLM response containing metric constraint: `{"metric": "LogLoss", "missing_strategy": "median", "external_data_allowed": false}`.
2. Act: Call `verifier.verify_metric_constraint(competition_id="football-match-prediction", metric_name="LogLoss")`.
3. Assert: Result confirms metric alignment and extracts rule dict with zero hallucinations.

**Expected Results**:
- Verifier returns valid compliance dictionary with `compliant=True`.

---

### KAG-01: Kaggle Credentials and Environment Verification
**Test Purpose**: Ensure `KaggleCLIRunner.check_environment()` checks existence of `~/.kaggle/kaggle.json`, inspects valid JSON structure (`username`, `key`), and warns/blocks if credentials are missing or corrupted.

**Test Data Preparation**:
- Test with temporary valid `kaggle.json` mock and missing file mock.

**Test Steps**:
1. Point configuration to mock credentials path.
2. Run `check_environment()`.
3. Verify returns `status="READY"`, `username="kizabgd123"`.
4. Point configuration to nonexistent path and assert `status="MISSING_CREDENTIALS"`.

**Expected Results**:
- Valid credentials succeed; missing credentials fail closed with remediation advice.

---

### KAG-02: Kaggle CLI Data Download & Extraction
**Test Purpose**: Verify `KaggleCLIRunner.download_competition_data()` calls the `kaggle competitions download` CLI with proper arguments, handles zip extraction safely, and checks target folder contents.

**Test Data Preparation**:
- Mock `subprocess.run` to simulate `kaggle competitions download -c test-comp`.
- Create dummy zip archive in temporary directory.

**Test Steps**:
1. Trigger download with destination directory.
2. Verify command line arguments passed to subprocess.
3. Verify extraction unzips files and returns list of extracted data files.

**Expected Results**:
- Returns status `SUCCESS` with valid file paths.

---

### EDA-01: Data Integrity & Schema Validation
**Test Purpose**: Check dataset columns, missing values, and target distribution against rules verified by NotebookLM.

**Test Data Preparation**:
- Synthetic DataFrame with valid features and intentional anomaly (e.g. negative odds or missing target).

**Test Steps**:
1. Load dataset into validator.
2. Check schema against verified competition spec.
3. Assert validator flags anomalies and computes summary statistics.

**Expected Results**:
- Anomalies identified; clean data passes validation.

---

### CV-01: Local Cross-Validation Replicate
**Test Purpose**: Ensure local CV reproduces the official metric with zero temporal or target leakage.

**Test Data Preparation**:
- Synthetic walk-forward or stratified fold splits.

**Test Steps**:
1. Run local CV evaluator.
2. Verify no train/val index overlap.
3. Verify returned score matches expected deterministic calculation.

**Expected Results**:
- Leak-free metric computed within expected boundaries.

---

### SUB-01: Kaggle CLI Automated Prediction Submission
**Test Purpose**: Verify submission file generation and execution of `kaggle competitions submit`.

**Test Data Preparation**:
- Valid mock `submission.csv` containing required ID and Target columns.

**Test Steps**:
1. Invoke `submit_prediction(competition_id, file_path, message)`.
2. Inspect subprocess arguments (`kaggle competitions submit -c ... -f ... -m ...`).
3. Assert return code is 0 and output contains submission confirmation.

**Expected Results**:
- Submission dispatched cleanly with message metadata.

---

### SUB-02: Submission Status Polling & Leaderboard Rank Extraction
**Test Purpose**: Verify polling loop for submission evaluation completion and leaderboard retrieval.

**Test Data Preparation**:
- Mock sequence of subprocess outputs: `pending` -> `successfully scored` (score: 0.1234).

**Test Steps**:
1. Run `poll_submission_status(competition_id, max_retries=3, delay_sec=0.01)`.
2. Verify polling loop terminates upon status change.
3. Retrieve leaderboard summary and assert score parsing.

**Expected Results**:
- Final status, score, and rank parsed accurately without infinite hanging.

---

### LOOP-01: Closed-Loop Hypothesis Gate — Approved Execution Flow
**Test Purpose**: Execute the full closed-loop workflow when hypothesis adheres to all verified rules.

**Test Steps**:
1. Define hypothesis: "LightGBM baseline with 5-fold CV using in-competition features only".
2. Consult NLM Rule Verifier -> returns `APPROVED`.
3. Run EDA & Local CV -> returns metric score.
4. Dispatch Kaggle CLI submission.
5. Poll leaderboard status.
6. Verify entire state machine completes with status `CYCLE_COMPLETE`.

**Expected Results**:
- End-to-end pipeline succeeds without manual intervention.

---

### LOOP-02: Closed-Loop Hypothesis Gate — Rule Violation Interception
**Test Purpose**: Verify that the safety gate halts the pipeline if a hypothesis violates competition rules (e.g. attempting to use external data when forbidden).

**Test Steps**:
1. Define hypothesis with external data flag: `use_external_data=True`.
2. Consult NLM Rule Verifier -> returns `BLOCKED: External data prohibited by competition rules`.
3. Attempt pipeline execution.
4. Assert pipeline HALTS before Kaggle CLI submit is called.
5. Assert submission file is NOT sent to Kaggle.

**Expected Results**:
- Fail-closed security behavior: zero invalid submissions dispatched.

---

## Test Considerations

### Mock Strategy
- External CLIs (`nlm` and `kaggle`) are mocked via `unittest.mock.patch("subprocess.run")` to guarantee fast, deterministic, offline test execution in CI/CD environments.
- Real filesystem interactions utilize temporary directories (`tempfile.TemporaryDirectory`).

### Boundary Conditions
- Missing or malformed `kaggle.json`.
- Missing target columns in `submission.csv`.
- Rate-limiting or timeout during submission status polling.
- NotebookLM server error or missing notebook ID.

### Asynchronous & Polling Operations
- Submission polling uses configurable delay parameters (default seconds, test milliseconds) with strict `max_retries` timeout to prevent deadlocks.
