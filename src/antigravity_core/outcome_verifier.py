#!/usr/bin/env python3
"""
Outcome & Evidence Verifier v3.0 - The Layer 4 Reality-Grounding Engine.
Enforces deterministic verification of real-world artifacts and runtime evidence
before any task can be marked COMPLETED or merged into main.

Key Guarantees:
1. Authoritative Key Resolution: No hardcoded HMAC secret; requires trusted key from env or secure path.
2. Cryptographic Contract Protection: HMAC signing of Acceptance Contract spec_hash prevents forgery.
3. Cryptographic Runtime Evidence: HMAC signing of TrustedRunner records prevents tampering.
4. Git Object Database & Blob Verification: Proves the physical artifact on disk matches the exact
   byte-level Git blob in the commit being merged.
5. True Video Frame Decoding: Decodes frames with ffmpeg, checks luminance variance and blackdetect filter
   (eliminates Wayland black-video canary failure).
6. Strict Empty Artifact Rejection: Odbacuje {"artifacts": []} when contract demands changes.
7. Strict Run ID Binding: Cross-verifies run_id across contract, manifest, runtime record, and verdict.
8. Clean Git Enforcement: Verifies working tree is clean at finalization.
"""

import os
import sys
import time
import json
import hmac
import hashlib
import subprocess
import logging
import re
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger(__name__)


def resolve_trusted_secret(explicit_secret: Optional[str] = None) -> str:
    """
    Resolves the authoritative cryptographic secret key for JudgeGuard.
    Order of precedence:
    1. Explicit secret argument (passed by trusted controller/test fixture).
    2. JUDGEGUARD_VERDICT_SECRET environment variable.
    3. Secure file outside workspace: ~/.config/judgeguard/trusted_secret_key (mode 0600).
    
    If none is available, raises ValueError (Fail-Closed).
    NEVER falls back to a public or hardcoded secret string.
    """
    if explicit_secret and explicit_secret.strip():
        return explicit_secret.strip()

    env_secret = os.getenv("JUDGEGUARD_VERDICT_SECRET")
    if env_secret and env_secret.strip():
        return env_secret.strip()

    config_path = os.path.expanduser("~/.config/judgeguard/trusted_secret_key")
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                key = f.read().strip()
                if key:
                    return key
        except Exception:
            pass

    raise ValueError(
        "AUTHORITATIVE SECRET MISSING: JUDGEGUARD_VERDICT_SECRET is not set, "
        "and no secure key file found at ~/.config/judgeguard/trusted_secret_key. "
        "Fail-closed: Refusing to sign or verify verdicts without an authoritative key."
    )


class PathSecurityError(ValueError):
    """Raised when a path escapes allowed root directory."""
    pass


class ContractTamperError(ValueError):
    """Raised when an acceptance contract was altered after creation."""
    pass


def compute_file_sha256(filepath: str) -> str:
    """Computes SHA-256 hash of a file directly from disk."""
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def compute_string_sha256(content: str) -> str:
    """Computes SHA-256 hash of a UTF-8 string."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def canonical_json(data: Any) -> str:
    """Serializes data to canonical deterministic JSON string."""
    return json.dumps(data, sort_keys=True, separators=(',', ':'))


def sanitize_and_resolve_path(target_path: str, root_dir: str) -> str:
    """
    Resolves path against root_dir and verifies it does not escape root_dir.
    Prevents path traversal attacks (../, absolute symlinks out of tree).
    """
    resolved_root = os.path.realpath(root_dir)
    if not os.path.isabs(target_path):
        resolved_target = os.path.realpath(os.path.join(resolved_root, target_path))
    else:
        resolved_target = os.path.realpath(target_path)

    # Must be within resolved_root
    if not (resolved_target == resolved_root or resolved_target.startswith(resolved_root + os.sep)):
        raise PathSecurityError(f"Path escapes allowed project root: {target_path} -> {resolved_target}")
    return resolved_target


class VerdictSigner:
    """
    Handles cryptographic HMAC-SHA256 operations for:
    - Verdict tickets
    - Acceptance Contract specifications
    - Trusted runtime evidence records
    """

    def __init__(self, secret_key: Optional[str] = None):
        self.secret_key = resolve_trusted_secret(secret_key)

    def sign(self, run_id: str, commit_sha: str, status: str, timestamp: str, manifest_hash: str) -> str:
        payload = f"verdict:{run_id}:{commit_sha}:{status}:{timestamp}:{manifest_hash}"
        return hmac.new(self.secret_key.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()

    def sign_contract(self, run_id: str, spec_hash: str) -> str:
        payload = f"contract:{run_id}:{spec_hash}"
        return hmac.new(self.secret_key.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()

    def verify_contract_signature(self, run_id: str, spec_hash: str, signature: str) -> bool:
        expected = self.sign_contract(run_id, spec_hash)
        return hmac.compare_digest(signature, expected)

    def sign_runtime_evidence(self, run_id: str, command: str, exit_code: int, stdout_hash: str, stderr_hash: str) -> str:
        payload = f"evidence:{run_id}:{command}:{exit_code}:{stdout_hash}:{stderr_hash}"
        return hmac.new(self.secret_key.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()

    def verify_runtime_evidence(self, record: Dict[str, Any]) -> Tuple[bool, str]:
        required_fields = ["run_id", "command", "exit_code", "stdout_hash", "stderr_hash", "evidence_signature"]
        for f in required_fields:
            if f not in record:
                return False, f"Missing required evidence field: {f}"
        sig = record["evidence_signature"]
        expected = self.sign_runtime_evidence(
            record["run_id"],
            record["command"],
            record["exit_code"],
            record["stdout_hash"],
            record["stderr_hash"]
        )
        if not hmac.compare_digest(sig, expected):
            return False, "Runtime evidence signature mismatch: tampering detected."
        return True, "Evidence signature valid"

    def create_ticket(
        self,
        run_id: str,
        verified_commit_sha: str,
        status: str,
        manifest_hash: str,
        details: Dict[str, Any],
        output_path: Optional[str] = None
    ) -> Dict[str, Any]:
        timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        sig = self.sign(run_id, verified_commit_sha, status, timestamp, manifest_hash)
        ticket = {
            "ticket_type": "JUDGEGUARD_VERDICT_TICKET",
            "version": "3.0",
            "run_id": run_id,
            "verified_commit_sha": verified_commit_sha,
            "status": status,
            "timestamp": timestamp,
            "manifest_hash": manifest_hash,
            "details": details,
            "signature": sig
        }
        if output_path:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(ticket, f, indent=2)
        return ticket

    def verify_ticket(self, ticket_path: str, expected_commit_sha: str, repo_root: Optional[str] = None) -> Tuple[bool, str]:
        if not os.path.exists(ticket_path):
            return False, f"Verdict ticket missing: {ticket_path}"
        try:
            with open(ticket_path, "r", encoding="utf-8") as f:
                ticket = json.load(f)
        except Exception as e:
            return False, f"Invalid verdict ticket JSON: {e}"

        run_id = ticket.get("run_id")
        commit_sha = ticket.get("verified_commit_sha")
        status = ticket.get("status")
        timestamp = ticket.get("timestamp")
        manifest_hash = ticket.get("manifest_hash")
        sig = ticket.get("signature")

        if not all([run_id, commit_sha, status, timestamp, manifest_hash, sig]):
            return False, "Incomplete verdict ticket structure"

        if status != "PASSED":
            return False, f"Ticket verdict is not PASSED (status: {status})"

        if not re.match(r"^[0-9a-fA-F]{40}$", expected_commit_sha):
            return False, f"Invalid expected commit SHA format: '{expected_commit_sha}' (must be 40-char hex)"

        if commit_sha.lower() != expected_commit_sha.lower():
            return False, f"Ticket commit SHA mismatch: expected {expected_commit_sha}, ticket has {commit_sha}"

        # Verify commit exists in git object database if repo_root provided
        if repo_root:
            git_check = subprocess.run(
                ["git", "cat-file", "-e", f"{expected_commit_sha}^{{commit}}"],
                cwd=repo_root,
                capture_output=True,
                text=True
            )
            if git_check.returncode != 0:
                return False, f"Commit {expected_commit_sha} does not exist in Git object database"

        expected_sig = self.sign(run_id, commit_sha, status, timestamp, manifest_hash)
        if not hmac.compare_digest(sig, expected_sig):
            return False, "INVALID VERDICT SIGNATURE: Cryptographic forgery detected"

        return True, "Verdict signature valid and verified."


class AcceptanceContract:
    """
    Pre-Flight Acceptance Contract defining immutable success criteria.
    Protected with HMAC cryptographic signature to prevent tampering.
    """

    @classmethod
    def create(
        cls,
        run_id: str,
        action: str,
        criteria: Dict[str, Any],
        output_contract_path: str,
        allowed_root: str,
        secret_key: Optional[str] = None
    ) -> Dict[str, Any]:
        signer = VerdictSigner(secret_key)
        created_at = time.time()
        created_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(created_at))

        # Build normalized criteria specification
        spec = {
            "run_id": run_id,
            "action": action,
            "allowed_root": os.path.realpath(allowed_root),
            "created_at": created_at,
            "created_iso": created_iso,
            "required_artifacts": criteria.get("required_artifacts", []),
            "required_executions": criteria.get("required_executions", []),
            "content_assertions": criteria.get("content_assertions", {}),
            "min_files_changed": criteria.get("min_files_changed", 0),
            "require_clean_git": criteria.get("require_clean_git", True),
            "custom_criteria": criteria.get("custom_criteria", {})
        }

        spec_json = canonical_json(spec)
        spec_hash = compute_string_sha256(spec_json)
        contract_sig = signer.sign_contract(run_id, spec_hash)

        contract_document = {
            "contract_version": "3.0",
            "run_id": run_id,
            "spec_hash": spec_hash,
            "contract_signature": contract_sig,
            "spec": spec
        }

        os.makedirs(os.path.dirname(output_contract_path), exist_ok=True)
        with open(output_contract_path, "w", encoding="utf-8") as f:
            json.dump(contract_document, f, indent=2)

        return contract_document

    @classmethod
    def verify_integrity(
        cls,
        contract_path: str,
        expected_run_id: Optional[str] = None,
        secret_key: Optional[str] = None
    ) -> Tuple[bool, Dict[str, Any], str]:
        if not os.path.exists(contract_path):
            raise ContractTamperError(f"Acceptance Contract file missing: {contract_path}")

        try:
            with open(contract_path, "r", encoding="utf-8") as f:
                doc = json.load(f)
        except Exception as e:
            raise ContractTamperError(f"Acceptance Contract corrupted: {e}")

        run_id = doc.get("run_id")
        spec_hash = doc.get("spec_hash")
        sig = doc.get("contract_signature")
        spec = doc.get("spec")

        if not all([run_id, spec_hash, sig, spec]):
            raise ContractTamperError("Acceptance Contract malformed (missing mandatory envelope fields).")

        if expected_run_id and run_id != expected_run_id:
            raise ContractTamperError(f"Acceptance Contract run_id mismatch: expected {expected_run_id}, got {run_id}")

        # 1. Cryptographic HMAC check
        signer = VerdictSigner(secret_key)
        if not signer.verify_contract_signature(run_id, spec_hash, sig):
            raise ContractTamperError("CONTRACT TAMPERING DETECTED: Cryptographic signature mismatch!")

        # 2. Hash check against spec contents
        recomputed_hash = compute_string_sha256(canonical_json(spec))
        if recomputed_hash != spec_hash:
            raise ContractTamperError("CONTRACT TAMPERING DETECTED: Spec content does not match spec_hash!")

        return True, spec, "Contract integrity verified."


class TrustedRunner:
    """
    Executes commands and independently records runtime facts (exit code, duration, stdout/stderr hash).
    Signs the runtime evidence record using HMAC-SHA256 to ensure authenticity.
    """

    @staticmethod
    def run_command(
        command: str,
        cwd: str,
        run_id: str,
        output_evidence_file: Optional[str] = None,
        secret_key: Optional[str] = None
    ) -> Dict[str, Any]:
        signer = VerdictSigner(secret_key)
        start_time = time.time()
        start_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(start_time))

        logger.info(f"TrustedRunner [{run_id}] executing: {command} in {cwd}")
        proc = subprocess.run(
            command,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True
        )

        end_time = time.time()
        end_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(end_time))
        duration_ms = round((end_time - start_time) * 1000, 2)

        stdout_hash = compute_string_sha256(proc.stdout)
        stderr_hash = compute_string_sha256(proc.stderr)

        sig = signer.sign_runtime_evidence(run_id, command, proc.returncode, stdout_hash, stderr_hash)

        record = {
            "run_id": run_id,
            "command": command,
            "cwd": cwd,
            "start_time": start_time,
            "start_iso": start_iso,
            "end_time": end_time,
            "end_iso": end_iso,
            "duration_ms": duration_ms,
            "exit_code": proc.returncode,
            "stdout_hash": stdout_hash,
            "stderr_hash": stderr_hash,
            "stdout_snippet": proc.stdout[:1000],
            "stderr_snippet": proc.stderr[:1000],
            "evidence_signature": sig
        }

        if output_evidence_file:
            os.makedirs(os.path.dirname(output_evidence_file), exist_ok=True)
            with open(output_evidence_file, "w", encoding="utf-8") as f:
                json.dump(record, f, indent=2)

        return record


class MediaValidator:
    """
    Validates media artifacts by decoding actual video frames, checking luminance variance,
    and verifying expected visual content (prevents black video canary errors).
    """

    @staticmethod
    def validate_video(filepath: str, min_duration: float = 0.05, min_luminance_variance: float = 0.5) -> Tuple[bool, str]:
        if not os.path.exists(filepath):
            return False, f"Video file not found: {filepath}"

        # 1. Probe video stream
        probe_cmd = [
            "ffprobe", "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height,duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            filepath
        ]
        probe_res = subprocess.run(probe_cmd, capture_output=True, text=True)
        if probe_res.returncode != 0:
            return False, f"Video decoding failed: ffprobe error: {probe_res.stderr.strip()[:200]}"

        probe_lines = [l.strip() for l in probe_res.stdout.splitlines() if l.strip()]
        if len(probe_lines) < 2:
            return False, "Video contains no valid video stream"

        # 2. Run blackdetect filter
        black_cmd = [
            "ffmpeg", "-i", filepath,
            "-vf", "blackdetect=d=0.05:pix_th=0.10",
            "-f", "null", "-"
        ]
        black_res = subprocess.run(black_cmd, capture_output=True, text=True)
        black_durations = []
        for line in black_res.stderr.splitlines():
            if "blackdetect" in line and "black_duration:" in line:
                try:
                    parts = line.split("black_duration:")
                    dur = float(parts[1].split()[0])
                    black_durations.append(dur)
                except Exception:
                    pass

        # 3. Decode sample frames to raw grayscale pixels and compute luminance variance
        decode_cmd = [
            "ffmpeg", "-i", filepath,
            "-vframes", "10",
            "-f", "rawvideo",
            "-pix_fmt", "gray",
            "-"
        ]
        decode_res = subprocess.run(decode_cmd, capture_output=True)
        raw_pixels = decode_res.stdout
        if not raw_pixels:
            return False, "Failed to decode any raw video frames from file"

        pixel_count = len(raw_pixels)
        mean_lum = sum(raw_pixels) / pixel_count
        variance = sum((b - mean_lum) ** 2 for b in raw_pixels) / pixel_count

        if mean_lum < 5.0 and variance < min_luminance_variance:
            return False, f"Decoded video is completely black/empty: mean luminance {mean_lum:.2f}, variance {variance:.4f}"

        if black_durations:
            total_black = sum(black_durations)
            try:
                total_dur = float(probe_lines[-1]) if probe_lines else 1.0
                if total_black >= (total_dur * 0.90):
                    return False, f"Decoded video is {total_black:.2f}s black out of {total_dur:.2f}s total (>=90% black)"
            except Exception:
                pass

        return True, f"Visual content valid: mean luminance {mean_lum:.2f}, variance {variance:.2f}"


class EvidenceValidator:
    """
    Performs comprehensive deterministic validation of the evidence manifest against:
    1. Acceptance Contract.
    2. Trusted Runtime Records.
    3. Git Object Database & Blob Truth.
    4. Decoded Media Variance.
    """

    @classmethod
    def validate(
        cls,
        manifest_path: str,
        contract_spec: Dict[str, Any],
        expected_run_id: str,
        trusted_runtime_record: Optional[Dict[str, Any]] = None,
        project_root: Optional[str] = None,
        commit_sha: Optional[str] = None,
        signer: Optional[VerdictSigner] = None
    ) -> Tuple[bool, List[str]]:
        errors = []

        if not os.path.exists(manifest_path):
            return False, [f"Manifest file does not exist: {manifest_path}"]

        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)
        except Exception as e:
            return False, [f"Manifest contains invalid JSON: {e}"]

        if not isinstance(manifest, dict) or len(manifest) == 0:
            return False, ["EMPTY OR MALFORMED MANIFEST: Manifest must be a non-empty JSON object."]

        # 1. Run ID Cross-Verification
        manifest_run_id = manifest.get("run_id")
        contract_run_id = contract_spec.get("run_id")
        if manifest_run_id != expected_run_id or contract_run_id != expected_run_id:
            errors.append(f"RUN_ID MISMATCH: Expected {expected_run_id}, manifest has '{manifest_run_id}', contract has '{contract_run_id}'")

        # 2. Trusted Runtime Verification
        if trusted_runtime_record:
            if trusted_runtime_record.get("run_id") != expected_run_id:
                errors.append(f"RUN_ID MISMATCH: Trusted runtime record run_id '{trusted_runtime_record.get('run_id')}' != '{expected_run_id}'")

            if signer:
                sig_ok, sig_err = signer.verify_runtime_evidence(trusted_runtime_record)
                if not sig_ok:
                    errors.append(f"FORGED RUNTIME EVIDENCE: {sig_err}")

            trusted_cmd = trusted_runtime_record.get("command")
            trusted_exit = trusted_runtime_record.get("exit_code")

            executions = manifest.get("executions", [])
            matching_claims = [e for e in executions if e.get("command") == trusted_cmd]
            if not matching_claims:
                errors.append(f"MISSING EXECUTION CLAIM IN MANIFEST: No execution claim for command '{trusted_cmd}'")
            else:
                claimed_exit = matching_claims[0].get("exit_code")
                if claimed_exit != trusted_exit:
                    errors.append(
                        f"FORGED EXECUTION EXIT CODE: Agent claimed exit {claimed_exit}, but TrustedRunner recorded {trusted_exit}"
                    )

            if trusted_exit != 0:
                errors.append(f"Trusted execution failed with non-zero exit code: {trusted_exit}")

        # 3. Required Executions Check
        for req_exec in contract_spec.get("required_executions", []):
            req_cmd = req_exec if isinstance(req_exec, str) else req_exec.get("command")
            expected_exit = 0 if isinstance(req_exec, str) else req_exec.get("exit_code", 0)
            executions = manifest.get("executions", [])
            matches = [e for e in executions if e.get("command") == req_cmd and e.get("exit_code") == expected_exit]
            if not matches:
                errors.append(f"CONTRACT VIOLATION: Required execution '{req_cmd}' (exit {expected_exit}) not satisfied in manifest.")

        # 4. Artifact Validation & Empty Set Rejection
        artifacts = manifest.get("artifacts")
        if artifacts is None or not isinstance(artifacts, list):
            errors.append("MALFORMED MANIFEST: 'artifacts' must be a list.")
            artifacts = []

        required_artifacts = contract_spec.get("required_artifacts", [])
        min_files_changed = contract_spec.get("min_files_changed", 0)

        if len(artifacts) == 0 and (required_artifacts or min_files_changed > 0):
            errors.append("EMPTY ARTIFACT SET REJECTED: Contract requires verified artifacts, but manifest contains empty artifact set.")

        if len(artifacts) < min_files_changed:
            errors.append(f"MIN FILES CHANGED VIOLATION: Expected at least {min_files_changed} files, got {len(artifacts)}")

        manifest_paths = {a.get("path") for a in artifacts if isinstance(a, dict)}
        for req_art in required_artifacts:
            req_path = req_art if isinstance(req_art, str) else (req_art.get("path") if isinstance(req_art, dict) else str(req_art))
            if req_path not in manifest_paths:
                errors.append(f"CONTRACT VIOLATION: Required artifact '{req_path}' missing from manifest.")

        allowed_root = contract_spec.get("allowed_root", project_root or os.getcwd())
        run_start = contract_spec.get("created_at", 0)
        run_end = time.time() + 300 # Grace window

        content_assertions = contract_spec.get("content_assertions", {})

        for idx, art in enumerate(artifacts):
            if not isinstance(art, dict):
                errors.append(f"Artifact #{idx} is not a valid dictionary.")
                continue

            rel_path = art.get("path")
            claimed_hash = art.get("sha256")
            min_size = art.get("min_size_bytes", 1)

            if not rel_path or not claimed_hash:
                errors.append(f"Artifact #{idx} missing required fields (path, sha256).")
                continue

            # Path Traversal Check
            try:
                full_path = sanitize_and_resolve_path(rel_path, allowed_root)
            except PathSecurityError as e:
                errors.append(f"SECURITY VIOLATION: {e}")
                continue

            # Existence Check
            if not os.path.exists(full_path):
                errors.append(f"GHOST ARTIFACT: Artifact does not exist on disk: {rel_path}")
                continue

            # Size Check
            size = os.path.getsize(full_path)
            if size < min_size:
                errors.append(f"INVALID ARTIFACT SIZE: {rel_path} size is {size} bytes (min: {min_size})")

            # Hash Check on Disk
            disk_hash = compute_file_sha256(full_path)
            if disk_hash.lower() != claimed_hash.lower():
                errors.append(f"HASH MISMATCH: {rel_path} SHA-256 mismatch: claimed {claimed_hash}, disk has {disk_hash}")

            # Mtime Freshness Check
            st_mtime = os.path.getmtime(full_path)
            if st_mtime < (run_start - 1.0):
                errors.append(
                    f"STALE ARTIFACT DETECTED: {rel_path} mtime ({st_mtime:.2f}) older than run_start ({run_start:.2f})."
                )

            # Git Blob Verification: Prove disk content is identical to Git blob in commit
            if commit_sha and project_root:
                git_blob_cmd = ["git", "cat-file", "-p", f"{commit_sha}:{rel_path}"]
                blob_res = subprocess.run(git_blob_cmd, cwd=project_root, capture_output=True)
                if blob_res.returncode != 0:
                    errors.append(f"GIT BLOB INTEGRITY ERROR: Artifact '{rel_path}' does not exist in commit {commit_sha}")
                else:
                    blob_hash = hashlib.sha256(blob_res.stdout).hexdigest()
                    if blob_hash.lower() != disk_hash.lower():
                        errors.append(
                            f"GIT BLOB INTEGRITY ERROR: Disk hash {disk_hash} != Git blob hash {blob_hash} for '{rel_path}'"
                        )

            # Content Assertions Check
            if content_assertions:
                if content_assertions.get("visual_content_required"):
                    is_media = any(rel_path.lower().endswith(ext) for ext in [".mp4", ".mov", ".avi", ".mkv", ".png", ".jpg"])
                    if is_media:
                        v_ok, v_msg = MediaValidator.validate_video(full_path)
                        if not v_ok:
                            errors.append(f"CONTENT VARIANCE CHECK FAILED (Media): {rel_path}: {v_msg}")

                if content_assertions.get("contains_text"):
                    expected_text = content_assertions["contains_text"]
                    try:
                        with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                            content = f.read()
                        if expected_text not in content:
                            errors.append(f"CONTENT ASSERTION FAILED: {rel_path} does not contain '{expected_text}'")
                    except Exception as e:
                        errors.append(f"CONTENT ASSERTION READ ERROR: {e}")

        # 5. Clean Git Tree Enforcement
        if contract_spec.get("require_clean_git", False) and project_root:
            status_res = subprocess.run(["git", "status", "--porcelain"], cwd=project_root, capture_output=True, text=True)
            dirty_lines = [
                l for l in status_res.stdout.splitlines()
                if l.strip() and not ".cache" in l and not "research.db" in l and not ".worktrees" in l and not "WORK_LOG.md" in l and not ".env" in l
            ]
            if dirty_lines:
                errors.append(f"GIT DIRTY TREE ERROR: Working tree has uncommitted modifications: {dirty_lines[:3]}")

        return len(errors) == 0, errors


class OutcomeVerifier:
    """
    Master Layer 4 Outcome Verifier coordinating:
    - Cryptographic Integrity of Acceptance Contract
    - Deterministic Evidence Validation & Git Blob Matching
    - True Video Frame Decoding
    - Advisory/Veto LLM Auditor
    - Cryptographic HMAC Verdict Signing
    """

    def __init__(self, project_root: str, secret_key: Optional[str] = None):
        self.project_root = os.path.realpath(project_root)
        self.signer = VerdictSigner(secret_key)

    def evaluate_task(
        self,
        run_id: str,
        manifest_path: str,
        contract_path: str,
        commit_sha: str,
        trusted_evidence_path: Optional[str] = None,
        llm_auditor_func: Optional[Any] = None
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        # 1. Verify Git commit exists in object database and HEAD matches
        if not re.match(r"^[0-9a-fA-F]{40}$", commit_sha):
            return False, f"Invalid Git SHA format: '{commit_sha}' (must be 40-character hexadecimal)", None

        git_check = subprocess.run(
            ["git", "cat-file", "-e", f"{commit_sha}^{{commit}}"],
            cwd=self.project_root,
            capture_output=True,
            text=True
        )
        if git_check.returncode != 0:
            return False, f"Commit {commit_sha} does not exist in local Git object database", None

        head_res = subprocess.run(["git", "rev-parse", "HEAD"], cwd=self.project_root, capture_output=True, text=True)
        if head_res.returncode == 0:
            current_head = head_res.stdout.strip()
            if current_head.lower() != commit_sha.lower():
                return False, f"HEAD COMMIT MISMATCH: HEAD is {current_head}, but evaluating commit {commit_sha}", None

        # 2. Verify Acceptance Contract Integrity
        try:
            contract_ok, contract_spec, cmsg = AcceptanceContract.verify_integrity(
                contract_path=contract_path,
                expected_run_id=run_id,
                secret_key=self.signer.secret_key
            )
        except ContractTamperError as e:
            return False, f"Contract Verification Failed: {e}", None

        # 3. Load and verify Trusted Runtime Evidence
        trusted_record = None
        if trusted_evidence_path:
            if not os.path.exists(trusted_evidence_path):
                return False, f"Trusted runtime evidence file missing: {trusted_evidence_path}", None
            try:
                with open(trusted_evidence_path, "r", encoding="utf-8") as f:
                    trusted_record = json.load(f)
            except Exception as e:
                return False, f"Invalid trusted runtime evidence JSON: {e}", None

        # 4. Deterministic Evidence Validation
        ev_ok, errors = EvidenceValidator.validate(
            manifest_path=manifest_path,
            contract_spec=contract_spec,
            expected_run_id=run_id,
            trusted_runtime_record=trusted_record,
            project_root=self.project_root,
            commit_sha=commit_sha,
            signer=self.signer
        )

        if not ev_ok:
            bullet_points = "\n- ".join(errors)
            return False, f"Deterministic Outcome Verification Failed:\n- {bullet_points}", None

        # 5. Advisory/Veto LLM Auditor
        if llm_auditor_func:
            try:
                llm_passed, llm_reason = llm_auditor_func(manifest_path, contract_path)
                if not llm_passed:
                    return False, f"LLM Auditor VETO: {llm_reason}", None
            except Exception as e:
                logger.warning(f"Advisory LLM check encountered error (failing closed): {e}")
                return False, f"LLM Auditor execution error (fail-closed): {e}", None

        # 6. Cryptographic Verdict Signing
        manifest_hash = compute_file_sha256(manifest_path)
        verdict_dir = os.path.join(self.project_root, ".cache", "verdicts")
        verdict_path = os.path.join(verdict_dir, f"verdict_{run_id}.json")

        ticket = self.signer.create_ticket(
            run_id=run_id,
            verified_commit_sha=commit_sha,
            status="PASSED",
            manifest_hash=manifest_hash,
            details={
                "action": contract_spec.get("action"),
                "spec_hash": compute_string_sha256(canonical_json(contract_spec)),
                "verified_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "verification_mode": "REALITY_GROUNDED_DETERMINISTIC_L4"
            },
            output_path=verdict_path
        )

        return True, f"Outcome Verification PASSED. Signed verdict: {verdict_path}", ticket
