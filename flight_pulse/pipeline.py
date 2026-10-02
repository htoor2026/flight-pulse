"""Small orchestration functions for flight ingestion."""

from __future__ import annotations

from datetime import datetime

from flight_pulse.ingestion.aerodatabox import AeroDataBoxClient
from flight_pulse.repository import FlightRepository


def ingest_yyz_window(
    client: AeroDataBoxClient,
    repository: FlightRepository,
    from_local: datetime,
    to_local: datetime,
) -> int:
    """Fetch, normalize, and persist one YYZ local-time window."""
    flights = client.fetch_airport_flights("YYZ", from_local, to_local)
    return repository.upsert_many(flights)
