from __future__ import annotations

import unittest
from unittest.mock import Mock

from flight_pulse.analysis.flights import (
    BY_AIRLINE_SQL,
    BY_HOUR_SQL,
    OVERVIEW_SQL,
    TOP_DELAYED_SQL,
    FlightAnalysis,
)


class FlightAnalysisTests(unittest.TestCase):
    def setUp(self) -> None:
        self.cursor = Mock()
        self.connection = Mock()
        self.connection.cursor.return_value = self.cursor
        self.analysis = FlightAnalysis(self.connection)

    def test_overview_returns_database_aggregates_and_closes_cursor(self) -> None:
        expected = {
            "total_flights": 12,
            "delayed_flights": 4,
            "cancelled_flights": 1,
            "delay_rate_percent": 33.33,
            "average_departure_delay_minutes": 14.5,
            "average_arrival_delay_minutes": 9.0,
        }
        self.cursor.fetchone.return_value = expected

        result = self.analysis.overview()

        self.assertEqual(result, expected)
        self.connection.cursor.assert_called_once_with(dictionary=True)
        self.cursor.execute.assert_called_once_with(OVERVIEW_SQL, ())
        self.cursor.close.assert_called_once_with()

    def test_airline_minimum_is_parameterized(self) -> None:
        self.cursor.fetchall.return_value = [
            {"airline": "Synthetic Air", "total_flights": 3}
        ]

        result = self.analysis.delays_by_airline(minimum_flights=3)

        self.assertEqual(result[0]["airline"], "Synthetic Air")
        self.cursor.execute.assert_called_once_with(BY_AIRLINE_SQL, (3,))
        self.cursor.close.assert_called_once_with()

    def test_top_delayed_limit_is_parameterized(self) -> None:
        self.cursor.fetchall.return_value = [{"flight_number": "AC101"}]

        result = self.analysis.top_delayed_flights(limit=5)

        self.assertEqual(result, [{"flight_number": "AC101"}])
        self.cursor.execute.assert_called_once_with(TOP_DELAYED_SQL, (5,))

    def test_hour_analysis_uses_parameterized_airport_context(self) -> None:
        self.cursor.fetchall.return_value = [{"scheduled_hour_utc": 12}]

        result = self.analysis.delays_by_hour(airport_iata="yyz")

        self.assertEqual(result, [{"scheduled_hour_utc": 12}])
        self.cursor.execute.assert_called_once_with(BY_HOUR_SQL, ("YYZ", "YYZ"))

    def test_rejects_invalid_group_and_limit_values_without_querying(self) -> None:
        with self.assertRaises(ValueError):
            self.analysis.delays_by_route(minimum_flights=0)
        with self.assertRaises(ValueError):
            self.analysis.top_delayed_flights(limit=101)
        with self.assertRaises(ValueError):
            self.analysis.delays_by_hour(airport_iata="Toronto")

        self.connection.cursor.assert_not_called()


if __name__ == "__main__":
    unittest.main()
