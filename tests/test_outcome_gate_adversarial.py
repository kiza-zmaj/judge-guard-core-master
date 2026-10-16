#!/usr/bin/env python3
"""
Adversarial Test Suite for JudgeGuard Layer 4 Outcome Verifier v3.0.
Validates all attack vectors and failure modes to guarantee that:
1. Forged exit codes are caught.
2. Empty or missing manifests are rejected.
3. Empty artifact manifests are rejected when contract requires changes.
4. Ghost or missing artifacts fail.
5. SHA-256 mismatches fail.
6. Stale artifacts (older mtime) fail.
7. Contract tampering (spec alteration) is detected.
8. Contract tampering with recomputed spec_hash is detected via HMAC failure.
9. Runtime evidence tampering is detected via HMAC failure.
10. Path traversal attacks fail.
11. Decoded black media (e.g. Wayland black video canary) fails frame decoding / luminance variance.
12. Git blob mismatch (uncommitted or altered disk content) is rejected.
13. Invalid git SHA formats (e.g. dummy_sha) are rejected.
14. Non-existent git commit SHAs cannot receive or pass a verdict.
15. Forged verdict signatures are rejected.
16. Legitimate golden path produces valid signed verdict ticket bound to real git commit.
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
    MediaValidator,
    canonical_json,
    compute_string_sha256,
    compute_file_sha256,
    PathSecurityError
)


def init_real_git_repo(workspace: str) -> str:
    """Initializes a real git repo and returns full 40-char HEAD commit SHA."""
    subprocess.run(["git", "init", "-b", "master"], cwd=workspace, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=workspace, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=workspace, check=True, capture_output=True)
    gitignore = os.path.join(workspace, ".gitignore")
    with open(gitignore, "w") as f:
        f.write(".cache\n.venv\n")
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
    """Manifest is empty {} or missing required envelope fields."""
    sha = init_real_git_repo(test_workspace)
    contract_file = os.path.join(test_workspace, ".cache", "contract.json")
    os.makedirs(os.path.dirname(contract_file), exist_ok=True)
    AcceptanceContract.create(
        run_id="run_test_empty",
        action="Test Action",
        criteria={},
        output_contract_path=contract_file,
        allowed_root=test_workspace
    )

    manifest_file = os.path.join(test_workspace, ".cache", "manifest.json")
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
    assert "EMPTY OR MALFORMED MANIFEST" in msg
    assert ticket is None


def test_empty_artifacts_rejected_when_required(test_workspace):
    """Manifest has {'artifacts': []} when contract requires artifacts."""
    sha = init_real_git_repo(test_workspace)
    contract_file = os.path.join(test_workspace, ".cache", "contract.json")
    os.makedirs(os.path.dirname(contract_file), exist_ok=True)
    AcceptanceContract.create(
        run_id="run_test_empty_arts",
        action="Empty Artifacts Test",
        criteria={"required_artifacts": ["output.txt"]},
        output_contract_path=contract_file,
        allowed_root=test_workspace
    )

    manifest_file = os.path.join(test_workspace, ".cache", "manifest.json")
    with open(manifest_file, "w") as f:
        json.dump({
            "run_id": "run_test_empty_arts",
            "artifacts": []
        }, f)

    verifier = OutcomeVerifier(project_root=test_workspace)
    success, msg, _ = verifier.evaluate_task(
        run_id="run_test_empty_arts",
        manifest_path=manifest_file,
        contract_path=contract_file,
        commit_sha=sha
    )

    assert not success
    assert "EMPTY ARTIFACT SET REJECTED" in msg


def test_ghost_or_missing_artifact_rejected(test_workspace):
    """Manifest claims an artifact exists, but file is absent on disk."""
    sha = init_real_git_repo(test_workspace)
    contract_file = os.path.join(test_workspace, ".cache", "contract.json")
    os.makedirs(os.path.dirname(contract_file), exist_ok=True)
    AcceptanceContract.create(
        run_id="run_test_ghost",
        action="Ghost Test",
        criteria={},
        output_contract_path=contract_file,
        allowed_root=test_workspace
    )

    manifest_file = os.path.join(test_workspace, ".cache", "manifest.json")
    with open(manifest_file, "w") as f:
        json.dump({
            "run_id": "run_test_ghost",
            "artifacts": [
                {"path": "non_existent_file.py", "sha256": "a" * 64, "min_size_bytes": 10}
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

    contract_file = os.path.join(test_workspace, ".cache", "contract.json")
    os.makedirs(os.path.dirname(contract_file), exist_ok=True)
    AcceptanceContract.create(
        run_id="run_test_hash",
        action="Hash Test",
        criteria={},
        output_contract_path=contract_file,
        allowed_root=test_workspace
    )

    manifest_file = os.path.join(test_workspace, ".cache", "manifest.json")
    with open(manifest_file, "w") as f:
        json.dump({
            "run_id": "run_test_hash",
            "artifacts": [
                {"path": "output.txt", "sha256": "0" * 64}
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
    contract_file = os.path.join(test_workspace, ".cache", "contract.json")
    os.makedirs(os.path.dirname(contract_file), exist_ok=True)
    AcceptanceContract.create(
        run_id="run_test_exit",
        action="Exit Code Test",
        criteria={},
        output_contract_path=contract_file,
        allowed_root=test_workspace,
        secret_key="test_secret_123"
    )

    # TrustedRunner runs failing command
    runtime_file = os.path.join(test_workspace, ".cache", "runtime.json")
    trusted_res = TrustedRunner.run_command(
        command="exit 1",
        cwd=test_workspace,
        run_id="run_test_exit",
        output_evidence_file=runtime_file,
        secret_key="test_secret_123"
    )
    assert trusted_res["exit_code"] == 1

    # Agent lies in manifest claiming exit 0
    manifest_file = os.path.join(test_workspace, ".cache", "manifest.json")
    with open(manifest_file, "w") as f:
        json.dump({
            "run_id": "run_test_exit",
            "artifacts": [],
            "executions": [
                {"command": "exit 1", "exit_code": 0}
            ]
        }, f)

    verifier = OutcomeVerifier(project_root=test_workspace, secret_key="test_secret_123")
    success, msg, _ = verifier.evaluate_task(
        run_id="run_test_exit",
        manifest_path=manifest_file,
        contract_path=contract_file,
        commit_sha=sha,
        trusted_evidence_path=runtime_file
    )

    assert not success
    assert "FORGED EXECUTION EXIT CODE" in msg


def test_stale_artifact_rejected(test_workspace):
    """Artifact exists, but has an old mtime from before the task started."""
    sha = init_real_git_repo(test_workspace)
    stale_file = os.path.join(test_workspace, "stale_output.json")
    with open(stale_file, "w") as f:
        f.write('{"status": "old"}')

    # Set mtime back by 10 minutes
    old_time = time.time() - 600
    os.utime(stale_file, (old_time, old_time))
    stale_sha = compute_file_sha256(stale_file)

    contract_file = os.path.join(test_workspace, ".cache", "contract.json")
    os.makedirs(os.path.dirname(contract_file), exist_ok=True)
    AcceptanceContract.create(
        run_id="run_test_stale",
        action="Stale Test",
        criteria={},
        output_contract_path=contract_file,
        allowed_root=test_workspace
    )

    manifest_file = os.path.join(test_workspace, ".cache", "manifest.json")
    with open(manifest_file, "w") as f:
        json.dump({
            "run_id": "run_test_stale",
            "artifacts": [
                {"path": "stale_output.json", "sha256": stale_sha}
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
    assert "STALE ARTIFACT DETECTED" in msg


def test_contract_tampering_spec_modified_rejected(test_workspace):
    """Agent attempts to modify the spec inside Acceptance Contract without updating spec_hash."""
    sha = init_real_git_repo(test_workspace)
    contract_file = os.path.join(test_workspace, ".cache", "contract.json")
    os.makedirs(os.path.dirname(contract_file), exist_ok=True)
    AcceptanceContract.create(
        run_id="run_test_tamper1",
        action="Tamper Test 1",
        criteria={"required_artifacts": ["important_result.csv"]},
        output_contract_path=contract_file,
        allowed_root=test_workspace
    )

    # Maliciously alter contract spec without updating spec_hash
    with open(contract_file, "r") as f:
        cdata = json.load(f)
    cdata["spec"]["required_artifacts"] = []
    with open(contract_file, "w") as f:
        json.dump(cdata, f)

    manifest_file = os.path.join(test_workspace, ".cache", "manifest.json")
    with open(manifest_file, "w") as f:
        json.dump({"run_id": "run_test_tamper1", "artifacts": []}, f)

    verifier = OutcomeVerifier(project_root=test_workspace)
    success, msg, _ = verifier.evaluate_task(
        run_id="run_test_tamper1",
        manifest_path=manifest_file,
        contract_path=contract_file,
        commit_sha=sha
    )

    assert not success
    assert "CONTRACT TAMPERING DETECTED: Spec content does not match spec_hash!" in msg


def test_contract_tampering_with_recomputed_spec_hash_rejected(test_workspace):
    """Agent alters spec AND recomputes spec_hash, but cannot forge contract_signature HMAC."""
    sha = init_real_git_repo(test_workspace)
    contract_file = os.path.join(test_workspace, ".cache", "contract.json")
    os.makedirs(os.path.dirname(contract_file), exist_ok=True)
    AcceptanceContract.create(
        run_id="run_test_tamper2",
        action="Tamper Test 2",
        criteria={"required_artifacts": ["critical.dat"]},
        output_contract_path=contract_file,
        allowed_root=test_workspace,
        secret_key="secret_signing_key_999"
    )

    with open(contract_file, "r") as f:
        cdata = json.load(f)
    cdata["spec"]["required_artifacts"] = []
    cdata["spec_hash"] = compute_string_sha256(canonical_json(cdata["spec"]))
    with open(contract_file, "w") as f:
        json.dump(cdata, f)

    manifest_file = os.path.join(test_workspace, ".cache", "manifest.json")
    with open(manifest_file, "w") as f:
        json.dump({"run_id": "run_test_tamper2", "artifacts": []}, f)

    verifier = OutcomeVerifier(project_root=test_workspace, secret_key="secret_signing_key_999")
    success, msg, _ = verifier.evaluate_task(
        run_id="run_test_tamper2",
        manifest_path=manifest_file,
        contract_path=contract_file,
        commit_sha=sha
    )

    assert not success
    assert "CONTRACT TAMPERING DETECTED: Cryptographic signature mismatch!" in msg


def test_runtime_evidence_tampering_rejected(test_workspace):
    """Attacker modifies TrustedRunner record file (alters exit_code), HMAC verification fails."""
    sha = init_real_git_repo(test_workspace)
    run_id = "run_test_ev_tamper"
    contract_file = os.path.join(test_workspace, ".cache", "contract.json")
    os.makedirs(os.path.dirname(contract_file), exist_ok=True)
    AcceptanceContract.create(
        run_id=run_id,
        action="Evidence Tamper Test",
        criteria={},
        output_contract_path=contract_file,
        allowed_root=test_workspace,
        secret_key="secret_xyz"
    )

    runtime_file = os.path.join(test_workspace, ".cache", "runtime.json")
    TrustedRunner.run_command(
        command="exit 1",
        cwd=test_workspace,
        run_id=run_id,
        output_evidence_file=runtime_file,
        secret_key="secret_xyz"
    )

    # Attacker modifies the recorded exit code in runtime.json from 1 to 0
    with open(runtime_file, "r") as f:
        rec = json.load(f)
    rec["exit_code"] = 0
    with open(runtime_file, "w") as f:
        json.dump(rec, f)

    manifest_file = os.path.join(test_workspace, ".cache", "manifest.json")
    with open(manifest_file, "w") as f:
        json.dump({
            "run_id": run_id,
            "artifacts": [],
            "executions": [{"command": "exit 1", "exit_code": 0}]
        }, f)

    verifier = OutcomeVerifier(project_root=test_workspace, secret_key="secret_xyz")
    success, msg, _ = verifier.evaluate_task(
        run_id=run_id,
        manifest_path=manifest_file,
        contract_path=contract_file,
        commit_sha=sha,
        trusted_evidence_path=runtime_file
    )

    assert not success
    assert "FORGED RUNTIME EVIDENCE" in msg


def test_path_traversal_rejected(test_workspace):
    """Manifest attempts path traversal outside project root."""
    sha = init_real_git_repo(test_workspace)
    contract_file = os.path.join(test_workspace, ".cache", "contract.json")
    os.makedirs(os.path.dirname(contract_file), exist_ok=True)
    AcceptanceContract.create(
        run_id="run_test_traversal",
        action="Path Traversal Test",
        criteria={},
        output_contract_path=contract_file,
        allowed_root=test_workspace
    )

    manifest_file = os.path.join(test_workspace, ".cache", "manifest.json")
    with open(manifest_file, "w") as f:
        json.dump({
            "run_id": "run_test_traversal",
            "artifacts": [
                {"path": "../../etc/passwd", "sha256": "0" * 64}
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
    assert "Path traversal detected" in msg or "SECURITY VIOLATION" in msg


def test_valid_mp4_black_video_rejected(test_workspace):
    """Real encoded MP4 containing only solid black frames (Wayland black video canary)."""
    black_mp4 = os.path.join(test_workspace, "black_video.mp4")
    cmd = [
        "ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=black:s=160x120:d=1",
        "-pix_fmt", "yuv420p", black_mp4
    ]
    res = subprocess.run(cmd, capture_output=True)
    assert res.returncode == 0
    assert os.path.exists(black_mp4)

    v_ok, v_msg = MediaValidator.validate_video(black_mp4)
    assert not v_ok
    assert "black" in v_msg.lower()


def test_git_blob_mismatch_rejected(test_workspace):
    """File on disk was modified after git commit, failing byte-for-byte Git blob verification."""
    init_real_git_repo(test_workspace)
    artifact_path = os.path.join(test_workspace, "committed_file.txt")
    with open(artifact_path, "w") as f:
        f.write("original committed content")
    subprocess.run(["git", "add", "committed_file.txt"], cwd=test_workspace, check=True)
    subprocess.run(["git", "commit", "-m", "add committed file"], cwd=test_workspace, check=True)
    real_commit_sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=test_workspace, capture_output=True, text=True, check=True).stdout.strip()

    # Modify file on disk AFTER commit
    with open(artifact_path, "w") as f:
        f.write("tampered uncommitted content")
    tampered_sha = compute_file_sha256(artifact_path)

    run_id = "run_blob_test"
    contract_file = os.path.join(test_workspace, ".cache", "contract.json")
    os.makedirs(os.path.dirname(contract_file), exist_ok=True)
    AcceptanceContract.create(
        run_id=run_id,
        action="Blob Mismatch Test",
        criteria={"required_artifacts": ["committed_file.txt"]},
        output_contract_path=contract_file,
        allowed_root=test_workspace
    )

    manifest_file = os.path.join(test_workspace, ".cache", "manifest.json")
    with open(manifest_file, "w") as f:
        json.dump({
            "run_id": run_id,
            "artifacts": [{"path": "committed_file.txt", "sha256": tampered_sha}]
        }, f)

    verifier = OutcomeVerifier(project_root=test_workspace)
    success, msg, _ = verifier.evaluate_task(
        run_id=run_id,
        manifest_path=manifest_file,
        contract_path=contract_file,
        commit_sha=real_commit_sha
    )

    assert not success
    assert "GIT BLOB INTEGRITY ERROR" in msg


def test_invalid_sha_format_rejected(test_workspace):
    """dummy_sha or non-40-char strings are rejected as invalid Git SHA format."""
    sha = init_real_git_repo(test_workspace)
    contract_file = os.path.join(test_workspace, ".cache", "contract.json")
    os.makedirs(os.path.dirname(contract_file), exist_ok=True)
    AcceptanceContract.create(
        run_id="run_test_invalid_sha",
        action="Invalid SHA Test",
        criteria={},
        output_contract_path=contract_file,
        allowed_root=test_workspace
    )

    manifest_file = os.path.join(test_workspace, ".cache", "manifest.json")
    with open(manifest_file, "w") as f:
        json.dump({"run_id": "run_test_invalid_sha", "artifacts": []}, f)

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
    contract_file = os.path.join(test_workspace, ".cache", "contract.json")
    os.makedirs(os.path.dirname(contract_file), exist_ok=True)
    AcceptanceContract.create(
        run_id="run_test_nonexistent_sha",
        action="Nonexistent Commit Test",
        criteria={},
        output_contract_path=contract_file,
        allowed_root=test_workspace
    )

    manifest_file = os.path.join(test_workspace, ".cache", "manifest.json")
    with open(manifest_file, "w") as f:
        json.dump({"run_id": "run_test_nonexistent_sha", "artifacts": []}, f)

    verifier = OutcomeVerifier(project_root=test_workspace)
    ghost_sha = "0000000000000000000000000000000000000000"
    success, msg, _ = verifier.evaluate_task(
        run_id="run_test_nonexistent_sha",
        manifest_path=manifest_file,
        contract_path=contract_file,
        commit_sha=ghost_sha
    )

    assert not success
    assert "does not exist in local Git object database" in msg


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
    tdata["signature"] = "deadbeef" * 8
    with open(ticket_file, "w") as f:
        json.dump(tdata, f)

    ok, err = signer.verify_ticket(ticket_file, expected_commit_sha=sha1, repo_root=test_workspace)
    assert not ok
    assert "Cryptographic forgery detected" in err


def test_golden_path_signed_and_approved(test_workspace):
    """Legitimate golden path: real git repo, real artifact, real execution, valid HMAC ticket."""
    init_real_git_repo(test_workspace)
    run_id = "run_golden_path_001"
    cache_dir = os.path.join(test_workspace, ".cache")
    os.makedirs(cache_dir, exist_ok=True)
    contract_file = os.path.join(cache_dir, "contract.json")

    # Pre-Flight: Create Contract
    AcceptanceContract.create(
        run_id=run_id,
        action="Golden Path Action",
        criteria={
            "required_artifacts": ["result.json"],
            "required_executions": [{"command": "python3 -c 'print(\"test success\")'", "exit_code": 0}],
            "require_clean_git": True
        },
        output_contract_path=contract_file,
        allowed_root=test_workspace,
        secret_key="test_secret"
    )

    # Execution: Produce real artifact and commit it to git
    artifact_path = os.path.join(test_workspace, "result.json")
    with open(artifact_path, "w") as f:
        json.dump({"accuracy": 0.98, "status": "ok"}, f)
    actual_sha = compute_file_sha256(artifact_path)

    subprocess.run(["git", "add", "result.json"], cwd=test_workspace, check=True)
    subprocess.run(["git", "commit", "-m", "add verified artifact"], cwd=test_workspace, check=True)
    real_commit_sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=test_workspace, capture_output=True, text=True, check=True).stdout.strip()

    # Execution: Run trusted test command
    runtime_file = os.path.join(cache_dir, "runtime.json")
    trusted_res = TrustedRunner.run_command(
        command="python3 -c 'print(\"test success\")'",
        cwd=test_workspace,
        run_id=run_id,
        output_evidence_file=runtime_file,
        secret_key="test_secret"
    )
    assert trusted_res["exit_code"] == 0

    # Post-Execution: Agent submits truthful manifest
    manifest_file = os.path.join(cache_dir, "manifest.json")
    with open(manifest_file, "w") as f:
        json.dump({
            "run_id": run_id,
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
