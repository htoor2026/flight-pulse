from __future__ import annotations

import re
import unittest
from datetime import datetime
from decimal import Decimal
from unittest.mock import Mock

from flight_pulse.analyst import (
    INSUFFICIENT_EVIDENCE,
    TOOL_DEFINITIONS,
    FlightAnalyst,
)
from flight_pulse.analyst.tools import (
    AIRLINE_ANALYSIS_SQL,
    FIND_FLIGHT_SQL,
    FLIGHT_NEWS_SQL,
    FLIGHT_WEATHER_SQL,
    READ_ONLY_SQL,
    ROUTE_FLIGHTS_SQL,
    ROUTE_STATUS_SQL,
    ROUTE_SUMMARY_SQL,
)


class FlightAnalystTests(unittest.TestCase):
    def setUp(self) -> None:
        self.cursor = Mock()
        self.connection = Mock()
        self.connection.cursor.return_value = self.cursor
        self.analysis = Mock()
        self.analyst = FlightAnalyst(self.connection, self.analysis)

    def test_overview_reuses_existing_analytics_and_returns_required_metrics(self) -> None:
        self.analysis.overview.return_value = {
            "total_flights": 72,
            "delayed_flights": 8,
            "cancelled_flights": 1,
            "delay_rate_percent": Decimal("11.11"),
            "average_departure_delay_minutes": Decimal("366.33"),
        }

        result = self.analyst.get_flight_overview()

        self.assertEqual(
            result,
            {
                "total_flights": 72,
                "delayed_flights": 8,
                "cancelled_flights": 1,
                "delay_rate_percent": 11.11,
            },
        )
        self.analysis.overview.assert_called_once_with()

    def test_find_flight_normalizes_input_and_serializes_database_values(self) -> None:
        self.cursor.fetchone.return_value = {
            "flight_number": "AC 154",
            "scheduled_arrival": datetime(2026, 10, 2, 9, 0),
            "arrival_delay_minutes": Decimal("-23.00"),
        }

        result = self.analyst.find_flight(" ac 154 ")

        self.assertEqual(result["scheduled_arrival"], "2026-10-02T09:00:00Z")
        self.assertEqual(result["arrival_delay_minutes"], -23.0)
        self.cursor.execute.assert_called_once_with(FIND_FLIGHT_SQL, ("AC154",))
        self.cursor.close.assert_called_once_with()

    def test_missing_flight_returns_none(self) -> None:
        self.cursor.fetchone.return_value = None

        self.assertIsNone(self.analyst.find_flight("ZZ999"))

    def test_airline_analysis_is_parameterized(self) -> None:
        self.cursor.fetchone.return_value = {
            "airline": "Air Canada",
            "total_flights": 14,
            "delayed_flights": 2,
            "average_departure_delay_minutes": Decimal("19.50"),
        }

        result = self.analyst.get_airline_analysis(" Air Canada ")

        self.assertEqual(result["average_departure_delay_minutes"], 19.5)
        self.cursor.execute.assert_called_once_with(
            AIRLINE_ANALYSIS_SQL,
            ("Air Canada", "Air Canada"),
        )

    def test_route_analysis_returns_summary_statuses_and_flights(self) -> None:
        self.cursor.fetchone.return_value = {
            "origin_iata": "YYZ",
            "destination_iata": "ORD",
            "total_flights": 3,
        }
        self.cursor.fetchall.side_effect = [
            [{"status": "departed", "flight_count": 2}],
            [{"flight_number": "AA 3606", "departure_delay_minutes": 1060}],
        ]

        result = self.analyst.get_route_analysis("yyz", "ord", limit=5)

        self.assertEqual(result["summary"]["total_flights"], 3)
        self.assertEqual(result["status_counts"][0]["status"], "departed")
        self.assertEqual(result["flights"][0]["flight_number"], "AA 3606")
        self.assertEqual(
            [call.args for call in self.cursor.execute.call_args_list],
            [
                (
                    ROUTE_SUMMARY_SQL,
                    ("YYZ", "ORD", "YYZ", "ORD"),
                ),
                (ROUTE_STATUS_SQL, ("YYZ", "ORD")),
                (ROUTE_FLIGHTS_SQL, ("YYZ", "ORD", 5)),
            ],
        )

    def test_weather_context_returns_none_when_no_match_exists(self) -> None:
        self.cursor.fetchone.return_value = None

        result = self.analyst.get_weather_context("AC154")

        self.assertIsNone(result)
        self.cursor.execute.assert_called_once_with(FLIGHT_WEATHER_SQL, ("AC154",))

    def test_news_context_returns_empty_list_when_no_articles_exist(self) -> None:
        self.cursor.fetchall.return_value = []

        result = self.analyst.get_news_context("AC154", limit=4)

        self.assertEqual(result, [])
        self.cursor.execute.assert_called_once_with(FLIGHT_NEWS_SQL, ("AC154", 4))

    def test_delay_investigation_reports_insufficient_evidence(self) -> None:
        self.analyst.find_flight = Mock(
            return_value={
                "flight_number": "AC 154",
                "status": "arrived",
                "departure_delay_minutes": 21,
                "arrival_delay_minutes": -23,
            }
        )
        self.analyst.get_weather_context = Mock(return_value=None)
        self.analyst.get_news_context = Mock(return_value=[])

        result = self.analyst.investigate_delay("AC 154")

        self.assertEqual(result["conclusion"], INSUFFICIENT_EVIDENCE)
        self.assertIsNone(result["weather_context"])
        self.assertEqual(result["news_context"], [])

    def test_missing_flight_investigation_does_not_query_context(self) -> None:
        self.analyst.find_flight = Mock(return_value=None)
        self.analyst.get_weather_context = Mock()
        self.analyst.get_news_context = Mock()

        result = self.analyst.investigate_delay("ZZ999")

        self.assertEqual(result["conclusion"], INSUFFICIENT_EVIDENCE)
        self.assertIn("No matching stored flight", result["limitations"][0])
        self.analyst.get_weather_context.assert_not_called()
        self.analyst.get_news_context.assert_not_called()

    def test_sql_surface_is_read_only(self) -> None:
        forbidden = re.compile(
            r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|CREATE)\b"
            r"|\bREPLACE\s+INTO\b",
            re.IGNORECASE,
        )
        for sql in READ_ONLY_SQL:
            self.assertRegex(sql, r"^(SELECT|WITH)\b")
            self.assertIsNone(forbidden.search(sql))

    def test_tool_definitions_expose_only_the_approved_tools(self) -> None:
        self.assertEqual(
            {definition["name"] for definition in TOOL_DEFINITIONS},
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
        for definition in TOOL_DEFINITIONS:
            self.assertFalse(definition["parameters"]["additionalProperties"])


if __name__ == "__main__":
    unittest.main()
