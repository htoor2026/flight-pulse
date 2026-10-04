from __future__ import annotations

import sqlite3
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

    def _execute_overview_semantics_in_sqlite(
        self,
        departure_delays: list[int | None],
    ) -> dict[str, object]:
        """Exercise median semantics only; MySQL syntax needs integration proof."""
        connection = sqlite3.connect(":memory:")
        connection.row_factory = sqlite3.Row
        try:
            connection.execute(
                """
                CREATE TABLE flights (
                    status TEXT,
                    departure_delay_minutes INTEGER,
                    arrival_delay_minutes INTEGER
                )
                """
            )
            connection.executemany(
                "INSERT INTO flights VALUES ('scheduled', ?, NULL)",
                [(delay,) for delay in departure_delays],
            )
            sqlite_sql = OVERVIEW_SQL.replace(" DIV ", " / ")
            return dict(connection.execute(sqlite_sql).fetchone())
        finally:
            connection.close()

    def test_overview_returns_database_aggregates_and_closes_cursor(self) -> None:
        expected = {
            "total_flights": 12,
            "delayed_flights": 4,
            "cancelled_flights": 1,
            "delay_rate_percent": 33.33,
            "average_departure_delay_minutes": 14.5,
            "median_departure_delay_minutes": 12.0,
            "average_arrival_delay_minutes": 9.0,
            "departure_delay_samples": 4,
            "arrival_delay_samples": 3,
        }
        self.cursor.fetchone.return_value = expected

        result = self.analysis.overview()

        self.assertEqual(result, expected)
        self.connection.cursor.assert_called_once_with(dictionary=True)
        self.cursor.execute.assert_called_once_with(OVERVIEW_SQL, ())
        self.cursor.close.assert_called_once_with()

    def test_sqlite_semantics_calculate_odd_sample_median(self) -> None:
        result = self._execute_overview_semantics_in_sqlite([5, 20, 90])

        self.assertEqual(result["median_departure_delay_minutes"], 20.0)
        self.assertEqual(result["departure_delay_samples"], 3)

    def test_sqlite_semantics_calculate_even_sample_median(self) -> None:
        result = self._execute_overview_semantics_in_sqlite([5, 20, 30, 90])

        self.assertEqual(result["median_departure_delay_minutes"], 25.0)
        self.assertEqual(result["departure_delay_samples"], 4)

    def test_sqlite_semantics_have_no_median_without_delay_observations(self) -> None:
        result = self._execute_overview_semantics_in_sqlite([None, None])

        self.assertIsNone(result["median_departure_delay_minutes"])
        self.assertEqual(result["departure_delay_samples"], 0)

    def test_overview_sql_uses_non_reserved_delay_rank_alias(self) -> None:
        normalized_sql = " ".join(OVERVIEW_SQL.split()).lower()

        self.assertIn(
            "row_number() over (order by departure_delay_minutes) as delay_rank",
            normalized_sql,
        )
        self.assertIn("where ranked.delay_rank in", normalized_sql)
        self.assertNotIn("as row_number", normalized_sql)
        self.assertNotIn("ranked.row_number", normalized_sql)

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

    def test_disrupted_flights_limit_is_parameterized(self) -> None:
        self.cursor.fetchall.return_value = []

        result = self.analysis.disrupted_flights(limit=25)

        self.assertEqual(result, [])
        sql, params = self.cursor.execute.call_args.args
        self.assertIn("status = 'cancelled'", sql)
        self.assertEqual(params, (25,))

    def test_weather_context_uses_parameterized_airport(self) -> None:
        self.cursor.fetchall.return_value = []

        result = self.analysis.weather_context(airport_iata="yyz")

        self.assertEqual(result, [])
        sql, params = self.cursor.execute.call_args.args
        self.assertIn("weather_observations", sql)
        self.assertEqual(params, ("YYZ",) * 4)


if __name__ == "__main__":
    unittest.main()
