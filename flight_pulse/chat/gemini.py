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

Do not add a general sample-size disclaimer. The application appends that
disclaimer exactly once after the grounded answer.

For delay investigations, organize the answer under these exact headings:
"Confirmed flight facts", "Weather context", "News/disruption context", and
"Conclusion". Weather and news are contextual associations unless stored
evidence explicitly confirms causation. When a stored delay value has an
absolute value greater than 360 minutes, introduce it with "The stored Flight
Pulse record indicates" and describe it cautiously. When stored news is empty,
say: "No stored news context is currently available for this flight." When the
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
NO_NEWS_CONTEXT = "No stored news context is currently available for this flight."
EXTREME_DELAY_THRESHOLD_MINUTES = 360
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


def _format_delay_investigation(result: Mapping[str, Any]) -> str:
    """Render one delay investigation from its structured, grounded evidence."""
    flight = result.get("flight")
    sections = ["### Confirmed flight facts"]
    if isinstance(flight, Mapping):
        fact_fields = (
            ("flight_number", "Flight"),
            ("airline", "Airline"),
            ("origin_iata", "Origin"),
            ("destination_iata", "Destination"),
            ("status", "Status"),
            ("scheduled_departure", "Scheduled departure"),
            ("actual_departure", "Actual departure"),
            ("scheduled_arrival", "Scheduled arrival"),
            ("actual_arrival", "Actual arrival"),
        )
        fact_lines = [
            f"- {label}: {flight[key]}"
            for key, label in fact_fields
            if flight.get(key) is not None
        ]
        for key, label in (
            ("departure_delay_minutes", "departure"),
            ("arrival_delay_minutes", "arrival"),
        ):
            delay = flight.get(key)
            if delay is None:
                continue
            if isinstance(delay, (int, float)) and abs(delay) > EXTREME_DELAY_THRESHOLD_MINUTES:
                fact_lines.append(
                    "- The stored Flight Pulse record indicates a "
                    f"{label} delay value of {delay} minutes. This exceeds the "
                    "project's 360-minute quality threshold and should be "
                    "interpreted cautiously."
                )
            else:
                fact_lines.append(f"- {label.capitalize()} delay: {delay} minutes")
        sections.append(
            "\n".join(fact_lines)
            if fact_lines
            else "A stored flight record was found, but its operational fields are empty."
        )
    else:
        sections.append("No matching stored flight record was found.")

    sections.append("\n### Weather context")
    weather = result.get("weather_context")
    if isinstance(weather, Mapping):
        weather_fields = (
            ("observation_time", "Observation time"),
            ("temperature_c", "Temperature (°C)"),
            ("precipitation_mm", "Precipitation (mm)"),
            ("snowfall_cm", "Snowfall (cm)"),
            ("visibility_m", "Visibility (m)"),
            ("wind_speed_kmh", "Wind speed (km/h)"),
            ("wind_gusts_kmh", "Wind gusts (km/h)"),
            ("weather_code", "Weather code"),
        )
        weather_lines = [
            f"- {label}: {weather[key]}"
            for key, label in weather_fields
            if weather.get(key) is not None
        ]
        sections.append(
            "\n".join(weather_lines)
            if weather_lines
            else "No stored weather context is currently available for this flight."
        )
    else:
        sections.append("No stored weather context is currently available for this flight.")

    sections.append("\n### News/disruption context")
    news = result.get("news_context")
    if isinstance(news, Sequence) and not isinstance(news, (str, bytes)) and news:
        news_lines = []
        for article in news:
            if not isinstance(article, Mapping):
                continue
            title = article.get("title") or "Untitled stored article"
            source = article.get("source_domain") or "unknown source"
            published = article.get("published_at")
            timing = f", published {published}" if published is not None else ""
            news_lines.append(f"- {title} ({source}{timing})")
        sections.append("\n".join(news_lines) if news_lines else NO_NEWS_CONTEXT)
    else:
        sections.append(NO_NEWS_CONTEXT)

    sections.append("\n### Conclusion")
    sections.append(INSUFFICIENT_EVIDENCE)
    return "\n".join(sections)


def _final_text(
    response: Any,
    *,
    insufficient_evidence: bool,
    investigation: Mapping[str, Any] | None = None,
) -> str:
    if investigation is not None:
        text = _format_delay_investigation(investigation)
    else:
        text = (getattr(response, "text", None) or "").strip()
    if not text:
        text = "I could not produce a grounded answer from the available data."
    if insufficient_evidence and INSUFFICIENT_EVIDENCE not in text:
        text = f"{text}\n\n{INSUFFICIENT_EVIDENCE}"
    text = text.replace(SAMPLE_LIMITATION, "").strip()
    return f"{text}\n\n{SAMPLE_LIMITATION}"


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
        investigation: Mapping[str, Any] | None = None
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
                        investigation=investigation,
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
                    if name == "investigate_delay" and isinstance(result, Mapping):
                        investigation = result
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
