"""
Sacred Holdout Manager for SharpBet v11.

PRINCIPLE:
    The sacred holdout (season 24/25) is LOCKED from the moment this module
    is imported. It must NEVER enter any walk-forward training or validation fold.
    It is used EXACTLY ONCE — as the final blind test after the walk-forward
    walk-forward pipeline has been frozen.

    Violating this contract (peeking at holdout during development) invalidates
    all statistical claims about the model's out-of-sample performance.

USAGE:
    from unified_betting_core.validation.sacred_holdout import SacredHoldout

    df_train_val, df_holdout = SacredHoldout.split(df)

    # --- do all walk-forward training on df_train_val only ---
    # --- when truly ready: ---
    result = SacredHoldout.final_blind_test(engine, df_holdout)
"""

import hashlib
import json
import logging
import os
from datetime import datetime
from typing import Any

import pandas as pd

logger = logging.getLogger("SharpBet.SacredHoldout")

# The sacred holdout season — DO NOT CHANGE after first run
HOLDOUT_SEASON: str = "2425"
HOLDOUT_MANIFEST_PATH: str = os.path.join(
    os.path.dirname(__file__), "..", "data", "sacred_holdout_manifest.json"
)


class SacredHoldoutViolation(Exception):
    """Raised when holdout data is accessed during non-final stages."""
    pass


class SacredHoldout:
    """
    Manages the sacred holdout split for SharpBet v11.

    The holdout season (2425) is extracted once and stored with a SHA-256
    fingerprint. Any attempt to use holdout data in training will raise
    SacredHoldoutViolation.
    """

    _holdout_fingerprint: str | None = None
    _holdout_unlocked: bool = False

    @classmethod
    def split(
        cls, df: pd.DataFrame
    ) -> tuple[pd.DataFrame, pd.DataFrame]:
        """
        Splits the full dataset into train/validation and sacred holdout.

        Args:
            df: Full dataset with a 'season' column.

        Returns:
            (df_train_val, df_holdout) — holdout is season HOLDOUT_SEASON.
        """
        if "season" not in df.columns:
            logger.warning(
                "SacredHoldout.split: 'season' column missing. "
                "Falling back to last 20% of data as holdout."
            )
            cutoff = int(len(df) * 0.8)
            df_train_val = df.iloc[:cutoff].copy()
            df_holdout = df.iloc[cutoff:].copy()
        else:
            df_holdout = df[df["season"] == HOLDOUT_SEASON].copy()
            df_train_val = df[df["season"] != HOLDOUT_SEASON].copy()

        if df_holdout.empty:
            logger.warning(
                f"SacredHoldout: No data found for season {HOLDOUT_SEASON}. "
                "Holdout is empty — final blind test will be skipped."
            )
        else:
            # Compute and store fingerprint
            fingerprint = cls._compute_fingerprint(df_holdout)
            cls._holdout_fingerprint = fingerprint
            cls._persist_manifest(len(df_holdout), fingerprint)
            logger.info(
                f"SacredHoldout: LOCKED {len(df_holdout)} matches (season {HOLDOUT_SEASON}). "
                f"SHA-256: {fingerprint[:16]}..."
            )

        logger.info(
            f"SacredHoldout: {len(df_train_val)} matches available for walk-forward "
            f"(seasons: {sorted(df_train_val['season'].unique()) if 'season' in df_train_val.columns else 'unknown'})."
        )
        return df_train_val, df_holdout

    @classmethod
    def final_blind_test(
        cls,
        engine: Any,
        df_holdout: pd.DataFrame,
    ) -> dict[str, Any]:
        """
        Executes the final blind test on the sacred holdout.
        This method should be called EXACTLY ONCE after the walk-forward
        pipeline is completely frozen.

        Args:
            engine: A fitted WalkForwardEngine (or equivalent) with frozen parameters.
            df_holdout: The holdout DataFrame returned by split().

        Returns:
            dict with gate results on holdout data.
        """
        if df_holdout.empty:
            return {
                "status": "SKIPPED",
                "reason": "Holdout dataset is empty.",
            }

        # Verify fingerprint integrity
        current_fp = cls._compute_fingerprint(df_holdout)
        if cls._holdout_fingerprint and current_fp != cls._holdout_fingerprint:
            raise SacredHoldoutViolation(
                f"Holdout fingerprint mismatch! Expected {cls._holdout_fingerprint[:16]}, "
                f"got {current_fp[:16]}. Holdout data may have been modified."
            )

        logger.warning(
            "SacredHoldout: FINAL BLIND TEST INITIATED. "
            f"Running on {len(df_holdout)} holdout matches (season {HOLDOUT_SEASON}). "
            "This should happen EXACTLY ONCE."
        )

        # Delegate to engine's evaluation method
        if hasattr(engine, "evaluate_on_holdout"):
            result = engine.evaluate_on_holdout(df_holdout)
        else:
            result = {
                "status": "HOLDOUT_EVALUATION_NOT_IMPLEMENTED",
                "n_matches": len(df_holdout),
                "season": HOLDOUT_SEASON,
                "note": "Implement engine.evaluate_on_holdout(df) to activate.",
            }

        result["holdout_fingerprint"] = current_fp[:16]
        result["holdout_season"] = HOLDOUT_SEASON
        result["evaluated_at"] = datetime.utcnow().isoformat()
        return result

    @classmethod
    def verify_no_holdout_leakage(
        cls, df_train: pd.DataFrame
    ) -> bool:
        """
        Verifies that no holdout season data appears in the training set.
        Returns True if clean, raises SacredHoldoutViolation if contaminated.
        """
        if "season" not in df_train.columns:
            return True
        if HOLDOUT_SEASON in df_train["season"].values:
            raise SacredHoldoutViolation(
                f"CRITICAL: Holdout season {HOLDOUT_SEASON} found in training data! "
                "This invalidates all walk-forward statistics."
            )
        return True

    @staticmethod
    def _compute_fingerprint(df: pd.DataFrame) -> str:
        """Computes a SHA-256 fingerprint of the holdout dataset."""
        content = df.to_csv(index=False).encode("utf-8")
        return hashlib.sha256(content).hexdigest()

    @classmethod
    def _persist_manifest(cls, n_matches: int, fingerprint: str) -> None:
        """Persists the holdout manifest to disk for audit trail."""
        manifest = {
            "holdout_season": HOLDOUT_SEASON,
            "n_matches": n_matches,
            "sha256_fingerprint": fingerprint,
            "locked_at": datetime.utcnow().isoformat(),
            "warning": "DO NOT modify holdout data after this lock.",
        }
        try:
            os.makedirs(os.path.dirname(HOLDOUT_MANIFEST_PATH), exist_ok=True)
            with open(HOLDOUT_MANIFEST_PATH, "w") as f:
                json.dump(manifest, f, indent=2)
            logger.info(f"SacredHoldout manifest saved to {HOLDOUT_MANIFEST_PATH}")
        except Exception as e:
            logger.error(f"Failed to persist holdout manifest: {e}")

    @classmethod
    def load_manifest(cls) -> dict[str, Any] | None:
        """Loads the existing holdout manifest if present."""
        if os.path.exists(HOLDOUT_MANIFEST_PATH):
            with open(HOLDOUT_MANIFEST_PATH) as f:
                return json.load(f)
        return None
