"""
Claude API integration helper for AURI.
Handles communication with Anthropic's Claude API including
message formatting, error handling, and fallback responses.
"""

import os
import json
import logging
from typing import Optional

import boto3
import anthropic

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
# Secret retrieval
# ---------------------------------------------------------------------------
_cached_api_key: Optional[str] = None


def _get_anthropic_api_key() -> str:
    """Retrieve Anthropic API key from environment or AWS Secrets Manager."""
    global _cached_api_key
    if _cached_api_key:
        return _cached_api_key

    # Try environment variable first
    key = os.environ.get("ANTHROPIC_API_KEY")
    if key:
        _cached_api_key = key
        return key

    # Fall back to Secrets Manager
    try:
        client = boto3.client(
            "secretsmanager",
            region_name=os.environ.get("AWS_REGION", "us-east-1"),
        )
        response = client.get_secret_value(SecretId="auri/anthropic-key")
        secret = json.loads(response["SecretString"])
        _cached_api_key = secret["ANTHROPIC_API_KEY"]
        return _cached_api_key
    except Exception as e:
        logger.error("Failed to retrieve API key from Secrets Manager: %s", e)
        raise


# ---------------------------------------------------------------------------
# Message formatting
# ---------------------------------------------------------------------------
def build_messages(
    query: str,
    history: list[dict],
) -> list[dict]:
    """
    Build the messages array for the Claude API call.

    Args:
        query: The current user query.
        history: Previous conversation messages.

    Returns:
        Formatted messages list for Claude API.
    """
    messages = []

    for msg in history:
        if msg.get("role") in ("user", "assistant") and msg.get("content"):
            messages.append({"role": msg["role"], "content": msg["content"]})

    messages.append({"role": "user", "content": query})
    return messages


# ---------------------------------------------------------------------------
# Main API call
# ---------------------------------------------------------------------------
def get_claude_response(
    query: str,
    history: list[dict],
    model: str = "claude-sonnet-4-20250514",
    system_prompt: str = AURI_SYSTEM_PROMPT,
    max_tokens: int = 512,
) -> str:
    """
    Get a response from Claude API.

    Args:
        query: The user's question or request.
        history: Conversation history (list of {role, content} dicts).
        model: Claude model to use.
        system_prompt: System prompt defining AURI's personality.
        max_tokens: Maximum tokens in the response.

    Returns:
        Claude's response text, or a fallback message on error.
    """
    try:
        api_key = _get_anthropic_api_key()
        client = anthropic.Anthropic(api_key=api_key)

        messages = build_messages(query, history)

        response = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=messages,
        )

        reply = response.content[0].text
        logger.info(
            "Claude response received (model=%s, tokens=%d)",
            model,
            response.usage.output_tokens,
        )
        return reply

    except anthropic.APIConnectionError:
        logger.error("Claude API connection error")
        return FALLBACK_RESPONSES[0]
    except anthropic.RateLimitError:
        logger.error("Claude API rate limit exceeded")
        return FALLBACK_RESPONSES[1]
    except anthropic.APIStatusError as e:
        logger.error("Claude API status error: %s", e.status_code)
        return FALLBACK_RESPONSES[2]
    except Exception as e:
        logger.error("Unexpected error calling Claude: %s", e, exc_info=True)
        return FALLBACK_RESPONSES[0]
