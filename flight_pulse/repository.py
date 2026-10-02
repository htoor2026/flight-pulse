"""MySQL persistence for normalized flight records."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime
from typing import Any

import mysql.connector

from flight_pulse.config import MySQLSettings
from flight_pulse.models import NormalizedFlight


UPSERT_FLIGHT_SQL = """
INSERT INTO flights (
    provider_flight_id,
    flight_number,
    airline,
    origin_iata,
    destination_iata,
    scheduled_departure,
    actual_departure,
    scheduled_arrival,
    actual_arrival,
    status,
    departure_delay_minutes,
    arrival_delay_minutes,
    fetched_at
) VALUES (
    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
)
ON DUPLICATE KEY UPDATE
    flight_number = VALUES(flight_number),
    airline = VALUES(airline),
    origin_iata = VALUES(origin_iata),
    destination_iata = VALUES(destination_iata),
    scheduled_departure = VALUES(scheduled_departure),
    actual_departure = VALUES(actual_departure),
    scheduled_arrival = VALUES(scheduled_arrival),
    actual_arrival = VALUES(actual_arrival),
    status = VALUES(status),
    departure_delay_minutes = VALUES(departure_delay_minutes),
    arrival_delay_minutes = VALUES(arrival_delay_minutes),
    fetched_at = VALUES(fetched_at)
""".strip()


def connect_mysql(settings: MySQLSettings) -> Any:
    """Create a MySQL connection only when explicitly called."""
    return mysql.connector.connect(
        host=settings.host,
        port=settings.port,
        database=settings.database,
        user=settings.user,
        password=settings.password,
        autocommit=False,
    )


def _mysql_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.utcoffset() is None:
        raise ValueError("MySQL timestamps must be timezone-aware before persistence")
    return value.astimezone(UTC).replace(tzinfo=None)


def _flight_values(flight: NormalizedFlight) -> tuple[object, ...]:
    return (
        flight.provider_flight_id,
        flight.flight_number,
        flight.airline,
        flight.origin_iata,
        flight.destination_iata,
        _mysql_datetime(flight.scheduled_departure),
        _mysql_datetime(flight.actual_departure),
        _mysql_datetime(flight.scheduled_arrival),
        _mysql_datetime(flight.actual_arrival),
        flight.status,
        flight.departure_delay_minutes,
        flight.arrival_delay_minutes,
        _mysql_datetime(flight.fetched_at),
    )


class FlightRepository:
    """Store normalized flights using an existing MySQL connection."""

    def __init__(self, connection: Any) -> None:
        self._connection = connection

    def upsert_many(self, flights: Iterable[NormalizedFlight]) -> int:
        records = list(flights)
        if not records:
            return 0

        cursor = self._connection.cursor()
        try:
            cursor.executemany(
                UPSERT_FLIGHT_SQL,
                [_flight_values(flight) for flight in records],
            )
            self._connection.commit()
        except Exception:
            self._connection.rollback()
            raise
        finally:
            cursor.close()

        return len(records)
