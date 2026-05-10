from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.collectors.http_scraper import HTTPScraper
from src.collectors.parsers.base import LogParser
from src.domain.log_entry import LogEntry


def _now() -> datetime:
    return datetime.now(timezone.utc)


class _FakeParser(LogParser):
    def __init__(self, raw_content: str = "html") -> None:
        self._raw = raw_content

    def parse(self, raw_response: str, source: str) -> list[LogEntry]:
        now = _now()
        return [
            LogEntry(timestamp=now, level="INFO", source=source,
                     message="parsed entry", raw=self._raw, collected_at=now)
        ]


def _make_scraper(parser: LogParser | None = None) -> HTTPScraper:
    return HTTPScraper(
        router_ip="192.168.0.1",
        login_path="/login",
        username="admin",
        password="pass",
        log_path="/logs",
        parser=parser or _FakeParser(),
    )


def _mock_response(text: str = "html") -> MagicMock:
    r = MagicMock()
    r.text = text
    r.raise_for_status = MagicMock()
    return r


async def test_collect_returns_parsed_entries():
    scraper = _make_scraper()
    scraper._client = AsyncMock()
    scraper._client.get = AsyncMock(return_value=_mock_response("html"))
    entries = await scraper.collect()
    assert len(entries) == 1
    assert entries[0].message == "parsed entry"


async def test_collect_deduplicates_by_raw():
    scraper = _make_scraper(_FakeParser(raw_content="identical-raw"))
    scraper._client = AsyncMock()
    scraper._client.get = AsyncMock(return_value=_mock_response())
    first = await scraper.collect()
    second = await scraper.collect()
    assert len(first) == 1
    assert len(second) == 0


async def test_collect_returns_new_entry_after_raw_changes():
    parser = _FakeParser(raw_content="first-content")
    scraper = _make_scraper(parser)
    scraper._client = AsyncMock()
    scraper._client.get = AsyncMock(return_value=_mock_response())
    await scraper.collect()
    parser._raw = "second-content"
    second = await scraper.collect()
    assert len(second) == 1


async def test_disconnect_closes_client():
    scraper = _make_scraper()
    scraper._client = AsyncMock()
    client = scraper._client
    await scraper.disconnect()
    client.aclose.assert_called_once()
    assert scraper._client is None
