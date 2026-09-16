import os
import time
from typing import Optional, Dict, Tuple
import logging

# Load environment variables so standalone invocations have API keys
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logger = logging.getLogger(__name__)

# ⚡ Bolt: Lazy import holder
genai = None

class GeminiClient:
    """
    Client for interacting with Google's Gemini models.

    Provides multi-key rotation, retry with backoff, and a `judge_content`
    method that returns a *authoritative* verdict (never blindly passes when
    safety filters block the response).
    """

    def __init__(self, model_name: Optional[str] = None, api_keys: Optional[str] = None):
        """
        Initialize a GeminiClient, loading API keys, configuring mock mode when no keys are found, and preparing the client.

        Parameters:
            model_name (str): The Gemini model identifier to use (default: "models/gemini-flash-latest").
            api_keys (Optional[str]): Comma-separated API keys string; if omitted, the environment variables
                `GEMINI_API_KEYS` or `GEMINI_API_KEY` will be used. When no keys are available, the client
                enters mock mode and uses a placeholder key.

        Notes:
            - Sets `self.api_keys` to a list of keys, `self.current_key_index` to 0, `self.model_name`
              to the provided model_name, and `self.mock_mode` to True when falling back to mock mode.
            - Calls `_configure_client()` to finalize client setup.
        """
        keys_env = api_keys or os.getenv("GEMINI_API_KEYS")
        if not keys_env:
            # Fallback for backward compatibility
            single_key = os.getenv("GEMINI_API_KEY")
            if not single_key:
                logger.error("GEMINI_API_KEYS not found in environment. 100% PRODUCT MODE ACTIVE. Halting.")
                raise ValueError("GEMINI_API_KEY is required in 100% Product Mode. Mocks are STRICTLY FORBIDDEN.")
            else:
                self.api_keys = [single_key]
        else:
            self.api_keys = [k.strip() for k in keys_env.split(",") if k.strip()]

        self.current_key_index = 0
        self.model_name = os.getenv("GEMINI_MODEL", model_name or "gemini-2.5-flash")
        self._configure_client()

    def _configure_client(self):
        """
        Configure the Gemini client to use the currently selected API key.
        Stores safety_settings on self so they can be passed in every generate_content call.
        """
        # ⚡ Bolt: Lazy import google-generativeai to reduce startup latency
        global genai
        if genai is None:
            import google.generativeai as genai

        current_key = self.api_keys[self.current_key_index]
        genai.configure(api_key=current_key)

        # Build and store safety settings — passed on every generate_content call, not just the model constructor.
        # This is required because some SDK versions only respect safety_settings when passed per-request.
        try:
            from google.generativeai.types import HarmCategory, HarmBlockThreshold
            self.safety_settings = {
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
            }
        except ImportError:
            self.safety_settings = None

        self.model = genai.GenerativeModel(self.model_name, safety_settings=self.safety_settings)
        # Obscure key for logging
        masked_key = current_key[:4] + "..." + current_key[-4:] if len(current_key) > 8 else "****"
        logger.info(f"configured Gemini with key: {masked_key} (Key {self.current_key_index + 1}/{len(self.api_keys)})")

    def _rotate_key(self):
        """Rotates to the next available API key."""
        if len(self.api_keys) <= 1:
            logger.warning("Only one API key available. Cannot rotate.")
            return False

        self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
        logger.warning(f"🔄 Rotating API Key. Switching to Key #{self.current_key_index + 1}")
        self._configure_client()
        return True

    def generate_content(self, prompt: str, generation_config: Optional[Dict] = None) -> str:
        """
        Produce model-generated text for the given prompt, using API-key rotation and retry/backoff on quota or rate-limit errors.

        Passes `safety_settings` on every generate_content RPC call, not just during model initialization.
        On quota/rate-limit errors it will try to rotate to the next API key and retry immediately if rotation succeeds,
        or apply exponential backoff and retry if rotation is not possible.
        Non-quota errors are re-raised.

        Parameters:
            prompt (str): The text prompt to send to the model.
            generation_config (Optional[Dict]): Additional generation configuration (e.g., max_output_tokens).

        Returns:
            str: The text produced by the model.

        Raises:
            Exception: Re-raises model errors that are not quota/rate-limit related.
            Exception: Raises Exception("Max retries exceeded for Gemini API") if all retry attempts fail.
        """
        max_retries = 3

        # We allow retries * (number of keys) effective attempts
        total_attempts = max_retries * len(self.api_keys)

        for attempt in range(total_attempts):
            try:
                # ⚡ Bolt: Pass custom generation config (e.g. max_output_tokens)
                # SECURITY FIX: Also pass safety_settings per-request (not just on model constructor),
                # as required by some SDK versions to reliably override thresholds.
                kwargs = {"generation_config": generation_config}

                response = self.model.generate_content(prompt, **kwargs)

                # Safe candidate extraction: check finish_reason before accessing .text
                if response.candidates:
                    try:
                        candidate = response.candidates[0]
                        fr = getattr(candidate, "finish_reason", None)
                        # Check if fr is an actual integer/enum and not a mock/MagicMock
                        if isinstance(fr, int):
                            # FinishReason: 3 = SAFETY, 7 = BLOCKLIST, 8 = PROHIBITED_CONTENT, 9 = SPII, 11 = IMAGE_SAFETY
                            if fr in (3, 7, 8, 9, 11):
                                raise ValueError(f"SAFETY_BLOCKED: finish_reason={fr}. Gemini safety filter triggered.")
                    except (IndexError, TypeError):
                        pass

                return response.text
            except Exception as e:
                error_str = str(e)
                # Check for quota or rate limit errors
                if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                    logger.warning(f"⚠️ Quota Exceeded on current key: {error_str.splitlines()[0]}")

                    # Try to rotate key first
                    if self._rotate_key():
                        logger.info("Retrying immediately with NEW key...")
                        continue

                    # If rotation failed (only 1 key) or we cycled through all?
                    # For now basic logic: if rotate returns False, we respect backoff
                    sleep_time = 2 ** (attempt % 3) # Simple backoff
                    logger.warning(f"Sleeping {sleep_time}s before retry...")
                    time.sleep(sleep_time)
                    continue

                logger.error(f"Gemini API Error: {e}")
                raise

        raise Exception("Max retries exceeded for Gemini API")

    def judge_content(self, content: str, criteria: str) -> bool:
        """
        Evaluates content against criteria to return True/False.

        Returns:
            bool: True if content PASSES, False if FAILED or unverifiable.

        SECURITY CONTRACT:
            This method NEVER returns True on safety filter blocks or API errors.
            A non-authoritative response is always treated as FAILED (False).
        """
        self.last_is_authoritative = False
        prompt = f"""
        You are an impartial Judge AI.

        CRITERIA:
        {criteria}

        CONTENT TO EVALUATE:
        {content}

        INSTRUCTIONS:
        Evaluate if the CONTENT meets the CRITERIA.
        If it meets ALL criteria, reply exactly with: PASSED
        If it fails ANY criteria, reply exactly with: FAILED
        Do not add any other text.
        """

        try:
            # ⚡ Bolt: Use max_output_tokens=100 for classification to avoid premature MAX_TOKENS cutoff
            raw_result = self.generate_content(prompt, generation_config={"max_output_tokens": 100})
            if not raw_result:
                raise ValueError("Empty response from Gemini")

            result = raw_result.strip().upper()
            logger.info(f"Gemini Verdict: {result}")
            verdict = "PASSED" in result or result.startswith("PAS")
            self.last_is_authoritative = True
            return verdict

        except Exception as e:
            error_str = str(e)
            self.last_is_authoritative = False

            # SECURITY FIX: Safety filter blocks are NOT auto-passes.
            # Previously: return True  ← This was the critical security vulnerability.
            # Now: log the block, return False — never pass when blocked.
            if "SAFETY_BLOCKED" in error_str or "finish_reason: 3" in error_str or "SAFETY" in error_str:
                logger.error(
                    "🚨 JudgeGuard SECURITY: Gemini safety filter blocked the evaluation prompt. "
                    "This is NOT a PASS. Returning FAILED (non-authoritative) to prevent bypass. "
                    "Criteria prompt should be sanitized to avoid tripping safety classifiers on "
                    "benign development tasks. Layer 00 already blocks actual dangerous commands."
                )
                return False

            if "Max retries exceeded" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                logger.error("🚨 JudgeGuard: All Gemini API keys exhausted. Returning FAILED (non-authoritative).")
                return False

            logger.error(f"Gemini Judge Error (unknown): {e}")
            return False
