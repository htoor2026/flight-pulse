"""Provider-independent flight records and calculations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone


def _require_aware(value: datetime | None, field_name: str) -> None:
    if value is not None and value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")


def calculate_delay_minutes(
    scheduled: datetime | None,
    actual: datetime | None,
) -> int | None:
    """Return signed whole-minute delay, or ``None`` when it is unknown."""
    if scheduled is None or actual is None:
        return None

    _require_aware(scheduled, "scheduled")
    _require_aware(actual, "actual")

    difference = actual.astimezone(timezone.utc) - scheduled.astimezone(timezone.utc)
    return int(difference.total_seconds() / 60)


@dataclass(frozen=True, slots=True)
class NormalizedFlight:
    """Flight data after provider-specific normalization."""

    provider_flight_id: str
    flight_number: str
    airline: str | None
    origin_iata: str | None
    destination_iata: str | None
    scheduled_departure: datetime | None
    actual_departure: datetime | None
    scheduled_arrival: datetime | None
    actual_arrival: datetime | None
    status: str
    departure_delay_minutes: int | None
    arrival_delay_minutes: int | None
    fetched_at: datetime

    def __post_init__(self) -> None:
        if not self.provider_flight_id.strip():
            raise ValueError("provider_flight_id must not be empty")
        if not self.flight_number.strip():
            raise ValueError("flight_number must not be empty")
        if not self.status.strip():
            raise ValueError("status must not be empty")

        for field_name in (
            "scheduled_departure",
            "actual_departure",
            "scheduled_arrival",
            "actual_arrival",
            "fetched_at",
        ):
            _require_aware(getattr(self, field_name), field_name)


@dataclass(frozen=True, slots=True)
class NormalizedWeatherObservation:
    """Provider-independent hourly weather observation."""

    airport_iata: str
    observation_time: datetime
    temperature_c: float | None
    precipitation_mm: float | None
    snowfall_cm: float | None
    visibility_m: float | None
    wind_speed_kmh: float | None
    wind_gusts_kmh: float | None
    weather_code: int | None
    fetched_at: datetime

    def __post_init__(self) -> None:
        airport = self.airport_iata.strip().upper()
        if len(airport) != 3 or not airport.isalpha():
            raise ValueError("airport_iata must be a three-letter IATA code")
        _require_aware(self.observation_time, "observation_time")
        _require_aware(self.fetched_at, "fetched_at")


@dataclass(frozen=True, slots=True)
class NormalizedNewsArticle:
    """Metadata-only news record, separate from causal flight analysis."""

    article_id: str
    title: str
    source_domain: str | None
    url: str
    published_at: datetime | None
    language: str | None
    query_topic: str
    fetched_at: datetime

    def __post_init__(self) -> None:
        if not self.article_id.strip():
            raise ValueError("article_id must not be empty")
        if not self.title.strip():
            raise ValueError("title must not be empty")
        if not self.url.strip():
            raise ValueError("url must not be empty")
        if not self.query_topic.strip():
            raise ValueError("query_topic must not be empty")
        _require_aware(self.published_at, "published_at")
        _require_aware(self.fetched_at, "fetched_at")
