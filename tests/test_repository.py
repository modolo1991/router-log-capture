import pytest
from datetime import datetime, timezone

from src.domain.log_entry import LogEntry
from src.repository.sqlite_repository import SQLiteLogRepository


def _entry(message: str = "test", level: str = "INFO", raw: str | None = None) -> LogEntry:
    now = datetime.now(timezone.utc)
    return LogEntry(
        timestamp=now, level=level, source="192.168.0.1",
        message=message, raw=raw or f"raw:{message}", collected_at=now,
    )


@pytest.fixture
async def repo(tmp_path):
    r = SQLiteLogRepository(str(tmp_path / "test.db"))
    await r.init()
    return r


async def test_save_and_get_recent(repo):
    await repo.save([_entry("msg1"), _entry("msg2")])
    result = await repo.get_recent(10)
    assert len(result) == 2


async def test_get_recent_respects_limit(repo):
    await repo.save([_entry(f"msg{i}", raw=f"raw{i}") for i in range(10)])
    result = await repo.get_recent(3)
    assert len(result) == 3


async def test_get_recent_returns_newest_first(repo):
    from datetime import timedelta
    now = datetime.now(timezone.utc)
    old = LogEntry(timestamp=now - timedelta(hours=1), level="INFO", source="x",
                   message="old", raw="old", collected_at=now)
    new = LogEntry(timestamp=now, level="INFO", source="x",
                   message="new", raw="new", collected_at=now)
    await repo.save([old, new])
    result = await repo.get_recent(10)
    assert result[0].message == "new"


async def test_deduplication_ignores_duplicate_raw(repo):
    entry = _entry("duplicate", raw="identical-raw-line")
    await repo.save([entry])
    await repo.save([entry])
    result = await repo.get_recent(10)
    assert len(result) == 1


async def test_query_filters_by_level(repo):
    await repo.save([_entry("info msg", "INFO"), _entry("error msg", "ERROR", raw="raw-error")])
    result = await repo.query(None, None, "ERROR", None, 10)
    assert len(result) == 1
    assert result[0].level == "ERROR"


async def test_query_filters_by_search(repo):
    await repo.save([_entry("connection dropped"), _entry("normal traffic", raw="raw-normal")])
    result = await repo.query(None, None, None, "dropped", 10)
    assert len(result) == 1
    assert "dropped" in result[0].message


async def test_save_empty_list_is_noop(repo):
    await repo.save([])
    result = await repo.get_recent(10)
    assert result == []
