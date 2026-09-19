"""
Smart Home handler for AURI.
Handles Alexa Smart Home directives: Discovery, PowerController,
BrightnessController, and StateReport.
"""

import logging
import uuid
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Device registry (in production, this would come from a database)
# ---------------------------------------------------------------------------
DEVICE_REGISTRY = {
    "light-sala-001": {
        "friendlyName": "Luz da Sala",
        "displayCategories": ["LIGHT"],
        "state": {"powerState": "OFF", "brightness": 100},
        "capabilities": [
            {
                "type": "AlexaInterface",
                "interface": "Alexa.PowerController",
                "version": "3",
                "properties": {
                    "supported": [{"name": "powerState"}],
                    "proactivelyReported": True,
                    "retrievable": True,
                },
            },
            {
                "type": "AlexaInterface",
                "interface": "Alexa.BrightnessController",
                "version": "3",
                "properties": {
                    "supported": [{"name": "brightness"}],
                    "proactivelyReported": True,
                    "retrievable": True,
                },
            },
            {
                "type": "AlexaInterface",
                "interface": "Alexa",
                "version": "3",
            },
        ],
    },
    "light-quarto-001": {
        "friendlyName": "Luz do Quarto",
        "displayCategories": ["LIGHT"],
        "state": {"powerState": "OFF", "brightness": 80},
        "capabilities": [
            {
                "type": "AlexaInterface",
                "interface": "Alexa.PowerController",
                "version": "3",
                "properties": {
                    "supported": [{"name": "powerState"}],
                    "proactivelyReported": True,
                    "retrievable": True,
                },
            },
            {
                "type": "AlexaInterface",
                "interface": "Alexa.BrightnessController",
                "version": "3",
                "properties": {
                    "supported": [{"name": "brightness"}],
                    "proactivelyReported": True,
                    "retrievable": True,
                },
            },
            {
                "type": "AlexaInterface",
                "interface": "Alexa",
                "version": "3",
            },
        ],
    },
    "thermostat-sala-001": {
        "friendlyName": "Ar Condicionado da Sala",
        "displayCategories": ["THERMOSTAT"],
        "state": {"targetSetpoint": 22, "thermostatMode": "AUTO"},
        "capabilities": [
            {
                "type": "AlexaInterface",
                "interface": "Alexa.ThermostatController",
                "version": "3",
                "properties": {
                    "supported": [
                        {"name": "targetSetpoint"},
                        {"name": "thermostatMode"},
                    ],
                    "proactivelyReported": True,
                    "retrievable": True,
                },
            },
            {
                "type": "AlexaInterface",
                "interface": "Alexa",
                "version": "3",
            },
        ],
    },
}


def _now_iso() -> str:
    """Return current UTC time in ISO 8601 format."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.00Z")


def _build_context_property(
    namespace: str, name: str, value, uncertainty_ms: int = 0
) -> dict:
    """Build a context property for the response."""
    return {
        "namespace": namespace,
        "name": name,
        "value": value,
        "timeOfSample": _now_iso(),
        "uncertaintyInMilliseconds": uncertainty_ms,
    }


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------
def handle_discovery(event: dict) -> dict:
    """Handle Alexa.Discovery directive — report available devices."""
    endpoints = []
    for endpoint_id, device in DEVICE_REGISTRY.items():
        endpoints.append(
            {
                "endpointId": endpoint_id,
                "manufacturerName": "AURI Smart Home",
                "friendlyName": device["friendlyName"],
                "description": f"AURI-controlled {device['friendlyName']}",
                "displayCategories": device["displayCategories"],
                "capabilities": device["capabilities"],
            }
        )

    return {
        "event": {
            "header": {
                "namespace": "Alexa.Discovery",
                "name": "Discover.Response",
                "payloadVersion": "3",
                "messageId": str(uuid.uuid4()),
            },
            "payload": {"endpoints": endpoints},
        }
    }


# ---------------------------------------------------------------------------
# Power Control
# ---------------------------------------------------------------------------
def handle_power_control(event: dict) -> dict:
    """Handle Alexa.PowerController directives (TurnOn/TurnOff)."""
    directive = event["directive"]
    endpoint_id = directive["endpoint"]["endpointId"]
    name = directive["header"]["name"]
    correlation_token = directive["header"].get("correlationToken", "")

    new_state = "ON" if name == "TurnOn" else "OFF"

    # Update device state
    if endpoint_id in DEVICE_REGISTRY:
        DEVICE_REGISTRY[endpoint_id]["state"]["powerState"] = new_state

    logger.info("Power %s device %s", new_state, endpoint_id)

    return {
        "event": {
            "header": {
                "namespace": "Alexa",
                "name": "Response",
                "payloadVersion": "3",
                "messageId": str(uuid.uuid4()),
                "correlationToken": correlation_token,
            },
            "endpoint": {"endpointId": endpoint_id},
            "payload": {},
        },
        "context": {
            "properties": [
                _build_context_property(
                    "Alexa.PowerController", "powerState", new_state
                )
            ]
        },
    }


# ---------------------------------------------------------------------------
# Brightness Control
# ---------------------------------------------------------------------------
def handle_brightness_control(event: dict) -> dict:
    """Handle Alexa.BrightnessController directives."""
    directive = event["directive"]
    endpoint_id = directive["endpoint"]["endpointId"]
    name = directive["header"]["name"]
    correlation_token = directive["header"].get("correlationToken", "")

    if name == "SetBrightness":
        brightness = directive["payload"]["brightness"]
    elif name == "AdjustBrightness":
        delta = directive["payload"]["brightnessDelta"]
        current = DEVICE_REGISTRY.get(endpoint_id, {}).get("state", {}).get(
            "brightness", 50
        )
        brightness = max(0, min(100, current + delta))
    else:
        brightness = 100

    # Update device state
    if endpoint_id in DEVICE_REGISTRY:
        DEVICE_REGISTRY[endpoint_id]["state"]["brightness"] = brightness

    logger.info("Brightness set to %d on device %s", brightness, endpoint_id)

    return {
        "event": {
            "header": {
                "namespace": "Alexa",
                "name": "Response",
                "payloadVersion": "3",
                "messageId": str(uuid.uuid4()),
                "correlationToken": correlation_token,
            },
            "endpoint": {"endpointId": endpoint_id},
            "payload": {},
        },
        "context": {
            "properties": [
                _build_context_property(
                    "Alexa.BrightnessController", "brightness", brightness
                )
            ]
        },
    }


# ---------------------------------------------------------------------------
# State Report
# ---------------------------------------------------------------------------
def handle_report_state(event: dict) -> dict:
    """Handle Alexa.ReportState — return current device state."""
    directive = event["directive"]
    endpoint_id = directive["endpoint"]["endpointId"]
    correlation_token = directive["header"].get("correlationToken", "")

    device = DEVICE_REGISTRY.get(endpoint_id, {})
    state = device.get("state", {})
    properties = []

    if "powerState" in state:
        properties.append(
            _build_context_property(
                "Alexa.PowerController", "powerState", state["powerState"]
            )
        )
    if "brightness" in state:
        properties.append(
            _build_context_property(
                "Alexa.BrightnessController", "brightness", state["brightness"]
            )
        )

    return {
        "event": {
            "header": {
                "namespace": "Alexa",
                "name": "StateReport",
                "payloadVersion": "3",
                "messageId": str(uuid.uuid4()),
                "correlationToken": correlation_token,
            },
            "endpoint": {"endpointId": endpoint_id},
            "payload": {},
        },
        "context": {"properties": properties},
    }


# ---------------------------------------------------------------------------
# Main dispatcher
# ---------------------------------------------------------------------------
def smart_home_handler(event: dict, context=None) -> dict:
    """
    Main Smart Home Lambda handler.
    Routes directives to the appropriate handler by namespace.
    """
    directive = event.get("directive", {})
    header = directive.get("header", {})
    namespace = header.get("namespace", "")
    name = header.get("name", "")

    logger.info("Smart Home directive: %s.%s", namespace, name)

    if namespace == "Alexa.Discovery":
        return handle_discovery(event)
    elif namespace == "Alexa.PowerController":
        return handle_power_control(event)
    elif namespace == "Alexa.BrightnessController":
        return handle_brightness_control(event)
    elif namespace == "Alexa" and name == "ReportState":
        return handle_report_state(event)
    else:
        logger.warning("Unsupported directive: %s.%s", namespace, name)
        return {
            "event": {
                "header": {
                    "namespace": "Alexa",
                    "name": "ErrorResponse",
                    "payloadVersion": "3",
                    "messageId": str(uuid.uuid4()),
                },
                "payload": {
                    "type": "INVALID_DIRECTIVE",
                    "message": f"Unsupported: {namespace}.{name}",
                },
            }
        }
