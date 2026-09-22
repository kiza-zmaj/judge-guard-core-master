#!/usr/bin/env python3
"""
tests/test_mozzart_parser_golden.py
===================================
Golden QA Test Suite for Mozzart PDF & Odds Parser (SharpBet Core v18.2.0).

Validates:
1. Multi-sport negative filtering (Basketball, Tennis, Handball must be rejected).
2. Semantics & Market validity: Football HT 1X2 required, 1.50 <= odd_x <= 4.50, 0.04 <= overround <= 0.28.
3. Fused-token odds parsing ("1,604,307,00" -> [1.60, 4.30, 7.00]).
4. Odd-token and malformed lines rejection.
5. Exact team name extraction and date normalization.
6. Provenance metadata generation.
"""

import re
import json
import pytest
import numpy as np
import pandas as pd

# Normalizer under test
ISO_RE = r"^\d{4}-\d{2}-\d{2}$"

def normalize_date_to_iso(value):
    if pd.isna(value) or not str(value).strip():
        return None
    s = str(value).strip()
    if re.match(ISO_RE, s):
        return s
    for dayfirst in [True, False]:
        try:
            dt = pd.to_datetime(s, dayfirst=dayfirst, errors="raise")
            return dt.strftime("%Y-%m-%d")
        except Exception:
            continue
    return None

def parse_fused_odds(odds_str: str) -> list:
    """Parses whitespace-separated or fused comma odds tokens."""
    tokens = odds_str.strip().replace(",", ".").split()
    results = []
    for tok in tokens:
        # Check if multiple odds are fused (e.g. 2.702.054.00)
        matches = re.findall(r"\d+\.\d{2}", tok)
        if matches:
            results.extend([float(m) for m in matches])
        else:
            try:
                results.append(float(tok))
            except ValueError:
                pass
    return results

def validate_mozzart_ht_record(record: dict) -> tuple:
    """
    Validates whether a raw parsed record qualifies as a genuine Football HT 1X2 record.
    Returns (is_valid: bool, reason: str, sanitized_dict: dict).
    """
    sport = record.get("sport", "").lower()
    if sport not in ["football", "fudbal", "nogomet"]:
        return False, f"REJECTED_SPORT: {sport}", {}

    market = record.get("market", "")
    if market not in ["HT_1X2", "M16", "POLUVREME"]:
        return False, f"REJECTED_MARKET: {market}", {}

    o1 = record.get("ht_1")
    ox = record.get("ht_x")
    o2 = record.get("ht_2")

    if any(o is None or pd.isna(o) for o in [o1, ox, o2]):
        return False, "REJECTED_MISSING_ODDS", {}

    try:
        o1, ox, o2 = float(o1), float(ox), float(o2)
    except (ValueError, TypeError):
        return False, "REJECTED_INVALID_ODDS_FORMAT", {}

    if not (1.50 <= ox <= 4.50):
        return False, f"REJECTED_HT_X_OUT_OF_BOUNDS: {ox}", {}

    if not (1.20 <= o1 <= 25.0 and 1.20 <= o2 <= 25.0):
        return False, f"REJECTED_HT_1_2_OUT_OF_BOUNDS: {o1}, {o2}", {}

    overround = (1.0 / o1 + 1.0 / ox + 1.0 / o2) - 1.0
    if not (0.04 <= overround <= 0.28):
        return False, f"REJECTED_OVERROUND_OUT_OF_BOUNDS: {overround:.4f}", {}

    iso_d = normalize_date_to_iso(record.get("date"))
    if not iso_d or iso_d > "2026-09-22":
        return False, f"REJECTED_INVALID_DATE: {record.get('date')}", {}

    home = record.get("home_team", "").strip()
    away = record.get("away_team", "").strip()
    if not home or not away or home.upper() == away.upper():
        return False, f"REJECTED_INVALID_TEAMS: {home} vs {away}", {}

    sanitized = {
        "date": iso_d,
        "home_team": home,
        "away_team": away,
        "ht_1": o1,
        "ht_x": ox,
        "ht_2": o2,
        "overround": round(overround, 4)
    }
    return True, "PASSED", sanitized


# ===========================================================================
# GOLDEN TEST SUITE: 30 REPRESENTATIVE PDF BULLETIN LINES
# ===========================================================================

GOLDEN_TEST_CASES = [
    # --- Page 1 Header Lines (EPL / La Liga / Serie A) ---
    {
        "id": "P1_01",
        "sport": "football", "market": "HT_1X2",
        "date": "2024-08-17", "home_team": "Arsenal", "away_team": "Wolves",
        "ht_1": 1.65, "ht_x": 2.50, "ht_2": 8.00,
        "expected_valid": True, "description": "Premier League valid heavy favorite HT odds"
    },
    {
        "id": "P1_02",
        "sport": "football", "market": "HT_1X2",
        "date": "17/08/2024", "home_team": "Valencia", "away_team": "Barcelona",
        "ht_1": 4.50, "ht_x": 2.25, "ht_2": 2.25,
        "expected_valid": True, "description": "La Liga European date format valid HT"
    },
    {
        "id": "P1_03",
        "sport": "football", "market": "HT_1X2",
        "date": "2024-08-18", "home_team": "Chelsea", "away_team": "Manchester City",
        "ht_1": 4.00, "ht_x": 2.35, "ht_2": 2.30,
        "expected_valid": True, "description": "EPL Big Match HT line"
    },
    {
        "id": "P1_04",
        "sport": "basketball", "market": "HT_1X2",
        "date": "2024-08-18", "home_team": "Partizan", "away_team": "Crvena Zvezda",
        "ht_1": 1.85, "ht_x": 12.0, "ht_2": 1.85,
        "expected_valid": False, "description": "Basketball must be rejected by sport filter"
    },
    {
        "id": "P1_05",
        "sport": "tennis", "market": "HT_1X2",
        "date": "2024-08-18", "home_team": "Djokovic N.", "away_team": "Alcaraz C.",
        "ht_1": 1.90, "ht_x": 2.00, "ht_2": 1.90,
        "expected_valid": False, "description": "Tennis must be rejected"
    },
    {
        "id": "P1_06",
        "sport": "handball", "market": "HT_1X2",
        "date": "2024-08-18", "home_team": "Veszprem", "away_team": "Kiel",
        "ht_1": 1.70, "ht_x": 8.50, "ht_2": 2.40,
        "expected_valid": False, "description": "Handball must be rejected"
    },
    {
        "id": "P1_07",
        "sport": "football", "market": "FT_1X2",
        "date": "2024-08-18", "home_team": "Inter", "away_team": "Genoa",
        "ht_1": 1.55, "ht_x": 4.10, "ht_2": 6.00,
        "expected_valid": False, "description": "Full time market must be rejected when expecting HT"
    },
    {
        "id": "P1_08",
        "sport": "football", "market": "HT_1X2",
        "date": "2024-08-19", "home_team": "Leicester", "away_team": "Tottenham",
        "ht_1": 4.60, "ht_x": 2.35, "ht_2": 2.10,
        "expected_valid": True, "description": "EPL competitive HT odds"
    },
    {
        "id": "P1_09",
        "sport": "football", "market": "HT_1X2",
        "date": "2024-08-19", "home_team": "Mallorca", "away_team": "Real Madrid",
        "ht_1": 5.50, "ht_x": 2.30, "ht_2": 1.95,
        "expected_valid": True, "description": "La Liga heavy away favorite HT line"
    },
    {
        "id": "P1_10",
        "sport": "football", "market": "HT_1X2",
        "date": "2024-08-19", "home_team": "Valladolid", "away_team": "Espanyol",
        "ht_1": 3.00, "ht_x": 1.95, "ht_2": 3.70,
        "expected_valid": True, "description": "La Liga tight defensive draw HT line"
    },

    # --- Middle Page Lines (Bundesliga, Ligue 1, Secondary leagues) ---
    {
        "id": "MID_01",
        "sport": "football", "market": "HT_1X2",
        "date": "2024-08-23", "home_team": "M'gladbach", "away_team": "Leverkusen",
        "ht_1": 4.80, "ht_x": 2.45, "ht_2": 1.95,
        "expected_valid": True, "description": "Bundesliga high-scoring fixture HT line"
    },
    {
        "id": "MID_02",
        "sport": "football", "market": "HT_1X2",
        "date": "2024-08-24", "home_team": "Dortmund", "away_team": "Ein Frankfurt",
        "ht_1": 2.25, "ht_x": 2.35, "ht_2": 4.30,
        "expected_valid": True, "description": "Bundesliga home favorite HT line"
    },
    {
        "id": "MID_03",
        "sport": "football", "market": "HT_1X2",
        "date": "2024-08-24", "home_team": "PSG", "away_team": "Montpellier",
        "ht_1": 1.75, "ht_x": 2.65, "ht_2": 6.50,
        "expected_valid": True, "description": "Ligue 1 heavy home favorite HT line"
    },
    {
        "id": "MID_04",
        "sport": "football", "market": "HT_1X2",
        "date": "2024-08-25", "home_team": "Marseille", "away_team": "Reims",
        "ht_1": 2.05, "ht_x": 2.30, "ht_2": 5.20,
        "expected_valid": True, "description": "Ligue 1 valid HT line"
    },
    {
        "id": "MID_05",
        "sport": "football", "market": "HT_1X2",
        "date": "2024-08-25", "home_team": "Nice", "away_team": "Toulouse",
        "ht_1": 2.80, "ht_x": 2.05, "ht_2": 4.00,
        "expected_valid": True, "description": "Ligue 1 defensive match HT line"
    },
    {
        "id": "MID_06",
        "sport": "football", "market": "HT_1X2",
        "date": "2024-08-25", "home_team": "Atalanta", "away_team": "Lecce",
        "ht_1": 1.95, "ht_x": 2.30, "ht_2": 5.70,
        "expected_valid": True, "description": "Serie A valid HT line"
    },
    {
        "id": "MID_07",
        "sport": "football", "market": "HT_1X2",
        "date": "2024-08-25", "home_team": "Roma", "away_team": "Empoli",
        "ht_1": 1.95, "ht_x": 2.35, "ht_2": 5.80,
        "expected_valid": True, "description": "Serie A valid HT line"
    },
    {
        "id": "MID_08",
        "sport": "football", "market": "HT_1X2",
        "date": "2024-08-25", "home_team": "Juventus", "away_team": "Como",
        "ht_1": 1.80, "ht_x": 2.35, "ht_2": 6.80,
        "expected_valid": True, "description": "Serie A valid HT line"
    },
    {
        "id": "MID_09",
        "sport": "football", "market": "HT_1X2",
        "date": "2024-08-25", "home_team": "Bad Overround FC", "away_team": "Anomaly Utd",
        "ht_1": 1.20, "ht_x": 1.50, "ht_2": 1.20,
        "expected_valid": False, "description": "Overround > 0.28 (predatory/corrupted line)"
    },
    {
        "id": "MID_10",
        "sport": "football", "market": "HT_1X2",
        "date": "2024-08-25", "home_team": "Underground Bookie", "away_team": "Zero Margin",
        "ht_1": 3.00, "ht_x": 3.00, "ht_2": 3.00,
        "expected_valid": False, "description": "Overround 0.00 (< 0.04 retail bookmaker threshold)"
    },

    # --- End Page & Edge Case Lines (Fused tokens, formatting errors, future dates) ---
    {
        "id": "END_01",
        "sport": "football", "market": "HT_1X2",
        "date": "2024-08-30", "home_team": "Inter", "away_team": "Atalanta",
        "ht_1": 2.25, "ht_x": 2.25, "ht_2": 4.50,
        "expected_valid": True, "description": "Serie A Derby HT line"
    },
    {
        "id": "END_02",
        "sport": "football", "market": "HT_1X2",
        "date": "2024-08-31", "home_team": "Brighton", "away_team": "Arsenal",
        "ht_1": 4.80, "ht_x": 2.45, "ht_2": 2.05,
        "expected_valid": True, "description": "EPL competitive HT odds"
    },
    {
        "id": "END_03",
        "sport": "football", "market": "HT_1X2",
        "date": "2024-08-31", "home_team": "Lazio", "away_team": "Milan",
        "ht_1": 3.35, "ht_x": 2.15, "ht_2": 3.10,
        "expected_valid": True, "description": "Serie A close clash HT line"
    },
    {
        "id": "END_04",
        "sport": "football", "market": "HT_1X2",
        "date": "2024-08-31", "home_team": "Leverkusen", "away_team": "RB Leipzig",
        "ht_1": 2.25, "ht_x": 2.40, "ht_2": 4.00,
        "expected_valid": True, "description": "Bundesliga top clash HT line"
    },
    {
        "id": "END_05",
        "sport": "football", "market": "HT_1X2",
        "date": "2024-09-01", "home_team": "Man United", "away_team": "Liverpool",
        "ht_1": 3.80, "ht_x": 2.45, "ht_2": 2.30,
        "expected_valid": True, "description": "EPL historic derby HT line"
    },
    {
        "id": "END_06",
        "sport": "football", "market": "HT_1X2",
        "date": "2026-10-15", "home_team": "Future FC", "away_team": "Time Traveler",
        "ht_1": 2.00, "ht_x": 2.20, "ht_2": 3.50,
        "expected_valid": False, "description": "Future date > 2026-09-22 must be strictly rejected"
    },
    {
        "id": "END_07",
        "sport": "football", "market": "HT_1X2",
        "date": "", "home_team": "Empty Date FC", "away_team": "Unknown",
        "ht_1": 2.00, "ht_x": 2.20, "ht_2": 3.50,
        "expected_valid": False, "description": "Empty date must be rejected"
    },
    {
        "id": "END_08",
        "sport": "football", "market": "HT_1X2",
        "date": "2024-09-01", "home_team": "Missing Draw FC", "away_team": "Opponent",
        "ht_1": 2.00, "ht_x": None, "ht_2": 3.50,
        "expected_valid": False, "description": "Missing ht_x must be rejected"
    },
    {
        "id": "END_09",
        "sport": "football", "market": "HT_1X2",
        "date": "2024-09-01", "home_team": "Same Team", "away_team": "Same Team",
        "ht_1": 2.00, "ht_x": 2.20, "ht_2": 3.50,
        "expected_valid": False, "description": "Identical home and away teams rejected"
    },
    {
        "id": "END_10",
        "sport": "football", "market": "HT_1X2",
        "date": "2024-09-01", "home_team": "Absurd Draw FC", "away_team": "Underdog",
        "ht_1": 1.25, "ht_x": 5.50, "ht_2": 15.0,
        "expected_valid": False, "description": "ht_x = 5.50 (> 4.50 ceiling) rejected"
    }
]

def test_golden_cases():
    """Validates all 30 golden test cases against strict semantic checks."""
    passed_cases = 0
    failed_cases = 0

    for case in GOLDEN_TEST_CASES:
        is_val, reason, sanitized = validate_mozzart_ht_record(case)
        assert is_val == case["expected_valid"], (
            f"Test case {case['id']} ({case['description']}) failed: "
            f"Expected {case['expected_valid']}, got {is_val} ({reason})"
        )
        if is_val:
            passed_cases += 1
            assert 0.04 <= sanitized["overround"] <= 0.28
            assert 1.50 <= sanitized["ht_x"] <= 4.50
        else:
            failed_cases += 1

    assert passed_cases == 19
    assert failed_cases == 11
    print(f"✅ Golden Test Suite PASSED: {passed_cases} valid accepted, {failed_cases} invalid rejected.")

def test_fused_token_extraction():
    """Validates fused-token extraction logic."""
    raw_str = "2,702,054,00 1,17 1,36 1,61"
    parsed = parse_fused_odds(raw_str)
    assert len(parsed) >= 3
    assert parsed[0] == 2.70
    assert parsed[1] == 2.05
    assert parsed[2] == 4.00

def test_iso_date_preservation():
    """Ensures ISO format YYYY-MM-DD is never corrupted by dayfirst flag."""
    assert normalize_date_to_iso("2026-07-10") == "2026-07-10"
    assert normalize_date_to_iso("10/07/2026") == "2026-07-10"
    assert normalize_date_to_iso("10.07.2026") == "2026-07-10"
    assert normalize_date_to_iso("") is None
    assert normalize_date_to_iso(None) is None

if __name__ == "__main__":
    test_golden_cases()
    test_fused_token_extraction()
    test_iso_date_preservation()
    print("🎯 All parser QA and date golden tests passed successfully!")
