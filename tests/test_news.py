from __future__ import annotations

import io
import json
import unittest
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import Mock
from urllib.parse import parse_qs, urlsplit

from flight_pulse.ingestion.gdelt import GDELTClient, normalize_article_payload
from flight_pulse.models import NormalizedNewsArticle
from flight_pulse.pipeline import (
    YYZ_DISRUPTION_QUERY,
    YYZ_NEWS_TOPIC,
    ingest_yyz_news,
)
from flight_pulse.repository import NewsRepository


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "gdelt_articles.json"
FETCHED_AT = datetime(2026, 10, 2, 12, 0, tzinfo=UTC)


class _MockResponse(io.BytesIO):
    def __enter__(self) -> "_MockResponse":
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()


def _article() -> NormalizedNewsArticle:
    return NormalizedNewsArticle(
        article_id="a" * 64,
        title="Operational delays reported at Toronto Pearson",
        source_domain="example.com",
        url="https://example.com/aviation/yyz-delays",
        published_at=datetime(2026, 10, 2, 9, 15, tzinfo=UTC),
        language="English",
        query_topic=YYZ_NEWS_TOPIC,
        fetched_at=FETCHED_AT,
    )


class GDELTTests(unittest.TestCase):
    def setUp(self) -> None:
        self.payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    def test_builds_yyz_article_list_request(self) -> None:
        request = GDELTClient().build_article_request(
            query=YYZ_DISRUPTION_QUERY,
            timespan="7d",
            max_records=75,
        )
        parsed = urlsplit(request.full_url)
        query = parse_qs(parsed.query)

        self.assertEqual(parsed.hostname, "api.gdeltproject.org")
        self.assertEqual(query["query"], [YYZ_DISRUPTION_QUERY])
        self.assertEqual(query["mode"], ["ArtList"])
        self.assertEqual(query["format"], ["json"])
        self.assertEqual(query["timespan"], ["7d"])
        self.assertEqual(query["maxrecords"], ["75"])
        self.assertEqual(query["sort"], ["DateDesc"])

    def test_normalizes_metadata_and_deduplicates_canonical_urls(self) -> None:
        articles = normalize_article_payload(
            self.payload,
            query_topic=YYZ_NEWS_TOPIC,
            fetched_at=FETCHED_AT,
        )

        self.assertEqual(len(articles), 2)
        self.assertEqual(len(articles[0].article_id), 64)
        self.assertEqual(articles[0].published_at.tzinfo, UTC)
        self.assertEqual(articles[0].query_topic, YYZ_NEWS_TOPIC)
        self.assertNotIn("#", articles[0].url)
        self.assertFalse(hasattr(articles[0], "article_text"))

    def test_fetch_uses_injected_opener(self) -> None:
        opener = Mock(return_value=_MockResponse(FIXTURE_PATH.read_bytes()))
        client = GDELTClient(opener=opener)

        articles = client.fetch_articles(
            query=YYZ_DISRUPTION_QUERY,
            query_topic=YYZ_NEWS_TOPIC,
        )

        self.assertEqual(len(articles), 2)
        opener.assert_called_once()
        self.assertEqual(opener.call_args.kwargs["timeout"], 20.0)


class NewsRepositoryTests(unittest.TestCase):
    def test_upserts_metadata_with_parameterized_sql(self) -> None:
        cursor = Mock()
        connection = Mock()
        connection.cursor.return_value = cursor
        repository = NewsRepository(connection)

        count = repository.upsert_many([_article()])

        self.assertEqual(count, 1)
        sql, rows = cursor.executemany.call_args.args
        self.assertIn("ON DUPLICATE KEY UPDATE", sql)
        self.assertEqual(rows[0][0], "a" * 64)
        self.assertEqual(rows[0][4], datetime(2026, 10, 2, 9, 15))
        self.assertEqual(rows[0][7], datetime(2026, 10, 2, 12, 0))
        connection.commit.assert_called_once_with()
        cursor.close.assert_called_once_with()


class NewsPipelineTests(unittest.TestCase):
    def test_pipeline_fetches_and_persists_recent_yyz_context(self) -> None:
        client = Mock()
        repository = Mock()
        article = _article()
        client.fetch_articles.return_value = [article]
        repository.upsert_many.return_value = 1

        count = ingest_yyz_news(client, repository)

        self.assertEqual(count, 1)
        client.fetch_articles.assert_called_once_with(
            query=YYZ_DISRUPTION_QUERY,
            query_topic=YYZ_NEWS_TOPIC,
            timespan="7d",
            max_records=75,
        )
        repository.upsert_many.assert_called_once_with([article])


if __name__ == "__main__":
    unittest.main()
