from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api import routes
from src.collector_status import CollectorStatus
from src.domain.log_entry import LogEntry


def _entry(id: int = 1, level: str = "INFO") -> LogEntry:
    now = datetime.now(timezone.utc)
    return LogEntry(
        id=id, timestamp=now, level=level, source="192.168.0.1",
        message="test message", raw="raw", collected_at=now,
    )


@pytest.fixture
def client():
    mock_reader = AsyncMock()
    mock_reader.get_recent.return_value = [_entry(1), _entry(2)]
    mock_reader.query.return_value = [_entry(1, "ERROR")]

    status = CollectorStatus(
        running=True,
        router_reachable=True,
        last_success=datetime.now(timezone.utc),
    )

    test_app = FastAPI()
    test_app.include_router(routes.router)
    test_app.state.reader = mock_reader
    test_app.state.status = status
    return TestClient(test_app)


def test_health_returns_ok(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_status_returns_running_true(client):
    r = client.get("/api/status")
    assert r.status_code == 200
    data = r.json()
    assert data["running"] is True
    assert data["router_reachable"] is True
    assert data["last_success"] is not None
    assert data["last_error"] is None


def test_recent_logs_returns_entries(client):
    r = client.get("/api/logs/recent?limit=10")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 2
    assert data[0]["level"] == "INFO"


def test_recent_logs_default_limit_is_100():
    from unittest.mock import AsyncMock
    from src.api import routes
    from src.collector_status import CollectorStatus

    mock_reader = AsyncMock()
    mock_reader.get_recent.return_value = []
    status = CollectorStatus(running=True)

    test_app = FastAPI()
    test_app.include_router(routes.router)
    test_app.state.reader = mock_reader
    test_app.state.status = status
    c = TestClient(test_app)

    c.get("/api/logs/recent")
    mock_reader.get_recent.assert_called_once_with(100)


def test_query_logs_passes_filters():
    from unittest.mock import AsyncMock
    from src.api import routes
    from src.collector_status import CollectorStatus

    mock_reader = AsyncMock()
    mock_reader.query.return_value = []
    status = CollectorStatus(running=True)

    test_app = FastAPI()
    test_app.include_router(routes.router)
    test_app.state.reader = mock_reader
    test_app.state.status = status
    c = TestClient(test_app)

    c.get("/api/logs?level=ERROR&search=test&limit=50")
    mock_reader.query.assert_called_once()
    args = mock_reader.query.call_args[0]
    assert args[2] == "ERROR"  # level is 3rd positional arg (index 2)
    assert args[3] == "test"   # search is 4th positional arg (index 3)
    assert args[4] == 50       # limit is 5th positional arg (index 4)


def test_export_json_returns_list(client):
    r = client.get("/api/export?format=json")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_export_csv_returns_text(client):
    r = client.get("/api/export?format=csv")
    assert r.status_code == 200
    assert "text/csv" in r.headers["content-type"]
