"""
Unit Tests for SharpBet Core v12: Halftime Goals & Quantitative Ticket Engine.
Tests probability calculus, Mozzart market settlement rules, and rolling feature integrity.
"""

import math
import pytest
import numpy as np
import pandas as pd
from scipy.stats import poisson

from unified_betting_core.training.model_trainer import evaluate_selection_outcome


class TestMozzartHalftimeSettlement:
    """
    Tests settlement logic for complex Mozzart halftime and combination markets.
    """

    def test_halftime_over_05(self):
        # FT 2-1, HT 1-0 -> tot_ht = 1 -> Won
        assert evaluate_selection_outcome("halftime_goals", "I1+", home_goals=2, away_goals=1, ht_home_goals=1, ht_away_goals=0) == 1
        # FT 2-0, HT 0-0 -> tot_ht = 0 -> Lost
        assert evaluate_selection_outcome("halftime_goals", "I1+", home_goals=2, away_goals=0, ht_home_goals=0, ht_away_goals=0) == 0

    def test_halftime_over_15(self):
        # FT 2-1, HT 1-1 -> tot_ht = 2 -> Won
        assert evaluate_selection_outcome("halftime_goals", "I2+", home_goals=2, away_goals=1, ht_home_goals=1, ht_away_goals=1) == 1
        # FT 3-0, HT 1-0 -> tot_ht = 1 -> Lost
        assert evaluate_selection_outcome("halftime_goals", "I2+", home_goals=3, away_goals=0, ht_home_goals=1, ht_away_goals=0) == 0

    def test_halftime_range_1_2(self):
        # HT 1-0 -> 1 goal -> Won
        assert evaluate_selection_outcome("halftime_goals", "I 1-2", home_goals=2, away_goals=0, ht_home_goals=1, ht_away_goals=0) == 1
        # HT 1-1 -> 2 goals -> Won
        assert evaluate_selection_outcome("halftime_goals", "I 1-2", home_goals=3, away_goals=1, ht_home_goals=1, ht_away_goals=1) == 1
        # HT 0-0 -> 0 goals -> Lost
        assert evaluate_selection_outcome("halftime_goals", "I 1-2", home_goals=1, away_goals=0, ht_home_goals=0, ht_away_goals=0) == 0
        # HT 2-1 -> 3 goals -> Lost
        assert evaluate_selection_outcome("halftime_goals", "I 1-2", home_goals=4, away_goals=2, ht_home_goals=2, ht_away_goals=1) == 0

    def test_goals_both_halves(self):
        # HT 1-0 (tot_ht=1), FT 2-1 (tot_sh=2) -> Both halves >= 1 -> Won
        assert evaluate_selection_outcome("goals_both_halves", "I1+&II1+", home_goals=2, away_goals=1, ht_home_goals=1, ht_away_goals=0) == 1
        # HT 0-0, FT 2-0 (tot_ht=0, tot_sh=2) -> 1st half had 0 -> Lost
        assert evaluate_selection_outcome("goals_both_halves", "I1+&II1+", home_goals=2, away_goals=0, ht_home_goals=0, ht_away_goals=0) == 0
        # HT 2-0, FT 2-0 (tot_ht=2, tot_sh=0) -> 2nd half had 0 -> Lost
        assert evaluate_selection_outcome("goals_both_halves", "I1+&II1+", home_goals=2, away_goals=0, ht_home_goals=2, ht_away_goals=0) == 0

    def test_half_with_more_goals(self):
        # HT 0-0, FT 2-1 -> 1H=0, 2H=3 -> 2H > 1H (I<II) -> Won
        assert evaluate_selection_outcome("half_with_more_goals", "I<II", home_goals=2, away_goals=1, ht_home_goals=0, ht_away_goals=0) == 1
        # HT 2-0, FT 2-1 -> 1H=2, 2H=1 -> 1H > 2H (I>II) -> Won
        assert evaluate_selection_outcome("half_with_more_goals", "I>II", home_goals=2, away_goals=1, ht_home_goals=2, ht_away_goals=0) == 1
        # HT 1-0, FT 1-1 -> 1H=1, 2H=1 -> 1H == 2H (I=II) -> Won
        assert evaluate_selection_outcome("half_with_more_goals", "I=II", home_goals=1, away_goals=1, ht_home_goals=1, ht_away_goals=0) == 1

    def test_combination_home_win_and_1h_goal(self):
        # Home Win (3-1) and 1H goal (HT 1-0) -> Won
        assert evaluate_selection_outcome("combo_result_ht_goals", "1&I1+", home_goals=3, away_goals=1, ht_home_goals=1, ht_away_goals=0) == 1
        # Home Win (1-0) but 1H had 0 goals (HT 0-0) -> Lost
        assert evaluate_selection_outcome("combo_result_ht_goals", "1&I1+", home_goals=1, away_goals=0, ht_home_goals=0, ht_away_goals=0) == 0
        # Draw (1-1) with 1H goal (HT 1-0) -> Lost (not home win)
        assert evaluate_selection_outcome("combo_result_ht_goals", "1&I1+", home_goals=1, away_goals=1, ht_home_goals=1, ht_away_goals=0) == 0


class TestHalftimeCalculusAndKelly:
    """
    Tests mathematical integrity of 1H Dixon-Coles Poisson matrix and fractional Kelly sizing.
    """

    def test_dixon_coles_1h_matrix_probabilities(self):
        # Baseline 1H intensities
        lh_1h = 0.65
        la_1h = 0.45
        rho_1h = -0.15

        # Tau adjustment matrix
        def tau(x, y):
            if x == 0 and y == 0:
                return 1.0 - lh_1h * la_1h * rho_1h
            elif x == 0 and y == 1:
                return 1.0 + lh_1h * rho_1h
            elif x == 1 and y == 0:
                return 1.0 + la_1h * rho_1h
            elif x == 1 and y == 1:
                return 1.0 - rho_1h
            return 1.0

        grid = np.zeros((6, 6))
        for x in range(6):
            for y in range(6):
                grid[x, y] = poisson.pmf(x, lh_1h) * poisson.pmf(y, la_1h) * tau(x, y)

        # Normalize grid
        grid_sum = np.sum(grid)
        assert abs(grid_sum - 1.0) < 0.05, f"Grid sum should be close to 1.0 before normalization, got {grid_sum}"
        grid /= grid_sum

        p_0_0 = grid[0, 0]
        p_over_05 = 1.0 - p_0_0

        # In football, 0-0 at HT is around 25% - 40%
        assert 0.25 <= p_0_0 <= 0.45
        assert abs((p_0_0 + p_over_05) - 1.0) < 1e-9

    def test_fractional_kelly_multi_bet(self):
        # Odds: 3.50, Fair Prob: 0.35 -> +EV = 0.35 * 3.5 - 1 = +22.5%
        p = 0.35
        odds = 3.50
        b = odds - 1.0
        full_kelly = (p * (b + 1) - 1) / b
        assert full_kelly > 0

        # Fractional Kelly (1/20th)
        fractional_kelly = full_kelly / 20.0
        capped_stake = min(fractional_kelly, 0.0075)  # 0.75% cap

        assert 0.0 < capped_stake <= 0.0075
