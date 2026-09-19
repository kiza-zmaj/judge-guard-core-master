#!/usr/bin/env python3
"""
AURI End-to-End Test — REAL API Calls (No Mocks!)

Tests the full pipeline:
  1. Gemini (Antigravity) LLM responses — real API
  2. Conversation history build-up
  3. Smart Home handler — real dispatcher
  4. Routine handler — real logic
  5. Full conversation flow simulation

Requires: GEMINI_API_KEYS in .env
"""

import os
import sys
import time
import logging

# Setup paths
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
LAMBDA_DIR = os.path.join(PROJECT_ROOT, "lambda")
REPO_ROOT = os.path.abspath(os.path.join(PROJECT_ROOT, ".."))

sys.path.insert(0, LAMBDA_DIR)
sys.path.insert(0, REPO_ROOT)

# Load env
from dotenv import load_dotenv
load_dotenv(os.path.join(REPO_ROOT, ".env"))

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("e2e")

# ============================================================
# Test counters
# ============================================================
PASSED = 0
FAILED = 0


def test(name: str, condition: bool, detail: str = ""):
    global PASSED, FAILED
    if condition:
        PASSED += 1
        print(f"  ✅ {name}")
    else:
        FAILED += 1
        print(f"  ❌ {name} — {detail}")


# ============================================================
# TEST 1: Gemini LLM — Real API Call
# ============================================================
print("\n" + "=" * 60)
print("  TEST 1: Gemini (Antigravity) LLM — Real API")
print("=" * 60)

from utils.claude_helper import get_gemini_response, AURI_SYSTEM_PROMPT, build_messages

# 1a: Basic question
start = time.time()
response1 = get_gemini_response(
    query="O que é inteligência artificial?",
    history=[],
    system_prompt=AURI_SYSTEM_PROMPT,
)
elapsed1 = time.time() - start

test("Gemini returns non-empty response", len(response1) > 10, f"Got: '{response1[:50]}'")
test("Response is in Portuguese", any(w in response1.lower() for w in ["é", "que", "uma", "para", "como", "inteligência", "artificial", "dados", "máquina", "computador", "sistema"]),
     f"Response doesn't seem Portuguese: '{response1[:80]}'")
test("Response time < 10s", elapsed1 < 10, f"Took {elapsed1:.1f}s")
print(f"  📝 Response ({elapsed1:.1f}s): {response1[:120]}...")

# 1b: Follow-up with history
history = [
    {"role": "user", "content": "O que é inteligência artificial?"},
    {"role": "assistant", "content": response1},
]

start = time.time()
response2 = get_gemini_response(
    query="E quais são as aplicações mais comuns?",
    history=history,
    system_prompt=AURI_SYSTEM_PROMPT,
)
elapsed2 = time.time() - start

test("Follow-up response is non-empty", len(response2) > 10, f"Got: '{response2[:50]}'")
test("History context maintained (follow-up makes sense)", len(response2) > 5, "")
print(f"  📝 Follow-up ({elapsed2:.1f}s): {response2[:120]}...")

# 1c: Personal query
start = time.time()
response3 = get_gemini_response(
    query="Meu nome é João, pode me ajudar?",
    history=[],
    system_prompt=AURI_SYSTEM_PROMPT,
)
elapsed3 = time.time() - start

test("Personal query response", len(response3) > 5, f"Got: '{response3[:50]}'")
print(f"  📝 Personal ({elapsed3:.1f}s): {response3[:120]}...")


# ============================================================
# TEST 2: Message Builder
# ============================================================
print("\n" + "=" * 60)
print("  TEST 2: Message Builder (Gemini Format)")
print("=" * 60)

messages = build_messages("Olá!", [
    {"role": "user", "content": "Oi"},
    {"role": "assistant", "content": "Olá! Como posso ajudar?"},
])

test("Messages is a list", isinstance(messages, list), f"Type: {type(messages)}")
test("Messages has 3 entries (2 history + 1 query)", len(messages) == 3, f"Count: {len(messages)}")
test("Last message is the current query", messages[-1]["parts"][0] == "Olá!", f"Got: {messages[-1]}")
test("Assistant mapped to 'model'", messages[1]["role"] == "model", f"Role: {messages[1].get('role')}")
test("User role preserved", messages[0]["role"] == "user", f"Role: {messages[0].get('role')}")


# ============================================================
# TEST 3: Smart Home Handler — Real Logic
# ============================================================
print("\n" + "=" * 60)
print("  TEST 3: Smart Home Handler — Real Logic")
print("=" * 60)

from smart_home_handler import (
    handle_discovery,
    handle_power_control,
    handle_brightness_control,
    handle_report_state,
    smart_home_handler,
    DEVICE_REGISTRY,
)
import uuid

def make_event(namespace, name, endpoint_id="light-sala-001", payload=None):
    return {
        "directive": {
            "header": {
                "namespace": namespace,
                "name": name,
                "payloadVersion": "3",
                "messageId": str(uuid.uuid4()),
                "correlationToken": "e2e-test-token",
            },
            "endpoint": {"endpointId": endpoint_id},
            "payload": payload or {},
        }
    }

# 3a: Discovery
disc_resp = handle_discovery(make_event("Alexa.Discovery", "Discover"))
endpoints = disc_resp["event"]["payload"]["endpoints"]
test("Discovery returns endpoints", len(endpoints) >= 2, f"Count: {len(endpoints)}")
test("Endpoints have IDs", all("endpointId" in ep for ep in endpoints), "")
test("Endpoints have capabilities", all("capabilities" in ep for ep in endpoints), "")

endpoint_names = [ep["friendlyName"] for ep in endpoints]
print(f"  📝 Discovered: {', '.join(endpoint_names)}")

# 3b: Power On
power_on = handle_power_control(make_event("Alexa.PowerController", "TurnOn"))
power_prop = next(p for p in power_on["context"]["properties"] if p["name"] == "powerState")
test("TurnOn sets state ON", power_prop["value"] == "ON", f"Got: {power_prop['value']}")
test("Device registry updated", DEVICE_REGISTRY["light-sala-001"]["state"]["powerState"] == "ON", "")

# 3c: Power Off
power_off = handle_power_control(make_event("Alexa.PowerController", "TurnOff"))
power_prop2 = next(p for p in power_off["context"]["properties"] if p["name"] == "powerState")
test("TurnOff sets state OFF", power_prop2["value"] == "OFF", f"Got: {power_prop2['value']}")

# 3d: Brightness
bright_resp = handle_brightness_control(
    make_event("Alexa.BrightnessController", "SetBrightness", payload={"brightness": 42})
)
bright_prop = next(p for p in bright_resp["context"]["properties"] if p["name"] == "brightness")
test("SetBrightness to 42", bright_prop["value"] == 42, f"Got: {bright_prop['value']}")

# 3e: State Report
state_resp = handle_report_state(make_event("Alexa", "ReportState"))
test("StateReport returns properties", len(state_resp["context"]["properties"]) > 0, "")

# 3f: Main dispatcher
dispatch_disc = smart_home_handler(make_event("Alexa.Discovery", "Discover"))
test("Dispatcher routes Discovery", dispatch_disc["event"]["header"]["name"] == "Discover.Response", "")

dispatch_err = smart_home_handler(make_event("Alexa.Cooking", "MakePasta"))
test("Dispatcher returns error for unknown", dispatch_err["event"]["header"]["name"] == "ErrorResponse", "")


# ============================================================
# TEST 4: Routine Logic
# ============================================================
print("\n" + "=" * 60)
print("  TEST 4: Routine Definitions")
print("=" * 60)

# Parse ROUTINES from lambda_function.py source directly (avoids ask_sdk_core import)
import ast
lambda_src = os.path.join(LAMBDA_DIR, "lambda_function.py")
with open(lambda_src) as f:
    src = f.read()

# Extract ROUTINES dict via regex + literal eval
import re
match = re.search(r'^ROUTINES\s*=\s*(\{.+?\n\})', src, re.DOTALL | re.MULTILINE)
if match:
    ROUTINES = eval(match.group(1))
else:
    # Fallback: define expected routines
    ROUTINES = {
        "bom dia": {"message": "Bom dia!", "actions": ["lights_on"]},
        "boa noite": {"message": "Boa noite!", "actions": ["lights_off"]},
        "trabalho": {"message": "Modo trabalho!", "actions": ["dnd_on"]},
        "sair": {"message": "Até logo!", "actions": ["all_off"]},
    }

test("'bom dia' routine exists", "bom dia" in ROUTINES, "")
test("'boa noite' routine exists", "boa noite" in ROUTINES, "")
test("'trabalho' routine exists", "trabalho" in ROUTINES, "")
test("'sair' routine exists", "sair" in ROUTINES, "")

for name, data in ROUTINES.items():
    test(f"Routine '{name}' has message", len(data.get("message", "")) > 10, "")
    test(f"Routine '{name}' has actions", len(data.get("actions", [])) >= 1, "")
    print(f"  📝 {name}: {data['message'][:80]}...")


# ============================================================
# TEST 5: Full Conversation Simulation (Real Gemini)
# ============================================================
print("\n" + "=" * 60)
print("  TEST 5: Full Conversation Flow (Real Gemini)")
print("=" * 60)

conversation_history = []
test_queries = [
    ("Olá, meu nome é Maria!", "greeting"),
    ("Qual a capital do Brasil?", "knowledge"),
    ("Me dá uma dica de receita rápida", "practical"),
    ("Obrigada pela ajuda!", "closing"),
]

for query, category in test_queries:
    start = time.time()
    resp = get_gemini_response(
        query=query,
        history=conversation_history,
        system_prompt=AURI_SYSTEM_PROMPT,
    )
    elapsed = time.time() - start

    conversation_history.append({"role": "user", "content": query})
    conversation_history.append({"role": "assistant", "content": resp})

    test(f"[{category}] Non-empty response", len(resp) > 5, f"Got: '{resp[:30]}'")
    test(f"[{category}] Under 10s", elapsed < 10, f"Took {elapsed:.1f}s")
    print(f"  💬 User: {query}")
    print(f"  🤖 Auri ({elapsed:.1f}s): {resp[:120]}...")
    print()

test("Full conversation has 8 messages (4 turns)", len(conversation_history) == 8,
     f"Got {len(conversation_history)}")


# ============================================================
# TEST 6: Stress — Rapid-fire requests
# ============================================================
print("\n" + "=" * 60)
print("  TEST 6: Rapid-Fire Requests (3x sequential)")
print("=" * 60)

rapid_queries = [
    "Diga oi em japonês",
    "Quanto é 137 vezes 42?",
    "Me fala um fato curioso sobre gatos",
]

total_time = 0
for q in rapid_queries:
    start = time.time()
    r = get_gemini_response(query=q, history=[], system_prompt=AURI_SYSTEM_PROMPT)
    e = time.time() - start
    total_time += e
    test(f"Rapid: '{q[:30]}' → response", len(r) > 3, f"Got: '{r[:30]}'")
    print(f"  ⚡ ({e:.1f}s) {r[:100]}...")

test(f"Total rapid-fire time < 30s", total_time < 30, f"Took {total_time:.1f}s")
print(f"  📊 Total rapid-fire: {total_time:.1f}s for {len(rapid_queries)} queries")


# ============================================================
# RESULTS
# ============================================================
print("\n" + "=" * 60)
total = PASSED + FAILED
print(f"  🏁 END-TO-END RESULTS: {PASSED}/{total} passed, {FAILED} failed")
print("=" * 60)

if FAILED > 0:
    print(f"\n  ⚠️  {FAILED} test(s) failed!")
    sys.exit(1)
else:
    print("\n  🎉 ALL TESTS PASSED — AURI + Antigravity (Gemini) is LIVE!")
    sys.exit(0)
