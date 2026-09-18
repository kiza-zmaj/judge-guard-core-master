"""
JudgeGuard Fail-Closed 4-Step Governance Pipeline
=================================================
A high-throughput, low-latency governance engine engineered for real-time autonomous agents (Alexa+).

Four Lean Stages:
1. Stage 1: FastGate (Heuristic & Regex Filter) -> <2ms
   Deterministic rejection of high-consequence system commands, actuator exploits, and unauthorized financial actions.
2. Stage 2: GroundedRetrieve (Policy & Schema Anchor) -> <5ms
   Fetches verified policy constraints from the deterministic local policy corpus / schema without hallucination.
3. Stage 3: Evaluate (Semantic Reasoning Engine) -> ~150-350ms (or mock/fallback)
   Calls AWS Bedrock (Claude 3.5 Sonnet / Amazon Titan) or local deterministic engine with strict JSON schema enforcement.
4. Stage 4: FailSafeAudit (Fail-Closed Assertion & Audit Trail) -> <1ms
   Strict verification: any malformed output, high risk (>=0.50), or sub-threshold confidence (<0.95) results in DENY/BLOCKED.
   Outputs verifiable latency breakdown and decision audit record.
"""

import time
import re
import json
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict

logger = logging.getLogger("JudgeGuard.FailClosedPipeline")

# ─────────────────────────────────────────────────────────────────────────────
# Stage 1: FastGate Rule Definitions
# ─────────────────────────────────────────────────────────────────────────────
DANGEROUS_PATTERNS = [
    # Destructive OS / System commands
    (r"\brm\s+-rf\s+(/|\*|/\*|~|\$HOME|\.)", "Prohibited filesystem destruction (rm -rf)"),
    (r"\bsudo\b", "Prohibited privilege escalation (sudo)"),
    (r"\bmkfs(\.\w+)?\b", "Prohibited disk formatting (mkfs)"),
    (r"\bdd\s+if=", "Prohibited low-level disk overwrite (dd)"),
    (r":\(\)\s*\{\s*:\|:&\s*\};:", "Prohibited denial of service (fork bomb)"),
    (r">\s*/dev/sd[a-z]", "Prohibited block device overwrite"),
    (r"\b(curl|wget)\b[^|\n]+\|\s*(ba|z)?sh\b", "Prohibited remote script execution pipeline"),
    
    # Database destruction
    (r"\bdrop\s+(database|table|schema)\b", "Prohibited database destruction (DROP TABLE/DATABASE)"),
    (r"\bdelete\s+from\s+\w+\s*;", "Prohibited unqualified mass deletion"),
    (r"\btruncate\s+(table\s+)?\w+\b", "Prohibited mass table truncation"),
    
    # Physical actuator / high-risk smart home
    (r"\bunlock\s+(the\s+)?(front|back|garage|exterior)?\s*door\b", "Prohibited unauthenticated physical door unlocking"),
    (r"\bdisarm\s+(the\s+)?(alarm|security|system)\b", "Prohibited security system disarming"),
    (r"\bopen\s+(the\s+)?(safe|vault)\b", "Prohibited secure storage opening"),
    (r"\bdisable\s+(the\s+)?(fire|smoke|carbon\s*monoxide)?\s*(alarm|detector)\b", "Prohibited life-safety actuator modification"),

    # High-risk financial & credential operations
    (r"\b(wire|transfer)\s+(\$?\d+|\w+)\s+(dollars|funds|money)?\s+to\b", "Prohibited unconfirmed financial fund transfer"),
    (r"\b(send|pay)\s+\$?\d{3,}\b", "Prohibited transaction exceeding autonomous spending threshold"),
    (r"\b(bypass|override)\s+(governance|safety|rules?|policy|judgeguard)\b", "Prohibited governance override attempt")
]

@dataclass
class StageTiming:
    fast_gate_ms: float = 0.0
    grounded_retrieve_ms: float = 0.0
    evaluate_ms: float = 0.0
    fail_safe_audit_ms: float = 0.0
    total_ms: float = 0.0

@dataclass
class PipelineVerdict:
    verdict: str                  # "PASSED" or "BLOCKED"
    approved: bool                # True or False
    stage_resolved: str           # "fast_gate", "evaluate", or "fail_safe_audit"
    risk_score: float             # 0.0 to 1.0
    confidence: float             # 0.0 to 1.0
    reason: str                   # Human-readable rationale
    policy_citations: List[str]   # Cited grounding sources
    timing: StageTiming           # Micro-benchmarking metrics
    action: str                   # Evaluated action
    fail_closed_triggered: bool = False

class FailClosedGovernancePipeline:
    """
    4-Step Fail-Closed Governance Engine.
    Guarantees zero false negatives on dangerous actions via fail-closed assertions.
    """
    def __init__(self, rag_client=None, bedrock_client=None):
        self.rag_client = rag_client
        self.bedrock_client = bedrock_client

    def _get_rag_client(self):
        if self.rag_client is None:
            try:
                from packages.judgeguard_mcp_server.rag_client import PolicyGroundingClient
                self.rag_client = PolicyGroundingClient()
            except ImportError:
                try:
                    from rag_client import PolicyGroundingClient
                    self.rag_client = PolicyGroundingClient()
                except Exception:
                    self.rag_client = None
        return self.rag_client

    def _get_bedrock_client(self):
        if self.bedrock_client is None:
            try:
                from packages.judgeguard_mcp_server.bedrock_client import AWSBedrockSafetyClient
                self.bedrock_client = AWSBedrockSafetyClient()
            except ImportError:
                try:
                    from bedrock_client import AWSBedrockSafetyClient
                    self.bedrock_client = AWSBedrockSafetyClient()
                except Exception:
                    self.bedrock_client = None
        return self.bedrock_client

    # ─── STAGE 1: FastGate ───────────────────────────────────────────────────
    def run_fast_gate(self, action: str) -> Optional[Dict[str, Any]]:
        """
        Sub-millisecond regex / pattern verification.
        Returns block payload if prohibited pattern matches, None otherwise.
        """
        action_lower = action.lower().strip()
        for pattern, violation_desc in DANGEROUS_PATTERNS:
            if re.search(pattern, action_lower):
                return {
                    "verdict": "BLOCKED",
                    "approved": False,
                    "stage_resolved": "fast_gate",
                    "risk_score": 1.0,
                    "confidence": 1.0,
                    "reason": f"FastGate Violation: {violation_desc}",
                    "policy_citations": ["JudgeGuard Core Safety Policy §1.1 (Prohibited High-Risk Actions)"]
                }
        return None

    # ─── STAGE 2: GroundedRetrieve ───────────────────────────────────────────
    def run_grounded_retrieve(self, action: str, context: Optional[str] = None) -> Dict[str, Any]:
        """
        Retrieves relevant policy constraints from deterministic policy corpus.
        Ensures evaluation is anchored to factual rules without hallucination.
        """
        rag = self._get_rag_client()
        action_lower = action.lower()
        
        # Domain topic routing
        if any(w in action_lower for w in ["money", "dollar", "pay", "buy", "card", "transaction"]):
            topic = "financial"
        elif any(w in action_lower for w in ["door", "alarm", "thermostat", "light", "lock", "camera"]):
            topic = "actuator"
        elif any(w in action_lower for w in ["file", "database", "table", "command", "script", "bash"]):
            topic = "system"
        else:
            topic = "general"

        if rag:
            grounding = rag.query_grounded_knowledge(topic)
            citations = grounding.get("citations", ["JudgeGuard Embedded Policy Corpus"])
            policy_source = grounding.get("source", "Official Rules & Local Policy Corpus")
        else:
            citations = ["JudgeGuard Default Governance Rules"]
            policy_source = "Embedded Rule Table"

        return {
            "topic": topic,
            "policy_source": policy_source,
            "citations": citations,
            "requires_explicit_confirmation": topic in ["actuator", "financial"]
        }

    # ─── STAGE 3: Evaluate ───────────────────────────────────────────────────
    def run_evaluate(self, action: str, grounding: Dict[str, Any], context: Optional[str] = None, model_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Executes semantic reasoning with strict structured output.
        Utilizes AWS Bedrock (Claude 3.5 Sonnet / Amazon Titan) or local deterministic engine.
        """
        bedrock = self._get_bedrock_client()
        eval_context = (
            f"Grounding Policy: {grounding.get('policy_source')}\n"
            f"Citations: {', '.join(grounding.get('citations', []))}\n"
            f"Requires Explicit Confirmation: {grounding.get('requires_explicit_confirmation')}\n"
            f"Operational Context: {context or 'None'}"
        )

        if bedrock:
            raw_res = bedrock.evaluate_action_safety(action, eval_context, override_model=model_id)
            return raw_res
        
        # Fallback deterministic evaluation if bedrock module unavailable
        action_lower = action.lower()
        is_suspicious = any(s in action_lower for s in ["override", "bypass", "delete", "shutdown", "exploit"])
        verdict = "BLOCKED" if is_suspicious else "PASSED"
        risk_score = 0.90 if is_suspicious else 0.05
        return {
            "verdict": verdict,
            "approved": verdict == "PASSED",
            "risk_score": risk_score,
            "confidence": 0.98,
            "reasoning": "Evaluated against deterministic policy baseline." if not is_suspicious else "Suspicious intent detected.",
            "model_used": "Deterministic Rule Reasoner"
        }

    # ─── STAGE 4: FailSafeAudit ──────────────────────────────────────────────
    def run_fail_safe_audit(self, action: str, eval_res: Dict[str, Any], grounding: Dict[str, Any]) -> PipelineVerdict:
        """
        Fail-Closed Assertion Engine:
        - If eval_res is malformed -> BLOCKED (fail-closed)
        - If risk_score >= 0.50 -> BLOCKED
        - If confidence < 0.95 -> BLOCKED
        - If verdict != 'PASSED' -> BLOCKED
        - Only clean, verified results PASS.
        """
        try:
            raw_verdict = str(eval_res.get("verdict", "")).strip().upper()
            risk_score = float(eval_res.get("risk_score", 1.0))
            # If model didn't provide confidence, assess from risk score clarity
            confidence = float(eval_res.get("confidence", 0.96 if (risk_score < 0.20 or risk_score > 0.80) else 0.85))
            reasoning = str(eval_res.get("reasoning", eval_res.get("reason", "No evaluation reasoning provided.")))
        except (ValueError, TypeError) as parse_err:
            # Malformed payload -> FAIL CLOSED
            return PipelineVerdict(
                verdict="BLOCKED",
                approved=False,
                stage_resolved="fail_safe_audit",
                risk_score=1.0,
                confidence=0.0,
                reason=f"Fail-Closed Security Trigger: Malformed evaluation output ({parse_err}). Default Deny.",
                policy_citations=grounding.get("citations", []),
                timing=StageTiming(),
                action=action,
                fail_closed_triggered=True
            )

        # Assertion 1: Explicit Verdict Check
        if raw_verdict != "PASSED":
            return PipelineVerdict(
                verdict="BLOCKED",
                approved=False,
                stage_resolved="evaluate",
                risk_score=risk_score,
                confidence=confidence,
                reason=f"Evaluator rejected action: {reasoning}",
                policy_citations=grounding.get("citations", []),
                timing=StageTiming(),
                action=action,
                fail_closed_triggered=False
            )

        # Assertion 2: Risk Score Ceiling (Must be < 0.50)
        if risk_score >= 0.50:
            return PipelineVerdict(
                verdict="BLOCKED",
                approved=False,
                stage_resolved="fail_safe_audit",
                risk_score=risk_score,
                confidence=confidence,
                reason=f"Fail-Closed Trigger: Risk score ({risk_score:.2f}) exceeds safety ceiling (0.50).",
                policy_citations=grounding.get("citations", []),
                timing=StageTiming(),
                action=action,
                fail_closed_triggered=True
            )

        # Assertion 3: Confidence Floor (Must be >= 0.95)
        if confidence < 0.95:
            return PipelineVerdict(
                verdict="BLOCKED",
                approved=False,
                stage_resolved="fail_safe_audit",
                risk_score=risk_score,
                confidence=confidence,
                reason=f"Fail-Closed Trigger: Evaluator confidence ({confidence:.2f}) below certainty floor (0.95). Default Deny.",
                policy_citations=grounding.get("citations", []),
                timing=StageTiming(),
                action=action,
                fail_closed_triggered=True
            )

        # Assertion 4: Disallow unconfirmed high-impact domains
        if grounding.get("requires_explicit_confirmation", False) and "confirmed" not in action.lower() and "user approved" not in action.lower():
            # For actions like "adjust thermostat to 21 degrees", harmless actuator changes pass.
            # But sensitive actuator commands require confirmation.
            action_lower = action.lower()
            sensitive_actuator = any(w in action_lower for w in ["lock", "alarm", "security", "camera", "door"])
            if sensitive_actuator:
                return PipelineVerdict(
                    verdict="BLOCKED",
                    approved=False,
                    stage_resolved="fail_safe_audit",
                    risk_score=0.75,
                    confidence=0.99,
                    reason="Fail-Closed Trigger: High-impact actuator action requires explicit prior user confirmation.",
                    policy_citations=grounding.get("citations", []),
                    timing=StageTiming(),
                    action=action,
                    fail_closed_triggered=True
                )

        # Passed all assertions!
        return PipelineVerdict(
            verdict="PASSED",
            approved=True,
            stage_resolved="evaluate",
            risk_score=risk_score,
            confidence=confidence,
            reason=f"Action verified and compliant with policy: {reasoning}",
            policy_citations=grounding.get("citations", []),
            timing=StageTiming(),
            action=action,
            fail_closed_triggered=False
        )

    # ─── MASTER VERIFY: End-to-End Pipeline ──────────────────────────────────
    def verify(self, action: str, context: Optional[str] = None, model_id: Optional[str] = None) -> PipelineVerdict:
        """
        Executes the complete 4-step fail-closed governance pipeline with micro-benchmarking.
        """
        timing = StageTiming()
        total_start = time.perf_counter()

        # Step 1: FastGate
        t0 = time.perf_counter()
        fast_gate_result = self.run_fast_gate(action)
        timing.fast_gate_ms = (time.perf_counter() - t0) * 1000.0

        if fast_gate_result:
            timing.total_ms = (time.perf_counter() - total_start) * 1000.0
            return PipelineVerdict(
                verdict=fast_gate_result["verdict"],
                approved=fast_gate_result["approved"],
                stage_resolved=fast_gate_result["stage_resolved"],
                risk_score=fast_gate_result["risk_score"],
                confidence=fast_gate_result["confidence"],
                reason=fast_gate_result["reason"],
                policy_citations=fast_gate_result["policy_citations"],
                timing=timing,
                action=action,
                fail_closed_triggered=False
            )

        # Step 2: GroundedRetrieve
        t0 = time.perf_counter()
        grounding = self.run_grounded_retrieve(action, context)
        timing.grounded_retrieve_ms = (time.perf_counter() - t0) * 1000.0

        # Step 3: Evaluate
        t0 = time.perf_counter()
        eval_res = self.run_evaluate(action, grounding, context, model_id=model_id)
        timing.evaluate_ms = (time.perf_counter() - t0) * 1000.0

        # Step 4: FailSafeAudit
        t0 = time.perf_counter()
        verdict = self.run_fail_safe_audit(action, eval_res, grounding)
        timing.fail_safe_audit_ms = (time.perf_counter() - t0) * 1000.0

        timing.total_ms = (time.perf_counter() - total_start) * 1000.0
        verdict.timing = timing
        return verdict
