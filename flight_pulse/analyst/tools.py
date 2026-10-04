"""Structured, read-only analytical tools for the Flight Pulse assistant."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from flight_pulse.analysis import FlightAnalysis


INSUFFICIENT_EVIDENCE = "Insufficient evidence to determine the delay cause."


FIND_FLIGHT_SQL = """
SELECT
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
FROM flights
WHERE REPLACE(UPPER(flight_number), ' ', '') = %s
ORDER BY COALESCE(scheduled_departure, scheduled_arrival) DESC
LIMIT 1
""".strip()


AIRLINE_ANALYSIS_SQL = """
SELECT
    %s AS airline,
    COUNT(*) AS total_flights,
    SUM(
        status = 'delayed'
        OR COALESCE(departure_delay_minutes, 0) > 0
        OR COALESCE(arrival_delay_minutes, 0) > 0
    ) AS delayed_flights,
    ROUND(
        100.0 * SUM(
            status = 'delayed'
            OR COALESCE(departure_delay_minutes, 0) > 0
            OR COALESCE(arrival_delay_minutes, 0) > 0
        ) / NULLIF(COUNT(*), 0),
        2
    ) AS delay_rate_percent,
    CASE
        WHEN COUNT(departure_delay_minutes) >= 2
        THEN ROUND(AVG(departure_delay_minutes), 2)
    END AS average_departure_delay_minutes,
    CASE
        WHEN COUNT(arrival_delay_minutes) >= 2
        THEN ROUND(AVG(arrival_delay_minutes), 2)
    END AS average_arrival_delay_minutes,
    COUNT(departure_delay_minutes) AS departure_delay_samples,
    COUNT(arrival_delay_minutes) AS arrival_delay_samples
FROM flights
WHERE LOWER(airline) = LOWER(%s)
""".strip()


ROUTE_SUMMARY_SQL = """
SELECT
    %s AS origin_iata,
    %s AS destination_iata,
    COUNT(*) AS total_flights,
    SUM(
        status = 'delayed'
        OR COALESCE(departure_delay_minutes, 0) > 0
        OR COALESCE(arrival_delay_minutes, 0) > 0
    ) AS delayed_flights,
    ROUND(
        100.0 * SUM(
            status = 'delayed'
            OR COALESCE(departure_delay_minutes, 0) > 0
            OR COALESCE(arrival_delay_minutes, 0) > 0
        ) / NULLIF(COUNT(*), 0),
        2
    ) AS delay_rate_percent,
    CASE
        WHEN COUNT(departure_delay_minutes) >= 2
        THEN ROUND(AVG(departure_delay_minutes), 2)
    END AS average_departure_delay_minutes,
    CASE
        WHEN COUNT(arrival_delay_minutes) >= 2
        THEN ROUND(AVG(arrival_delay_minutes), 2)
    END AS average_arrival_delay_minutes,
    COUNT(departure_delay_minutes) AS departure_delay_samples,
    COUNT(arrival_delay_minutes) AS arrival_delay_samples
FROM flights
WHERE origin_iata = %s AND destination_iata = %s
""".strip()


ROUTE_STATUS_SQL = """
SELECT status, COUNT(*) AS flight_count
FROM flights
WHERE origin_iata = %s AND destination_iata = %s
GROUP BY status
ORDER BY flight_count DESC, status
""".strip()


ROUTE_FLIGHTS_SQL = """
SELECT
    flight_number,
    airline,
    scheduled_departure,
    actual_departure,
    scheduled_arrival,
    actual_arrival,
    status,
    departure_delay_minutes,
    arrival_delay_minutes
FROM flights
WHERE origin_iata = %s AND destination_iata = %s
ORDER BY COALESCE(scheduled_departure, scheduled_arrival) DESC
LIMIT %s
""".strip()


FLIGHT_WEATHER_SQL = """
WITH target_flight AS (
    SELECT
        flight_number,
        origin_iata,
        destination_iata,
        CASE
            WHEN origin_iata = 'YYZ' THEN scheduled_departure
            WHEN destination_iata = 'YYZ' THEN scheduled_arrival
        END AS yyz_event_time
    FROM flights
    WHERE REPLACE(UPPER(flight_number), ' ', '') = %s
    ORDER BY COALESCE(scheduled_departure, scheduled_arrival) DESC
    LIMIT 1
)
SELECT
    flight.flight_number,
    flight.origin_iata,
    flight.destination_iata,
    flight.yyz_event_time,
    weather.observation_time,
    weather.temperature_c,
    weather.precipitation_mm,
    weather.snowfall_cm,
    weather.visibility_m,
    weather.wind_speed_kmh,
    weather.wind_gusts_kmh,
    weather.weather_code
FROM target_flight AS flight
LEFT JOIN weather_observations AS weather
    ON weather.airport_iata = 'YYZ'
    AND weather.observation_time = DATE_FORMAT(
        flight.yyz_event_time,
        '%Y-%m-%d %H:00:00'
    )
WHERE flight.yyz_event_time IS NOT NULL
""".strip()


FLIGHT_NEWS_SQL = """
WITH target_flight AS (
    SELECT
        CASE
            WHEN origin_iata = 'YYZ' THEN scheduled_departure
            WHEN destination_iata = 'YYZ' THEN scheduled_arrival
        END AS yyz_event_time
    FROM flights
    WHERE REPLACE(UPPER(flight_number), ' ', '') = %s
    ORDER BY COALESCE(scheduled_departure, scheduled_arrival) DESC
    LIMIT 1
)
SELECT
    news.article_id,
    news.title,
    news.source_domain,
    news.url,
    news.published_at,
    news.language,
    news.query_topic
FROM target_flight AS flight
JOIN news_articles AS news
    ON news.published_at BETWEEN
        DATE_SUB(flight.yyz_event_time, INTERVAL 24 HOUR)
        AND DATE_ADD(flight.yyz_event_time, INTERVAL 24 HOUR)
WHERE flight.yyz_event_time IS NOT NULL
ORDER BY
    ABS(TIMESTAMPDIFF(MINUTE, news.published_at, flight.yyz_event_time)),
    news.published_at DESC
LIMIT %s
""".strip()


READ_ONLY_SQL = (
    FIND_FLIGHT_SQL,
    AIRLINE_ANALYSIS_SQL,
    ROUTE_SUMMARY_SQL,
    ROUTE_STATUS_SQL,
    ROUTE_FLIGHTS_SQL,
    FLIGHT_WEATHER_SQL,
    FLIGHT_NEWS_SQL,
)


TOOL_DEFINITIONS: tuple[dict[str, Any], ...] = (
    {
        "name": "get_flight_overview",
        "description": (
            "Return current sample metrics plus status, disrupted-flight, airline, "
            "and route breakdowns when include_breakdowns is true. Use false for "
            "totals and true for cancelled-flight lists or airline/route rankings."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "include_breakdowns": {
                    "type": "boolean",
                    "description": (
                        "Include status, disrupted-flight, airline, and route details."
                    ),
                }
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "find_flight",
        "description": "Find the most recent stored record for a flight number.",
        "parameters": {
            "type": "object",
            "properties": {"flight_number": {"type": "string"}},
            "required": ["flight_number"],
            "additionalProperties": False,
        },
    },
    {
        "name": "get_airline_analysis",
        "description": "Return flight and delay metrics for one airline.",
        "parameters": {
            "type": "object",
            "properties": {"airline": {"type": "string"}},
            "required": ["airline"],
            "additionalProperties": False,
        },
    },
    {
        "name": "get_route_analysis",
        "description": "Return flights, statuses, and delay metrics for one route.",
        "parameters": {
            "type": "object",
            "properties": {
                "origin": {"type": "string", "minLength": 3, "maxLength": 3},
                "destination": {"type": "string", "minLength": 3, "maxLength": 3},
                "limit": {"type": "integer", "minimum": 1, "maximum": 100},
            },
            "required": ["origin", "destination"],
            "additionalProperties": False,
        },
    },
    {
        "name": "get_weather_context",
        "description": "Return stored YYZ weather at the flight's scheduled YYZ hour.",
        "parameters": {
            "type": "object",
            "properties": {"flight_number": {"type": "string"}},
            "required": ["flight_number"],
            "additionalProperties": False,
        },
    },
    {
        "name": "get_news_context",
        "description": "Return stored news metadata published within 24 hours of a flight.",
        "parameters": {
            "type": "object",
            "properties": {
                "flight_number": {"type": "string"},
                "limit": {"type": "integer", "minimum": 1, "maximum": 50},
            },
            "required": ["flight_number"],
            "additionalProperties": False,
        },
    },
    {
        "name": "investigate_delay",
        "description": "Combine stored flight, weather, and news evidence without asserting causality.",
        "parameters": {
            "type": "object",
            "properties": {"flight_number": {"type": "string"}},
            "required": ["flight_number"],
            "additionalProperties": False,
        },
    },
)


def _json_safe(value: Any) -> Any:
    """Convert MySQL values to JSON-compatible values for future model tools."""
    if isinstance(value, datetime):
        timestamp = value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
        return timestamp.isoformat().replace("+00:00", "Z")
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, Mapping):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return value


def _flight_number(value: str) -> str:
    normalized = "".join(value.split()).upper()
    if not normalized or not normalized.isalnum():
        raise ValueError("flight_number must contain only letters, numbers, and spaces")
    return normalized


def _iata(value: str, name: str) -> str:
    normalized = value.strip().upper()
    if len(normalized) != 3 or not normalized.isalpha():
        raise ValueError(f"{name} must be a three-letter IATA code")
    return normalized


class FlightAnalyst:
    """Expose a fixed set of grounded tools over an existing MySQL connection."""

    def __init__(self, connection: Any, analysis: FlightAnalysis | None = None) -> None:
        self._connection = connection
        self._analysis = analysis or FlightAnalysis(connection)

    def _fetch_one(
        self,
        sql: str,
        params: Sequence[object] = (),
    ) -> dict[str, Any] | None:
        cursor = self._connection.cursor(dictionary=True)
        try:
            cursor.execute(sql, tuple(params))
            row = cursor.fetchone()
            return _json_safe(row) if row else None
        finally:
            cursor.close()

    def _fetch_all(
        self,
        sql: str,
        params: Sequence[object] = (),
    ) -> list[dict[str, Any]]:
        cursor = self._connection.cursor(dictionary=True)
        try:
            cursor.execute(sql, tuple(params))
            return _json_safe(list(cursor.fetchall()))
        finally:
            cursor.close()

    def get_flight_overview(
        self,
        include_breakdowns: bool = False,
    ) -> dict[str, Any]:
        if not isinstance(include_breakdowns, bool):
            raise ValueError("include_breakdowns must be a boolean")
        overview = self._analysis.overview()
        selected = {
            key: overview.get(key)
            for key in (
                "total_flights",
                "delayed_flights",
                "cancelled_flights",
                "delay_rate_percent",
            )
        }
        if include_breakdowns:
            selected.update(
                {
                    "status_counts": self._analysis.status_counts(),
                    "disrupted_flights": self._analysis.disrupted_flights(),
                    "delays_by_airline": self._analysis.delays_by_airline(
                        minimum_flights=1,
                    ),
                    "delays_by_route": self._analysis.delays_by_route(
                        minimum_flights=1,
                    ),
                }
            )
        return _json_safe(selected)

    def find_flight(self, flight_number: str) -> dict[str, Any] | None:
        return self._fetch_one(FIND_FLIGHT_SQL, (_flight_number(flight_number),))

    def get_airline_analysis(self, airline: str) -> dict[str, Any]:
        name = airline.strip()
        if not name:
            raise ValueError("airline must not be empty")
        result = self._fetch_one(AIRLINE_ANALYSIS_SQL, (name, name))
        return result or {
            "airline": name,
            "total_flights": 0,
            "delayed_flights": 0,
            "delay_rate_percent": None,
            "average_departure_delay_minutes": None,
            "average_arrival_delay_minutes": None,
            "departure_delay_samples": 0,
            "arrival_delay_samples": 0,
        }

    def get_route_analysis(
        self,
        origin: str,
        destination: str,
        limit: int = 25,
    ) -> dict[str, Any]:
        origin_iata = _iata(origin, "origin")
        destination_iata = _iata(destination, "destination")
        if not 1 <= limit <= 100:
            raise ValueError("limit must be between 1 and 100")
        summary = self._fetch_one(
            ROUTE_SUMMARY_SQL,
            (origin_iata, destination_iata, origin_iata, destination_iata),
        )
        statuses = self._fetch_all(ROUTE_STATUS_SQL, (origin_iata, destination_iata))
        flights = self._fetch_all(
            ROUTE_FLIGHTS_SQL,
            (origin_iata, destination_iata, limit),
        )
        return {"summary": summary, "status_counts": statuses, "flights": flights}

    def get_weather_context(self, flight_number: str) -> dict[str, Any] | None:
        return self._fetch_one(FLIGHT_WEATHER_SQL, (_flight_number(flight_number),))

    def get_news_context(
        self,
        flight_number: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        if not 1 <= limit <= 50:
            raise ValueError("limit must be between 1 and 50")
        return self._fetch_all(
            FLIGHT_NEWS_SQL,
            (_flight_number(flight_number), limit),
        )

    def investigate_delay(self, flight_number: str) -> dict[str, Any]:
        normalized = _flight_number(flight_number)
        flight = self.find_flight(normalized)
        if flight is None:
            return {
                "flight_number": normalized,
                "flight": None,
                "weather_context": None,
                "news_context": [],
                "conclusion": INSUFFICIENT_EVIDENCE,
                "limitations": ["No matching stored flight record was found."],
            }

        weather = self.get_weather_context(normalized)
        news_available = True
        try:
            news = self.get_news_context(normalized)
        except Exception:
            news = []
            news_available = False
        limitations = [
            "Weather near the scheduled YYZ event is contextual association, not proof of causation.",
            "Stored news metadata is supporting context and does not confirm a flight-specific cause.",
        ]
        if not news_available:
            limitations.append(
                "No stored news context is currently available for this flight."
            )
        return {
            "flight_number": normalized,
            "flight": flight,
            "weather_context": weather,
            "news_context": news,
            "news_context_available": news_available,
            "conclusion": INSUFFICIENT_EVIDENCE,
            "limitations": limitations,
        }
