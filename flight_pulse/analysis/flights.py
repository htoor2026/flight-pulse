"""Readable MySQL analytics over normalized flight records."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any


DELAYED_PREDICATE = """(
    status = 'delayed'
    OR COALESCE(departure_delay_minutes, 0) > 0
    OR COALESCE(arrival_delay_minutes, 0) > 0
)"""


OVERVIEW_SQL = f"""
SELECT
    COUNT(*) AS total_flights,
    COALESCE(SUM(CASE WHEN {DELAYED_PREDICATE} THEN 1 ELSE 0 END), 0)
        AS delayed_flights,
    COALESCE(SUM(CASE WHEN status = 'cancelled' THEN 1 ELSE 0 END), 0)
        AS cancelled_flights,
    ROUND(
        100.0 * COALESCE(SUM(CASE WHEN {DELAYED_PREDICATE} THEN 1 ELSE 0 END), 0)
        / NULLIF(COUNT(*), 0),
        2
    ) AS delay_rate_percent,
    ROUND(AVG(departure_delay_minutes), 2) AS average_departure_delay_minutes,
    (
        SELECT ROUND(AVG(ranked.departure_delay_minutes), 2)
        FROM (
            SELECT
                departure_delay_minutes,
                ROW_NUMBER() OVER (ORDER BY departure_delay_minutes) AS delay_rank,
                COUNT(*) OVER () AS sample_count
            FROM flights
            WHERE departure_delay_minutes IS NOT NULL
        ) AS ranked
        WHERE ranked.delay_rank IN (
            (ranked.sample_count + 1) DIV 2,
            (ranked.sample_count + 2) DIV 2
        )
    ) AS median_departure_delay_minutes,
    ROUND(AVG(arrival_delay_minutes), 2) AS average_arrival_delay_minutes,
    COUNT(departure_delay_minutes) AS departure_delay_samples,
    COUNT(arrival_delay_minutes) AS arrival_delay_samples
FROM flights
""".strip()


STATUS_COUNTS_SQL = """
SELECT
    status,
    COUNT(*) AS flight_count
FROM flights
GROUP BY status
ORDER BY flight_count DESC, status
""".strip()


BY_AIRLINE_SQL = f"""
SELECT
    COALESCE(NULLIF(airline, ''), 'Unknown') AS airline,
    COUNT(*) AS total_flights,
    SUM(CASE WHEN {DELAYED_PREDICATE} THEN 1 ELSE 0 END) AS delayed_flights,
    ROUND(
        100.0 * SUM(CASE WHEN {DELAYED_PREDICATE} THEN 1 ELSE 0 END) / COUNT(*),
        2
    ) AS delay_rate_percent,
    ROUND(AVG(departure_delay_minutes), 2) AS average_departure_delay_minutes,
    ROUND(AVG(arrival_delay_minutes), 2) AS average_arrival_delay_minutes,
    COUNT(departure_delay_minutes) AS departure_delay_samples,
    COUNT(arrival_delay_minutes) AS arrival_delay_samples
FROM flights
GROUP BY COALESCE(NULLIF(airline, ''), 'Unknown')
HAVING COUNT(*) >= %s
ORDER BY delayed_flights DESC, delay_rate_percent DESC, airline
""".strip()


BY_ROUTE_SQL = f"""
SELECT
    COALESCE(origin_iata, 'Unknown') AS origin_iata,
    COALESCE(destination_iata, 'Unknown') AS destination_iata,
    COUNT(*) AS total_flights,
    SUM(CASE WHEN {DELAYED_PREDICATE} THEN 1 ELSE 0 END) AS delayed_flights,
    ROUND(
        100.0 * SUM(CASE WHEN {DELAYED_PREDICATE} THEN 1 ELSE 0 END) / COUNT(*),
        2
    ) AS delay_rate_percent,
    ROUND(AVG(departure_delay_minutes), 2) AS average_departure_delay_minutes,
    ROUND(AVG(arrival_delay_minutes), 2) AS average_arrival_delay_minutes,
    COUNT(departure_delay_minutes) AS departure_delay_samples,
    COUNT(arrival_delay_minutes) AS arrival_delay_samples
FROM flights
GROUP BY COALESCE(origin_iata, 'Unknown'), COALESCE(destination_iata, 'Unknown')
HAVING COUNT(*) >= %s
ORDER BY delayed_flights DESC, delay_rate_percent DESC, origin_iata, destination_iata
""".strip()


BY_HOUR_SQL = f"""
SELECT
    HOUR(
        CASE
            WHEN origin_iata = %s THEN scheduled_departure
            WHEN destination_iata = %s THEN scheduled_arrival
            ELSE COALESCE(scheduled_departure, scheduled_arrival)
        END
    ) AS scheduled_hour_utc,
    COUNT(*) AS total_flights,
    SUM(CASE WHEN {DELAYED_PREDICATE} THEN 1 ELSE 0 END) AS delayed_flights,
    ROUND(
        100.0 * SUM(CASE WHEN {DELAYED_PREDICATE} THEN 1 ELSE 0 END) / COUNT(*),
        2
    ) AS delay_rate_percent,
    ROUND(AVG(departure_delay_minutes), 2) AS average_departure_delay_minutes,
    ROUND(AVG(arrival_delay_minutes), 2) AS average_arrival_delay_minutes
FROM flights
WHERE scheduled_departure IS NOT NULL OR scheduled_arrival IS NOT NULL
GROUP BY scheduled_hour_utc
ORDER BY scheduled_hour_utc
""".strip()


TOP_DELAYED_SQL = """
SELECT
    flight_number,
    airline,
    origin_iata,
    destination_iata,
    scheduled_departure,
    departure_delay_minutes,
    arrival_delay_minutes,
    CASE
        WHEN departure_delay_minutes IS NULL THEN arrival_delay_minutes
        WHEN arrival_delay_minutes IS NULL THEN departure_delay_minutes
        ELSE GREATEST(departure_delay_minutes, arrival_delay_minutes)
    END AS maximum_delay_minutes,
    status
FROM flights
WHERE departure_delay_minutes IS NOT NULL OR arrival_delay_minutes IS NOT NULL
ORDER BY maximum_delay_minutes DESC, scheduled_departure, flight_number
LIMIT %s
""".strip()


DATA_QUALITY_SQL = """
SELECT
    COUNT(*) AS total_rows,
    SUM(airline IS NULL OR airline = '') AS missing_airline,
    SUM(origin_iata IS NULL OR origin_iata = '') AS missing_origin_iata,
    SUM(destination_iata IS NULL OR destination_iata = '') AS missing_destination_iata,
    SUM(scheduled_departure IS NULL) AS missing_scheduled_departure,
    SUM(actual_departure IS NULL) AS missing_actual_departure,
    SUM(scheduled_arrival IS NULL) AS missing_scheduled_arrival,
    SUM(actual_arrival IS NULL) AS missing_actual_arrival,
    SUM(status IS NULL OR status = '') AS missing_status,
    COUNT(*) - COUNT(DISTINCT provider_flight_id) AS duplicate_provider_ids,
    SUM(ABS(departure_delay_minutes) > 360) AS extreme_departure_delay,
    SUM(ABS(arrival_delay_minutes) > 360) AS extreme_arrival_delay
FROM flights
""".strip()


DISRUPTED_FLIGHTS_SQL = f"""
SELECT
    flight_number,
    airline,
    origin_iata,
    destination_iata,
    scheduled_departure,
    scheduled_arrival,
    status,
    departure_delay_minutes,
    arrival_delay_minutes
FROM flights
WHERE status = 'cancelled' OR {DELAYED_PREDICATE}
ORDER BY
    CASE WHEN status = 'cancelled' THEN 0 ELSE 1 END,
    COALESCE(scheduled_departure, scheduled_arrival),
    flight_number
LIMIT %s
""".strip()


WEATHER_CONTEXT_SQL = f"""
WITH airport_flights AS (
    SELECT
        provider_flight_id,
        CASE
            WHEN origin_iata = %s THEN scheduled_departure
            ELSE scheduled_arrival
        END AS airport_event_time,
        CASE WHEN {DELAYED_PREDICATE} THEN 1 ELSE 0 END AS is_delayed,
        CASE WHEN status = 'cancelled' THEN 1 ELSE 0 END AS is_cancelled
    FROM flights
    WHERE origin_iata = %s OR destination_iata = %s
)
SELECT
    weather.observation_time,
    weather.temperature_c,
    weather.precipitation_mm,
    weather.snowfall_cm,
    weather.visibility_m,
    weather.wind_speed_kmh,
    weather.wind_gusts_kmh,
    weather.weather_code,
    COUNT(flight.provider_flight_id) AS total_flights,
    COALESCE(SUM(flight.is_delayed), 0) AS delayed_flights,
    COALESCE(SUM(flight.is_cancelled), 0) AS cancelled_flights
FROM weather_observations AS weather
LEFT JOIN airport_flights AS flight
    ON weather.observation_time = DATE_FORMAT(
        flight.airport_event_time,
        '%Y-%m-%d %H:00:00'
    )
WHERE weather.airport_iata = %s
GROUP BY
    weather.observation_time,
    weather.temperature_c,
    weather.precipitation_mm,
    weather.snowfall_cm,
    weather.visibility_m,
    weather.wind_speed_kmh,
    weather.wind_gusts_kmh,
    weather.weather_code
ORDER BY weather.observation_time
""".strip()


class FlightAnalysis:
    """Execute read-only flight analytics using an existing MySQL connection."""

    def __init__(self, connection: Any) -> None:
        self._connection = connection

    def _fetch_all(
        self,
        sql: str,
        params: Sequence[object] = (),
    ) -> list[dict[str, Any]]:
        cursor = self._connection.cursor(dictionary=True)
        try:
            cursor.execute(sql, tuple(params))
            return list(cursor.fetchall())
        finally:
            cursor.close()

    def _fetch_one(
        self,
        sql: str,
        params: Sequence[object] = (),
    ) -> dict[str, Any]:
        cursor = self._connection.cursor(dictionary=True)
        try:
            cursor.execute(sql, tuple(params))
            return cursor.fetchone() or {}
        finally:
            cursor.close()

    def overview(self) -> dict[str, Any]:
        return self._fetch_one(OVERVIEW_SQL)

    def status_counts(self) -> list[dict[str, Any]]:
        return self._fetch_all(STATUS_COUNTS_SQL)

    def delays_by_airline(self, *, minimum_flights: int = 1) -> list[dict[str, Any]]:
        if minimum_flights < 1:
            raise ValueError("minimum_flights must be at least 1")
        return self._fetch_all(BY_AIRLINE_SQL, (minimum_flights,))

    def delays_by_route(self, *, minimum_flights: int = 1) -> list[dict[str, Any]]:
        if minimum_flights < 1:
            raise ValueError("minimum_flights must be at least 1")
        return self._fetch_all(BY_ROUTE_SQL, (minimum_flights,))

    def delays_by_hour(self, *, airport_iata: str = "YYZ") -> list[dict[str, Any]]:
        airport = airport_iata.strip().upper()
        if len(airport) != 3 or not airport.isalpha():
            raise ValueError("airport_iata must be a three-letter IATA code")
        return self._fetch_all(BY_HOUR_SQL, (airport, airport))

    def top_delayed_flights(self, *, limit: int = 10) -> list[dict[str, Any]]:
        if not 1 <= limit <= 100:
            raise ValueError("limit must be between 1 and 100")
        return self._fetch_all(TOP_DELAYED_SQL, (limit,))

    def data_quality(self) -> dict[str, Any]:
        return self._fetch_one(DATA_QUALITY_SQL)

    def disrupted_flights(self, *, limit: int = 100) -> list[dict[str, Any]]:
        if not 1 <= limit <= 500:
            raise ValueError("limit must be between 1 and 500")
        return self._fetch_all(DISRUPTED_FLIGHTS_SQL, (limit,))

    def weather_context(
        self,
        *,
        airport_iata: str = "YYZ",
    ) -> list[dict[str, Any]]:
        airport = airport_iata.strip().upper()
        if len(airport) != 3 or not airport.isalpha():
            raise ValueError("airport_iata must be a three-letter IATA code")
        return self._fetch_all(
            WEATHER_CONTEXT_SQL,
            (airport, airport, airport, airport),
        )

    def report(
        self,
        *,
        minimum_flights: int = 1,
        top_limit: int = 10,
    ) -> dict[str, Any]:
        return {
            "overview": self.overview(),
            "status_counts": self.status_counts(),
            "delays_by_airline": self.delays_by_airline(
                minimum_flights=minimum_flights,
            ),
            "delays_by_route": self.delays_by_route(
                minimum_flights=minimum_flights,
            ),
            "delays_by_hour": self.delays_by_hour(),
            "top_delayed_flights": self.top_delayed_flights(limit=top_limit),
            "data_quality": self.data_quality(),
            "disrupted_flights": self.disrupted_flights(),
            "weather_context": self.weather_context(),
        }
