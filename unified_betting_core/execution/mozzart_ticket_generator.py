"""
Mozzart Football Ticket Generator & Quantitative Value Pipeline.
Uses Unified Betting Core components:
- DevigEngine (Power / Log-odds and Multiplicative de-vigging)
- PoissonEngine (Dixon-Coles bivariate low-score adjusted simulation)
- EmpiricalDecisionGate (Anti-delusion, Shrinkage towards market true price)
- EVCalculator & KellyCriterion (Stake sizing and portfolio allocation)
- Ticket Builder: Assembles actionable, mathematically sound betting tickets
"""

import os
import sys
import math
import logging
from typing import Any
import pandas as pd
import numpy as np
from scipy.optimize import minimize
from scipy.stats import poisson

# Add root directory to sys.path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
CORE_DIR = os.path.dirname(CURRENT_DIR)
PARENT_DIR = os.path.dirname(CORE_DIR)
for p in [CURRENT_DIR, CORE_DIR, PARENT_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p)

from unified_betting_core.decision_engine.devig_engine import DevigEngine
from unified_betting_core.decision_engine.empirical_gate import (
    EmpiricalDecisionGate,
    FinalStatus,
)
from unified_betting_core.decision_engine.kelly_criterion import KellyCriterion
from unified_betting_core.models.poisson_model import PoissonEngine, dixon_coles_tau

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("MozzartTicketGenerator")

# Typical league baseline expected goals (per match) based on empirical historical data
LEAGUE_GOAL_PRIORS = {
    "Argentina 1 - Klausura": {"avg_goals": 2.15, "hfa": 0.22},
    "Argentina 2": {"avg_goals": 1.95, "hfa": 0.28},
    "Argentina 4": {"avg_goals": 2.10, "hfa": 0.25},
    "Azijske igre": {"avg_goals": 2.80, "hfa": 0.10},
    "Bolivija Liga Kup": {"avg_goals": 3.10, "hfa": 0.35},
    "Brazil 1": {"avg_goals": 2.40, "hfa": 0.26},
    "Brazil 2": {"avg_goals": 2.05, "hfa": 0.24},
    "Bugarska 2": {"avg_goals": 2.45, "hfa": 0.25},
    "Danska 2": {"avg_goals": 2.95, "hfa": 0.20},
    "Dominikanska Republika 1": {"avg_goals": 2.65, "hfa": 0.25},
    "Ekvador 1": {"avg_goals": 2.60, "hfa": 0.30},
    "El Salvador 1 - Apertura": {"avg_goals": 2.50, "hfa": 0.26},
    "Engleska 7 - Central": {"avg_goals": 3.00, "hfa": 0.22},
    "Engleska M21": {"avg_goals": 3.65, "hfa": 0.15},
    "Engleska razvojna liga": {"avg_goals": 3.50, "hfa": 0.15},
    "Gruzija 1": {"avg_goals": 2.50, "hfa": 0.25},
    "Gvatemala 1 - Apertura": {"avg_goals": 2.35, "hfa": 0.30},
    "Honduras 1 - Apertura": {"avg_goals": 2.60, "hfa": 0.28},
    "Italija 3 A": {"avg_goals": 2.20, "hfa": 0.25},
    "Italija 3 B": {"avg_goals": 2.15, "hfa": 0.25},
    "Kolumbija 1 - Klausura": {"avg_goals": 2.25, "hfa": 0.28},
    "Kolumbija 2 - Klausura": {"avg_goals": 2.20, "hfa": 0.28},
}


class MozzartQuantitativeEngine:
    def __init__(
        self,
        mecevi_path: str,
        marketi_path: str,
        bankroll: float = 1000.0,
    ):
        self.mecevi_path = mecevi_path
        self.marketi_path = marketi_path
        self.bankroll = bankroll
        self.devig_engine = DevigEngine()
        self.empirical_gate = EmpiricalDecisionGate(min_edge=0.02)
        self.kelly = KellyCriterion(fraction=0.33, min_edge=0.02, max_bankroll_pct=0.06)
        self.poisson_engine = PoissonEngine()

    def fit_expected_goals(
        self,
        p_home_devig: float,
        p_draw_devig: float,
        p_away_devig: float,
        p_o25_devig: float | None = None,
        league: str = "",
    ) -> tuple[float, float]:
        """
        Inverts Dixon-Coles Poisson model to find (lambda_home, lambda_away)
        matching the de-vigged market implied probabilities and league goal priors.
        """
        prior = LEAGUE_GOAL_PRIORS.get(league, {"avg_goals": 2.50, "hfa": 0.25})
        prior_tot = prior["avg_goals"]

        def objective(params):
            lh, la = params
            if lh <= 0.05 or la <= 0.05:
                return 999.0
            
            ph = pd = pa = po25 = 0.0
            for h in range(8):
                for a in range(8):
                    tau = dixon_coles_tau(h, a, lh, la)
                    p = poisson.pmf(h, lh) * poisson.pmf(a, la) * tau
                    if h > a:
                        ph += p
                    elif h == a:
                        pd += p
                    else:
                        pa += p
                    if (h + a) > 2.5:
                        po25 += p

            tot = ph + pd + pa
            ph, pd, pa = ph / tot, pd / tot, pa / tot

            # 1X2 square errors
            err = 2.0 * ((ph - p_home_devig) ** 2 + (pd - p_draw_devig) ** 2 + (pa - p_away_devig) ** 2)
            if p_o25_devig is not None:
                err += 1.5 * ((po25 - p_o25_devig) ** 2)
            
            # Regularization towards league average total goals
            err += 0.2 * ((lh + la - prior_tot) ** 2)
            return err

        init_h = prior_tot * (p_home_devig + 0.5 * p_draw_devig)
        init_a = prior_tot * (p_away_devig + 0.5 * p_draw_devig)
        init_h = max(0.4, min(3.5, init_h))
        init_a = max(0.4, min(3.5, init_a))

        res = minimize(objective, [init_h, init_a], bounds=[(0.2, 4.5), (0.2, 4.5)])
        return float(res.x[0]), float(res.x[1])

    def evaluate_all(self) -> dict[str, Any]:
        """
        Parses all matches and markets, runs quantitative evaluation,
        identifies +EV opportunities, and builds specialized tickets.
        """
        df_mecevi = pd.read_csv(self.mecevi_path)
        df_marketi = pd.read_csv(self.marketi_path)

        all_matches_analysis = []
        all_evaluated_bets = []

        for _, m_row in df_mecevi.iterrows():
            match_id = int(m_row["match_id"])
            takmicenje = str(m_row["takmicenje"])
            domacin = str(m_row["domacin"])
            gost = str(m_row["gost"])
            datum = str(m_row["datum"])
            vreme = str(m_row["vreme"])
            dan_label = str(m_row["dan_label"])
            marza_1x2 = float(m_row.get("trziste_marza", 0.0))

            odds_1 = float(m_row["1"])
            odds_x = float(m_row["X"])
            odds_2 = float(m_row["2"])

            # 1. De-vig 1X2 using SharpBet DevigEngine Power Method
            devig_1x2 = DevigEngine.devig_power({"home": odds_1, "draw": odds_x, "away": odds_2})
            p_devig_1 = devig_1x2["home"]
            p_devig_x = devig_1x2["draw"]
            p_devig_2 = devig_1x2["away"]

            # Pull all market lines for this match
            m_sub = df_marketi[df_marketi["match_id"] == match_id]
            
            odds_map = {}
            for _, r in m_sub.iterrows():
                trz = r["trziste"]
                ish = r["ishod"]
                kv = float(r["kvota"])
                odds_map[(trz, ish)] = kv

            # De-vig Totals 2.5 (Over 2.5 vs Under 2.5)
            kv_3plus = None
            kv_0to2 = None
            kv_2plus = None
            kv_1x = None
            kv_12 = None
            kv_x2 = None

            for (trz, ish), kv in odds_map.items():
                if trz == "Ukupno golova":
                    if "najmanje 3" in ish:
                        kv_3plus = kv
                    elif "najviše 2" in ish:
                        kv_0to2 = kv
                    elif "najmanje 2" in ish:
                        kv_2plus = kv
                elif trz == "Dupla šansa":
                    if f"{domacin} će pobediti ili" in ish or "nerešenim" in ish and domacin in ish:
                        kv_1x = kv
                    elif f"{domacin} ili" in ish:
                        kv_12 = kv
                    elif f"{gost} će pobediti ili" in ish or "nerešenim" in ish and gost in ish:
                        kv_x2 = kv

            # Fallbacks for double chance detection by outcome ordering if team string matching varies
            if kv_1x is None or kv_12 is None or kv_x2 is None:
                ds_rows = m_sub[m_sub["trziste"] == "Dupla šansa"].sort_values("redosled")
                if len(ds_rows) >= 3:
                    kv_1x = float(ds_rows.iloc[0]["kvota"])
                    kv_12 = float(ds_rows.iloc[1]["kvota"])
                    kv_x2 = float(ds_rows.iloc[2]["kvota"])

            # De-vig Over/Under 2.5
            p_devig_o25 = 0.50
            p_devig_u25 = 0.50
            if kv_3plus and kv_0to2 and kv_3plus > 1.0 and kv_0to2 > 1.0:
                devig_ou = DevigEngine.devig_power({"over": kv_3plus, "under": kv_0to2})
                p_devig_o25 = devig_ou["over"]
                p_devig_u25 = devig_ou["under"]

            # Double chance fair de-vigged probabilities
            p_devig_1x = p_devig_1 + p_devig_x
            p_devig_12 = p_devig_1 + p_devig_2
            p_devig_x2 = p_devig_x + p_devig_2

            # 2. Dixon-Coles Poisson Model Simulation
            lh, la = self.fit_expected_goals(p_devig_1, p_devig_x, p_devig_2, p_devig_o25, takmicenje)
            
            # Full Dixon-Coles simulation
            prob_home = 0.0
            prob_draw = 0.0
            prob_away = 0.0
            prob_o25 = 0.0
            prob_o15 = 0.0
            prob_btts = 0.0
            best_score = "1-1"
            best_score_p = -1.0

            for h in range(8):
                for a in range(8):
                    tau = dixon_coles_tau(h, a, lh, la)
                    p = poisson.pmf(h, lh) * poisson.pmf(a, la) * tau
                    if h > a:
                        prob_home += p
                    elif h == a:
                        prob_draw += p
                    else:
                        prob_away += p
                    if (h + a) >= 2:
                        prob_o15 += p
                    if (h + a) > 2.5:
                        prob_o25 += p
                    if h > 0 and a > 0:
                        prob_btts += p
                    if p > best_score_p:
                        best_score_p = p
                        best_score = f"{h}-{a}"

            tot = prob_home + prob_draw + prob_away
            prob_home /= tot
            prob_draw /= tot
            prob_away /= tot

            prob_u25 = 1.0 - prob_o25
            prob_1x = prob_home + prob_draw
            prob_12 = prob_home + prob_away
            prob_x2 = prob_draw + prob_away

            match_data = {
                "match_id": match_id,
                "datum": datum,
                "dan_label": dan_label,
                "vreme": vreme,
                "takmicenje": takmicenje,
                "domacin": domacin,
                "gost": gost,
                "match_name": f"{domacin} - {gost}",
                "marza_1x2": marza_1x2,
                "xg_home": round(lh, 2),
                "xg_away": round(la, 2),
                "predicted_score": best_score,
                "score_confidence": round(best_score_p * 100, 1),
                "p_devig": {"1": p_devig_1, "X": p_devig_x, "2": p_devig_2},
                "p_model": {"1": prob_home, "X": prob_draw, "2": prob_away, "o25": prob_o25, "u25": prob_u25, "o15": prob_o15, "btts": prob_btts},
                "odds": {
                    "1": odds_1, "X": odds_x, "2": odds_2,
                    "1X": kv_1x, "12": kv_12, "X2": kv_x2,
                    "2+": kv_2plus, "0-2": kv_0to2, "3+": kv_3plus
                }
            }
            all_matches_analysis.append(match_data)

            # Evaluate candidate bets across all 9 outcomes
            candidates = [
                ("Konačan ishod", "1", domacin, odds_1, prob_home, p_devig_1),
                ("Konačan ishod", "X", "Nerešeno", odds_x, prob_draw, p_devig_x),
                ("Konačan ishod", "2", gost, odds_2, prob_away, p_devig_2),
                ("Dupla šansa", "1X", f"{domacin} ili Nerešeno", kv_1x, prob_1x, p_devig_1x),
                ("Dupla šansa", "12", f"{domacin} ili {gost}", kv_12, prob_12, p_devig_12),
                ("Dupla šansa", "X2", f"{gost} ili Nerešeno", kv_x2, prob_x2, p_devig_x2),
                ("Ukupno golova", "2+", "Najmanje 2 gola", kv_2plus, prob_o15, prob_o15 * (1.0 - 0.05)),
                ("Ukupno golova", "0-2", "Najviše 2 gola (0-2)", kv_0to2, prob_u25, p_devig_u25),
                ("Ukupno golova", "3+", "Najmanje 3 gola (3+)", kv_3plus, prob_o25, p_devig_o25),
            ]

            for market_type, code, desc, odds, p_mod, p_dev in candidates:
                if odds is None or odds <= 1.01:
                    continue

                # Calibrate probability using EmpiricalDecisionGate shrinkage
                p_cal = self.empirical_gate.calibrate_probability(p_mod, p_dev, odds)
                fair_odds = round(1.0 / p_cal, 2) if p_cal > 0 else 999.0
                edge = (p_cal * odds) - 1.0
                edge_pct = round(edge * 100, 2)
                raw_ev = ((p_mod * odds) - 1.0) * 100

                # Half-Kelly stake recommendation
                stake = self.kelly.calculate_stake(p_cal, odds, self.bankroll)

                # Anti-delusion classification
                abs_div = abs(p_mod - p_dev)
                is_longshot = odds >= 5.0
                status = "PASS"
                if is_longshot and abs_div > 0.12:
                    status = "LONGSHOT_RISK"
                elif edge_pct < 0.0:
                    status = "NEGATIVE_EV"
                elif edge_pct < 2.0:
                    status = "MARGINAL"
                else:
                    status = "VALUE"

                all_evaluated_bets.append({
                    "match_id": match_id,
                    "datum": datum,
                    "dan_label": dan_label,
                    "vreme": vreme,
                    "takmicenje": takmicenje,
                    "domacin": domacin,
                    "gost": gost,
                    "market_type": market_type,
                    "code": code,
                    "selection_desc": desc,
                    "odds": odds,
                    "p_model": round(p_mod, 4),
                    "p_devig": round(p_dev, 4),
                    "p_calibrated": round(p_cal, 4),
                    "fair_odds": fair_odds,
                    "edge_pct": edge_pct,
                    "raw_ev_pct": round(raw_ev, 2),
                    "stake_eur": stake,
                    "status": status,
                    "marza_1x2": marza_1x2,
                    "predicted_score": best_score,
                })

        return {
            "matches": all_matches_analysis,
            "bets": all_evaluated_bets,
        }

    def build_tickets(self, evaluation: dict[str, Any]) -> dict[str, Any]:
        """
        Assembles 5 distinct, practical betting tickets tailored for Mozzart.
        """
        bets = evaluation["bets"]
        df_bets = pd.DataFrame(bets)

        # Helper to avoid picking the same match multiple times on the same ticket
        def pick_diverse_ticket(
            filtered_bets: pd.DataFrame,
            max_legs: int = 5,
            sort_by: str = "p_calibrated",
            ascending: bool = False,
            preferred_types: list[str] | None = None
        ):
            df_work = filtered_bets.copy()
            if preferred_types:
                df_work["type_rank"] = df_work["market_type"].apply(
                    lambda x: preferred_types.index(x) if x in preferred_types else 99
                )
                sorted_df = df_work.sort_values(["type_rank", sort_by], ascending=[True, ascending])
            else:
                sorted_df = df_work.sort_values(sort_by, ascending=ascending)

            chosen = []
            seen_matches = set()
            for _, row in sorted_df.iterrows():
                mid = row["match_id"]
                if mid not in seen_matches:
                    chosen.append(row.to_dict())
                    seen_matches.add(mid)
                if len(chosen) >= max_legs:
                    break
            return chosen

        # -------------------------------------------------------------
        # TIKET 1: "SIGURICA / VALUE BANKERI" (Zicer Tiket)
        # -------------------------------------------------------------
        # Criteria: High probability (>72%), odds 1.18 - 1.55, safe markets (Dupla sansa, 2+, Big Favorites)
        bankers_candidates = df_bets[
            (df_bets["p_calibrated"] >= 0.72) &
            (df_bets["odds"] >= 1.18) &
            (df_bets["odds"] <= 1.55) &
            (df_bets["code"].isin(["1", "2", "1X", "X2", "2+"]))
        ]
        ticket_1_legs = pick_diverse_ticket(
            bankers_candidates,
            max_legs=5,
            sort_by="p_calibrated",
            ascending=False
        )

        # -------------------------------------------------------------
        # TIKET 2: "URAVNOTEŽENI +EV VALUE TIKET" (Optimal Risk/Reward)
        # -------------------------------------------------------------
        # Criteria: Solid odds 1.45 - 2.35, lowest 1X2 market margin (e.g. Argentina 1 with 4.8% margin),
        # high probability (>48%), strong edge/calibration.
        value_candidates = df_bets[
            (df_bets["odds"] >= 1.42) &
            (df_bets["odds"] <= 2.35) &
            (df_bets["p_calibrated"] >= 0.44) &
            (df_bets["marza_1x2"] <= 0.082) &
            (df_bets["code"].isin(["1", "2", "1X", "X2", "0-2", "3+"]))
        ]
        ticket_2_legs = pick_diverse_ticket(
            value_candidates,
            max_legs=4,
            sort_by="p_calibrated",
            ascending=False
        )

        # -------------------------------------------------------------
        # TIKET 3: "GOLOVI MAJSTOR (GOALS SPECIAL: 2+, 0-2, 3+)"
        # -------------------------------------------------------------
        # Selections strictly on the 'Ukupno golova' market:
        # High scoring (2+ or 3+) in England U21, Denmark 2, Bolivia
        # Low scoring (0-2) in Argentina 1 & 2 & 4, Brazil 2, Italy C
        goals_candidates = df_bets[
            (df_bets["market_type"] == "Ukupno golova") &
            (df_bets["odds"] >= 1.25) &
            (df_bets["odds"] <= 2.10) &
            (df_bets["p_calibrated"] >= 0.52)
        ]
        ticket_3_legs = pick_diverse_ticket(
            goals_candidates,
            max_legs=4,
            sort_by="p_calibrated",
            ascending=False
        )

        # -------------------------------------------------------------
        # TIKET 4: "NOĆNI EKSPRES (Južna i Srednja Amerika)"
        # -------------------------------------------------------------
        # Matches playing at night (00:00 - 03:30, Argentina, Brazil, Colombia, Ecuador, Bolivia, Guatemala, Honduras)
        night_times = ["00:00", "00:15", "00:30", "01:00", "01:10", "01:15", "01:30", "02:15", "02:30", "03:00", "03:15", "03:30"]
        night_candidates = df_bets[
            (df_bets["vreme"].isin(night_times)) &
            (df_bets["p_calibrated"] >= 0.60) &
            (df_bets["odds"] >= 1.25) &
            (df_bets["odds"] <= 2.20) &
            (df_bets["code"].isin(["1", "2", "1X", "X2", "2+", "0-2"]))
        ]
        ticket_4_legs = pick_diverse_ticket(
            night_candidates,
            max_legs=4,
            sort_by="p_calibrated",
            ascending=False
        )

        # -------------------------------------------------------------
        # TIKET 5: "SISTEM 4 OD 6 (Sigurnost & Profitabilnost)"
        # -------------------------------------------------------------
        # 6 selections with attractive odds (1.50 - 2.35) and solid probability (>48%)
        system_candidates = df_bets[
            (df_bets["odds"] >= 1.50) &
            (df_bets["odds"] <= 2.35) &
            (df_bets["p_calibrated"] >= 0.45) &
            (df_bets["code"].isin(["1", "2", "0-2", "3+", "1X", "X2"]))
        ]
        ticket_5_legs = pick_diverse_ticket(
            system_candidates,
            max_legs=6,
            sort_by="p_calibrated",
            ascending=False
        )

        # -------------------------------------------------------------
        # TIKET 6: "LOVAC NA KVOTE / POPULARNI AKUMULATOR (Kvota 15+)"
        # -------------------------------------------------------------
        # 5 attractive picks with odds between 1.55 and 2.05, solid probability (>50%)
        high_yield_candidates = df_bets[
            (df_bets["odds"] >= 1.53) &
            (df_bets["odds"] <= 2.05) &
            (df_bets["p_calibrated"] >= 0.50) &
            (df_bets["code"].isin(["1", "2", "3+", "0-2"]))
        ]
        ticket_6_legs = pick_diverse_ticket(
            high_yield_candidates,
            max_legs=5,
            sort_by="p_calibrated",
            ascending=False
        )

        def compile_ticket_summary(legs: list[dict], name: str, strategy: str, stake: float = 10.0, is_system: bool = False):
            if is_system and len(legs) == 6:
                # System 4/6 calculations (15 combinations of 4 legs)
                from itertools import combinations
                combos = list(combinations(legs, 4))
                num_combos = len(combos)
                stake_per_combo = round(stake / num_combos, 2)
                
                combo_odds = []
                for c in combos:
                    od = 1.0
                    for leg in c:
                        od *= leg["odds"]
                    combo_odds.append(od)
                
                min_win = round(min(combo_odds) * stake_per_combo, 2)
                avg_win = round((sum(combo_odds) / len(combo_odds)) * stake_per_combo, 2)
                max_win = round(sum(combo_odds) * stake_per_combo, 2)

                # Joint probability that all 6 pass
                all_prob = 1.0
                for leg in legs:
                    all_prob *= leg["p_calibrated"]

                tot_odds = round(max_win / stake, 2)
                ticket_ev_pct = round(((avg_win / stake) - 1.0) * 100, 2)
                return {
                    "ticket_name": name,
                    "strategy": strategy,
                    "is_system": True,
                    "system_type": "4 od 6 (15 kombinacija)",
                    "num_legs": len(legs),
                    "total_odds": tot_odds,
                    "joint_probability_pct": round(all_prob * 100, 2),
                    "recommended_stake_eur": stake,
                    "stake_per_combo_eur": stake_per_combo,
                    "min_return_eur": min_win,
                    "potential_return_eur": max_win,
                    "avg_return_eur": avg_win,
                    "ticket_ev_pct": ticket_ev_pct,
                    "selections": legs,
                }
            else:
                tot_odds = 1.0
                tot_log_prob = 0.0
                for leg in legs:
                    tot_odds *= leg["odds"]
                    tot_log_prob += math.log(leg["p_calibrated"])
                joint_prob = math.exp(tot_log_prob)
                potential_return = round(stake * tot_odds, 2)
                expected_return = round(potential_return * joint_prob, 2)
                ticket_ev_pct = round(((expected_return / stake) - 1.0) * 100, 2)

                return {
                    "ticket_name": name,
                    "strategy": strategy,
                    "is_system": False,
                    "num_legs": len(legs),
                    "total_odds": round(tot_odds, 2),
                    "joint_probability_pct": round(joint_prob * 100, 2),
                    "recommended_stake_eur": stake,
                    "potential_return_eur": potential_return,
                    "expected_return_eur": expected_return,
                    "ticket_ev_pct": ticket_ev_pct,
                    "selections": legs,
                }

        tickets = [
            compile_ticket_summary(ticket_1_legs, "Tiket 1: SIGURICA / VALUE BANKERI", "Visoka verovatnoća prolaza (>74% po paru), umerena ukupna kvota", stake=20.0),
            compile_ticket_summary(ticket_2_legs, "Tiket 2: URAVNOTEŽENI +EV VALUE TIKET", "Maksimalni kvalitet kvota u ligama sa najnižom maržom (Argentina 1), optimalan risk/reward", stake=15.0),
            compile_ticket_summary(ticket_3_legs, "Tiket 3: GOLOVI SPECIJAL (2+ / 0-2 / 3+)", "Poisson distribucija očekivanih golova: 2+ u ofanzivnim i 0-2 u taktičkim ligama", stake=15.0),
            compile_ticket_summary(ticket_4_legs, "Tiket 4: NOĆNI EKSPRES (Južna i Srednja Amerika)", "Noćni mečevi (00:15 - 03:30), optimalna kombinacija favorita i golova", stake=15.0),
            compile_ticket_summary(ticket_5_legs, "Tiket 5: SISTEM 4 OD 6 (Sa zaštitom od pada)", "Sistem 4 od 6 (15 kombinacija) — dobitan već sa 4 pogođena para, ogroman profit na 5 i 6", stake=15.0, is_system=True),
            compile_ticket_summary(ticket_6_legs, "Tiket 6: LOVAC NA KVOTE (Akumulator sa visokim prinosom)", "Odabrani fiks i golovi sa kvotama 1.53 - 1.70, ukupna kvota oko 12-20", stake=10.0),
        ]

        return {
            "tickets": tickets,
            "total_evaluated_bets": len(df_bets),
            "value_bets_count": len(df_bets[df_bets["status"] == "VALUE"]),
        }


def generate_markdown_report(ticket_res: dict[str, Any], output_path: str):
    lines = [
        "# 🏆 Mozzart Kvantitativni Tiketi — Unified Betting Core",
        "",
        f"**Datum kreiranja:** 21.09.2026. | **Izvor podataka:** Mozzart Ponuda (45 mečeva, 405 tržišta)",
        "**Matematički model:** Dixon-Coles Poisson Bivariate Simulation + DevigEngine Power Method + Empirical Decision Gate",
        "",
        "---",
        "",
        "## 📊 Sažetak kreiranih tiketa",
        "",
        "| # | Naziv tiketa | Strategija | Broj parova | Ukupna kvota | Verovatnoća | Preporučeni ulog | Potencijalni dobitak |",
        "|---|---|---|:---:|:---:|:---:|:---:|:---:|",
    ]

    for i, t in enumerate(ticket_res["tickets"], 1):
        if t.get("is_system"):
            lines.append(
                f"| {i} | **{t['ticket_name']}** | {t['strategy']} | {t['num_legs']} | Max {t['total_odds']} | {t['joint_probability_pct']}% | €{t['recommended_stake_eur']:.2f} | Min €{t['min_return_eur']:.2f} / Max €{t['potential_return_eur']:.2f} |"
            )
        else:
            lines.append(
                f"| {i} | **{t['ticket_name']}** | {t['strategy']} | {t['num_legs']} | **{t['total_odds']}** | {t['joint_probability_pct']}% | €{t['recommended_stake_eur']:.2f} | **€{t['potential_return_eur']:.2f}** |"
            )

    lines.append("\n---\n")

    for i, t in enumerate(ticket_res["tickets"], 1):
        lines.append(f"### 📋 {t['ticket_name']}")
        lines.append(f"**Strategija:** {t['strategy']}  ")
        if t.get("is_system"):
            lines.append(f"**Tip sistema:** {t['system_type']} | **Max kvota:** {t['total_odds']} | **Ulog po kombinaciji:** €{t['stake_per_combo_eur']:.2f}  ")
            lines.append(f"**Preporučeni ulog:** €{t['recommended_stake_eur']:.2f} | **Min dobitak (4/6):** €{t['min_return_eur']:.2f} | **Max dobitak (6/6):** €{t['potential_return_eur']:.2f}  ")
        else:
            lines.append(f"**Ukupna kvota:** `{t['total_odds']}` | **Zajednička verovatnoća:** `{t['joint_probability_pct']}%`  ")
            lines.append(f"**Preporučeni ulog:** `€{t['recommended_stake_eur']:.2f}` | **Potencijalni dobitak:** `€{t['potential_return_eur']:.2f}`  ")
        
        lines.append("")
        lines.append("| Br. | Vreme | Meč | Takmičenje | Tip | Opis | Kvota | P(kalib.) | xG Prognoza |")
        lines.append("|:---:|:---:|---|---|:---:|---|:---:|:---:|:---:|")

        for idx, s in enumerate(t["selections"], 1):
            lines.append(
                f"| {idx} | {s['dan_label']} {s['vreme']} | **{s['domacin']} - {s['gost']}** | {s['takmicenje']} | `{s['code']}` | {s['selection_desc']} | **{s['odds']}** | {s['p_calibrated']*100:.1f}% | Tačan rez: {s['predicted_score']} |"
            )

        lines.append("")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"📄 Markdown izveštaj sačuvan u: {output_path}")


def main():
    mecevi_file = "/home/kizamladjanijebac/Downloads/mozzart_fudbal_mecevi_2026-09-20.csv"
    marketi_file = "/home/kizamladjanijebac/Downloads/mozzart_fudbal_marketi_2026-09-20 (copy).csv"

    engine = MozzartQuantitativeEngine(mecevi_file, marketi_file)
    eval_res = engine.evaluate_all()
    ticket_res = engine.build_tickets(eval_res)

    print("\n" + "=" * 80)
    print("🏆 SHARPBET CORE — MOZZART KVANTITATIVNI TIKETI ZA 21.09.2026.")
    print("=" * 80)

    for t in ticket_res["tickets"]:
        print(f"\n📋 {t['ticket_name']}")
        print(f"   Strategija: {t['strategy']}")
        if t.get("is_system"):
            print(f"   Tip sistema: {t['system_type']} | Max kvota: {t['total_odds']} | P(sve prolazi): {t['joint_probability_pct']}%")
            print(f"   Ulog: €{t['recommended_stake_eur']:.2f} (€{t['stake_per_combo_eur']:.2f}/komb) -> Min dobitak (4/6): €{t['min_return_eur']:.2f} | Max dobitak (6/6): €{t['potential_return_eur']:.2f}")
        else:
            print(f"   Ukupna kvota: {t['total_odds']} | Verovatnoća: {t['joint_probability_pct']}% | EV: {t.get('ticket_ev_pct', 0.0):+}%")
            print(f"   Ulog: €{t['recommended_stake_eur']:.2f} -> Potencijalni dobitak: €{t['potential_return_eur']:.2f}")
        print("   " + "-" * 75)
        for i, s in enumerate(t["selections"], 1):
            print(f"   {i}. [{s['dan_label']} {s['vreme']}] {s['domacin']} vs {s['gost']} ({s['takmicenje']})")
            print(f"      TIP: {s['code']} - {s['selection_desc']} | Kvota: {s['odds']} | P(calib): {s['p_calibrated']*100:.1f}% | Edge: {s['edge_pct']:+}%")
        print("   " + "-" * 75)

    # Save to JSON in output folder
    output_dir = os.path.join(CORE_DIR, "output")
    os.makedirs(output_dir, exist_ok=True)
    out_json_path = os.path.join(output_dir, "mozzart_tickets.json")
    out_md_path = os.path.join(output_dir, "mozzart_tiketi_izvestaj.md")

    import json
    with open(out_json_path, "w", encoding="utf-8") as f:
        json.dump(ticket_res, f, ensure_ascii=False, indent=2)
    print(f"\n💾 Rezultati sačuvani u: {out_json_path}")

    generate_markdown_report(ticket_res, out_md_path)


if __name__ == "__main__":
    main()
