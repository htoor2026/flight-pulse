from __future__ import annotations

import json
import os
import unittest
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

from streamlit.testing.v1 import AppTest

from flight_pulse.config import demo_mode_enabled
from flight_pulse.demo import DEMO_REPORT_PATH, REQUIRED_SECTIONS, load_demo_report


APP_PATH = Path(__file__).resolve().parent.parent / "app.py"


class DemoModeConfigurationTests(unittest.TestCase):
    @patch("flight_pulse.config.load_dotenv")
    def test_missing_value_defaults_to_mysql_mode(self, _load_dotenv: Mock) -> None:
        with patch.dict(os.environ, {}, clear=True):
            self.assertFalse(demo_mode_enabled())

    @patch("flight_pulse.config.load_dotenv")
    def test_accepts_explicit_true_and_false_values(
        self,
        _load_dotenv: Mock,
    ) -> None:
        cases = {
            "1": True,
            "true": True,
            "YES": True,
            " on ": True,
            "0": False,
            "false": False,
            "NO": False,
            " off ": False,
        }
        for value, expected in cases.items():
            with self.subTest(value=value), patch.dict(
                os.environ,
                {"DEMO_MODE": value},
                clear=True,
            ):
                self.assertIs(demo_mode_enabled(), expected)

    @patch("flight_pulse.config.load_dotenv")
    def test_rejects_empty_and_invalid_values(self, _load_dotenv: Mock) -> None:
        for value in ("", "demo", "2"):
            with self.subTest(value=value), patch.dict(
                os.environ,
                {"DEMO_MODE": value},
                clear=True,
            ):
                with self.assertRaisesRegex(ValueError, "DEMO_MODE must be one of"):
                    demo_mode_enabled()


class DemoReportTests(unittest.TestCase):
    def test_snapshot_matches_dashboard_contract_and_validated_metrics(self) -> None:
        report = load_demo_report()
        overview = report["overview"]
        weather = report["weather_context"]

        self.assertEqual(set(report), set(REQUIRED_SECTIONS))
        self.assertEqual(overview["total_flights"], 72)
        self.assertEqual(overview["delayed_flights"], 8)
        self.assertEqual(overview["cancelled_flights"], 1)
        self.assertEqual(overview["delay_rate_percent"], 11.11)
        self.assertEqual(overview["median_departure_delay_minutes"], 21.0)
        self.assertEqual(overview["departure_delay_samples"], 3)
        self.assertEqual(len(weather), 48)
        self.assertEqual(sum(row["total_flights"] for row in weather), 72)

        self.assertEqual(
            sum(row["flight_count"] for row in report["status_counts"]),
            overview["total_flights"],
        )
        self.assertEqual(
            sum(row["delayed_flights"] for row in report["delays_by_airline"]),
            overview["delayed_flights"],
        )
        self.assertEqual(
            sum(row["delayed_flights"] for row in report["delays_by_route"]),
            overview["delayed_flights"],
        )
        self.assertEqual(
            sum(row["delayed_flights"] for row in report["delays_by_hour"]),
            overview["delayed_flights"],
        )
        self.assertEqual(
            sum(row["delayed_flights"] for row in weather),
            overview["delayed_flights"],
        )
        self.assertEqual(
            sum(row["cancelled_flights"] for row in weather),
            overview["cancelled_flights"],
        )

        hourly_weather = defaultdict(lambda: {"total_flights": 0, "delayed_flights": 0})
        for row in weather:
            hour = datetime.fromisoformat(
                row["observation_time"].replace("Z", "+00:00")
            ).hour
            hourly_weather[hour]["total_flights"] += row["total_flights"]
            hourly_weather[hour]["delayed_flights"] += row["delayed_flights"]
        self.assertEqual(
            {
                hour: counts
                for hour, counts in hourly_weather.items()
                if counts["total_flights"] or counts["delayed_flights"]
            },
            {
                row["scheduled_hour_utc"]: {
                    "total_flights": row["total_flights"],
                    "delayed_flights": row["delayed_flights"],
                }
                for row in report["delays_by_hour"]
            },
        )

    def test_snapshot_contains_no_obvious_secrets_or_provider_fields(self) -> None:
        report = json.loads(DEMO_REPORT_PATH.read_text(encoding="utf-8"))
        forbidden_keys = {
            "api_key",
            "apikey",
            "credential",
            "fetched_at",
            "password",
            "provider_flight_id",
            "rapidapi",
            "secret",
            "token",
            "url",
        }
        forbidden_values = (
            "aerodatabox",
            "rapidapi",
            "x-rapidapi",
            "mysql://",
            "gemini_api_key",
        )

        def inspect(value: object) -> None:
            if isinstance(value, dict):
                for key, child in value.items():
                    normalized_key = str(key).lower()
                    self.assertFalse(
                        any(part in normalized_key for part in forbidden_keys),
                        normalized_key,
                    )
                    inspect(child)
            elif isinstance(value, list):
                for child in value:
                    inspect(child)
            elif isinstance(value, str):
                normalized_value = value.lower()
                self.assertFalse(
                    any(part in normalized_value for part in forbidden_values),
                    value,
                )

        inspect(report)


class DemoModeStreamlitTests(unittest.TestCase):
    def test_demo_mode_renders_offline_without_database_or_gemini(self) -> None:
        with (
            patch.dict(os.environ, {"DEMO_MODE": "true"}, clear=True),
            patch("flight_pulse.config.load_dotenv"),
            patch(
                "flight_pulse.repository.connect_mysql",
                side_effect=AssertionError("MySQL must not be used in demo mode"),
            ) as connect_mysql,
            patch(
                "flight_pulse.chat.GeminiAnalystChat",
                side_effect=AssertionError("Gemini chat must not be constructed"),
            ) as chat,
            patch(
                "flight_pulse.chat.gemini.genai.Client",
                side_effect=AssertionError("Gemini client must not be constructed"),
            ) as gemini_client,
            patch(
                "urllib.request.urlopen",
                side_effect=AssertionError("External requests are forbidden"),
            ) as urlopen,
            patch(
                "socket.create_connection",
                side_effect=AssertionError("Network access is forbidden"),
            ) as create_connection,
        ):
            app = AppTest.from_file(APP_PATH).run(timeout=30)

        self.assertEqual(list(app.exception), [])
        top_level_tabs = [
            child
            for child in app.main.children.values()
            if getattr(child, "type", None) == "tab_container"
        ]
        self.assertEqual(len(top_level_tabs), 1)
        self.assertEqual(
            [tab.label for tab in top_level_tabs[0].children.values()],
            ["Flight Analytics", "Business Overview", "Technical Overview"],
        )
        self.assertIn("Overview", [header.value for header in app.header])
        self.assertIn("Business Overview", [header.value for header in app.header])
        self.assertIn("Technical Overview", [header.value for header in app.header])
        self.assertIn(
            "Public demo mode uses a synthetic snapshot modeled on the project's "
            "validated local results. It does not query live flight, weather, news, "
            "or database services.",
            [message.value for message in app.info],
        )
        self.assertEqual(len(app.chat_input), 0)
        connect_mysql.assert_not_called()
        chat.assert_not_called()
        gemini_client.assert_not_called()
        urlopen.assert_not_called()
        create_connection.assert_not_called()

    def test_false_mode_uses_existing_mysql_report_path(self) -> None:
        connection = Mock()
        report = load_demo_report()
        environment = {
            "DEMO_MODE": "false",
            "MYSQL_DATABASE": "flight_pulse",
            "MYSQL_USER": "test-user",
            "MYSQL_PASSWORD": "test-password",
        }
        with (
            patch.dict(os.environ, environment, clear=True),
            patch("flight_pulse.config.load_dotenv"),
            patch(
                "flight_pulse.repository.connect_mysql",
                return_value=connection,
            ) as connect_mysql,
            patch("flight_pulse.analysis.FlightAnalysis") as analysis,
        ):
            analysis.return_value.report.return_value = report
            app = AppTest.from_file(APP_PATH).run(timeout=30)

        self.assertEqual(list(app.exception), [])
        connect_mysql.assert_called_once()
        analysis.assert_called_once_with(connection)
        analysis.return_value.report.assert_called_once_with(
            minimum_flights=1,
            top_limit=10,
        )
        connection.close.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
