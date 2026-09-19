"""
Antigravity (Gemini) AI integration helper for AURI.
Replaces Claude with Google Gemini as the LLM backend.
Uses the same GeminiClient from the antigravity_core package
with multi-key rotation and retry logic.
"""

import os
import sys
import logging
from typing import Optional

# Add project root to path so we can import antigravity_core
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

# Load .env
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(_PROJECT_ROOT, ".env"))
except ImportError:
    pass

import google.generativeai as genai

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# System prompt for AURI personality
# ---------------------------------------------------------------------------
AURI_SYSTEM_PROMPT = (
    "Você é a Auri, uma assistente virtual inteligente, amigável e prestativa. "
    "Responda de forma concisa e natural em português brasileiro. "
    "Seja calorosa mas profissional. Limite respostas a 2-3 frases quando possível. "
    "Evite usar markdown, emojis ou formatação complexa pois suas respostas serão "
    "faladas em voz alta. Use linguagem coloquial e acessível."
)

FALLBACK_RESPONSES = [
    "Desculpa, tive um probleminha. Pode tentar de novo?",
    "Ops, algo deu errado do meu lado. Pode repetir a pergunta?",
    "Não consegui processar agora. Tente novamente em alguns segundos.",
]

# ---------------------------------------------------------------------------
# Gemini client (singleton)
# ---------------------------------------------------------------------------
_gemini_model = None


def _get_gemini_model():
    """Get or create the Gemini GenerativeModel instance with key rotation."""
    global _gemini_model
    if _gemini_model is not None:
        return _gemini_model

    keys_env = os.environ.get("GEMINI_API_KEYS", "")
    if not keys_env:
        keys_env = os.environ.get("GEMINI_API_KEY", "")

    if not keys_env:
        raise ValueError("GEMINI_API_KEYS or GEMINI_API_KEY must be set in environment")

    api_keys = [k.strip() for k in keys_env.split(",") if k.strip()]
    model_name = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

    # Configure with first key
    genai.configure(api_key=api_keys[0])

    _gemini_model = genai.GenerativeModel(
        model_name,
        system_instruction=AURI_SYSTEM_PROMPT,
    )

    masked = api_keys[0][:4] + "..." + api_keys[0][-4:] if len(api_keys[0]) > 8 else "****"
    logger.info("Antigravity (Gemini) configured: model=%s, key=%s, total_keys=%d",
                model_name, masked, len(api_keys))

    return _gemini_model


# ---------------------------------------------------------------------------
# Message formatting
# ---------------------------------------------------------------------------
def build_messages(
    query: str,
    history: list[dict],
) -> list[dict]:
    """
    Build the messages/contents array for Gemini API.

    Gemini uses 'user' and 'model' roles (not 'assistant').
    """
    contents = []

    for msg in history:
        role = msg.get("role", "")
        content = msg.get("content", "")
        if not content:
            continue

        # Map 'assistant' -> 'model' for Gemini
        if role == "assistant":
            role = "model"
        elif role != "user":
            continue

        contents.append({"role": role, "parts": [content]})

    contents.append({"role": "user", "parts": [query]})
    return contents


# ---------------------------------------------------------------------------
# Main API call
# ---------------------------------------------------------------------------
def get_gemini_response(
    query: str,
    history: list[dict],
    system_prompt: str = AURI_SYSTEM_PROMPT,
    max_tokens: int = 512,
) -> str:
    """
    Get a response from Gemini (Antigravity) API.

    Args:
        query: The user's question or request.
        history: Conversation history (list of {role, content} dicts).
        system_prompt: System prompt defining AURI's personality.
        max_tokens: Maximum tokens in the response.

    Returns:
        Gemini's response text, or a fallback message on error.
    """
    try:
        model = _get_gemini_model()
        contents = build_messages(query, history)

        response = model.generate_content(
            contents,
            generation_config={"max_output_tokens": max_tokens},
        )

        if not response.candidates:
            logger.warning("Gemini returned no candidates")
            return FALLBACK_RESPONSES[0]

        reply = response.text
        logger.info("Antigravity response received (tokens used in response)")
        return reply

    except Exception as e:
        error_str = str(e)
        if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
            logger.error("Gemini API rate limit exceeded: %s", error_str[:100])
            return FALLBACK_RESPONSES[1]
        logger.error("Unexpected error calling Gemini: %s", e, exc_info=True)
        return FALLBACK_RESPONSES[0]


# Keep backward compat alias
get_claude_response = get_gemini_response
