"""
AURI — Claude-powered Alexa Voice Assistant
Main Lambda handler for the AURI Alexa Skill.
"""

import os
import logging

from ask_sdk_core.skill_builder import CustomSkillBuilder
from ask_sdk_core.handler_input import HandlerInput
from ask_sdk_core.utils import is_intent_name, is_request_type
from ask_sdk_core.dispatch_components import (
    AbstractRequestHandler,
    AbstractExceptionHandler,
)
from ask_sdk_model import Response
from ask_sdk_dynamodb_persistence_adapter import DynamoDbPersistenceAdapter

from utils.claude_helper import get_gemini_response, AURI_SYSTEM_PROMPT
from utils.polly_helper import synthesize_speech, build_ssml
from utils.dynamodb_helper import add_to_history, get_history

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
GEMINI_MODEL = "gemini-2.5-flash"
MAX_HISTORY = 20
MAX_RESPONSE_CHARS = 600
DYNAMODB_TABLE = os.environ.get("DYNAMODB_TABLE", "auri-users")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# ---------------------------------------------------------------------------
# Persistence adapter
# ---------------------------------------------------------------------------
dynamodb_adapter = DynamoDbPersistenceAdapter(
    table_name=DYNAMODB_TABLE,
    partition_key_name="userId",
)

sb = CustomSkillBuilder(persistence_adapter=dynamodb_adapter)

# ---------------------------------------------------------------------------
# APL helpers
# ---------------------------------------------------------------------------
CHAT_APL_DOCUMENT = {
    "type": "APL",
    "version": "2023.3",
    "theme": "dark",
    "mainTemplate": {
        "parameters": ["payload"],
        "items": [
            {
                "type": "Container",
                "width": "100%",
                "height": "100%",
                "backgroundColor": "#1a1a2e",
                "items": [
                    {
                        "type": "Text",
                        "text": "AURI",
                        "fontSize": "32dp",
                        "color": "#e94560",
                        "textAlign": "center",
                        "paddingTop": "20dp",
                        "fontWeight": "bold",
                    },
                    {
                        "type": "Text",
                        "text": "${payload.lastResponse}",
                        "fontSize": "24dp",
                        "color": "#ffffff",
                        "padding": "20dp",
                        "maxLines": 8,
                        "grow": 1,
                    },
                    {
                        "type": "Text",
                        "text": "Diga algo para continuar...",
                        "fontSize": "18dp",
                        "color": "#888888",
                        "textAlign": "center",
                        "paddingBottom": "20dp",
                    },
                ],
            }
        ],
    },
}


def _supports_apl(handler_input: HandlerInput) -> bool:
    """Check if the device supports APL (Alexa Presentation Language)."""
    try:
        supported = (
            handler_input.request_envelope.context.system.device.supported_interfaces
        )
        return getattr(supported, "alexa_presentation_apl", None) is not None
    except AttributeError:
        return False


def _add_apl_chat(handler_input: HandlerInput, text: str) -> None:
    """Add APL chat interface directive if device supports it."""
    if _supports_apl(handler_input):
        handler_input.response_builder.add_directive(
            {
                "type": "Alexa.Presentation.APL.RenderDocument",
                "token": "auri-chat",
                "document": CHAT_APL_DOCUMENT,
                "datasources": {"payload": {"lastResponse": text}},
            }
        )


# ---------------------------------------------------------------------------
# Routine definitions
# ---------------------------------------------------------------------------
ROUTINES = {
    "bom dia": {
        "message": "Bom dia! Acendendo as luzes, ligando a cafeteira e preparando sua playlist matinal. Vamos começar o dia com energia!",
        "actions": ["lights_on", "coffee_start", "playlist_morning"],
    },
    "boa noite": {
        "message": "Boa noite! Apagando as luzes, ativando o modo não perturbe e ajustando o ar para 22 graus. Durma bem!",
        "actions": ["lights_off", "dnd_on", "thermostat_22"],
    },
    "trabalho": {
        "message": "Modo trabalho ativado! Silenciando notificações, ajustando a iluminação para foco e iniciando sua playlist de concentração.",
        "actions": ["dnd_on", "lights_focus", "playlist_focus"],
    },
    "sair": {
        "message": "Até logo! Desligando tudo, ativando o alarme e trancando as portas. Tenha um ótimo dia!",
        "actions": ["all_off", "alarm_on", "locks_on"],
    },
}


# ===========================================================================
# Request Handlers
# ===========================================================================
class LaunchRequestHandler(AbstractRequestHandler):
    """Handler for Skill Launch."""

    def can_handle(self, handler_input: HandlerInput) -> bool:
        return is_request_type("LaunchRequest")(handler_input)

    def handle(self, handler_input: HandlerInput) -> Response:
        attrs = handler_input.attributes_manager.persistent_attributes
        name = attrs.get("name", "")
        if name:
            greeting = f"Oi, {name}! Eu sou a Auri. Como posso ajudar?"
        else:
            greeting = "Oi! Eu sou a Auri, sua assistente inteligente. Como posso ajudar?"

        _add_apl_chat(handler_input, greeting)

        return (
            handler_input.response_builder.speak(greeting)
            .ask("Em que posso ajudar?")
            .response
        )


class ChatIntentHandler(AbstractRequestHandler):
    """Handler for ChatIntent — routes queries to Claude."""

    def can_handle(self, handler_input: HandlerInput) -> bool:
        return is_intent_name("ChatIntent")(handler_input)

    def handle(self, handler_input: HandlerInput) -> Response:
        slots = handler_input.request_envelope.request.intent.slots
        query = slots.get("query")
        query_value = query.value if query else None

        if not query_value:
            return (
                handler_input.response_builder.speak("Pode repetir? Não entendi bem.")
                .ask("Pode repetir?")
                .response
            )

        # Load conversation history
        attrs = handler_input.attributes_manager.persistent_attributes
        history = attrs.get("history", [])

        # Get Gemini (Antigravity) response
        reply = get_gemini_response(
            query=query_value,
            history=history[-MAX_HISTORY:],
            system_prompt=AURI_SYSTEM_PROMPT,
        )

        # Truncate if too long for Alexa
        if len(reply) > MAX_RESPONSE_CHARS:
            reply = reply[:MAX_RESPONSE_CHARS] + "... Quer que eu continue?"

        # Save history
        history.append({"role": "user", "content": query_value})
        history.append({"role": "assistant", "content": reply})
        attrs["history"] = history[-50:]
        handler_input.attributes_manager.persistent_attributes = attrs
        handler_input.attributes_manager.save_persistent_attributes()

        # Add APL visual
        _add_apl_chat(handler_input, reply)

        return (
            handler_input.response_builder.speak(reply)
            .ask("Mais alguma coisa?")
            .response
        )


class SetNameIntentHandler(AbstractRequestHandler):
    """Handler for SetNameIntent — remembers the user's name."""

    def can_handle(self, handler_input: HandlerInput) -> bool:
        return is_intent_name("SetNameIntent")(handler_input)

    def handle(self, handler_input: HandlerInput) -> Response:
        slots = handler_input.request_envelope.request.intent.slots
        user_name = slots.get("userName")
        name_value = user_name.value if user_name else None

        if not name_value:
            return (
                handler_input.response_builder.speak(
                    "Desculpa, não consegui pegar seu nome. Pode repetir?"
                )
                .ask("Qual é seu nome?")
                .response
            )

        attrs = handler_input.attributes_manager.persistent_attributes
        attrs["name"] = name_value
        handler_input.attributes_manager.persistent_attributes = attrs
        handler_input.attributes_manager.save_persistent_attributes()

        reply = f"Prazer, {name_value}! Vou lembrar do seu nome. Como posso ajudar?"
        return (
            handler_input.response_builder.speak(reply)
            .ask("Em que posso ajudar?")
            .response
        )


class SmartHomeIntentHandler(AbstractRequestHandler):
    """Handler for SmartHomeIntent — voice-based device control."""

    def can_handle(self, handler_input: HandlerInput) -> bool:
        return is_intent_name("SmartHomeIntent")(handler_input)

    def handle(self, handler_input: HandlerInput) -> Response:
        slots = handler_input.request_envelope.request.intent.slots
        device = slots.get("device")
        action = slots.get("action")

        device_value = device.value if device else "dispositivo"
        action_value = action.value if action else "controlar"

        if action_value in ("liga", "acende", "ativa"):
            reply = f"Pronto! Liguei {device_value}."
        elif action_value in ("desliga", "apaga", "desativa"):
            reply = f"Pronto! Desliguei {device_value}."
        else:
            reply = f"Pronto! Executei {action_value} em {device_value}."

        logger.info("Smart Home action: %s on %s", action_value, device_value)

        return (
            handler_input.response_builder.speak(reply)
            .ask("Mais algum comando?")
            .response
        )


class RoutineIntentHandler(AbstractRequestHandler):
    """Handler for RoutineIntent — triggers predefined routines."""

    def can_handle(self, handler_input: HandlerInput) -> bool:
        return is_intent_name("RoutineIntent")(handler_input)

    def handle(self, handler_input: HandlerInput) -> Response:
        slots = handler_input.request_envelope.request.intent.slots
        routine = slots.get("routine")
        routine_value = routine.value if routine else None

        if routine_value and routine_value.lower() in ROUTINES:
            routine_data = ROUTINES[routine_value.lower()]
            reply = routine_data["message"]
            logger.info(
                "Executing routine '%s' with actions: %s",
                routine_value,
                routine_data["actions"],
            )
        else:
            reply = (
                "Não conheço essa rotina. As rotinas disponíveis são: "
                "bom dia, boa noite, trabalho e sair."
            )

        _add_apl_chat(handler_input, reply)

        return (
            handler_input.response_builder.speak(reply)
            .ask("Quer ativar outra rotina?")
            .response
        )


class HelpIntentHandler(AbstractRequestHandler):
    """Handler for AMAZON.HelpIntent."""

    def can_handle(self, handler_input: HandlerInput) -> bool:
        return is_intent_name("AMAZON.HelpIntent")(handler_input)

    def handle(self, handler_input: HandlerInput) -> Response:
        help_text = (
            "Eu sou a Auri, sua assistente inteligente! "
            "Você pode me fazer qualquer pergunta, pedir para controlar dispositivos, "
            "ou ativar rotinas como bom dia e boa noite. O que gostaria de fazer?"
        )
        return (
            handler_input.response_builder.speak(help_text)
            .ask("O que gostaria de saber?")
            .response
        )


class CancelStopIntentHandler(AbstractRequestHandler):
    """Handler for AMAZON.CancelIntent and AMAZON.StopIntent."""

    def can_handle(self, handler_input: HandlerInput) -> bool:
        return is_intent_name("AMAZON.CancelIntent")(
            handler_input
        ) or is_intent_name("AMAZON.StopIntent")(handler_input)

    def handle(self, handler_input: HandlerInput) -> Response:
        return handler_input.response_builder.speak("Até mais! Tchau!").response


class FallbackIntentHandler(AbstractRequestHandler):
    """Handler for AMAZON.FallbackIntent."""

    def can_handle(self, handler_input: HandlerInput) -> bool:
        return is_intent_name("AMAZON.FallbackIntent")(handler_input)

    def handle(self, handler_input: HandlerInput) -> Response:
        return (
            handler_input.response_builder.speak(
                "Hmm, não entendi. Pode tentar de outra forma?"
            )
            .ask("Pode reformular?")
            .response
        )


class SessionEndedRequestHandler(AbstractRequestHandler):
    """Handler for SessionEndedRequest."""

    def can_handle(self, handler_input: HandlerInput) -> bool:
        return is_request_type("SessionEndedRequest")(handler_input)

    def handle(self, handler_input: HandlerInput) -> Response:
        reason = handler_input.request_envelope.request.reason
        logger.info("Session ended with reason: %s", reason)
        return handler_input.response_builder.response


# ===========================================================================
# Exception Handler
# ===========================================================================
class GlobalExceptionHandler(AbstractExceptionHandler):
    """Catch-all exception handler."""

    def can_handle(self, handler_input: HandlerInput, exception: Exception) -> bool:
        return True

    def handle(self, handler_input: HandlerInput, exception: Exception) -> Response:
        logger.error("Unhandled exception: %s", exception, exc_info=True)
        return (
            handler_input.response_builder.speak(
                "Desculpa, tive um problema. Pode tentar de novo?"
            )
            .ask("Pode repetir?")
            .response
        )


# ===========================================================================
# Register handlers and export
# ===========================================================================
sb.add_request_handler(LaunchRequestHandler())
sb.add_request_handler(ChatIntentHandler())
sb.add_request_handler(SetNameIntentHandler())
sb.add_request_handler(SmartHomeIntentHandler())
sb.add_request_handler(RoutineIntentHandler())
sb.add_request_handler(HelpIntentHandler())
sb.add_request_handler(CancelStopIntentHandler())
sb.add_request_handler(FallbackIntentHandler())
sb.add_request_handler(SessionEndedRequestHandler())
sb.add_exception_handler(GlobalExceptionHandler())

handler = sb.lambda_handler()
