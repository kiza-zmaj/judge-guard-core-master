#!/usr/bin/env python3
"""
Generate and Verify S6E9 Frankenstein Top-5 Assault Submissions (Subs 23 - 27).

Fuses:
1. SOTA External Benchmarks (r8_m50 [LB 0.94657], r8_m75 [LB 0.94657], r6_rebuilt [LB 0.94651], mega_blend [LB 0.94644])
2. In-House Champion Models (sub21 [LB 0.94641], sub18 [LB 0.94635], sub7 [LB 0.94632])
3. Deterministic Physics Boundary Corrections
4. Zero-Tie Secondary & Tertiary Lexsort
5. 6-Point JudgeGuard Submission Verification Audit
"""

import sys
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import rankdata

CURRENT_DIR = Path(__file__).resolve().parent
SUBMISSIONS_DIR = CURRENT_DIR / "submissions"
DATA_DIR = CURRENT_DIR / "data" / "raw"

TEST_PATH = DATA_DIR / "test.csv"
SAMPLE_SUB_PATH = DATA_DIR / "sample_submission.csv"

# Sources
p_m50 = Path("/tmp/defiaudit/r8_m50.csv")
p_m75 = Path("/tmp/defiaudit/r8_m75.csv")
p_r6 = Path("/tmp/defiaudit/r6_rebuilt_94651.csv")
p_mega = Path("/tmp/megayak/blend.csv")
p_sub21 = SUBMISSIONS_DIR / "sub21_top10_master_assault_calibrated.csv"
p_sub18 = SUBMISSIONS_DIR / "sub18_xgb_recipe_public_calibrated.csv"
p_sub7 = SUBMISSIONS_DIR / "submission_7_xgb_recipe_base_margin.csv"


def postprocess_physics_zerotie(base_ranks: np.ndarray,
                                tiebreaker_ranks: np.ndarray,
                                test_incomes: np.ndarray,
                                test_commute: np.ndarray,
                                subsidy_no: np.ndarray,
                                env_1: np.ndarray,
                                anx_med_high: np.ndarray) -> np.ndarray:
    """Applies physics boundary shifts and zero-tie ordinal sorting."""
    calibrated = base_ranks.copy()
    calibrated[test_incomes >= 170537.0] += 10.0
    calibrated[(test_incomes >= 31004.0) & (test_incomes <= 41970.0)] -= 10.0
    calibrated[test_commute >= 83.0] -= 5.0
    calibrated[(test_incomes == 30000.0) & subsidy_no & (env_1 | anx_med_high)] -= 5.0

    order = np.lexsort((tiebreaker_ranks, calibrated))
    ranks = np.empty(len(order), dtype=np.int64)
    ranks[order] = np.arange(1, len(order) + 1)
    return (ranks - 0.5) / len(ranks)


def verify_6point(sub: pd.DataFrame, sample_sub: pd.DataFrame, name: str):
    """Strict JudgeGuard 6-Point Submission Audit."""
    assert len(sub) == 286571, f"[{name}] Row count mismatch: {len(sub)} != 286571"
    assert list(sub.columns) == ["id", "Will_Buy_EV"], f"[{name}] Column schema mismatch: {list(sub.columns)}"
    assert (sub["id"].values == sample_sub["id"].values).all(), f"[{name}] ID alignment mismatch!"
    assert not sub["Will_Buy_EV"].isna().any(), f"[{name}] Found NaN values!"
    assert not np.isinf(sub["Will_Buy_EV"]).any(), f"[{name}] Found infinite values!"
    assert sub["Will_Buy_EV"].min() >= 0.0 and sub["Will_Buy_EV"].max() <= 1.0, f"[{name}] Values out of bounds [0, 1]!"
    assert sub["Will_Buy_EV"].nunique() == 286571, f"[{name}] Not 100% unique ranks (has ties)!"
    print(f"  ✅ [JudgeGuard PASSED] {name}: 286,571 rows | Zero Ties | Bounds: [{sub['Will_Buy_EV'].min():.6f}, {sub['Will_Buy_EV'].max():.6f}]")


def main():
    print("=" * 80)
    print("🧟⚡ GENERATING S6E9 FRANKENSTEIN TOP-5 ASSAULT SUBMISSIONS (SUBS 23 - 27)")
    print("=" * 80)

    test = pd.read_csv(TEST_PATH)
    sample_sub = pd.read_csv(SAMPLE_SUB_PATH)

    test_incomes = pd.to_numeric(test["Annual_Income_USD"], errors="coerce").to_numpy()
    test_commute = pd.to_numeric(test["Daily_Commute_km"], errors="coerce").to_numpy()
    subsidy_no = (test["Subsidy_Available"].astype(str) == "No").to_numpy()
    env_1 = (pd.to_numeric(test["Environmental_Concern_Level"], errors="coerce") == 1.0).to_numpy()
    anx_med_high = test["Range_Anxiety_Level"].isin(["Medium", "High"]).to_numpy()

    print("📥 Ingesting Frankenstein components...")
    r8_m50 = pd.read_csv(p_m50)["Will_Buy_EV"].values
    r8_m75 = pd.read_csv(p_m75)["Will_Buy_EV"].values
    r6_94651 = pd.read_csv(p_r6)["Will_Buy_EV"].values
    mega = pd.read_csv(p_mega)["Will_Buy_EV"].values
    sub21 = pd.read_csv(p_sub21)["Will_Buy_EV"].values
    sub18 = pd.read_csv(p_sub18)["Will_Buy_EV"].values
    sub7 = pd.read_csv(p_sub7)["Will_Buy_EV"].values

    n = len(sub21)
    rk = lambda x: (rankdata(x) - 0.5) / n

    r_m50 = rk(r8_m50)
    r_m75 = rk(r8_m75)
    r_r6 = rk(r6_94651)
    r_mega = rk(mega)
    r_sub21 = rk(sub21)
    r_sub18 = rk(sub18)
    r_sub7 = rk(sub7)

    candidates = {}

    # SUBMISSION 23: Frankenstein Alpha — Zero-Tie Lexsort on r8_m50 with sub21
    print("\n[1/5] Building Sub 23 (Frankenstein Alpha: Zero-Tie Lexsort on r8_m50)...")
    preds_23 = postprocess_physics_zerotie(r_m50, r_sub21, test_incomes, test_commute, subsidy_no, env_1, anx_med_high)
    candidates["sub23_frankestein_alpha_r8m50_zerotie.csv"] = (
        preds_23, "Sub 23: Frankenstein Alpha — r8_m50 (0.94657) + sub21 Lexsort Tiebreaker + Physics"
    )

    # SUBMISSION 24: Frankenstein Beta — 50/50 Fusion of r8_m50 + sub21
    print("\n[2/5] Building Sub 24 (Frankenstein Beta: 50% r8_m50 + 50% sub21)...")
    blend_24 = 0.50 * r_m50 + 0.50 * r_sub21
    preds_24 = postprocess_physics_zerotie(blend_24, r_sub21, test_incomes, test_commute, subsidy_no, env_1, anx_med_high)
    candidates["sub24_frankestein_beta_50m50_50sub21.csv"] = (
        preds_24, "Sub 24: Frankenstein Beta — 50% r8_m50 (0.94657) + 50% sub21 (0.94641) + Zero-Tie"
    )

    # SUBMISSION 25: Frankenstein Gamma — 45% r8_m75 + 35% sub21 + 20% r6_94651
    print("\n[3/5] Building Sub 25 (Frankenstein Gamma: Tri-Source Super-Blend)...")
    blend_25 = 0.45 * r_m75 + 0.35 * r_sub21 + 0.20 * r_r6
    preds_25 = postprocess_physics_zerotie(blend_25, r_sub21, test_incomes, test_commute, subsidy_no, env_1, anx_med_high)
    candidates["sub25_frankestein_gamma_m75_sub21_r6.csv"] = (
        preds_25, "Sub 25: Frankenstein Gamma — 45% r8_m75 + 35% sub21 + 20% r6 (0.94651) + Physics"
    )

    # SUBMISSION 26: Frankenstein Delta — Quad-Engine Mega Assault
    print("\n[4/5] Building Sub 26 (Frankenstein Delta: Quad-Engine Mega Assault)...")
    blend_26 = 0.30 * r_m50 + 0.30 * r_sub21 + 0.20 * r_sub7 + 0.20 * r_mega
    preds_26 = postprocess_physics_zerotie(blend_26, r_sub21, test_incomes, test_commute, subsidy_no, env_1, anx_med_high)
    candidates["sub26_frankestein_delta_quad_assault.csv"] = (
        preds_26, "Sub 26: Frankenstein Delta — 30% m50 + 30% sub21 + 20% sub7 + 20% mega + Zero-Tie"
    )

    # SUBMISSION 27: Frankenstein Omega — Supreme Top-5 Master Assault
    print("\n[5/5] Building Sub 27 (Frankenstein Omega: Supreme Top-5 Assault)...")
    blend_27 = 0.40 * r_m50 + 0.30 * r_sub21 + 0.15 * r_sub18 + 0.15 * r_r6
    preds_27 = postprocess_physics_zerotie(blend_27, r_sub21, test_incomes, test_commute, subsidy_no, env_1, anx_med_high)
    candidates["sub27_frankestein_omega_supreme_top5.csv"] = (
        preds_27, "Sub 27: Frankenstein Omega — 40% m50 + 30% sub21 + 15% sub18 + 15% r6 (Top-5 Target)"
    )

    print("\n" + "=" * 80)
    print("💾 VERIFYING AND SAVING SUBMISSIONS 23 THROUGH 27")
    print("=" * 80)

    generated = []
    for fname, (preds, desc) in candidates.items():
        sub_df = pd.DataFrame({"id": sample_sub["id"], "Will_Buy_EV": preds})
        verify_6point(sub_df, sample_sub, fname)
        out_p = SUBMISSIONS_DIR / fname
        sub_df.to_csv(out_p, index=False)
        generated.append((out_p, desc))

    print(f"\n🎉 Successfully created and verified all {len(generated)} Frankenstein submissions!")
    return generated


if __name__ == "__main__":
    main()
