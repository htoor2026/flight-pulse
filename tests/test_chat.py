from __future__ import annotations

import os
import unittest
from unittest.mock import Mock, patch

from google.genai import types

from flight_pulse.analyst import INSUFFICIENT_EVIDENCE, FlightAnalyst
from flight_pulse.chat.gemini import (
    SAMPLE_LIMITATION,
    GeminiAnalystChat,
    ToolValidationError,
    dispatch_tool,
)
from flight_pulse.config import GeminiSettings


def _tool_call_response(
    name: str,
    arguments: dict[str, object],
    *,
    call_id: str = "call-1",
) -> types.GenerateContentResponse:
    return types.GenerateContentResponse(
        candidates=[
            types.Candidate(
                content=types.Content(
                    role="model",
                    parts=[
                        types.Part(
                            function_call=types.FunctionCall(
                                id=call_id,
                                name=name,
                                args=arguments,
                            )
                        )
                    ],
                )
            )
        ]
    )


def _text_response(text: str) -> types.GenerateContentResponse:
    return types.GenerateContentResponse(
        candidates=[
            types.Candidate(
                content=types.Content(
                    role="model",
                    parts=[types.Part(text=text)],
                )
            )
        ]
    )


class ToolDispatchTests(unittest.TestCase):
    def setUp(self) -> None:
        self.analyst = Mock(spec=FlightAnalyst)

    def test_dispatches_an_approved_tool_with_valid_arguments(self) -> None:
        self.analyst.find_flight.return_value = {"flight_number": "AA 3606"}

        result = dispatch_tool(
            self.analyst,
            "find_flight",
            {"flight_number": "AA 3606"},
        )

        self.assertEqual(result, {"flight_number": "AA 3606"})
        self.analyst.find_flight.assert_called_once_with(flight_number="AA 3606")

    def test_rejects_unknown_tools_without_execution(self) -> None:
        with self.assertRaisesRegex(ToolValidationError, "unapproved"):
            dispatch_tool(self.analyst, "query_sql", {"sql": "SELECT 1"})

        self.assertEqual(self.analyst.mock_calls, [])

    def test_rejects_missing_extra_and_wrong_type_arguments(self) -> None:
        invalid_calls = (
            ("find_flight", {}),
            ("find_flight", {"flight_number": "AC154", "sql": "SELECT 1"}),
            ("get_flight_overview", {"include_breakdowns": 1}),
            (
                "get_route_analysis",
                {"origin": "YYZ", "destination": "ORD", "limit": True},
            ),
        )

        for name, arguments in invalid_calls:
            with self.subTest(name=name, arguments=arguments):
                with self.assertRaises(ToolValidationError):
                    dispatch_tool(self.analyst, name, arguments)

        self.assertEqual(self.analyst.mock_calls, [])


class GeminiAnalystChatTests(unittest.TestCase):
    def setUp(self) -> None:
        self.analyst = Mock(spec=FlightAnalyst)
        self.client = Mock()
        self.settings = GeminiSettings(
            api_key="synthetic-test-key",
            model="gemini-3.1-flash-lite",
        )
        self.chat = GeminiAnalystChat(
            self.analyst,
            self.settings,
            client=self.client,
        )

    def test_executes_declared_tool_and_returns_grounded_model_text(self) -> None:
        self.analyst.get_flight_overview.return_value = {
            "total_flights": 72,
            "delayed_flights": 8,
        }
        self.client.models.generate_content.side_effect = [
            _tool_call_response("get_flight_overview", {}),
            _text_response(
                "There are 8 delayed flights in the current Flight Pulse sample."
            ),
        ]

        reply = self.chat.answer("How many flights were delayed?")

        self.assertEqual(
            reply.text,
            (
                "There are 8 delayed flights in the current Flight Pulse sample."
                f"\n\n{SAMPLE_LIMITATION}"
            ),
        )
        self.assertEqual(
            reply.tool_calls,
            ({"name": "get_flight_overview", "arguments": {}},),
        )
        self.assertEqual(reply.api_requests, 2)
        self.analyst.get_flight_overview.assert_called_once_with()
        self.assertEqual(self.client.models.generate_content.call_count, 2)

        first_call = self.client.models.generate_content.call_args_list[0].kwargs
        self.assertEqual(first_call["model"], "gemini-3.1-flash-lite")
        declarations = first_call["config"].tools[0].function_declarations
        self.assertEqual(
            {declaration.name for declaration in declarations},
            {
                "get_flight_overview",
                "find_flight",
                "get_airline_analysis",
                "get_route_analysis",
                "get_weather_context",
                "get_news_context",
                "investigate_delay",
            },
        )

        second_call = self.client.models.generate_content.call_args_list[1].kwargs
        function_response = second_call["contents"][-1].parts[0].function_response
        self.assertEqual(function_response.id, "call-1")
        self.assertEqual(function_response.name, "get_flight_overview")
        self.assertEqual(function_response.response["result"]["delayed_flights"], 8)

    def test_unknown_model_tool_request_is_returned_as_error_not_executed(self) -> None:
        self.client.models.generate_content.side_effect = [
            _tool_call_response("query_sql", {"sql": "DROP TABLE flights"}),
            _text_response("That operation is unavailable."),
        ]

        reply = self.chat.answer("Delete the flight data")

        self.assertIn("unavailable", reply.text)
        self.assertEqual(self.analyst.mock_calls, [])
        second_call = self.client.models.generate_content.call_args_list[1].kwargs
        payload = second_call["contents"][-1].parts[0].function_response.response
        self.assertIn("error", payload)

    def test_validation_mode_forces_overview_breakdowns_off(self) -> None:
        restricted_chat = GeminiAnalystChat(
            self.analyst,
            self.settings,
            client=self.client,
            allow_overview_breakdowns=False,
        )
        self.analyst.get_flight_overview.return_value = {
            "total_flights": 72,
            "delayed_flights": 8,
        }
        self.client.models.generate_content.side_effect = [
            _tool_call_response(
                "get_flight_overview",
                {"include_breakdowns": True},
            ),
            _text_response("There were 8 delayed flights."),
        ]

        reply = restricted_chat.answer("How many flights were delayed?")

        self.analyst.get_flight_overview.assert_called_once_with(
            include_breakdowns=False
        )
        self.assertEqual(
            reply.tool_calls[0]["arguments"],
            {"include_breakdowns": False},
        )

    def test_investigation_enforces_exact_insufficient_evidence_wording(self) -> None:
        self.analyst.investigate_delay.return_value = {
            "flight_number": "AA3606",
            "weather_context": {"wind_gusts_kmh": 46.8},
            "news_context": [],
            "conclusion": INSUFFICIENT_EVIDENCE,
        }
        self.client.models.generate_content.side_effect = [
            _tool_call_response(
                "investigate_delay",
                {"flight_number": "AA 3606"},
            ),
            _text_response("Wind gusts were recorded near the scheduled YYZ time."),
        ]

        reply = self.chat.answer("Why was AA 3606 delayed?")

        self.assertIn(INSUFFICIENT_EVIDENCE, reply.text)
        self.assertIn(SAMPLE_LIMITATION, reply.text)

    def test_previous_streamlit_history_is_sent_as_conversation_context(self) -> None:
        self.client.models.generate_content.return_value = _text_response(
            "I can help with the current Flight Pulse sample."
        )

        self.chat.answer(
            "What about its weather?",
            history=[
                {"role": "user", "content": "Tell me about AA 3606."},
                {"role": "assistant", "content": "AA 3606 flew YYZ to ORD."},
            ],
        )

        contents = self.client.models.generate_content.call_args.kwargs["contents"]
        self.assertEqual([content.role for content in contents], ["user", "model", "user"])
        self.assertEqual(contents[-1].parts[0].text, "What about its weather?")

    def test_empty_question_does_not_call_gemini(self) -> None:
        with self.assertRaisesRegex(ValueError, "must not be empty"):
            self.chat.answer("   ")

        self.client.models.generate_content.assert_not_called()


class GeminiSettingsTests(unittest.TestCase):
    def test_reads_api_key_and_model_from_environment(self) -> None:
        with patch.dict(
            os.environ,
            {
                "GEMINI_API_KEY": "synthetic-key",
                "GEMINI_MODEL": "gemini-3.1-flash-lite",
            },
        ):
            settings = GeminiSettings.from_env()

        self.assertEqual(settings.api_key, "synthetic-key")
        self.assertEqual(settings.model, "gemini-3.1-flash-lite")


if __name__ == "__main__":
    unittest.main()
