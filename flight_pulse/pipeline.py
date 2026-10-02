"""Small orchestration functions for flight ingestion."""

from __future__ import annotations

from datetime import datetime

from flight_pulse.ingestion.aerodatabox import AeroDataBoxClient
from flight_pulse.ingestion.open_meteo import (
    OpenMeteoClient,
    YYZ_LATITUDE,
    YYZ_LONGITUDE,
)
from flight_pulse.repository import FlightRepository, WeatherRepository


def ingest_yyz_window(
    client: AeroDataBoxClient,
    repository: FlightRepository,
    from_local: datetime,
    to_local: datetime,
) -> int:
    """Fetch, normalize, and persist one YYZ local-time window."""
    flights = client.fetch_airport_flights("YYZ", from_local, to_local)
    return repository.upsert_many(flights)


def ingest_yyz_weather(
    client: OpenMeteoClient,
    repository: WeatherRepository,
) -> int:
    """Fetch and store YYZ hourly weather for the existing flight window."""
    window_start, window_end = repository.flight_time_window("YYZ")
    observations = client.fetch_hourly(
        airport_iata="YYZ",
        latitude=YYZ_LATITUDE,
        longitude=YYZ_LONGITUDE,
        start_date=window_start.date(),
        end_date=window_end.date(),
    )
    return repository.upsert_many(observations)
