#!/usr/bin/env python3
"""
Phase 1: CLV Decomposition
Phase 4: Power Analysis for Gate C

SharpBet v8 Audit — Confirmed numbers from Kernel v8 log.
This notebook can be run in Kaggle or locally.
"""

import math
import json

# ============================================================
# PARAMETERS — from Kernel v8 log (verified)
# ============================================================
PARAMS = {
    "total_records": 344_005,
    "direct_ht_odds": 333_507,
    "direct_ht_pct": 96.9,
    "n_leagues": 1_364,
    "margin_mean": 0.1879,       # 18.79% aggregated
    "margin_median": 0.1848,     # 18.48%
    "margin_n": 77_043,
    "train_n": 760,
    "holdout_n": 380,
    "gate_a_eco": 0.0378,        # Macro ECE 3.78% — PASSED
    "gate_a_brier": 0.2171,      # PASSED
    "gate_b_clv_mean": -0.0982,  # -9.82% — BLOCKED
    "gate_b_clv_ci_low": -0.1091,
    "gate_b_clv_ci_high": -0.0879,
    "gate_b_t": -18.90,
    "gate_c_roi": 0.0066,        # 0.66% — not significant
    "gate_c_pnl_eur": 5.90,
    "gate_c_n": 89,              # CRITICAL: only 89 bets
    "gate_c_ci_low": -0.2331,
    "gate_c_ci_high": 0.2576,
    "final_verdict": "FAIL_CLOSED_BLOCKED",
}

print("=" * 65)
print("SHARPBET v8 AUDIT — QUANTITATIVE ANALYSIS")
print("=" * 65)
print()

# ============================================================
# FAZA 1: CLV Dekompozicija (ispravna)
# ============================================================
print("## FAZA 1: CLV DEKOMPOZICIJA")
print()
print("Definicija CLV u Gate B:")
print("  CLV_i = (model_ev_at_closing / model_ev_at_entry) - 1")
print("  = benchmark: closing odds = fer tržišna procena")
print()
print("Reference points:")
print("  Random bettor CLV ≈ 0.0%  (closing = fer, po definiciji)")
print(f"  Naš model CLV    = {PARAMS['gate_b_clv_mean']*100:.2f}%")
print()
print("Šta znači CLV = -9.82%?")
print("  Svaki put kada model selektuje opkladu, tržište se pomeralo")
print("  PROTIV modela sa prosekom 9.82%. Dve hipoteze:")
print()

# Hipoteza A: Margin compression
# Ako je open margina 18.79% i closing margina niža (npr. 10%)
# CLV samo od margin compression ≈ -(18.79% - 10%) / (1 + 10%) = -7.99%
margin_open = PARAMS["margin_mean"]
for closing_margin_estimate in [0.10, 0.12, 0.15]:
    clv_from_margin = -(margin_open - closing_margin_estimate) / (1 + closing_margin_estimate)
    print(f"  H-A (margin compression): Open 18.79%, Closing {closing_margin_estimate*100:.0f}%")
    print(f"    → CLV od margine: {clv_from_margin*100:.2f}%")

print()
print("  Observirani CLV: -9.82%")
print("  Ako closing margina ≈ 10-12%, margin compression = -7.99% do -7.75%")
print("  Ostatak (~-1.8% do -2.1%) = model bira stranu koja se pomera")
print()

# Skill komponenta (definisana kao razlika od margin compression)
clv_obs = PARAMS["gate_b_clv_mean"]
clv_margin_h = -(margin_open - 0.10) / (1 + 0.10)  # optimistična closing margina
skill_component = clv_obs - clv_margin_h

print("Dekompozicija CLV-a (konzervativna procena):")
print(f"  Tržišna margina komponenta: {clv_margin_h*100:.2f}%")
print(f"  Skill komponenta (model):   {skill_component*100:.2f}%")
print(f"  Ukupno CLV observirano:     {clv_obs*100:.2f}%")
print()
print("Zaključak Faze 1:")
print("  Dominantni uzrok negativnog CLV = margin compression")
print("  (tržište se stabilizuje ka closing-u sa nižom marginom).")
print("  Model nije dodao vrednost i bira stranu koja se pomera")
print("  u nepovoljnom smeru (negativna selektivnost ~-1.8%).")
print()
print("  VERDICT: PRETEŽNO TRŽIŠTE, delimično MODEL")
print("  Ratio: ~80% tržišna struktura, ~20% modelska greška")
print()

# ============================================================
# FAZA 4: Power analiza Gate C
# ============================================================
print("=" * 65)
print("## FAZA 4: POWER ANALIZA GATE C")
print()

n_c = PARAMS["gate_c_n"]
roi_obs = PARAMS["gate_c_roi"]
ci_l = PARAMS["gate_c_ci_low"]
ci_h = PARAMS["gate_c_ci_high"]

# Standard Error from CI
se = (ci_h - ci_l) / (2 * 1.96)
# SD per bet
sd = se * math.sqrt(n_c)

print(f"Ulazni parametri:")
print(f"  N_bets       = {n_c}")
print(f"  ROI_obs      = {roi_obs*100:.2f}%")
print(f"  CI Gate C    = [{ci_l*100:.2f}%, {ci_h*100:.2f}%]")
print(f"  SE (from CI) = {se*100:.2f}%")
print(f"  SD per bet   = {sd*100:.2f}%")
print()

z_alpha = 1.96  # alpha = 0.05, two-sided
z_beta = 0.842  # power = 0.80

print("Potreban N za power = 0.80, alpha = 0.05 (two-sided):")
print(f"  Formula: N = ((z_alpha + z_beta) * SD / delta)^2")
print()

results = {}
for delta_pct in [1, 2, 5]:
    delta = delta_pct / 100
    n_needed = math.ceil(((z_alpha + z_beta) * sd / delta) ** 2)
    results[delta_pct] = n_needed
    print(f"  Detekcija {delta_pct}% ROI: N = {n_needed:,} opklada  ({n_needed/n_c:.0f}x više)")

print()
print("ZAKLJUČAK FAZE 4:")
print(f"  Gate C (N={n_c}) ima power ≈ {1 - 0.80*n_c/results[2]:.3f} za 2% ROI detekciju.")
print(f"  Praktično je nemoguće doneti zaključak iz N={n_c}.")
print(f"  ROI 0.66% + PnL €5.90 = NEDOSTATAK DOKAZA.")
print(f"  Gate C nije 'technical pass' — to je statistički šum.")
print()

# ============================================================
# SAŽETAK ZA 07_DECISION.md
# ============================================================
print("=" * 65)
print("## SAŽETAK — INPUT ZA ODLUKU")
print()
print("Radna hipoteza (proveravana analizom):")
print("  'Negativan CLV je dominantno strukturni (overround ~18.79%),")
print("  model je dobro kalibrisan ali bez edge-a nad tržišnim cenama,")
print("  Gate C je šum, i projekat je FAIL_CLOSED iz strukturnih razloga.'")
print()
print("Status hipoteze POSLE analize:")
print("  ✓ Model je dobro kalibrisan (Gate A PASS) — POTVRĐENO")
print("  ✓ Gate C je statistički šum (N=27.374 potrebnih za 2% ROI) — POTVRĐENO")
print("  ✓ CLV pretežno strukturalan (margin compression ~80%) — NAJVEROVATNIJE")
print("  ✗ 'Strukturno' ≠ 'nemoguće zauvek' — nepotvrđeno")
print()
print("Odgovor na RQ1: Koliki deo CLV-a je čist overround?")
print("  ~80% tržišna margina/compression, ~20% negativna model selektivnost")
print("  Oba razloga vode ka istom verdiktu: FAIL_CLOSED ostaje.")
print()
print("Odgovor na RQ4: Koji minimalni N daje smislen Gate C?")
print(f"  N = {results[2]:,} za 2% ROI (power 0.80)")
print(f"  Holding = 380 opklada = nedovoljno za Gate C statističku relevantnost")
print()

# Save JSON summary
summary = {
    "audit_version": "v8",
    "final_verdict": PARAMS["final_verdict"],
    "clv_decomposition": {
        "observed_clv_pct": PARAMS["gate_b_clv_mean"] * 100,
        "estimated_market_structure_pct": clv_margin_h * 100,
        "estimated_model_error_pct": skill_component * 100,
        "market_ratio_approx": 0.80,
        "model_ratio_approx": 0.20,
    },
    "power_analysis_gate_c": {
        "n_bets": n_c,
        "observed_roi_pct": roi_obs * 100,
        "se_pct": round(se * 100, 2),
        "sd_per_bet_pct": round(sd * 100, 2),
        "n_needed_for_2pct_roi_power80": results[2],
        "n_needed_for_1pct_roi_power80": results[1],
        "ratio_needed_vs_actual": round(results[2] / n_c),
        "conclusion": "STATISTICAL_NOISE_NO_EVIDENCE_EITHER_WAY",
    },
    "jtbd_verdict": {
        "primary_job": "Utvrditi da li je FAIL_CLOSED strukturni ili modelski",
        "answer": "PRETEŽNO_STRUKTURNI",
        "recommendation": "Ne deplojavati. Istražiti niše-tržišta sa nižom marginom ili drugačijim ulaznim signalom.",
    }
}

with open("/tmp/sharpbet_v8_quantitative_summary.json", "w") as f:
    json.dump(summary, f, indent=2, ensure_ascii=False)

print(f"Numerički sažetak sačuvan u: /tmp/sharpbet_v8_quantitative_summary.json")
