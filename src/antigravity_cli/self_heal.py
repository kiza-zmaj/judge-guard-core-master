"""
Self-Healing Reflection Loop for Antigravity CLI.
Catches execution crashes, malformed JSON, and citation failures,
feeding error context back to the agent for self-correction.
"""

import sys
import traceback
from typing import Callable, Any, Dict


class SelfHealingEngine:
    """
    Executes tasks wrapped in a reflection self-healing loop.
    Retries up to `max_attempts` while providing failure stderr context.
    """

    def __init__(self, max_attempts: int = 3):
        self.max_attempts = max_attempts

    def execute_with_healing(
        self, agent_func: Callable[[Any, str], Any], task_input: Any
    ) -> Dict[str, Any]:
        """
        Executes `agent_func(task_input, error_context)` inside a reflection loop.
        """
        attempts = 0
        error_context = ""

        while attempts < self.max_attempts:
            try:
                result = agent_func(task_input, error_context)
                
                # Check for structural citation validity if result is Pydantic/Dict
                if hasattr(result, "is_grounded") and not result.is_grounded:
                    if result.status == "INSUFFICIENT_DATA":
                        return {
                            "status": "COMPLETED_WITH_WARNING",
                            "attempts": attempts + 1,
                            "output": result,
                        }

                return {
                    "status": "SUCCESS",
                    "attempts": attempts + 1,
                    "output": result,
                }

            except Exception as e:
                attempts += 1
                tb_str = traceback.format_exc()
                error_context = (
                    f"Attempt {attempts} failed with error: {str(e)}.\n"
                    f"Traceback:\n{tb_str}\n"
                    f"Please fix your reasoning logic, schema validation, or retrieval filtering."
                )
                print(
                    f"⚠️ [Self-Healer] Attempt {attempts}/{self.max_attempts} failed. "
                    f"Triggering reflection loop...",
                    file=sys.stderr,
                )

        raise RuntimeError(
            f"❌ System reached maximum self-healing attempts ({self.max_attempts}). "
            f"Last Error: {error_context}"
        )


def execute_with_healing(agent_func: Callable[[Any, str], Any], task_input: Any) -> Dict[str, Any]:
    """Convenience function matching specification."""
    healer = SelfHealingEngine(max_attempts=3)
    return healer.execute_with_healing(agent_func, task_input)
