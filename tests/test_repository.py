from __future__ import annotations

import unittest
from datetime import UTC, datetime, timedelta, timezone
from unittest.mock import Mock, patch

from flight_pulse.config import MySQLSettings
from flight_pulse.models import NormalizedFlight
from flight_pulse.pipeline import ingest_yyz_window
from flight_pulse.repository import FlightRepository, connect_mysql


def _flight() -> NormalizedFlight:
    eastern = timezone(timedelta(hours=-4))
    return NormalizedFlight(
        provider_flight_id="aerodatabox:AC101:YYZ:YVR:2026-10-02T14:00:00+00:00",
        flight_number="AC101",
        airline="Air Canada",
        origin_iata="YYZ",
        destination_iata="YVR",
        scheduled_departure=datetime(2026, 10, 2, 10, 0, tzinfo=eastern),
        actual_departure=datetime(2026, 10, 2, 10, 15, tzinfo=eastern),
        scheduled_arrival=datetime(2026, 10, 2, 19, 0, tzinfo=UTC),
        actual_arrival=datetime(2026, 10, 2, 19, 10, tzinfo=UTC),
        status="arrived",
        departure_delay_minutes=15,
        arrival_delay_minutes=10,
        fetched_at=datetime(2026, 10, 2, 20, 0, tzinfo=UTC),
    )


class MySQLConnectionTests(unittest.TestCase):
    @patch("flight_pulse.repository.mysql.connector.connect")
    def test_connect_mysql_passes_only_configured_values(self, connect: Mock) -> None:
        settings = MySQLSettings(
            host="localhost",
            port=3306,
            database="flight_pulse",
            user="flight_user",
            password="synthetic-password",
        )

        result = connect_mysql(settings)

        self.assertIs(result, connect.return_value)
        connect.assert_called_once_with(
            host="localhost",
            port=3306,
            database="flight_pulse",
            user="flight_user",
            password="synthetic-password",
            autocommit=False,
        )


class FlightRepositoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.cursor = Mock()
        self.connection = Mock()
        self.connection.cursor.return_value = self.cursor
        self.repository = FlightRepository(self.connection)

    def test_upsert_uses_parameters_and_commits(self) -> None:
        count = self.repository.upsert_many([_flight()])

        self.assertEqual(count, 1)
        self.cursor.executemany.assert_called_once()
        sql, rows = self.cursor.executemany.call_args.args
        row = rows[0]

        self.assertIn("ON DUPLICATE KEY UPDATE", sql)
        self.assertEqual(row[0], _flight().provider_flight_id)
        self.assertEqual(row[5], datetime(2026, 10, 2, 14, 0))
        self.assertIsNone(row[5].tzinfo)
        self.assertEqual(row[6], datetime(2026, 10, 2, 14, 15))
        self.assertEqual(row[12], datetime(2026, 10, 2, 20, 0))
        self.connection.commit.assert_called_once_with()
        self.connection.rollback.assert_not_called()
        self.cursor.close.assert_called_once_with()

    def test_upsert_rolls_back_and_closes_cursor_on_failure(self) -> None:
        self.cursor.executemany.side_effect = RuntimeError("synthetic failure")

        with self.assertRaisesRegex(RuntimeError, "synthetic failure"):
            self.repository.upsert_many([_flight()])

        self.connection.commit.assert_not_called()
        self.connection.rollback.assert_called_once_with()
        self.cursor.close.assert_called_once_with()

    def test_empty_batch_does_not_open_cursor(self) -> None:
        count = self.repository.upsert_many([])

        self.assertEqual(count, 0)
        self.connection.cursor.assert_not_called()
        self.connection.commit.assert_not_called()


class PipelineTests(unittest.TestCase):
    def test_pipeline_fetches_yyz_and_persists_returned_records(self) -> None:
        from_local = datetime(2026, 10, 2, 10, 0)
        to_local = datetime(2026, 10, 2, 12, 0)
        flight = _flight()
        client = Mock()
        repository = Mock()
        client.fetch_airport_flights.return_value = [flight]
        repository.upsert_many.return_value = 1

        result = ingest_yyz_window(client, repository, from_local, to_local)

        self.assertEqual(result, 1)
        client.fetch_airport_flights.assert_called_once_with(
            "YYZ",
            from_local,
            to_local,
        )
        repository.upsert_many.assert_called_once_with([flight])


if __name__ == "__main__":
    unittest.main()
