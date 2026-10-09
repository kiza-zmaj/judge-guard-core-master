#!/usr/bin/env python3
"""
Empirical Verification Suite: Ollama Cloud Gemma 4 Gate & Google Gemini Production Client
Authority: MASTER_ORCHESTRATION.md
Mode: 100% PRODUCTION MODE (Zero mocks, zero simulations)
"""

import os
import sys
import time
import json
import logging

# Ensure project paths
_repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, _repo_root)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("VERIFY_SUITE")

def verify_ollama_cloud_gemma4() -> dict:
    """Verifies live Ollama Cloud Gemma 4 ticket validator gate."""
    logger.info("=== STEP 1: Verifying Ollama Cloud Gemma 4 Gate ===")
    from src.antigravity_core.ticket_verifier import TicketVerifier
    
    verifier = TicketVerifier()
    action = "Verify Ollama Cloud Gemma 4 and Gemini Production Integration"
    
    t0 = time.time()
    approved, response_text = verifier.verify_ticket(action)
    latency_ms = (time.time() - t0) * 1000
    
    result = {
        "service": "Ollama Cloud Gemma 4 Gate",
        "api_url": verifier.api_url,
        "model": verifier.model,
        "action_tested": action,
        "approved": approved,
        "latency_ms": round(latency_ms, 2),
        "response_excerpt": response_text[:300].replace("\n", " "),
        "status": "PASS" if approved else "FAIL"
    }
    
    print(f"\n[Ollama Cloud Gemma 4 Evidence]")
    print(f"  • Endpoint: {result['api_url']}")
    print(f"  • Model: {result['model']}")
    print(f"  • Latency: {result['latency_ms']} ms")
    print(f"  • Gate Verdict: {'APPROVED' if approved else 'REJECTED'}")
    print(f"  • Model Response: {result['response_excerpt']}")
    
    return result

def verify_gemini_client() -> dict:
    """Verifies live Google Gemini production client."""
    logger.info("=== STEP 2: Verifying Google Gemini Production Client ===")
    from src.antigravity_core.gemini_client import GeminiClient
    
    client = GeminiClient()
    test_prompt = "Reply with one word confirming your identity: Gemini"
    
    t0 = time.time()
    generation = client.generate_content(test_prompt, generation_config={"max_output_tokens": 2048})
    latency_ms = (time.time() - t0) * 1000
    
    # Also verify model security lock (passcode 0012)
    try:
        client.change_model("gemini-2.5-flash", passcode="wrong_code")
        unauthorized_blocked = False
    except PermissionError:
        unauthorized_blocked = True
        
    authorized_change = client.change_model("gemini-3.7-flash", passcode="0012")
    # Restore standard
    client.change_model("gemini-3.8-flash", passcode="0012")
    
    security_verified = unauthorized_blocked and (authorized_change is True)
    has_status = bool(generation and len(generation.strip()) > 0)
    
    result = {
        "service": "Google Gemini Client",
        "active_model": client.model_name,
        "model_hierarchy": client.models,
        "num_api_keys": len(client.api_keys),
        "security_lock_passcode_0012": "PASS" if security_verified else "FAIL",
        "latency_ms": round(latency_ms, 2),
        "generation_output": generation.strip().replace("\n", " "),
        "status": "PASS" if (has_status and security_verified) else "FAIL"
    }
    
    print(f"\n[Google Gemini Production Evidence]")
    print(f"  • Active Model: {result['active_model']}")
    print(f"  • Rotation Hierarchy: {result['model_hierarchy']}")
    print(f"  • Configured Production Keys: {result['num_api_keys']}")
    print(f"  • Passcode '0012' Model Lock: {result['security_lock_passcode_0012']}")
    print(f"  • Latency: {result['latency_ms']} ms")
    print(f"  • Live Generation: {result['generation_output']}")
    
    return result

def main():
    print("=" * 70)
    print("  JUDGEGUARD EMPIRICAL VERIFICATION: OLLAMA CLOUD & GEMINI")
    print("=" * 70)
    
    ollama_res = verify_ollama_cloud_gemma4()
    gemini_res = verify_gemini_client()
    
    print("\n" + "=" * 70)
    print("  FINAL EMPIRICAL VERIFICATION MATRIX")
    print("=" * 70)
    print(f"  Ollama Cloud Gemma 4 Gate:  [{ollama_res['status']}] (Latency: {ollama_res['latency_ms']} ms)")
    print(f"  Google Gemini Live Client:  [{gemini_res['status']}] (Latency: {gemini_res['latency_ms']} ms)")
    print(f"  Model Security Lock (0012): [{gemini_res['security_lock_passcode_0012']}]")
    print("=" * 70)
    
    if ollama_res["status"] == "PASS" and gemini_res["status"] == "PASS":
        print("🎉 ALL PRODUCTION SYSTEMS EMPIRICALLY VERIFIED AND OPERATIONAL.")
        sys.exit(0)
    else:
        print("🛑 ONE OR MORE VERIFICATION CHECKS FAILED.")
        sys.exit(1)

if __name__ == "__main__":
    main()
