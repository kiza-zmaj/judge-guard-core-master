import unittest

from unified_betting_core.models.calibration import ModelCalibration


class TestModelCalibration(unittest.TestCase):
    def test_empty_input_handled_safely(self):
        # Passing empty list should return None ECE, not 0.00%
        result = ModelCalibration.calculate_ece([], [])
        self.assertIsNone(result["ece"])
        self.assertIsNone(result["ece_pct"])
        self.assertEqual(result["error"], "EMPTY_INPUT — ECE not measurable")

    def test_multiclass_ece_empty_input(self):
        # Empty predictions list for multiclass ECE
        result = ModelCalibration.calculate_multiclass_ece([], [])
        self.assertIsNone(result["ece_multiclass"])
        self.assertIsNone(result["ece_pct"])
        self.assertEqual(result["error"], "EMPTY_INPUT — ECE not measurable")

    def test_multiclass_ece_missing_outcomes(self):
        # Test where some predictions are missing outcome keys
        preds = [
            {"home": 0.5, "draw": 0.3, "away": 0.2},
            {"home": 0.1},  # missing draw and away
            {},  # empty dict
        ]
        actuals = ["home", "draw", "away"]

        result = ModelCalibration.calculate_multiclass_ece(preds, actuals)
        self.assertIsNotNone(result["ece_multiclass"])
        # ECE should still compute using default 0.0 probability for missing keys

    def test_brier_score_empty_input(self):
        # Brier score should return fallback 0.6667 for empty inputs
        result = ModelCalibration.calculate_brier_score([], [])
        self.assertEqual(result["brier_score"], 0.6667)
        self.assertEqual(result["error"], "EMPTY_OR_MISMATCHED_INPUT")

    def test_evaluate_gate_rejects_empty(self):
        # The main gate should FAIL gracefully when given no out-of-sample data
        verdict = ModelCalibration.evaluate_out_of_sample_gate([], [])
        self.assertFalse(verdict.passed)
        self.assertEqual(verdict.status, "CALIBRATION_FAILED")
        self.assertTrue(
            any("Insufficient OOS sample" in r for r in verdict.failure_reasons)
        )
        self.assertTrue(
            any("ECE could not be computed" in r for r in verdict.failure_reasons)
        )
        self.assertIsNone(verdict.ece_pct)

    def test_evaluate_gate_rejects_few_samples(self):
        # The main gate requires at least min_sample_size (default 100)
        preds = [{"home": 0.33, "draw": 0.33, "away": 0.34}] * 50
        actuals = ["home"] * 50

        verdict = ModelCalibration.evaluate_out_of_sample_gate(
            preds, actuals, min_sample_size=100
        )
        self.assertFalse(verdict.passed)
        self.assertEqual(verdict.status, "CALIBRATION_FAILED")
        self.assertTrue(
            any("Insufficient OOS sample" in r for r in verdict.failure_reasons)
        )


if __name__ == "__main__":
    unittest.main()
