from __future__ import annotations

import io
import json
import unittest
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import Mock
from urllib.parse import parse_qs, urlsplit

from flight_pulse.config import AeroDataBoxSettings
from flight_pulse.ingestion.aerodatabox import (
    AeroDataBoxClient,
    normalize_flight,
    normalize_payload,
)
from flight_pulse.models import calculate_delay_minutes


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "aerodatabox_airport.json"
FETCHED_AT = datetime(2026, 10, 2, 20, 0, tzinfo=UTC)


class _MockResponse(io.BytesIO):
    def __enter__(self) -> "_MockResponse":
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()


class DelayCalculationTests(unittest.TestCase):
    def test_delay_is_none_when_a_timestamp_is_missing(self) -> None:
        actual = datetime(2026, 10, 2, 14, 15, tzinfo=UTC)
        self.assertIsNone(calculate_delay_minutes(None, actual))
        self.assertIsNone(calculate_delay_minutes(actual, None))

    def test_delay_uses_signed_whole_minutes(self) -> None:
        scheduled = datetime(2026, 10, 2, 14, 0, tzinfo=UTC)
        late = datetime(2026, 10, 2, 14, 15, 59, tzinfo=UTC)
        early = datetime(2026, 10, 2, 13, 55, tzinfo=UTC)

        self.assertEqual(calculate_delay_minutes(scheduled, late), 15)
        self.assertEqual(calculate_delay_minutes(scheduled, early), -5)


class AeroDataBoxNormalizationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        self.flights = normalize_payload(self.payload, fetched_at=FETCHED_AT)
        self.by_number = {flight.flight_number: flight for flight in self.flights}

    def test_normalizes_required_fields_and_explicit_actual_times(self) -> None:
        flight = self.by_number["AC101"]

        self.assertTrue(flight.provider_flight_id.startswith("aerodatabox:AC101:"))
        self.assertEqual(flight.airline, "Air Canada")
        self.assertEqual(flight.origin_iata, "YYZ")
        self.assertEqual(flight.destination_iata, "YVR")
        self.assertEqual(flight.status, "arrived")
        self.assertEqual(flight.scheduled_departure.tzinfo, UTC)
        self.assertEqual(flight.actual_departure.hour, 14)
        self.assertEqual(flight.actual_arrival.hour, 19)
        self.assertEqual(flight.departure_delay_minutes, 15)
        self.assertEqual(flight.arrival_delay_minutes, 10)
        self.assertEqual(flight.fetched_at, FETCHED_AT)

    def test_does_not_treat_unconfirmed_revised_times_as_actual(self) -> None:
        flight = self.by_number["WS202"]

        self.assertEqual(flight.status, "delayed")
        self.assertIsNone(flight.actual_departure)
        self.assertIsNone(flight.actual_arrival)
        self.assertIsNone(flight.departure_delay_minutes)
        self.assertIsNone(flight.arrival_delay_minutes)

    def test_uses_revised_departure_only_after_departure_is_confirmed(self) -> None:
        flight = self.by_number["AC303"]

        self.assertEqual(flight.status, "departed")
        self.assertEqual(flight.actual_departure.minute, 8)
        self.assertEqual(flight.departure_delay_minutes, 8)
        self.assertIsNone(flight.actual_arrival)
        self.assertIsNone(flight.arrival_delay_minutes)

    def test_cancellation_has_no_fabricated_actual_times_or_delays(self) -> None:
        flight = self.by_number["PD404"]

        self.assertEqual(flight.status, "cancelled")
        self.assertIsNone(flight.actual_departure)
        self.assertIsNone(flight.actual_arrival)
        self.assertIsNone(flight.departure_delay_minutes)
        self.assertIsNone(flight.arrival_delay_minutes)

    def test_converts_offset_timestamps_to_utc(self) -> None:
        raw = {
            "number": "AC505",
            "status": "Departed",
            "departure": {
                "airport": {"iata": "yyz"},
                "scheduledTime": {"utc": "2026-10-02T10:00:00-04:00"},
                "actualTime": {"utc": "2026-10-02T10:30:00-04:00"},
            },
            "arrival": {
                "airport": {"iata": "yow"},
                "scheduledTime": {"utc": "2026-10-02T15:00:00Z"},
            },
        }

        flight = normalize_flight(raw, fetched_at=FETCHED_AT)

        self.assertEqual(flight.scheduled_departure.hour, 14)
        self.assertEqual(flight.actual_departure.hour, 14)
        self.assertEqual(flight.departure_delay_minutes, 30)
        self.assertEqual(flight.origin_iata, "YYZ")
        self.assertEqual(flight.destination_iata, "YOW")

    def test_removes_obvious_duplicates_within_one_payload(self) -> None:
        duplicate = self.payload["departures"][0]
        flights = normalize_payload(
            {"departures": [duplicate, duplicate]},
            fetched_at=FETCHED_AT,
        )

        self.assertEqual(len(flights), 1)


class AeroDataBoxClientTests(unittest.TestCase):
    def setUp(self) -> None:
        self.settings = AeroDataBoxSettings(
            rapidapi_key="synthetic-test-key",
            rapidapi_host="aerodatabox.p.rapidapi.com",
        )

    def test_builds_yyz_airport_request_without_sending_it(self) -> None:
        client = AeroDataBoxClient(self.settings)

        request = client.build_airport_request(
            "yyz",
            datetime(2026, 10, 2, 10, 0),
            datetime(2026, 10, 2, 12, 0),
        )
        parsed = urlsplit(request.full_url)
        headers = {key.lower(): value for key, value in request.header_items()}

        self.assertEqual(parsed.hostname, "aerodatabox.p.rapidapi.com")
        self.assertEqual(
            parsed.path,
            "/flights/airports/iata/YYZ/2026-10-02T10%3A00/2026-10-02T12%3A00",
        )
        self.assertEqual(parse_qs(parsed.query)["direction"], ["Both"])
        self.assertEqual(parse_qs(parsed.query)["withCancelled"], ["true"])
        self.assertEqual(headers["x-rapidapi-key"], "synthetic-test-key")
        self.assertEqual(headers["x-rapidapi-host"], self.settings.rapidapi_host)

    def test_fetch_uses_injected_opener_instead_of_network(self) -> None:
        payload_bytes = FIXTURE_PATH.read_bytes()
        opener = Mock(return_value=_MockResponse(payload_bytes))
        client = AeroDataBoxClient(self.settings, opener=opener)

        flights = client.fetch_airport_flights(
            "YYZ",
            datetime(2026, 10, 2, 10, 0),
            datetime(2026, 10, 2, 12, 0),
        )

        self.assertEqual(len(flights), 4)
        opener.assert_called_once()
        self.assertEqual(opener.call_args.kwargs["timeout"], 15.0)


if __name__ == "__main__":
    unittest.main()
