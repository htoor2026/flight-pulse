"""GDELT DOC 2.0 article-list requests and metadata normalization."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen

from flight_pulse.models import NormalizedNewsArticle


GDELT_DOC_URL = "https://api.gdeltproject.org/api/v2/doc/doc"


def _canonical_url(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("GDELT article URL must be a non-empty string")
    parsed = urlsplit(value.strip())
    scheme = parsed.scheme.lower()
    if scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("GDELT article URL must be HTTP or HTTPS")

    hostname = parsed.hostname.lower()
    port = parsed.port
    if port is not None and not (
        (scheme == "http" and port == 80) or (scheme == "https" and port == 443)
    ):
        hostname = f"{hostname}:{port}"
    return urlunsplit((scheme, hostname, parsed.path or "/", parsed.query, ""))


def _article_id(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()


def _optional_text(value: object) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    return value.strip()


def _published_at(value: object) -> datetime | None:
    text = _optional_text(value)
    if text is None:
        return None

    for date_format in ("%Y%m%dT%H%M%SZ", "%Y%m%d%H%M%S"):
        try:
            return datetime.strptime(text, date_format).replace(tzinfo=UTC)
        except ValueError:
            pass

    iso_text = f"{text[:-1]}+00:00" if text.endswith("Z") else text
    try:
        parsed = datetime.fromisoformat(iso_text)
    except ValueError as exc:
        raise ValueError("Unsupported GDELT article date format") from exc
    if parsed.utcoffset() is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def normalize_article_payload(
    payload: object,
    *,
    query_topic: str,
    fetched_at: datetime | None = None,
) -> list[NormalizedNewsArticle]:
    """Normalize and de-duplicate GDELT metadata without article body text."""
    if not isinstance(payload, Mapping):
        raise ValueError("GDELT response must be an object")
    raw_articles = payload.get("articles")
    if not isinstance(raw_articles, list):
        raise ValueError("GDELT response is missing an articles list")

    topic = query_topic.strip()
    if not topic:
        raise ValueError("query_topic must not be empty")
    fetched_timestamp = fetched_at or datetime.now(UTC)
    normalized: dict[str, NormalizedNewsArticle] = {}

    for raw_article in raw_articles:
        if not isinstance(raw_article, Mapping):
            raise ValueError("GDELT article entry must be an object")
        url = _canonical_url(raw_article.get("url"))
        title = _optional_text(raw_article.get("title"))
        if title is None:
            raise ValueError("GDELT article is missing its title")

        identifier = _article_id(url)
        normalized.setdefault(
            identifier,
            NormalizedNewsArticle(
                article_id=identifier,
                title=title,
                source_domain=(
                    _optional_text(raw_article.get("domain"))
                    or urlsplit(url).hostname
                ),
                url=url,
                published_at=_published_at(raw_article.get("seendate")),
                language=_optional_text(raw_article.get("language")),
                query_topic=topic,
                fetched_at=fetched_timestamp,
            ),
        )
    return list(normalized.values())


class GDELTClient:
    """Small GDELT DOC 2.0 client with injectable HTTP I/O."""

    def __init__(
        self,
        *,
        opener: Callable[..., Any] = urlopen,
        timeout_seconds: float = 20.0,
    ) -> None:
        self._opener = opener
        self._timeout_seconds = timeout_seconds

    def build_article_request(
        self,
        *,
        query: str,
        timespan: str = "7d",
        max_records: int = 75,
    ) -> Request:
        if not query.strip():
            raise ValueError("query must not be empty")
        if not timespan.strip():
            raise ValueError("timespan must not be empty")
        if not 1 <= max_records <= 250:
            raise ValueError("max_records must be between 1 and 250")

        parameters = urlencode(
            {
                "query": query.strip(),
                "mode": "ArtList",
                "format": "json",
                "timespan": timespan.strip(),
                "maxrecords": max_records,
                "sort": "DateDesc",
            }
        )
        return Request(
            f"{GDELT_DOC_URL}?{parameters}",
            headers={"Accept": "application/json"},
            method="GET",
        )

    def fetch_articles(
        self,
        *,
        query: str,
        query_topic: str,
        timespan: str = "7d",
        max_records: int = 75,
    ) -> list[NormalizedNewsArticle]:
        request = self.build_article_request(
            query=query,
            timespan=timespan,
            max_records=max_records,
        )
        with self._opener(request, timeout=self._timeout_seconds) as response:
            payload = json.load(response)
        return normalize_article_payload(
            payload,
            query_topic=query_topic,
            fetched_at=datetime.now(UTC),
        )
