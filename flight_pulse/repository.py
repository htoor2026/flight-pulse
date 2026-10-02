"""MySQL persistence for normalized flight records."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime
from typing import Any

import mysql.connector

from flight_pulse.config import MySQLSettings
from flight_pulse.models import NormalizedFlight, NormalizedWeatherObservation


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


UPSERT_WEATHER_SQL = """
INSERT INTO weather_observations (
    airport_iata,
    observation_time,
    temperature_c,
    precipitation_mm,
    snowfall_cm,
    visibility_m,
    wind_speed_kmh,
    wind_gusts_kmh,
    weather_code,
    fetched_at
) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
ON DUPLICATE KEY UPDATE
    temperature_c = VALUES(temperature_c),
    precipitation_mm = VALUES(precipitation_mm),
    snowfall_cm = VALUES(snowfall_cm),
    visibility_m = VALUES(visibility_m),
    wind_speed_kmh = VALUES(wind_speed_kmh),
    wind_gusts_kmh = VALUES(wind_gusts_kmh),
    weather_code = VALUES(weather_code),
    fetched_at = VALUES(fetched_at)
""".strip()


FLIGHT_WINDOW_SQL = """
SELECT
    MIN(
        CASE
            WHEN origin_iata = %s THEN scheduled_departure
            WHEN destination_iata = %s THEN scheduled_arrival
        END
    ) AS window_start,
    MAX(
        CASE
            WHEN origin_iata = %s THEN scheduled_departure
            WHEN destination_iata = %s THEN scheduled_arrival
        END
    ) AS window_end
FROM flights
WHERE origin_iata = %s OR destination_iata = %s
""".strip()


FLIGHT_WEATHER_MATCH_SUMMARY_SQL = """
WITH airport_flights AS (
    SELECT
        provider_flight_id,
        CASE
            WHEN origin_iata = %s THEN scheduled_departure
            ELSE scheduled_arrival
        END AS airport_event_time
    FROM flights
    WHERE origin_iata = %s OR destination_iata = %s
)
SELECT
    COUNT(*) AS total_flights,
    SUM(weather.observation_time IS NOT NULL) AS matched_flights
FROM airport_flights AS flight
LEFT JOIN weather_observations AS weather
    ON weather.airport_iata = %s
    AND weather.observation_time = DATE_FORMAT(
        flight.airport_event_time,
        '%Y-%m-%d %H:00:00'
    )
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


def _weather_values(observation: NormalizedWeatherObservation) -> tuple[object, ...]:
    return (
        observation.airport_iata.strip().upper(),
        _mysql_datetime(observation.observation_time),
        observation.temperature_c,
        observation.precipitation_mm,
        observation.snowfall_cm,
        observation.visibility_m,
        observation.wind_speed_kmh,
        observation.wind_gusts_kmh,
        observation.weather_code,
        _mysql_datetime(observation.fetched_at),
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


class WeatherRepository:
    """Read flight windows and persist normalized hourly weather."""

    def __init__(self, connection: Any) -> None:
        self._connection = connection

    def flight_time_window(self, airport_iata: str) -> tuple[datetime, datetime]:
        airport = airport_iata.strip().upper()
        if len(airport) != 3 or not airport.isalpha():
            raise ValueError("airport_iata must be a three-letter IATA code")

        cursor = self._connection.cursor(dictionary=True)
        try:
            cursor.execute(FLIGHT_WINDOW_SQL, (airport,) * 6)
            row = cursor.fetchone() or {}
        finally:
            cursor.close()

        start = row.get("window_start")
        end = row.get("window_end")
        if not isinstance(start, datetime) or not isinstance(end, datetime):
            raise ValueError(f"No scheduled flight window found for {airport}")
        return start.replace(tzinfo=UTC), end.replace(tzinfo=UTC)

    def upsert_many(
        self,
        observations: Iterable[NormalizedWeatherObservation],
    ) -> int:
        records = list(observations)
        if not records:
            return 0

        cursor = self._connection.cursor()
        try:
            cursor.executemany(
                UPSERT_WEATHER_SQL,
                [_weather_values(observation) for observation in records],
            )
            self._connection.commit()
        except Exception:
            self._connection.rollback()
            raise
        finally:
            cursor.close()
        return len(records)

    def flight_match_summary(self, airport_iata: str) -> dict[str, Any]:
        airport = airport_iata.strip().upper()
        if len(airport) != 3 or not airport.isalpha():
            raise ValueError("airport_iata must be a three-letter IATA code")

        cursor = self._connection.cursor(dictionary=True)
        try:
            cursor.execute(
                FLIGHT_WEATHER_MATCH_SUMMARY_SQL,
                (airport, airport, airport, airport),
            )
            return cursor.fetchone() or {}
        finally:
            cursor.close()
