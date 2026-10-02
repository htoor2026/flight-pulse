"""Explicit Gemini function calling over the approved Flight Pulse tools."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from google import genai
from google.genai import types

from flight_pulse.analyst import (
    INSUFFICIENT_EVIDENCE,
    TOOL_DEFINITIONS,
    FlightAnalyst,
)
from flight_pulse.config import GeminiSettings


SYSTEM_INSTRUCTION = """
You are the Flight Pulse AI analyst for the current local YYZ flight sample.

Use only the declared Flight Pulse tools for factual claims about flights,
airlines, routes, weather, news, counts, or delays. You have no SQL tool and no
access to data outside the tool results. Never invent missing values.

Every analytical answer must state that it describes only the current Flight
Pulse sample and is not representative of broader airline, route, airport, or
historical performance.

For delay investigations, clearly separate confirmed flight facts from weather
or news context and from possible contributors. Weather and news are contextual
associations unless stored evidence explicitly confirms causation. When the
evidence does not confirm a cause, include this exact sentence:
"Insufficient evidence to determine the delay cause."

Use get_flight_overview for totals, cancelled-flight lists, delayed routes, and
airline or route rankings. Use investigate_delay for questions asking why a
specific flight was delayed. Keep answers concise and grounded in returned data.
""".strip()

SAMPLE_LIMITATION = (
    "This answer describes only the current Flight Pulse sample and is not "
    "representative of broader performance."
)
MAX_TOOL_ROUNDS = 4


@dataclass(frozen=True, slots=True)
class ChatReply:
    text: str
    tool_calls: tuple[dict[str, Any], ...]
    api_requests: int


@dataclass(frozen=True, slots=True)
class _ToolRoute:
    method_name: str
    required: Mapping[str, type]
    optional: Mapping[str, type]


class ToolValidationError(ValueError):
    """Raised before execution when a model tool request is not approved."""


_TOOL_ROUTES: dict[str, _ToolRoute] = {
    "get_flight_overview": _ToolRoute(
        "get_flight_overview",
        {},
        {"include_breakdowns": bool},
    ),
    "find_flight": _ToolRoute("find_flight", {"flight_number": str}, {}),
    "get_airline_analysis": _ToolRoute(
        "get_airline_analysis",
        {"airline": str},
        {},
    ),
    "get_route_analysis": _ToolRoute(
        "get_route_analysis",
        {"origin": str, "destination": str},
        {"limit": int},
    ),
    "get_weather_context": _ToolRoute(
        "get_weather_context",
        {"flight_number": str},
        {},
    ),
    "get_news_context": _ToolRoute(
        "get_news_context",
        {"flight_number": str},
        {"limit": int},
    ),
    "investigate_delay": _ToolRoute(
        "investigate_delay",
        {"flight_number": str},
        {},
    ),
}


def _matches_type(value: object, expected: type) -> bool:
    if expected is int:
        return isinstance(value, int) and not isinstance(value, bool)
    return isinstance(value, expected)


def dispatch_tool(
    analyst: FlightAnalyst,
    name: str,
    arguments: Mapping[str, Any] | None,
) -> Any:
    """Validate and execute one approved analyst tool request."""
    route = _TOOL_ROUTES.get(name)
    if route is None:
        raise ToolValidationError(f"Unknown or unapproved tool: {name!r}")
    if arguments is None:
        arguments = {}
    if not isinstance(arguments, Mapping):
        raise ToolValidationError("Tool arguments must be an object")

    provided = set(arguments)
    allowed = set(route.required) | set(route.optional)
    missing = set(route.required) - provided
    extra = provided - allowed
    if missing:
        raise ToolValidationError(
            f"Missing required arguments for {name}: {', '.join(sorted(missing))}"
        )
    if extra:
        raise ToolValidationError(
            f"Unexpected arguments for {name}: {', '.join(sorted(extra))}"
        )

    for argument_name, expected_type in {
        **route.required,
        **route.optional,
    }.items():
        if argument_name in arguments and not _matches_type(
            arguments[argument_name],
            expected_type,
        ):
            raise ToolValidationError(
                f"Argument {argument_name!r} for {name} must be "
                f"{expected_type.__name__}"
            )

    method = getattr(analyst, route.method_name)
    return method(**dict(arguments))


def _gemini_tool() -> types.Tool:
    declarations = [
        types.FunctionDeclaration(
            name=definition["name"],
            description=definition["description"],
            parameters_json_schema=definition["parameters"],
        )
        for definition in TOOL_DEFINITIONS
    ]
    return types.Tool(function_declarations=declarations)


def _history_contents(
    history: Sequence[Mapping[str, str]],
) -> list[types.Content]:
    contents: list[types.Content] = []
    for message in history[-10:]:
        role = message.get("role")
        content = message.get("content", "").strip()
        if role not in {"user", "assistant"} or not content:
            continue
        contents.append(
            types.Content(
                role="model" if role == "assistant" else "user",
                parts=[types.Part(text=content)],
            )
        )
    return contents


def _model_content(response: Any) -> types.Content:
    candidates = getattr(response, "candidates", None) or []
    if not candidates or candidates[0].content is None:
        raise RuntimeError("Gemini returned no response content")
    return candidates[0].content


def _function_calls(content: types.Content) -> list[types.FunctionCall]:
    return [
        part.function_call
        for part in content.parts or []
        if part.function_call is not None
    ]


def _final_text(response: Any, *, insufficient_evidence: bool) -> str:
    text = (getattr(response, "text", None) or "").strip()
    if not text:
        text = "I could not produce a grounded answer from the available data."
    if insufficient_evidence and INSUFFICIENT_EVIDENCE not in text:
        text = f"{text}\n\n{INSUFFICIENT_EVIDENCE}"
    if SAMPLE_LIMITATION not in text:
        text = f"{text}\n\n{SAMPLE_LIMITATION}"
    return text


class GeminiAnalystChat:
    """Run a bounded Gemini tool loop over a FlightAnalyst instance."""

    def __init__(
        self,
        analyst: FlightAnalyst,
        settings: GeminiSettings,
        *,
        client: Any | None = None,
        allow_overview_breakdowns: bool = True,
    ) -> None:
        self._analyst = analyst
        self._settings = settings
        self._client = client or genai.Client(api_key=settings.api_key)
        self._allow_overview_breakdowns = allow_overview_breakdowns
        self._config = types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            tools=[_gemini_tool()],
            automatic_function_calling=types.AutomaticFunctionCallingConfig(
                disable=True
            ),
            temperature=0.1,
        )

    def answer(
        self,
        question: str,
        *,
        history: Sequence[Mapping[str, str]] = (),
    ) -> ChatReply:
        prompt = question.strip()
        if not prompt:
            raise ValueError("question must not be empty")

        contents = _history_contents(history)
        contents.append(types.Content(role="user", parts=[types.Part(text=prompt)]))
        tool_log: list[dict[str, Any]] = []
        insufficient_evidence = False
        api_requests = 0

        for _ in range(MAX_TOOL_ROUNDS):
            api_requests += 1
            response = self._client.models.generate_content(
                model=self._settings.model,
                contents=contents,
                config=self._config,
            )
            model_content = _model_content(response)
            calls = _function_calls(model_content)
            if not calls:
                return ChatReply(
                    text=_final_text(
                        response,
                        insufficient_evidence=insufficient_evidence,
                    ),
                    tool_calls=tuple(tool_log),
                    api_requests=api_requests,
                )

            contents.append(model_content)
            function_responses: list[types.Part] = []
            for call in calls:
                name = call.name or ""
                arguments = dict(call.args or {})
                if name == "get_flight_overview" and not self._allow_overview_breakdowns:
                    arguments["include_breakdowns"] = False
                tool_log.append({"name": name, "arguments": arguments})
                try:
                    result = dispatch_tool(self._analyst, name, arguments)
                    if (
                        isinstance(result, Mapping)
                        and result.get("conclusion") == INSUFFICIENT_EVIDENCE
                    ):
                        insufficient_evidence = True
                    payload = {"result": result}
                except (ToolValidationError, ValueError) as exc:
                    payload = {"error": str(exc)}
                except Exception:
                    payload = {"error": "The approved analytical tool failed."}

                function_responses.append(
                    types.Part(
                        function_response=types.FunctionResponse(
                            id=call.id,
                            name=name,
                            response=payload,
                        )
                    )
                )

            contents.append(types.Content(role="user", parts=function_responses))

        return ChatReply(
            text=(
                "I could not complete the analytical tool sequence safely.\n\n"
                f"{SAMPLE_LIMITATION}"
            ),
            tool_calls=tuple(tool_log),
            api_requests=api_requests,
        )
