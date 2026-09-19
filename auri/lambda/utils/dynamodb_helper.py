"""
DynamoDB persistence helper for AURI.
Manages user profiles, conversation history, and preferences
in Amazon DynamoDB with automatic TTL.
"""

import time
import logging
from typing import Any, Optional

import boto3
from boto3.dynamodb.conditions import Key

logger = logging.getLogger(__name__)

# TTL: 180 days in seconds
TTL_SECONDS = 180 * 24 * 3600


def _get_table(table_name: str = "auri-users", region: str = "us-east-1"):
    """Get DynamoDB table resource."""
    dynamodb = boto3.resource("dynamodb", region_name=region)
    return dynamodb.Table(table_name)


def get_user_profile(
    user_id: str,
    table_name: str = "auri-users",
) -> dict[str, Any]:
    """
    Retrieve a user profile from DynamoDB.

    Args:
        user_id: The Alexa user ID.
        table_name: DynamoDB table name.

    Returns:
        User profile dict, or empty defaults if not found.
    """
    try:
        table = _get_table(table_name)
        response = table.get_item(Key={"userId": user_id})
        item = response.get("Item", {})

        return {
            "userId": user_id,
            "name": item.get("name", ""),
            "history": item.get("history", []),
            "preferences": item.get(
                "preferences",
                {
                    "language": "pt-BR",
                    "voice": "Vitoria",
                    "personality": "assistente profissional",
                },
            ),
            "smartHome": item.get("smartHome", {"devices": {}, "routines": {}}),
            "updatedAt": item.get("updatedAt", int(time.time())),
        }
    except Exception as e:
        logger.error("Error fetching user profile: %s", e)
        return {
            "userId": user_id,
            "name": "",
            "history": [],
            "preferences": {
                "language": "pt-BR",
                "voice": "Vitoria",
                "personality": "assistente profissional",
            },
            "smartHome": {"devices": {}, "routines": {}},
            "updatedAt": int(time.time()),
        }


def save_user_profile(
    user_id: str,
    profile: dict[str, Any],
    table_name: str = "auri-users",
) -> bool:
    """
    Save a user profile to DynamoDB with TTL.

    Args:
        user_id: The Alexa user ID.
        profile: Profile data to save.
        table_name: DynamoDB table name.

    Returns:
        True if saved successfully, False otherwise.
    """
    try:
        table = _get_table(table_name)
        item = {
            "userId": user_id,
            "name": profile.get("name", ""),
            "history": profile.get("history", []),
            "preferences": profile.get("preferences", {}),
            "smartHome": profile.get("smartHome", {}),
            "updatedAt": int(time.time()),
            "ttl": int(time.time()) + TTL_SECONDS,
        }
        table.put_item(Item=item)
        logger.info("Saved profile for user %s", user_id[:20])
        return True
    except Exception as e:
        logger.error("Error saving user profile: %s", e)
        return False


def add_to_history(
    user_id: str,
    role: str,
    content: str,
    table_name: str = "auri-users",
    max_messages: int = 50,
) -> bool:
    """
    Add a message to the user's conversation history.

    Args:
        user_id: The Alexa user ID.
        role: Message role ('user' or 'assistant').
        content: Message content.
        table_name: DynamoDB table name.
        max_messages: Maximum history messages to retain.

    Returns:
        True if saved successfully.
    """
    try:
        profile = get_user_profile(user_id, table_name)
        history = profile.get("history", [])
        history.append({"role": role, "content": content})

        # Trim to max
        if len(history) > max_messages:
            history = history[-max_messages:]

        profile["history"] = history
        return save_user_profile(user_id, profile, table_name)
    except Exception as e:
        logger.error("Error adding to history: %s", e)
        return False


def get_history(
    user_id: str,
    table_name: str = "auri-users",
    limit: int = 20,
) -> list[dict]:
    """
    Get conversation history for a user.

    Args:
        user_id: The Alexa user ID.
        table_name: DynamoDB table name.
        limit: Maximum number of recent messages.

    Returns:
        List of message dicts.
    """
    profile = get_user_profile(user_id, table_name)
    history = profile.get("history", [])
    return history[-limit:]


def clear_history(
    user_id: str,
    table_name: str = "auri-users",
) -> bool:
    """
    Clear conversation history for a user.

    Args:
        user_id: The Alexa user ID.
        table_name: DynamoDB table name.

    Returns:
        True if cleared successfully.
    """
    try:
        profile = get_user_profile(user_id, table_name)
        profile["history"] = []
        return save_user_profile(user_id, profile, table_name)
    except Exception as e:
        logger.error("Error clearing history: %s", e)
        return False
