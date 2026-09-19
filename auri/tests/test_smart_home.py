"""
Unit tests for the AURI Smart Home handler.
"""

import sys
import os
import uuid
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lambda"))

from smart_home_handler import (
    handle_discovery,
    handle_power_control,
    handle_brightness_control,
    handle_report_state,
    smart_home_handler,
)


def _make_directive(namespace, name, endpoint_id="light-sala-001", payload=None):
    """Helper to build a smart home directive event."""
    return {
        "directive": {
            "header": {
                "namespace": namespace,
                "name": name,
                "payloadVersion": "3",
                "messageId": str(uuid.uuid4()),
                "correlationToken": "test-token-123",
            },
            "endpoint": {"endpointId": endpoint_id},
            "payload": payload or {},
        }
    }


class TestDiscovery:
    """Tests for device discovery."""

    def test_discovery_returns_endpoints(self):
        """Discovery should return all registered devices."""
        event = _make_directive("Alexa.Discovery", "Discover")
        response = handle_discovery(event)

        assert response["event"]["header"]["name"] == "Discover.Response"
        endpoints = response["event"]["payload"]["endpoints"]
        assert len(endpoints) >= 2  # At least light + thermostat

    def test_discovery_endpoint_has_capabilities(self):
        """Each endpoint should have capabilities defined."""
        event = _make_directive("Alexa.Discovery", "Discover")
        response = handle_discovery(event)

        for endpoint in response["event"]["payload"]["endpoints"]:
            assert "capabilities" in endpoint
            assert len(endpoint["capabilities"]) > 0
            assert "friendlyName" in endpoint


class TestPowerControl:
    """Tests for PowerController."""

    def test_turn_on(self):
        """TurnOn should set powerState to ON."""
        event = _make_directive("Alexa.PowerController", "TurnOn")
        response = handle_power_control(event)

        assert response["event"]["header"]["name"] == "Response"
        props = response["context"]["properties"]
        power_prop = next(p for p in props if p["name"] == "powerState")
        assert power_prop["value"] == "ON"

    def test_turn_off(self):
        """TurnOff should set powerState to OFF."""
        event = _make_directive("Alexa.PowerController", "TurnOff")
        response = handle_power_control(event)

        props = response["context"]["properties"]
        power_prop = next(p for p in props if p["name"] == "powerState")
        assert power_prop["value"] == "OFF"


class TestBrightnessControl:
    """Tests for BrightnessController."""

    def test_set_brightness(self):
        """SetBrightness should set the exact brightness value."""
        event = _make_directive(
            "Alexa.BrightnessController",
            "SetBrightness",
            payload={"brightness": 75},
        )
        response = handle_brightness_control(event)

        props = response["context"]["properties"]
        brightness_prop = next(p for p in props if p["name"] == "brightness")
        assert brightness_prop["value"] == 75

    def test_adjust_brightness(self):
        """AdjustBrightness should adjust relative to current value."""
        event = _make_directive(
            "Alexa.BrightnessController",
            "AdjustBrightness",
            payload={"brightnessDelta": -20},
        )
        response = handle_brightness_control(event)

        props = response["context"]["properties"]
        brightness_prop = next(p for p in props if p["name"] == "brightness")
        assert 0 <= brightness_prop["value"] <= 100


class TestStateReport:
    """Tests for ReportState."""

    def test_report_state(self):
        """ReportState should return current device state."""
        event = _make_directive("Alexa", "ReportState")
        response = handle_report_state(event)

        assert response["event"]["header"]["name"] == "StateReport"
        assert len(response["context"]["properties"]) > 0


class TestDispatcher:
    """Tests for the main dispatcher."""

    def test_routes_discovery(self):
        """Dispatcher should route Discovery correctly."""
        event = _make_directive("Alexa.Discovery", "Discover")
        response = smart_home_handler(event)
        assert response["event"]["header"]["name"] == "Discover.Response"

    def test_routes_power(self):
        """Dispatcher should route PowerController correctly."""
        event = _make_directive("Alexa.PowerController", "TurnOn")
        response = smart_home_handler(event)
        assert response["event"]["header"]["name"] == "Response"

    def test_unsupported_namespace(self):
        """Unsupported namespace should return ErrorResponse."""
        event = _make_directive("Alexa.Cooking", "CookPasta")
        response = smart_home_handler(event)
        assert response["event"]["header"]["name"] == "ErrorResponse"
