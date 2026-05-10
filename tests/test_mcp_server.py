import httpx
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture(autouse=True)
def patch_base_url(monkeypatch):
    monkeypatch.setattr("mcp_server._BASE_URL", "http://test-server:8080")


# ---------------------------------------------------------------------------
# get_status
# ---------------------------------------------------------------------------

def _status_response(data: dict) -> MagicMock:
    r = MagicMock()
    r.raise_for_status = MagicMock()
    r.json.return_value = data
    return r


async def test_get_status_returns_data():
    from mcp_server import get_status
    data = {"running": True, "router_reachable": True, "last_success": None, "last_error": None}
    with patch("httpx.AsyncClient") as mock_cls:
        mock_instance = AsyncMock()
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_instance.get = AsyncMock(return_value=_status_response(data))
        result = await get_status()
    assert result["running"] is True
    assert result["router_reachable"] is True


async def test_get_status_handles_connection_error():
    from mcp_server import get_status
    with patch("httpx.AsyncClient") as mock_cls:
        mock_instance = AsyncMock()
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_instance.get = AsyncMock(side_effect=httpx.ConnectError("refused"))
        result = await get_status()
    assert "error" in result
    assert result["running"] is False


# ---------------------------------------------------------------------------
# get_recent_logs
# ---------------------------------------------------------------------------

async def test_get_recent_logs_returns_entries():
    from mcp_server import get_recent_logs
    r = MagicMock()
    r.raise_for_status = MagicMock()
    r.json.return_value = [{"id": 1, "message": "hello"}]
    with patch("httpx.AsyncClient") as mock_cls:
        mock_instance = AsyncMock()
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_instance.get = AsyncMock(return_value=r)
        result = await get_recent_logs(limit=10)
    assert result[0]["id"] == 1


async def test_get_recent_logs_passes_limit():
    from mcp_server import get_recent_logs
    r = MagicMock()
    r.raise_for_status = MagicMock()
    r.json.return_value = []
    with patch("httpx.AsyncClient") as mock_cls:
        mock_instance = AsyncMock()
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_instance.get = AsyncMock(return_value=r)
        await get_recent_logs(limit=42)
    assert mock_instance.get.call_args[1]["params"]["limit"] == 42


async def test_get_recent_logs_caps_at_1000():
    from mcp_server import get_recent_logs
    r = MagicMock()
    r.raise_for_status = MagicMock()
    r.json.return_value = []
    with patch("httpx.AsyncClient") as mock_cls:
        mock_instance = AsyncMock()
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_instance.get = AsyncMock(return_value=r)
        await get_recent_logs(limit=99999)
    assert mock_instance.get.call_args[1]["params"]["limit"] == 1000


async def test_get_recent_logs_handles_error():
    from mcp_server import get_recent_logs
    with patch("httpx.AsyncClient") as mock_cls:
        mock_instance = AsyncMock()
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_instance.get = AsyncMock(side_effect=httpx.ConnectError("refused"))
        result = await get_recent_logs()
    assert "error" in result[0]


# ---------------------------------------------------------------------------
# search_logs
# ---------------------------------------------------------------------------

async def test_search_logs_passes_all_params():
    from mcp_server import search_logs
    r = MagicMock()
    r.raise_for_status = MagicMock()
    r.json.return_value = []
    with patch("httpx.AsyncClient") as mock_cls:
        mock_instance = AsyncMock()
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_instance.get = AsyncMock(return_value=r)
        await search_logs(
            start="2026-05-10T00:00:00+00:00",
            end="2026-05-10T23:59:59+00:00",
            level="ERROR",
            search="WAN",
            limit=100,
        )
    params = mock_instance.get.call_args[1]["params"]
    assert params["start"] == "2026-05-10T00:00:00+00:00"
    assert params["end"] == "2026-05-10T23:59:59+00:00"
    assert params["level"] == "ERROR"
    assert params["search"] == "WAN"
    assert params["limit"] == 100


async def test_search_logs_omits_none_params():
    from mcp_server import search_logs
    r = MagicMock()
    r.raise_for_status = MagicMock()
    r.json.return_value = []
    with patch("httpx.AsyncClient") as mock_cls:
        mock_instance = AsyncMock()
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_instance.get = AsyncMock(return_value=r)
        await search_logs()
    params = mock_instance.get.call_args[1]["params"]
    assert "start" not in params
    assert "end" not in params
    assert "level" not in params
    assert "search" not in params


async def test_search_logs_caps_limit_at_5000():
    from mcp_server import search_logs
    r = MagicMock()
    r.raise_for_status = MagicMock()
    r.json.return_value = []
    with patch("httpx.AsyncClient") as mock_cls:
        mock_instance = AsyncMock()
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_instance.get = AsyncMock(return_value=r)
        await search_logs(limit=999999)
    assert mock_instance.get.call_args[1]["params"]["limit"] == 5000


async def test_search_logs_handles_error():
    from mcp_server import search_logs
    with patch("httpx.AsyncClient") as mock_cls:
        mock_instance = AsyncMock()
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_instance.get = AsyncMock(side_effect=httpx.ConnectError("refused"))
        result = await search_logs()
    assert "error" in result[0]
