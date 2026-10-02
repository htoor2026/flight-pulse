from __future__ import annotations

import io
import json
import unittest
from datetime import UTC, date, datetime
from pathlib import Path
from unittest.mock import Mock
from urllib.parse import parse_qs, urlsplit

from flight_pulse.ingestion.open_meteo import (
    HOURLY_VARIABLES,
    OpenMeteoClient,
    YYZ_LATITUDE,
    YYZ_LONGITUDE,
    normalize_hourly_payload,
)
from flight_pulse.models import NormalizedWeatherObservation
from flight_pulse.pipeline import ingest_yyz_weather
from flight_pulse.repository import WeatherRepository


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "open_meteo_hourly.json"
FETCHED_AT = datetime(2026, 10, 2, 12, 0, tzinfo=UTC)


class _MockResponse(io.BytesIO):
    def __enter__(self) -> "_MockResponse":
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()


def _observation() -> NormalizedWeatherObservation:
    return NormalizedWeatherObservation(
        airport_iata="YYZ",
        observation_time=datetime(2026, 10, 1, 17, 0, tzinfo=UTC),
        temperature_c=17.2,
        precipitation_mm=0.0,
        snowfall_cm=0.0,
        visibility_m=24140.0,
        wind_speed_kmh=14.5,
        wind_gusts_kmh=25.6,
        weather_code=1,
        fetched_at=FETCHED_AT,
    )


class OpenMeteoTests(unittest.TestCase):
    def setUp(self) -> None:
        self.payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    def test_builds_keyless_utc_yyz_request(self) -> None:
        request = OpenMeteoClient().build_hourly_request(
            latitude=YYZ_LATITUDE,
            longitude=YYZ_LONGITUDE,
            start_date=date(2026, 10, 1),
            end_date=date(2026, 10, 2),
        )
        query = parse_qs(urlsplit(request.full_url).query)

        self.assertEqual(query["latitude"], [str(YYZ_LATITUDE)])
        self.assertEqual(query["longitude"], [str(YYZ_LONGITUDE)])
        self.assertEqual(query["timezone"], ["GMT"])
        self.assertEqual(query["hourly"], [",".join(HOURLY_VARIABLES)])
        self.assertNotIn("apikey", query)

    def test_normalizes_hourly_values_and_utc_timestamps(self) -> None:
        observations = normalize_hourly_payload(
            self.payload,
            airport_iata="yyz",
            fetched_at=FETCHED_AT,
        )

        self.assertEqual(len(observations), 2)
        self.assertEqual(observations[0].airport_iata, "YYZ")
        self.assertEqual(observations[0].observation_time.tzinfo, UTC)
        self.assertEqual(observations[1].precipitation_mm, 0.4)
        self.assertEqual(observations[1].weather_code, 61)

    def test_fetch_uses_injected_opener(self) -> None:
        opener = Mock(return_value=_MockResponse(FIXTURE_PATH.read_bytes()))
        client = OpenMeteoClient(opener=opener)

        observations = client.fetch_hourly(
            airport_iata="YYZ",
            latitude=YYZ_LATITUDE,
            longitude=YYZ_LONGITUDE,
            start_date=date(2026, 10, 1),
            end_date=date(2026, 10, 2),
        )

        self.assertEqual(len(observations), 2)
        opener.assert_called_once()
        self.assertEqual(opener.call_args.kwargs["timeout"], 15.0)


class WeatherRepositoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.cursor = Mock()
        self.connection = Mock()
        self.connection.cursor.return_value = self.cursor
        self.repository = WeatherRepository(self.connection)

    def test_reads_utc_flight_window(self) -> None:
        self.cursor.fetchone.return_value = {
            "window_start": datetime(2026, 10, 1, 17, 20),
            "window_end": datetime(2026, 10, 2, 11, 25),
        }

        start, end = self.repository.flight_time_window("yyz")

        self.assertEqual(start, datetime(2026, 10, 1, 17, 20, tzinfo=UTC))
        self.assertEqual(end, datetime(2026, 10, 2, 11, 25, tzinfo=UTC))
        self.assertEqual(self.cursor.execute.call_args.args[1], ("YYZ",) * 6)
        self.cursor.close.assert_called_once_with()

    def test_upserts_hourly_observations_with_utc_mysql_times(self) -> None:
        count = self.repository.upsert_many([_observation()])

        self.assertEqual(count, 1)
        sql, rows = self.cursor.executemany.call_args.args
        self.assertIn("ON DUPLICATE KEY UPDATE", sql)
        self.assertEqual(rows[0][1], datetime(2026, 10, 1, 17, 0))
        self.assertEqual(rows[0][9], datetime(2026, 10, 2, 12, 0))
        self.connection.commit.assert_called_once_with()

    def test_matches_flights_to_their_utc_observation_hour(self) -> None:
        self.cursor.fetchone.return_value = {
            "total_flights": 72,
            "matched_flights": 72,
        }

        result = self.repository.flight_match_summary("yyz")

        self.assertEqual(result["matched_flights"], 72)
        sql, params = self.cursor.execute.call_args.args
        self.assertIn("'%Y-%m-%d %H:00:00'", sql)
        self.assertEqual(params, ("YYZ",) * 4)
        self.cursor.close.assert_called_once_with()


class WeatherPipelineTests(unittest.TestCase):
    def test_pipeline_uses_existing_flight_window(self) -> None:
        client = Mock()
        repository = Mock()
        observation = _observation()
        repository.flight_time_window.return_value = (
            datetime(2026, 10, 1, 17, 20, tzinfo=UTC),
            datetime(2026, 10, 2, 11, 25, tzinfo=UTC),
        )
        client.fetch_hourly.return_value = [observation]
        repository.upsert_many.return_value = 1

        count = ingest_yyz_weather(client, repository)

        self.assertEqual(count, 1)
        client.fetch_hourly.assert_called_once_with(
            airport_iata="YYZ",
            latitude=YYZ_LATITUDE,
            longitude=YYZ_LONGITUDE,
            start_date=date(2026, 10, 1),
            end_date=date(2026, 10, 2),
        )
        repository.upsert_many.assert_called_once_with([observation])


if __name__ == "__main__":
    unittest.main()
