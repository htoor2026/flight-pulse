"""Validated loading for the bundled synthetic public-demo report."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any


DEMO_REPORT_PATH = Path(__file__).resolve().parent.parent / "data" / "demo_report.json"
REQUIRED_SECTIONS = {
    "overview": dict,
    "status_counts": list,
    "delays_by_airline": list,
    "delays_by_route": list,
    "delays_by_hour": list,
    "top_delayed_flights": list,
    "data_quality": dict,
    "disrupted_flights": list,
    "weather_context": list,
}
FORBIDDEN_KEY_PARTS = {
    "api_key",
    "apikey",
    "article_text",
    "credential",
    "fetched_at",
    "password",
    "provider_flight_id",
    "rapidapi",
    "secret",
    "token",
    "url",
}


def _reject_forbidden_fields(value: Any, path: str = "report") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = str(key).lower()
            if any(part in normalized for part in FORBIDDEN_KEY_PARTS):
                raise ValueError(f"Forbidden demo field: {path}.{key}")
            _reject_forbidden_fields(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_forbidden_fields(child, f"{path}[{index}]")


def validate_demo_report(report: Any) -> dict[str, Any]:
    """Validate the dashboard contract and fixed public-demo headline metrics."""
    if not isinstance(report, dict):
        raise ValueError("Demo report must be a JSON object")
    if set(report) != set(REQUIRED_SECTIONS):
        raise ValueError("Demo report sections do not match the dashboard contract")
    for section, expected_type in REQUIRED_SECTIONS.items():
        if not isinstance(report[section], expected_type):
            raise ValueError(f"Demo report section {section!r} has the wrong type")

    overview = report["overview"]
    expected_metrics = {
        "total_flights": 72,
        "delayed_flights": 8,
        "cancelled_flights": 1,
        "delay_rate_percent": 11.11,
        "median_departure_delay_minutes": 21.0,
        "departure_delay_samples": 3,
    }
    for key, expected in expected_metrics.items():
        if overview.get(key) != expected:
            raise ValueError(f"Unexpected demo metric: {key}")

    grouped_sections = ("status_counts", "delays_by_airline", "delays_by_route")
    for section in grouped_sections:
        count_key = "flight_count" if section == "status_counts" else "total_flights"
        if sum(row[count_key] for row in report[section]) != 72:
            raise ValueError(f"Demo {section} totals must equal 72")
    for section in ("delays_by_airline", "delays_by_route", "delays_by_hour"):
        if sum(row["delayed_flights"] for row in report[section]) != 8:
            raise ValueError(f"Demo {section} delayed totals must equal 8")
    if sum(row["total_flights"] for row in report["delays_by_hour"]) != 72:
        raise ValueError("Demo hourly totals must equal 72")

    weather = report["weather_context"]
    if len(weather) != 48:
        raise ValueError("Demo report must contain 48 weather observations")
    if sum(row["total_flights"] for row in weather) != 72:
        raise ValueError("Demo weather matches must total 72 flights")
    if sum(row["delayed_flights"] for row in weather) != 8:
        raise ValueError("Demo weather delayed matches must total 8 flights")
    if sum(row["cancelled_flights"] for row in weather) != 1:
        raise ValueError("Demo weather cancelled matches must total 1 flight")

    hourly_weather: dict[int, dict[str, int]] = defaultdict(
        lambda: {"total_flights": 0, "delayed_flights": 0, "cancelled_flights": 0}
    )
    for row in weather:
        hour = datetime.fromisoformat(row["observation_time"].replace("Z", "+00:00")).hour
        for key in hourly_weather[hour]:
            hourly_weather[hour][key] += row[key]
    expected_hours = {
        row["scheduled_hour_utc"]: {
            "total_flights": row["total_flights"],
            "delayed_flights": row["delayed_flights"],
        }
        for row in report["delays_by_hour"]
    }
    actual_hours = {
        hour: {
            "total_flights": counts["total_flights"],
            "delayed_flights": counts["delayed_flights"],
        }
        for hour, counts in hourly_weather.items()
        if counts["total_flights"] or counts["delayed_flights"]
    }
    if actual_hours != expected_hours:
        raise ValueError("Demo weather matches must align with hourly analytics")

    disrupted = report["disrupted_flights"]
    delayed_hours = Counter(
        datetime.fromisoformat(row["scheduled_departure"].replace("Z", "+00:00")).hour
        for row in disrupted
        if row["status"] == "delayed"
    )
    if delayed_hours != Counter(
        {hour: counts["delayed_flights"] for hour, counts in expected_hours.items()}
    ):
        raise ValueError("Demo disrupted flights must align with hourly delays")
    cancelled_hours = Counter(
        datetime.fromisoformat(row["scheduled_departure"].replace("Z", "+00:00")).hour
        for row in disrupted
        if row["status"] == "cancelled"
    )
    weather_cancelled_hours = Counter(
        {
            hour: counts["cancelled_flights"]
            for hour, counts in hourly_weather.items()
            if counts["cancelled_flights"]
        }
    )
    if cancelled_hours != weather_cancelled_hours:
        raise ValueError("Demo disrupted cancellations must align with weather matches")
    if sum(cancelled_hours.values()) != overview["cancelled_flights"]:
        raise ValueError("Demo disrupted cancellations must match the overview")

    _reject_forbidden_fields(report)
    return report


def load_demo_report(path: Path = DEMO_REPORT_PATH) -> dict[str, Any]:
    """Load and validate the bundled synthetic report without external I/O."""
    with path.open(encoding="utf-8") as source:
        return validate_demo_report(json.load(source))
