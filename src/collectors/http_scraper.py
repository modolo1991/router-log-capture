import hashlib

import httpx

from src.collectors.base import LogCollector
from src.collectors.parsers.base import LogParser
from src.domain.log_entry import LogEntry


class HTTPScraper(LogCollector):
    def __init__(
        self,
        router_ip: str,
        login_path: str,
        username: str,
        password: str,
        log_path: str,
        parser: LogParser,
        username_field: str = "username",
        password_field: str = "password",
    ) -> None:
        self._base_url = f"http://{router_ip}"
        self._login_path = login_path
        self._username = username
        self._password = password
        self._log_path = log_path
        self._parser = parser
        self._username_field = username_field
        self._password_field = password_field
        self._client: httpx.AsyncClient | None = None
        self._seen: set[str] = set()

    async def connect(self) -> None:
        self._client = httpx.AsyncClient(base_url=self._base_url, timeout=10.0)
        await self._login()

    async def collect(self) -> list[LogEntry]:
        if self._client is None:
            raise RuntimeError("connect() must be called before collect()")
        try:
            response = await self._client.get(self._log_path)
            response.raise_for_status()
        except httpx.HTTPStatusError:
            await self._login()
            response = await self._client.get(self._log_path)
            response.raise_for_status()

        all_entries = self._parser.parse(response.text, source=self._base_url)
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

    async def _login(self) -> None:
        if self._client is None:
            return
        await self._client.post(
            self._login_path,
            data={
                self._username_field: self._username,
                self._password_field: self._password,
            },
        )
