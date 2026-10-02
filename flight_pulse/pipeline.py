"""Small orchestration functions for flight ingestion."""

from __future__ import annotations

from datetime import datetime

from flight_pulse.ingestion.aerodatabox import AeroDataBoxClient
from flight_pulse.ingestion.gdelt import GDELTClient
from flight_pulse.ingestion.open_meteo import (
    OpenMeteoClient,
    YYZ_LATITUDE,
    YYZ_LONGITUDE,
)
from flight_pulse.repository import FlightRepository, NewsRepository, WeatherRepository


YYZ_DISRUPTION_QUERY = (
    '("Toronto Pearson" OR YYZ) '
    '("flight delays" OR "flight cancellations" OR "airport disruption" OR '
    'strike OR "air traffic control" OR "severe weather disruption" OR '
    '"runway closure" OR "security incident")'
)
YYZ_NEWS_TOPIC = "YYZ operational disruption"


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


def ingest_yyz_news(
    client: GDELTClient,
    repository: NewsRepository,
) -> int:
    """Fetch and store recent YYZ disruption article metadata."""
    articles = client.fetch_articles(
        query=YYZ_DISRUPTION_QUERY,
        query_topic=YYZ_NEWS_TOPIC,
        timespan="7d",
        max_records=75,
    )
    return repository.upsert_many(articles)
