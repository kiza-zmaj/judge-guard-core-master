#!/usr/bin/env python3
"""
Adversarial Test Suite for JudgeGuard Layer 4 Outcome Verifier.
Validates all attack vectors and failure modes to guarantee that:
1. Forged exit codes are caught.
2. Empty or missing manifests are rejected.
3. Ghost or missing artifacts fail.
4. SHA-256 mismatches fail.
5. Stale artifacts (older mtime) fail.
6. Contract tampering is detected.
7. Path traversal attacks fail.
8. Empty/zeroed media (e.g. Wayland black video) fail variance test.
9. Forged verdict signatures are rejected.
10. Non-existent git commit SHAs cannot receive or pass a verdict.
11. Invalid git SHA formats (e.g. dummy_sha) are rejected.
12. Legitimate golden path produces valid signed verdict ticket bound to real git commit.
"""

import os
import sys
import time
import json
import pytest
import tempfile
import shutil
import subprocess

# Ensure source tree is available
_current_dir = os.path.dirname(os.path.abspath(__file__))
_repo_root = os.path.abspath(os.path.join(_current_dir, ".."))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

from src.antigravity_core.outcome_verifier import (
    TrustedRunner,
    AcceptanceContract,
    VerdictSigner,
    EvidenceValidator,
    OutcomeVerifier,
    compute_file_sha256,
    PathSecurityError
)


def init_real_git_repo(workspace: str) -> str:
    """Initializes a real git repo and returns full 40-char HEAD commit SHA."""
    subprocess.run(["git", "init"], cwd=workspace, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=workspace, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=workspace, check=True, capture_output=True)
    dummy_file = os.path.join(workspace, ".initial_commit_anchor")
    with open(dummy_file, "w") as f:
        f.write("anchor")
    subprocess.run(["git", "add", "."], cwd=workspace, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "initial anchor commit"], cwd=workspace, check=True, capture_output=True)
    res = subprocess.run(["git", "rev-parse", "HEAD"], cwd=workspace, check=True, capture_output=True, text=True)
    return res.stdout.strip()


@pytest.fixture
def test_workspace():
    tmp_dir = tempfile.mkdtemp(prefix="judgeguard_test_")
    yield tmp_dir
    shutil.rmtree(tmp_dir, ignore_errors=True)


def test_empty_or_malformed_manifest_rejected(test_workspace):
    """Manifest is empty {} or missing required artifacts list."""
    sha = init_real_git_repo(test_workspace)
    contract_file = os.path.join(test_workspace, "contract.json")
    AcceptanceContract.create(
        run_id="run_test_empty",
        action="Test Action",
        criteria={},
        output_contract_path=contract_file,
        allowed_root=test_workspace
    )

    manifest_file = os.path.join(test_workspace, "manifest.json")
    with open(manifest_file, "w") as f:
        json.dump({}, f)

    verifier = OutcomeVerifier(project_root=test_workspace)
    success, msg, ticket = verifier.evaluate_task(
        run_id="run_test_empty",
        manifest_path=manifest_file,
        contract_path=contract_file,
        commit_sha=sha
    )

    assert not success
    assert "Manifest is empty" in msg or "missing required 'artifacts'" in msg
    assert ticket is None


def test_ghost_or_missing_artifact_rejected(test_workspace):
    """Manifest claims an artifact exists, but file is absent on disk."""
    sha = init_real_git_repo(test_workspace)
    contract_file = os.path.join(test_workspace, "contract.json")
    AcceptanceContract.create(
        run_id="run_test_ghost",
        action="Ghost Test",
        criteria={},
        output_contract_path=contract_file,
        allowed_root=test_workspace
    )

    manifest_file = os.path.join(test_workspace, "manifest.json")
    with open(manifest_file, "w") as f:
        json.dump({
            "artifacts": [
                {"path": "non_existent_file.py", "min_size_bytes": 10}
            ]
        }, f)

    verifier = OutcomeVerifier(project_root=test_workspace)
    success, msg, _ = verifier.evaluate_task(
        run_id="run_test_ghost",
        manifest_path=manifest_file,
        contract_path=contract_file,
        commit_sha=sha
    )

    assert not success
    assert "Artifact does not exist on disk" in msg


def test_sha256_hash_mismatch_rejected(test_workspace):
    """Manifest supplies an incorrect/forged SHA-256 for an existing file."""
    sha = init_real_git_repo(test_workspace)
    real_file = os.path.join(test_workspace, "output.txt")
    with open(real_file, "w") as f:
        f.write("Actual real content on disk.")

    contract_file = os.path.join(test_workspace, "contract.json")
    AcceptanceContract.create(
        run_id="run_test_hash",
        action="Hash Test",
        criteria={},
        output_contract_path=contract_file,
        allowed_root=test_workspace
    )

    manifest_file = os.path.join(test_workspace, "manifest.json")
    with open(manifest_file, "w") as f:
        json.dump({
            "artifacts": [
                {"path": "output.txt", "sha256": "0000000000000000000000000000000000000000000000000000000000000000"}
            ]
        }, f)

    verifier = OutcomeVerifier(project_root=test_workspace)
    success, msg, _ = verifier.evaluate_task(
        run_id="run_test_hash",
        manifest_path=manifest_file,
        contract_path=contract_file,
        commit_sha=sha
    )

    assert not success
    assert "SHA-256 mismatch" in msg


def test_forged_exit_code_rejected(test_workspace):
    """Agent manifest claims exit_code 0, but TrustedRunner saw exit code 1."""
    sha = init_real_git_repo(test_workspace)
    contract_file = os.path.join(test_workspace, "contract.json")
    AcceptanceContract.create(
        run_id="run_test_exit",
        action="Exit Code Test",
        criteria={},
        output_contract_path=contract_file,
        allowed_root=test_workspace
    )

    # TrustedRunner runs failing command
    runtime_file = os.path.join(test_workspace, "runtime.json")
    trusted_res = TrustedRunner.run_command(
        command="exit 1",
        cwd=test_workspace,
        run_id="run_test_exit",
        output_evidence_file=runtime_file
    )
    assert trusted_res["exit_code"] == 1

    # Agent lies in manifest claiming exit 0
    manifest_file = os.path.join(test_workspace, "manifest.json")
    with open(manifest_file, "w") as f:
        json.dump({
            "artifacts": [],
            "executions": [
                {"command": "exit 1", "exit_code": 0}
            ]
        }, f)

    verifier = OutcomeVerifier(project_root=test_workspace)
    success, msg, _ = verifier.evaluate_task(
        run_id="run_test_exit",
        manifest_path=manifest_file,
        contract_path=contract_file,
        commit_sha=sha,
        trusted_evidence_path=runtime_file
    )

    assert not success
    assert "FORGED EXECUTION EXIT CODE" in msg or "non-zero exit code" in msg


def test_stale_artifact_rejected(test_workspace):
    """Artifact exists, but has an old mtime from before the task started."""
    sha = init_real_git_repo(test_workspace)
    stale_file = os.path.join(test_workspace, "stale_output.json")
    with open(stale_file, "w") as f:
        f.write('{"status": "old"}')

    # Set mtime back by 10 minutes
    old_time = time.time() - 600
    os.utime(stale_file, (old_time, old_time))

    contract_file = os.path.join(test_workspace, "contract.json")
    AcceptanceContract.create(
        run_id="run_test_stale",
        action="Stale Test",
        criteria={},
        output_contract_path=contract_file,
        allowed_root=test_workspace
    )

    manifest_file = os.path.join(test_workspace, "manifest.json")
    with open(manifest_file, "w") as f:
        json.dump({
            "artifacts": [
                {"path": "stale_output.json"}
            ]
        }, f)

    verifier = OutcomeVerifier(project_root=test_workspace)
    success, msg, _ = verifier.evaluate_task(
        run_id="run_test_stale",
        manifest_path=manifest_file,
        contract_path=contract_file,
        commit_sha=sha
    )

    assert not success
    assert "STALE ARTIFACT" in msg


def test_contract_tampering_rejected(test_workspace):
    """Agent attempts to modify the Acceptance Contract to lower criteria."""
    sha = init_real_git_repo(test_workspace)
    contract_file = os.path.join(test_workspace, "contract.json")
    AcceptanceContract.create(
        run_id="run_test_tamper",
        action="Tamper Test",
        criteria={"required_artifacts": [{"path": "important_result.csv"}]},
        output_contract_path=contract_file,
        allowed_root=test_workspace
    )

    # Maliciously alter contract
    with open(contract_file, "r") as f:
        cdata = json.load(f)
    cdata["spec"]["required_artifacts"] = []
    with open(contract_file, "w") as f:
        json.dump(cdata, f)

    manifest_file = os.path.join(test_workspace, "manifest.json")
    with open(manifest_file, "w") as f:
        json.dump({"artifacts": []}, f)

    verifier = OutcomeVerifier(project_root=test_workspace)
    success, msg, _ = verifier.evaluate_task(
        run_id="run_test_tamper",
        manifest_path=manifest_file,
        contract_path=contract_file,
        commit_sha=sha
    )

    assert not success
    assert "CONTRACT TAMPERING DETECTED" in msg


def test_path_traversal_rejected(test_workspace):
    """Manifest attempts path traversal outside project root."""
    sha = init_real_git_repo(test_workspace)
    contract_file = os.path.join(test_workspace, "contract.json")
    AcceptanceContract.create(
        run_id="run_test_traversal",
        action="Path Traversal Test",
        criteria={},
        output_contract_path=contract_file,
        allowed_root=test_workspace
    )

    manifest_file = os.path.join(test_workspace, "manifest.json")
    with open(manifest_file, "w") as f:
        json.dump({
            "artifacts": [
                {"path": "../../etc/passwd"}
            ]
        }, f)

    verifier = OutcomeVerifier(project_root=test_workspace)
    success, msg, _ = verifier.evaluate_task(
        run_id="run_test_traversal",
        manifest_path=manifest_file,
        contract_path=contract_file,
        commit_sha=sha
    )

    assert not success
    assert "escapes allowed project root" in msg


def test_empty_black_media_rejected(test_workspace):
    """Media file contains all null 0x00 bytes (Wayland black video canary)."""
    sha = init_real_git_repo(test_workspace)
    black_video = os.path.join(test_workspace, "record.mp4")
    with open(black_video, "wb") as f:
        f.write(b"\x00" * 65536) # 64KB of zeros

    contract_file = os.path.join(test_workspace, "contract.json")
    AcceptanceContract.create(
        run_id="run_test_media",
        action="Media Test",
        criteria={},
        output_contract_path=contract_file,
        allowed_root=test_workspace
    )

    manifest_file = os.path.join(test_workspace, "manifest.json")
    with open(manifest_file, "w") as f:
        json.dump({
            "artifacts": [
                {"path": "record.mp4", "check_variance": True}
            ]
        }, f)

    verifier = OutcomeVerifier(project_root=test_workspace)
    success, msg, _ = verifier.evaluate_task(
        run_id="run_test_media",
        manifest_path=manifest_file,
        contract_path=contract_file,
        commit_sha=sha
    )

    assert not success
    assert "CONTENT VARIANCE CHECK FAILED" in msg


def test_invalid_sha_format_rejected(test_workspace):
    """dummy_sha or non-40-char strings are rejected as invalid Git SHA format."""
    sha = init_real_git_repo(test_workspace)
    contract_file = os.path.join(test_workspace, "contract.json")
    AcceptanceContract.create(
        run_id="run_test_invalid_sha",
        action="Invalid SHA Test",
        criteria={},
        output_contract_path=contract_file,
        allowed_root=test_workspace
    )

    manifest_file = os.path.join(test_workspace, "manifest.json")
    with open(manifest_file, "w") as f:
        json.dump({"artifacts": []}, f)

    verifier = OutcomeVerifier(project_root=test_workspace)
    success, msg, _ = verifier.evaluate_task(
        run_id="run_test_invalid_sha",
        manifest_path=manifest_file,
        contract_path=contract_file,
        commit_sha="dummy_sha" # NOT 40-char hex
    )

    assert not success
    assert "Invalid Git SHA format" in msg


def test_nonexistent_git_commit_rejected(test_workspace):
    """40-char hex commit that does not exist in local Git object database is rejected."""
    sha = init_real_git_repo(test_workspace)
    contract_file = os.path.join(test_workspace, "contract.json")
    AcceptanceContract.create(
        run_id="run_test_nonexistent_sha",
        action="Nonexistent Commit Test",
        criteria={},
        output_contract_path=contract_file,
        allowed_root=test_workspace
    )

    manifest_file = os.path.join(test_workspace, "manifest.json")
    with open(manifest_file, "w") as f:
        json.dump({"artifacts": []}, f)

    verifier = OutcomeVerifier(project_root=test_workspace)
    ghost_sha = "0000000000000000000000000000000000000000"
    success, msg, _ = verifier.evaluate_task(
        run_id="run_test_nonexistent_sha",
        manifest_path=manifest_file,
        contract_path=contract_file,
        commit_sha=ghost_sha
    )

    assert not success
    assert "Commit 0000000000000000000000000000000000000000 does not exist in local Git object database" in msg


def test_forged_verdict_signature_rejected(test_workspace):
    """Attempting to verify a ticket with a forged signature or wrong commit SHA."""
    sha1 = init_real_git_repo(test_workspace)
    signer = VerdictSigner(secret_key="legitimate_secret_123")
    ticket_file = os.path.join(test_workspace, "ticket.json")

    signer.create_ticket(
        run_id="run_sig_test",
        verified_commit_sha=sha1,
        status="PASSED",
        manifest_hash="hash_abc",
        details={},
        output_path=ticket_file
    )

    # 1. Verification with wrong commit SHA must fail
    dummy_other_sha = "1111111111111111111111111111111111111111"
    ok, err = signer.verify_ticket(ticket_file, expected_commit_sha=dummy_other_sha, repo_root=test_workspace)
    assert not ok
    assert "commit SHA mismatch" in err or "does not exist in Git object database" in err

    # 2. Tampering with signature must fail
    with open(ticket_file, "r") as f:
        tdata = json.load(f)
    tdata["hmac_signature"] = "deadbeef" * 8
    with open(ticket_file, "w") as f:
        json.dump(tdata, f)

    ok, err = signer.verify_ticket(ticket_file, expected_commit_sha=sha1, repo_root=test_workspace)
    assert not ok
    assert "Cryptographic forgery detected" in err


def test_golden_path_signed_and_approved(test_workspace):
    """Legitimate golden path: real git repo, real artifact, real execution, valid HMAC ticket."""
    real_commit_sha = init_real_git_repo(test_workspace)
    run_id = "run_golden_path_001"
    contract_file = os.path.join(test_workspace, "contract.json")
    
    # Pre-Flight: Create Contract
    AcceptanceContract.create(
        run_id=run_id,
        action="Golden Path Action",
        criteria={
            "required_artifacts": [{"path": "result.json"}]
        },
        output_contract_path=contract_file,
        allowed_root=test_workspace
    )

    # Execution: Produce real artifact
    artifact_path = os.path.join(test_workspace, "result.json")
    with open(artifact_path, "w") as f:
        json.dump({"accuracy": 0.98, "status": "ok"}, f)
    actual_sha = compute_file_sha256(artifact_path)

    # Execution: Run trusted test command
    runtime_file = os.path.join(test_workspace, "runtime.json")
    trusted_res = TrustedRunner.run_command(
        command="python3 -c 'print(\"test success\")'",
        cwd=test_workspace,
        run_id=run_id,
        output_evidence_file=runtime_file
    )
    assert trusted_res["exit_code"] == 0

    # Post-Execution: Agent submits truthful manifest
    manifest_file = os.path.join(test_workspace, "manifest.json")
    with open(manifest_file, "w") as f:
        json.dump({
            "artifacts": [
                {"path": "result.json", "sha256": actual_sha, "min_size_bytes": 10}
            ],
            "executions": [
                {"command": "python3 -c 'print(\"test success\")'", "exit_code": 0}
            ]
        }, f)

    # Evaluate Task
    verifier = OutcomeVerifier(project_root=test_workspace, secret_key="test_secret")
    success, msg, ticket = verifier.evaluate_task(
        run_id=run_id,
        manifest_path=manifest_file,
        contract_path=contract_file,
        commit_sha=real_commit_sha,
        trusted_evidence_path=runtime_file
    )

    assert success
    assert "Outcome Verification PASSED" in msg
    assert ticket is not None
    assert ticket["status"] == "PASSED"
    assert ticket["verified_commit_sha"] == real_commit_sha

    # Verify the generated ticket cryptographically with repo_root check
    ticket_file = os.path.join(test_workspace, ".cache", "verdicts", f"verdict_{run_id}.json")
    ok, verify_msg = verifier.signer.verify_ticket(ticket_file, expected_commit_sha=real_commit_sha, repo_root=test_workspace)
    assert ok
    assert "signature valid" in verify_msg
