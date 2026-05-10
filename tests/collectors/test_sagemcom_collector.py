import gzip
import hashlib
import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.collectors.sagemcom_collector import (
    SagemcomCollector,
    _compute_auth_key,
    _sha512,
)


# ---------------------------------------------------------------------------
# Unit helpers
# ---------------------------------------------------------------------------

def test_sha512_returns_128_hex_chars():
    result = _sha512("test")
    assert len(result) == 128
    assert all(c in "0123456789abcdef" for c in result)


def test_sha512_deterministic():
    assert _sha512("hello") == _sha512("hello")


def test_compute_auth_key_matches_browser():
    # Verified against a real browser login capture (credentials anonymised)
    username = "testuser"
    password = "testpass123"
    password_hash = _sha512(password)
    server_nonce = ""          # empty on login → double-colon in ha1
    request_id = 0
    cnonce = 2113430775
    expected = (
        "e97a54a11463d8b6dc583f31daaf225831a8f893337efe4fac4cbb5d6a6653b6"
        "b275c52db47145e3d9fa3238ca97995b7ef656552232bf89f31e332cad504dc7"
    )
    assert _compute_auth_key(username, password_hash, server_nonce, request_id, cnonce) == expected


def test_compute_auth_key_changes_with_cnonce():
    ph = _sha512("pass")
    assert _compute_auth_key("u", ph, "", 0, 1) != _compute_auth_key("u", ph, "", 0, 2)


def test_compute_auth_key_changes_with_request_id():
    ph = _sha512("pass")
    assert _compute_auth_key("u", ph, "", 0, 99) != _compute_auth_key("u", ph, "", 1, 99)


def test_compute_auth_key_changes_with_nonce():
    ph = _sha512("pass")
    assert _compute_auth_key("u", ph, "", 0, 1) != _compute_auth_key("u", ph, "abc", 0, 1)


# ---------------------------------------------------------------------------
# Collector behaviour
# ---------------------------------------------------------------------------

def _make_collector() -> SagemcomCollector:
    return SagemcomCollector(router_ip="192.168.0.1", username="admin", password="pass")


def _login_response(session_id: int = 999, nonce: str = "testnonce") -> MagicMock:
    r = MagicMock()
    r.raise_for_status = MagicMock()
    r.json.return_value = {
        "reply": {
            "actions": [{
                "callbacks": [{
                    "parameters": {"id": session_id, "nonce": nonce}
                }]
            }]
        }
    }
    return r


def _uri_response(uri: str = "/download/abc/logFile") -> MagicMock:
    r = MagicMock()
    r.raise_for_status = MagicMock()
    r.json.return_value = {
        "reply": {
            "actions": [{"callbacks": [{"parameters": {"uri": uri}}]}]
        }
    }
    return r


def _log_response(content: bytes) -> MagicMock:
    r = MagicMock()
    r.raise_for_status = MagicMock()
    r.content = content
    return r


async def test_collect_raises_before_connect():
    collector = _make_collector()
    with pytest.raises(RuntimeError, match="connect\\(\\) must be called"):
        await collector.collect()


async def test_collect_returns_parsed_entries():
    collector = _make_collector()
    collector._client = AsyncMock()
    collector._session_id = 999
    collector._server_nonce = "testnonce"

    log_text = b"<6>May 10 12:00:00 router daemon.info: WAN up\n"
    collector._client.post = AsyncMock(return_value=_uri_response())
    collector._client.get = AsyncMock(return_value=_log_response(log_text))

    entries = await collector.collect()
    assert len(entries) == 1
    assert "WAN up" in entries[0].message


async def test_collect_deduplicates_identical_lines():
    collector = _make_collector()
    collector._client = AsyncMock()
    collector._session_id = 999
    collector._server_nonce = "testnonce"

    log_text = b"<6>May 10 12:00:00 router daemon.info: same line\n"
    collector._client.post = AsyncMock(return_value=_uri_response())
    collector._client.get = AsyncMock(return_value=_log_response(log_text))

    first = await collector.collect()
    second = await collector.collect()
    assert len(first) == 1
    assert len(second) == 0


async def test_collect_handles_gzip_content():
    collector = _make_collector()
    collector._client = AsyncMock()
    collector._session_id = 999
    collector._server_nonce = "testnonce"

    raw = "<6>May 10 12:00:00 router daemon.info: compressed\n"
    gz_content = gzip.compress(raw.encode())
    collector._client.post = AsyncMock(return_value=_uri_response())
    collector._client.get = AsyncMock(return_value=_log_response(gz_content))

    entries = await collector.collect()
    assert "compressed" in entries[0].message


async def test_collect_retries_login_on_http_error():
    import httpx

    collector = _make_collector()
    collector._client = AsyncMock()

    log_text = b"<6>May 10 12:00:00 router a: ok\n"

    request = MagicMock()
    bad_post = MagicMock()
    bad_post.raise_for_status = MagicMock(
        side_effect=httpx.HTTPStatusError("401", request=request, response=MagicMock())
    )

    collector._login = AsyncMock()
    collector._client.post = AsyncMock(side_effect=[bad_post, _uri_response()])
    collector._client.get = AsyncMock(return_value=_log_response(log_text))

    entries = await collector.collect()
    collector._login.assert_called_once()
    assert len(entries) == 1


async def test_login_stores_session_id_and_nonce():
    collector = _make_collector()
    collector._client = AsyncMock()
    collector._client.post = AsyncMock(return_value=_login_response(session_id=12345, nonce="mynonce"))

    await collector._login()

    assert collector._session_id == 12345
    assert collector._server_nonce == "mynonce"


async def test_login_increments_req_index():
    collector = _make_collector()
    collector._client = AsyncMock()
    collector._client.post = AsyncMock(return_value=_login_response())

    assert collector._req_index == 0
    await collector._login()
    assert collector._req_index == 1


async def test_disconnect_closes_client():
    collector = _make_collector()
    collector._client = AsyncMock()
    client = collector._client
    await collector.disconnect()
    client.aclose.assert_called_once()
    assert collector._client is None


async def test_disconnect_is_safe_when_not_connected():
    collector = _make_collector()
    await collector.disconnect()


def test_decode_content_plain_text():
    collector = _make_collector()
    assert collector._decode_content(b"hello world") == "hello world"


def test_decode_content_gzip():
    collector = _make_collector()
    compressed = gzip.compress(b"hello gzip")
    assert collector._decode_content(compressed) == "hello gzip"


def test_build_payload_includes_auth_key_and_cnonce():
    collector = _make_collector()
    collector._session_id = 999
    collector._server_nonce = "testnonce"

    payload = json.loads(collector._build_payload(actions=[{"id": 0, "method": "test"}]))
    req = payload["request"]

    assert "auth-key" in req
    assert "cnonce" in req
    assert len(req["auth-key"]) == 128
    assert req["session-id"] == 999
