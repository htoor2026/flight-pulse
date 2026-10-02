"""Open-Meteo request construction and hourly weather normalization."""

# Weather data by Open-Meteo.com, licensed under CC BY 4.0.

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from datetime import UTC, date, datetime
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from flight_pulse.models import NormalizedWeatherObservation


OPEN_METEO_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
YYZ_LATITUDE = 43.6777
YYZ_LONGITUDE = -79.6248
HOURLY_VARIABLES = (
    "temperature_2m",
    "precipitation",
    "snowfall",
    "visibility",
    "wind_speed_10m",
    "wind_gusts_10m",
    "weather_code",
)


def _optional_number(value: object, name: str) -> float | None:
    if value is None:
        return None
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(f"Open-Meteo {name} value must be numeric or null")
    return float(value)


def _parse_observation_time(value: object) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Open-Meteo observation time must be a non-empty string")
    parsed = datetime.fromisoformat(value)
    if parsed.utcoffset() is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def normalize_hourly_payload(
    payload: object,
    *,
    airport_iata: str,
    fetched_at: datetime | None = None,
) -> list[NormalizedWeatherObservation]:
    """Normalize one Open-Meteo hourly response into UTC observations."""
    if not isinstance(payload, Mapping):
        raise ValueError("Open-Meteo response must be an object")
    if payload.get("utc_offset_seconds") not in (None, 0):
        raise ValueError("Open-Meteo response must use UTC/GMT timestamps")

    hourly = payload.get("hourly")
    if not isinstance(hourly, Mapping):
        raise ValueError("Open-Meteo response is missing hourly data")

    times = hourly.get("time")
    if not isinstance(times, list):
        raise ValueError("Open-Meteo hourly time must be a list")

    values_by_name: dict[str, list[object]] = {}
    for name in HOURLY_VARIABLES:
        values = hourly.get(name)
        if not isinstance(values, list):
            raise ValueError(f"Open-Meteo hourly {name} must be a list")
        if len(values) != len(times):
            raise ValueError(f"Open-Meteo hourly {name} length does not match time")
        values_by_name[name] = values

    airport = airport_iata.strip().upper()
    fetched_timestamp = fetched_at or datetime.now(UTC)
    observations: list[NormalizedWeatherObservation] = []
    for index, time_value in enumerate(times):
        weather_code_value = values_by_name["weather_code"][index]
        weather_code_number = _optional_number(weather_code_value, "weather_code")
        observations.append(
            NormalizedWeatherObservation(
                airport_iata=airport,
                observation_time=_parse_observation_time(time_value),
                temperature_c=_optional_number(
                    values_by_name["temperature_2m"][index],
                    "temperature_2m",
                ),
                precipitation_mm=_optional_number(
                    values_by_name["precipitation"][index],
                    "precipitation",
                ),
                snowfall_cm=_optional_number(
                    values_by_name["snowfall"][index],
                    "snowfall",
                ),
                visibility_m=_optional_number(
                    values_by_name["visibility"][index],
                    "visibility",
                ),
                wind_speed_kmh=_optional_number(
                    values_by_name["wind_speed_10m"][index],
                    "wind_speed_10m",
                ),
                wind_gusts_kmh=_optional_number(
                    values_by_name["wind_gusts_10m"][index],
                    "wind_gusts_10m",
                ),
                weather_code=(
                    int(weather_code_number)
                    if weather_code_number is not None
                    else None
                ),
                fetched_at=fetched_timestamp,
            )
        )
    return observations


class OpenMeteoClient:
    """Small keyless Open-Meteo client with injectable I/O for tests."""

    def __init__(
        self,
        *,
        opener: Callable[..., Any] = urlopen,
        timeout_seconds: float = 15.0,
    ) -> None:
        self._opener = opener
        self._timeout_seconds = timeout_seconds

    def build_hourly_request(
        self,
        *,
        latitude: float,
        longitude: float,
        start_date: date,
        end_date: date,
    ) -> Request:
        if start_date > end_date:
            raise ValueError("start_date must not be after end_date")
        query = urlencode(
            {
                "latitude": latitude,
                "longitude": longitude,
                "hourly": ",".join(HOURLY_VARIABLES),
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "timezone": "GMT",
            }
        )
        return Request(
            f"{OPEN_METEO_FORECAST_URL}?{query}",
            headers={"Accept": "application/json"},
            method="GET",
        )

    def fetch_hourly(
        self,
        *,
        airport_iata: str,
        latitude: float,
        longitude: float,
        start_date: date,
        end_date: date,
    ) -> list[NormalizedWeatherObservation]:
        request = self.build_hourly_request(
            latitude=latitude,
            longitude=longitude,
            start_date=start_date,
            end_date=end_date,
        )
        with self._opener(request, timeout=self._timeout_seconds) as response:
            payload = json.load(response)
        return normalize_hourly_payload(
            payload,
            airport_iata=airport_iata,
            fetched_at=datetime.now(UTC),
        )
