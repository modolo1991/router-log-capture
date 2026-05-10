import gzip
import hashlib
import json
import random

import httpx

from src.collectors.base import LogCollector
from src.collectors.parsers.sagemcom_parser import SagemcomParser
from src.domain.log_entry import LogEntry

_LOG_XPATH = "Device/DeviceInfo/VendorLogFiles/VendorLogFile[@uid='1']"


def _sha512(s: str) -> str:
    return hashlib.sha512(s.encode()).hexdigest()


def _compute_auth_key(username: str, password_hash: str, server_nonce: str,
                      request_id: int, cnonce: int) -> str:
    ha1 = _sha512(f"{username}:{server_nonce}:{password_hash}")
    return _sha512(f"{ha1}:{request_id}:{cnonce}:JSON:/cgi/json-req")


class SagemcomCollector(LogCollector):
    def __init__(self, router_ip: str, username: str, password: str) -> None:
        self._base_url = f"http://{router_ip}"
        self._username = username
        self._password_hash = _sha512(password)
        self._session_id: str | int = "0"
        self._server_nonce: str = ""
        self._req_index: int = 0
        self._client: httpx.AsyncClient | None = None
        self._parser = SagemcomParser()
        self._seen: set[str] = set()

    async def connect(self) -> None:
        self._client = httpx.AsyncClient(base_url=self._base_url, timeout=30.0)
        await self._login()

    async def collect(self) -> list[LogEntry]:
        if self._client is None:
            raise RuntimeError("connect() must be called before collect()")
        try:
            download_url = await self._get_log_uri()
        except (httpx.HTTPError, KeyError, IndexError, ValueError):
            await self._login()
            download_url = await self._get_log_uri()

        response = await self._client.get(download_url)
        response.raise_for_status()

        raw_text = self._decode_content(response.content)
        all_entries = self._parser.parse(raw_text, source=self._base_url)
        new_entries: list[LogEntry] = []
        for entry in all_entries:
            key = hashlib.sha256(entry.raw.encode()).hexdigest()
            if key not in self._seen:
                self._seen.add(key)
                new_entries.append(entry)
        return new_entries

    async def disconnect(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    def _decode_content(self, content: bytes) -> str:
        if content[:2] == b"\x1f\x8b":
            content = gzip.decompress(content)
        return content.decode("utf-8", errors="replace")

    def _next_request(self, actions: list, priority: bool = False) -> tuple[int, int, str]:
        """Return (request_id, cnonce, auth_key) and advance the request counter."""
        request_id = self._req_index
        self._req_index = (self._req_index + 1) % 0xFFFFFFFF
        cnonce = random.randint(0, 0xFFFFFFFF)
        auth_key = _compute_auth_key(
            self._username, self._password_hash,
            self._server_nonce, request_id, cnonce,
        )
        return request_id, cnonce, auth_key

    def _build_payload(self, actions: list, priority: bool = False) -> str:
        request_id, cnonce, auth_key = self._next_request(actions, priority)
        return json.dumps({
            "request": {
                "id": request_id,
                "session-id": self._session_id,
                "priority": priority,
                "actions": actions,
                "cnonce": cnonce,
                "auth-key": auth_key,
            }
        })

    async def _login(self) -> None:
        if self._client is None:
            return

        # For login the server nonce is empty, producing a double-colon in ha1.
        self._server_nonce = ""
        self._session_id = "0"
        self._req_index = 0

        payload = self._build_payload(
            actions=[{
                "id": 0,
                "method": "logIn",
                "parameters": {
                    "user": self._username,
                    "persistent": "true",
                    "session-options": {
                        "nss": [{"name": "gtw", "uri": "http://sagemcom.com/gateway-data"}],
                        "language": "ident",
                        "context-flags": {"get-content-name": True, "local-time": True},
                        "capability-depth": 2,
                        "capability-flags": {
                            "name": True, "default-value": False,
                            "restriction": True, "description": False,
                        },
                        "time-format": "ISO_8601",
                        "write-only-string": "_XMO_WRITE_ONLY_",
                        "undefined-write-only-string": "_XMO_UNDEFINED_WRITE_ONLY_",
                    },
                },
            }],
            priority=True,
        )

        r = await self._client.post("/cgi/json-req", data={"req": payload})
        r.raise_for_status()
        data = r.json()

        try:
            params = data["reply"]["actions"][0]["callbacks"][0]["parameters"]
            self._session_id = params["id"]
            self._server_nonce = params["nonce"]
        except (KeyError, IndexError) as exc:
            import logging
            logging.error("Login failed. Router response: %s", data)
            raise RuntimeError(f"Router login failed — unexpected response structure: {data}") from exc

    async def _get_log_uri(self) -> str:
        if self._client is None:
            raise RuntimeError("client not initialised")

        payload = self._build_payload(
            actions=[{
                "id": 0,
                "method": "getVendorLogDownloadURI",
                "xpath": _LOG_XPATH,
                "parameters": {"FileName": "logFile"},
            }],
            priority=False,
        )
        r = await self._client.post("/cgi/json-req", data={"req": payload})
        r.raise_for_status()
        data = r.json()
        uri: str = data["reply"]["actions"][0]["callbacks"][0]["parameters"]["uri"]
        return uri
