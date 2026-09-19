"""
Unit tests for the AURI Lambda handler.
Tests all intent handlers with mocked dependencies.
"""

import sys
import os
import pytest
from unittest.mock import MagicMock, patch, PropertyMock

# Add lambda directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lambda"))


class TestLaunchRequestHandler:
    """Tests for LaunchRequestHandler."""

    def test_launch_new_user(self, mock_handler_input):
        """New user should get a generic greeting."""
        from lambda_function import LaunchRequestHandler

        handler = LaunchRequestHandler()
        hi = mock_handler_input(request_type="LaunchRequest", persistent_attrs={})

        assert handler.can_handle(hi)
        handler.handle(hi)

        hi.response_builder.speak.assert_called_once()
        call_args = hi.response_builder.speak.call_args[0][0]
        assert "Auri" in call_args

    def test_launch_returning_user(self, mock_handler_input, sample_user_attrs):
        """Returning user should be greeted by name."""
        from lambda_function import LaunchRequestHandler

        handler = LaunchRequestHandler()
        hi = mock_handler_input(
            request_type="LaunchRequest", persistent_attrs=sample_user_attrs
        )

        handler.handle(hi)

        call_args = hi.response_builder.speak.call_args[0][0]
        assert "João" in call_args


class TestChatIntentHandler:
    """Tests for ChatIntentHandler."""

    @patch("lambda_function.get_claude_response")
    def test_chat_basic(self, mock_claude, mock_handler_input):
        """ChatIntent should call Claude and return a response."""
        from lambda_function import ChatIntentHandler

        mock_claude.return_value = "O clima hoje está ótimo!"

        query_slot = MagicMock()
        query_slot.value = "como está o clima"
        slots = {"query": query_slot}

        hi = mock_handler_input(
            request_type="IntentRequest",
            intent_name="ChatIntent",
            slots=slots,
            persistent_attrs={"history": []},
        )

        handler = ChatIntentHandler()
        assert handler.can_handle(hi)
        handler.handle(hi)

        mock_claude.assert_called_once()
        hi.response_builder.speak.assert_called_once()

    def test_chat_no_query(self, mock_handler_input):
        """ChatIntent with no query should ask user to repeat."""
        from lambda_function import ChatIntentHandler

        query_slot = MagicMock()
        query_slot.value = None
        slots = {"query": query_slot}

        hi = mock_handler_input(
            request_type="IntentRequest",
            intent_name="ChatIntent",
            slots=slots,
            persistent_attrs={},
        )

        handler = ChatIntentHandler()
        handler.handle(hi)

        call_args = hi.response_builder.speak.call_args[0][0]
        assert "repetir" in call_args.lower() or "entendi" in call_args.lower()

    @patch("lambda_function.get_claude_response")
    def test_chat_long_response_truncated(self, mock_claude, mock_handler_input):
        """Long Claude responses should be truncated."""
        from lambda_function import ChatIntentHandler, MAX_RESPONSE_CHARS

        mock_claude.return_value = "A" * (MAX_RESPONSE_CHARS + 100)

        query_slot = MagicMock()
        query_slot.value = "conte uma história longa"
        slots = {"query": query_slot}

        hi = mock_handler_input(
            request_type="IntentRequest",
            intent_name="ChatIntent",
            slots=slots,
            persistent_attrs={"history": []},
        )

        handler = ChatIntentHandler()
        handler.handle(hi)

        call_args = hi.response_builder.speak.call_args[0][0]
        assert "continue" in call_args.lower()


class TestRoutineIntentHandler:
    """Tests for RoutineIntentHandler."""

    def test_routine_bom_dia(self, mock_handler_input):
        """'bom dia' routine should activate correctly."""
        from lambda_function import RoutineIntentHandler

        routine_slot = MagicMock()
        routine_slot.value = "bom dia"
        slots = {"routine": routine_slot}

        hi = mock_handler_input(
            request_type="IntentRequest",
            intent_name="RoutineIntent",
            slots=slots,
            persistent_attrs={},
        )

        handler = RoutineIntentHandler()
        assert handler.can_handle(hi)
        handler.handle(hi)

        call_args = hi.response_builder.speak.call_args[0][0]
        assert "Bom dia" in call_args

    def test_routine_unknown(self, mock_handler_input):
        """Unknown routine should list available options."""
        from lambda_function import RoutineIntentHandler

        routine_slot = MagicMock()
        routine_slot.value = "festa"
        slots = {"routine": routine_slot}

        hi = mock_handler_input(
            request_type="IntentRequest",
            intent_name="RoutineIntent",
            slots=slots,
            persistent_attrs={},
        )

        handler = RoutineIntentHandler()
        handler.handle(hi)

        call_args = hi.response_builder.speak.call_args[0][0]
        assert "rotina" in call_args.lower()


class TestHelpStopFallback:
    """Tests for Help, Stop/Cancel, and Fallback handlers."""

    def test_help_intent(self, mock_handler_input):
        """Help intent should describe capabilities."""
        from lambda_function import HelpIntentHandler

        hi = mock_handler_input(
            request_type="IntentRequest", intent_name="AMAZON.HelpIntent"
        )

        handler = HelpIntentHandler()
        assert handler.can_handle(hi)
        handler.handle(hi)
        hi.response_builder.speak.assert_called_once()

    def test_stop_intent(self, mock_handler_input):
        """Stop intent should say goodbye."""
        from lambda_function import CancelStopIntentHandler

        hi = mock_handler_input(
            request_type="IntentRequest", intent_name="AMAZON.StopIntent"
        )

        handler = CancelStopIntentHandler()
        assert handler.can_handle(hi)
        handler.handle(hi)

        call_args = hi.response_builder.speak.call_args[0][0]
        assert "mais" in call_args.lower() or "tchau" in call_args.lower()

    def test_fallback_intent(self, mock_handler_input):
        """Fallback intent should ask user to rephrase."""
        from lambda_function import FallbackIntentHandler

        hi = mock_handler_input(
            request_type="IntentRequest", intent_name="AMAZON.FallbackIntent"
        )

        handler = FallbackIntentHandler()
        assert handler.can_handle(hi)
        handler.handle(hi)
        hi.response_builder.speak.assert_called_once()


class TestExceptionHandler:
    """Tests for GlobalExceptionHandler."""

    def test_exception_handler(self, mock_handler_input):
        """Exception handler should return a friendly error message."""
        from lambda_function import GlobalExceptionHandler

        hi = mock_handler_input(request_type="LaunchRequest")
        exception = ValueError("Test error")

        handler = GlobalExceptionHandler()
        assert handler.can_handle(hi, exception)
        handler.handle(hi, exception)

        call_args = hi.response_builder.speak.call_args[0][0]
        assert "problema" in call_args.lower() or "desculpa" in call_args.lower()
