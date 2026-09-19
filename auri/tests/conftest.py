"""
Pytest fixtures for AURI Lambda handler tests.
"""

import pytest
from unittest.mock import MagicMock, patch


@pytest.fixture
def sample_user_attrs():
    """Sample persistent attributes for a returning user."""
    return {
        "name": "João",
        "history": [
            {"role": "user", "content": "Olá"},
            {"role": "assistant", "content": "Oi João! Como posso ajudar?"},
        ],
        "preferences": {
            "language": "pt-BR",
            "voice": "Vitoria",
            "personality": "assistente profissional",
        },
        "smartHome": {"devices": {}, "routines": {}},
    }


@pytest.fixture
def empty_user_attrs():
    """Empty persistent attributes for a new user."""
    return {}


@pytest.fixture
def mock_handler_input():
    """Create a mock HandlerInput object."""

    def _create(
        request_type="LaunchRequest",
        intent_name=None,
        slots=None,
        persistent_attrs=None,
        supports_apl=False,
    ):
        handler_input = MagicMock()

        # Request type
        handler_input.request_envelope.request.object_type = request_type

        # Intent
        if intent_name:
            handler_input.request_envelope.request.intent.name = intent_name
            handler_input.request_envelope.request.intent.slots = slots or {}

        # Persistent attributes
        attrs = persistent_attrs or {}
        handler_input.attributes_manager.persistent_attributes = attrs

        # APL support
        if supports_apl:
            handler_input.request_envelope.context.system.device.supported_interfaces.alexa_presentation_apl = (
                MagicMock()
            )
        else:
            handler_input.request_envelope.context.system.device.supported_interfaces.alexa_presentation_apl = (
                None
            )

        # Response builder
        handler_input.response_builder.speak.return_value = handler_input.response_builder
        handler_input.response_builder.ask.return_value = handler_input.response_builder
        handler_input.response_builder.add_directive.return_value = handler_input.response_builder
        handler_input.response_builder.response = MagicMock()

        return handler_input

    return _create


@pytest.fixture
def mock_claude_client():
    """Mock the Anthropic Claude client."""
    with patch("utils.claude_helper.anthropic.Anthropic") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client

        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Resposta teste da Auri.")]
        mock_response.usage.output_tokens = 10
        mock_client.messages.create.return_value = mock_response

        yield mock_client


@pytest.fixture
def mock_dynamodb():
    """Mock DynamoDB operations."""
    with patch("utils.dynamodb_helper.boto3.resource") as mock_resource:
        mock_table = MagicMock()
        mock_resource.return_value.Table.return_value = mock_table
        mock_table.get_item.return_value = {"Item": {}}
        mock_table.put_item.return_value = {}
        yield mock_table
