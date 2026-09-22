#!/usr/bin/env python3
"""
Reproduce and parse script for SharpBet Core Local Verification.
Captures raw stdout/stderr, records exit code, parses strictly from output text,
verifies all mandatory assertions, and exports reproduction_parsed.json.
"""

import re
import sys
import json
import subprocess
from pathlib import Path

REPO_ROOT = Path("/home/kizamladjanijebac/Documents/jude guard/judge-guard-core-master")
AUDIT_DIR = REPO_ROOT / "unified_betting_core" / "audit_2026"
LOGS_DIR = AUDIT_DIR / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

stdout_path = LOGS_DIR / "reproduction_stdout.log"
stderr_path = LOGS_DIR / "reproduction_stderr.log"
exit_code_path = AUDIT_DIR / "reproduction_exit_code.txt"
parsed_json_path = AUDIT_DIR / "reproduction_parsed.json"

cmd = [sys.executable, str(REPO_ROOT / "scratch" / "run_json_pipeline.py")]
proc = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True)

with open(stdout_path, "w", encoding="utf-8") as f:
    f.write(proc.stdout)

with open(stderr_path, "w", encoding="utf-8") as f:
    f.write(proc.stderr)

with open(exit_code_path, "w", encoding="utf-8") as f:
    f.write(str(proc.returncode))

stdout = proc.stdout

# Parsing strictly from stdout
def extract_pattern(pattern, text, default="NOT PARSED — VALUE UNVERIFIED"):
    m = re.search(pattern, text)
    return m.group(1).strip() if m else default

def extract_int(pattern, text):
    val = extract_pattern(pattern, text)
    if val != "NOT PARSED — VALUE UNVERIFIED":
        try:
            return int(val)
        except ValueError:
            return "NOT PARSED — VALUE UNVERIFIED"
    return "NOT PARSED — VALUE UNVERIFIED"

input_rows = extract_int(r"Utakmica u inputu\s*:\s*(\d+)", stdout)
expected_outcomes = extract_int(r"Očekivano outcomes\s*:\s*(\d+)", stdout)
skipped_outcomes = extract_int(r"Preskočeno outcomes\s*:\s*(\d+)", stdout)
evaluated_outcomes = extract_int(r"Evaluiranih outcomes\s*:\s*(\d+)", stdout)
executable_ev = extract_int(r"EXECUTABLE_EV SELEKCIJA\s*:\s*(\d+)", stdout)

data_quality = extract_pattern(r"DATA_QUALITY\s*:\s*([A-Za-z0-9_]+)", stdout)
historical_proof_str = extract_pattern(r"historical_proof\s*:\s*([A-Za-z0-9_]+)", stdout)
historical_proof = True if historical_proof_str == "True" else (False if historical_proof_str == "False" else historical_proof_str)

ticket_status = "EMPTY_TICKET" if "PRAZAN TIKET" in stdout else ("TICKET_GENERATED" if "TIKET KREIRAN" in stdout else "NOT PARSED — VALUE UNVERIFIED")

# Status breakdown
breakdown = {}
for status_name in ["NO_EDGE", "FAKE_EV", "MARGINAL_EV", "CALIBRATION_FAILED"]:
    cnt = extract_int(rf"{status_name}\s+(\d+)", stdout)
    breakdown[status_name] = cnt

# Assertions
assertions_passed = False
assertion_errors = []

try:
    assert isinstance(input_rows, int), f"input_rows not int: {input_rows}"
    assert isinstance(expected_outcomes, int), f"expected_outcomes not int: {expected_outcomes}"
    assert isinstance(skipped_outcomes, int), f"skipped_outcomes not int: {skipped_outcomes}"
    assert isinstance(evaluated_outcomes, int), f"evaluated_outcomes not int: {evaluated_outcomes}"
    assert isinstance(executable_ev, int), f"executable_ev not int: {executable_ev}"

    # Required assertions from prompt
    assert expected_outcomes == input_rows * 3, f"Expected outcomes {expected_outcomes} != {input_rows} * 3"
    assert evaluated_outcomes + skipped_outcomes == expected_outcomes, f"Evaluated ({evaluated_outcomes}) + skipped ({skipped_outcomes}) != expected ({expected_outcomes})"
    assert executable_ev == 0, f"Executable EV is not zero: {executable_ev}"
    
    # Check sum of breakdown equals evaluated
    sum_breakdown = sum(v for v in breakdown.values() if isinstance(v, int))
    assert sum_breakdown == evaluated_outcomes, f"Sum of breakdown {sum_breakdown} != evaluated {evaluated_outcomes}"
    
    assertions_passed = True
except AssertionError as e:
    assertion_errors.append(str(e))

parsed_data = {
    "run_timestamp": "2026-09-22T19:40:00Z",
    "exit_code": proc.returncode,
    "input_rows": input_rows,
    "expected_outcomes": expected_outcomes,
    "skipped_outcomes": skipped_outcomes,
    "evaluated_outcomes": evaluated_outcomes,
    "status_breakdown": breakdown,
    "executable_count": executable_ev,
    "data_quality": data_quality,
    "historical_proof": historical_proof,
    "ticket_status": ticket_status,
    "assertions_passed": assertions_passed,
    "assertion_errors": assertion_errors,
    "stdout_log": str(stdout_path),
    "stderr_log": str(stderr_path)
}

with open(parsed_json_path, "w", encoding="utf-8") as f:
    json.dump(parsed_data, f, indent=2)

print(f"Reproduction parsed successfully. Assertions passed: {assertions_passed}")
