"""AeroDataBox request construction and response normalization."""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from typing import Any
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from flight_pulse.config import AeroDataBoxSettings
from flight_pulse.models import NormalizedFlight, calculate_delay_minutes


_STATUS_MAP = {
    "unknown": "unknown",
    "expected": "scheduled",
    "checkin": "scheduled",
    "boarding": "scheduled",
    "gateclosed": "scheduled",
    "departed": "departed",
    "enroute": "en_route",
    "delayed": "delayed",
    "approaching": "en_route",
    "arrived": "arrived",
    "canceled": "cancelled",
    "cancelled": "cancelled",
    "diverted": "diverted",
    "canceleduncertain": "unknown",
    "cancelleduncertain": "unknown",
}

_CONFIRMED_DEPARTURE_STATUSES = {
    "departed",
    "enroute",
    "approaching",
    "arrived",
    "diverted",
}
_CONFIRMED_ARRIVAL_STATUSES = {"arrived"}


def _status_key(value: object) -> str:
    if not isinstance(value, str):
        return "unknown"
    return "".join(character for character in value.lower() if character.isalnum())


def _normalize_status(value: object) -> str:
    return _STATUS_MAP.get(_status_key(value), "unknown")


def _parse_utc_timestamp(value: object) -> datetime | None:
    if isinstance(value, Mapping):
        value = value.get("utc")
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("AeroDataBox timestamp must be a string or object")

    timestamp = value.strip()
    if not timestamp:
        return None
    if timestamp.endswith("Z"):
        timestamp = f"{timestamp[:-1]}+00:00"

    parsed = datetime.fromisoformat(timestamp)
    if parsed.utcoffset() is None:
        raise ValueError("AeroDataBox UTC timestamp is missing an offset")
    return parsed.astimezone(UTC)


def _movement(raw_flight: Mapping[str, Any], name: str) -> Mapping[str, Any]:
    value = raw_flight.get(name)
    return value if isinstance(value, Mapping) else {}


def _airport_iata(movement: Mapping[str, Any]) -> str | None:
    airport = movement.get("airport")
    if not isinstance(airport, Mapping):
        return None
    value = airport.get("iata")
    if not isinstance(value, str) or not value.strip():
        return None
    return value.strip().upper()


def _airline_name(raw_flight: Mapping[str, Any]) -> str | None:
    airline = raw_flight.get("airline")
    if not isinstance(airline, Mapping):
        return None
    for key in ("name", "iata", "icao"):
        value = airline.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _actual_time(
    movement: Mapping[str, Any],
    raw_status_key: str,
    confirmed_statuses: set[str],
) -> datetime | None:
    explicit_actual = _parse_utc_timestamp(movement.get("actualTime"))
    if explicit_actual is not None:
        return explicit_actual

    if raw_status_key in confirmed_statuses:
        for key in ("runwayTime", "revisedTime"):
            timestamp = _parse_utc_timestamp(movement.get(key))
            if timestamp is not None:
                return timestamp
    return None


def _provider_flight_id(
    raw_flight: Mapping[str, Any],
    flight_number: str,
    origin_iata: str | None,
    destination_iata: str | None,
    scheduled_departure: datetime | None,
    scheduled_arrival: datetime | None,
) -> str:
    for key in ("id", "flightId"):
        value = raw_flight.get(key)
        if isinstance(value, (str, int)) and str(value).strip():
            return f"aerodatabox:{str(value).strip()}"

    scheduled_identity = scheduled_departure or scheduled_arrival
    if scheduled_identity is None:
        raise ValueError("Cannot identify flight without a provider ID or scheduled time")

    return ":".join(
        (
            "aerodatabox",
            flight_number.upper(),
            origin_iata or "unknown",
            destination_iata or "unknown",
            scheduled_identity.astimezone(UTC).isoformat(),
        )
    )


def normalize_flight(
    raw_flight: Mapping[str, Any],
    *,
    fetched_at: datetime | None = None,
) -> NormalizedFlight:
    """Normalize one AeroDataBox flight without retaining provider JSON."""
    number_value = raw_flight.get("number")
    if not isinstance(number_value, str) or not number_value.strip():
        raise ValueError("AeroDataBox flight is missing its flight number")
    flight_number = number_value.strip().upper()

    departure = _movement(raw_flight, "departure")
    arrival = _movement(raw_flight, "arrival")
    origin_iata = _airport_iata(departure)
    destination_iata = _airport_iata(arrival)

    scheduled_departure = _parse_utc_timestamp(departure.get("scheduledTime"))
    scheduled_arrival = _parse_utc_timestamp(arrival.get("scheduledTime"))

    raw_status_key = _status_key(raw_flight.get("status"))
    status = _normalize_status(raw_flight.get("status"))
    actual_departure = _actual_time(
        departure,
        raw_status_key,
        _CONFIRMED_DEPARTURE_STATUSES,
    )
    actual_arrival = _actual_time(
        arrival,
        raw_status_key,
        _CONFIRMED_ARRIVAL_STATUSES,
    )

    fetched_timestamp = fetched_at or datetime.now(UTC)

    return NormalizedFlight(
        provider_flight_id=_provider_flight_id(
            raw_flight,
            flight_number,
            origin_iata,
            destination_iata,
            scheduled_departure,
            scheduled_arrival,
        ),
        flight_number=flight_number,
        airline=_airline_name(raw_flight),
        origin_iata=origin_iata,
        destination_iata=destination_iata,
        scheduled_departure=scheduled_departure,
        actual_departure=actual_departure,
        scheduled_arrival=scheduled_arrival,
        actual_arrival=actual_arrival,
        status=status,
        departure_delay_minutes=calculate_delay_minutes(
            scheduled_departure,
            actual_departure,
        ),
        arrival_delay_minutes=calculate_delay_minutes(
            scheduled_arrival,
            actual_arrival,
        ),
        fetched_at=fetched_timestamp,
    )


def normalize_payload(
    payload: object,
    *,
    fetched_at: datetime | None = None,
    airport_iata: str | None = None,
) -> list[NormalizedFlight]:
    """Normalize and de-duplicate an airport response."""
    focal_airport: str | None = None
    if airport_iata is not None:
        focal_airport = airport_iata.strip().upper()
        if len(focal_airport) != 3 or not focal_airport.isalpha():
            raise ValueError("airport_iata must be a three-letter IATA code")

    raw_flights: list[tuple[object, str | None]]
    if isinstance(payload, list):
        raw_flights = [(flight, None) for flight in payload]
    elif isinstance(payload, Mapping):
        raw_flights = []
        for key in ("departures", "arrivals", "flights"):
            value = payload.get(key)
            if value is not None and not isinstance(value, list):
                raise ValueError(f"AeroDataBox {key} must be a list")
            if isinstance(value, list):
                focal_movement = {
                    "departures": "departure",
                    "arrivals": "arrival",
                }.get(key)
                raw_flights.extend((flight, focal_movement) for flight in value)
    else:
        raise ValueError("AeroDataBox response must be an object or list")

    normalized_by_id: dict[str, NormalizedFlight] = {}
    fetched_timestamp = fetched_at or datetime.now(UTC)
    for raw_flight, focal_movement in raw_flights:
        if not isinstance(raw_flight, Mapping):
            raise ValueError("AeroDataBox flight entry must be an object")

        flight_input = raw_flight
        if focal_airport is not None and focal_movement is not None:
            movement = dict(_movement(raw_flight, focal_movement))
            airport_value = movement.get("airport")
            airport = dict(airport_value) if isinstance(airport_value, Mapping) else {}
            if not isinstance(airport.get("iata"), str) or not airport["iata"].strip():
                airport["iata"] = focal_airport
                movement["airport"] = airport
                flight_input = dict(raw_flight)
                flight_input[focal_movement] = movement

        flight = normalize_flight(flight_input, fetched_at=fetched_timestamp)
        normalized_by_id.setdefault(flight.provider_flight_id, flight)

    return list(normalized_by_id.values())


class AeroDataBoxClient:
    """Small RapidAPI client with injectable I/O for unit tests."""

    def __init__(
        self,
        settings: AeroDataBoxSettings,
        *,
        opener: Callable[..., Any] = urlopen,
        timeout_seconds: float = 15.0,
    ) -> None:
        self._settings = settings
        self._opener = opener
        self._timeout_seconds = timeout_seconds

    def build_airport_request(
        self,
        airport_iata: str,
        from_local: datetime,
        to_local: datetime,
    ) -> Request:
        airport = airport_iata.strip().upper()
        if len(airport) != 3 or not airport.isalpha():
            raise ValueError("airport_iata must be a three-letter IATA code")
        if from_local.utcoffset() is not None or to_local.utcoffset() is not None:
            raise ValueError("AeroDataBox airport-window values must be naive local times")
        if from_local >= to_local:
            raise ValueError("from_local must be earlier than to_local")

        start = quote(from_local.strftime("%Y-%m-%dT%H:%M"), safe="")
        end = quote(to_local.strftime("%Y-%m-%dT%H:%M"), safe="")
        query = urlencode(
            {
                "withLeg": "true",
                "direction": "Both",
                "withCancelled": "true",
                "withCodeshared": "false",
                "withCargo": "false",
                "withPrivate": "false",
            }
        )
        url = (
            f"https://{self._settings.rapidapi_host}"
            f"/flights/airports/iata/{airport}/{start}/{end}?{query}"
        )
        return Request(
            url,
            headers={
                "X-RapidAPI-Key": self._settings.rapidapi_key,
                "X-RapidAPI-Host": self._settings.rapidapi_host,
                "Accept": "application/json",
            },
            method="GET",
        )

    def fetch_airport_flights(
        self,
        airport_iata: str,
        from_local: datetime,
        to_local: datetime,
    ) -> list[NormalizedFlight]:
        request = self.build_airport_request(airport_iata, from_local, to_local)
        with self._opener(request, timeout=self._timeout_seconds) as response:
            payload = json.load(response)
        return normalize_payload(
            payload,
            fetched_at=datetime.now(UTC),
            airport_iata=airport_iata,
        )
