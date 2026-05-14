import asyncio
import hashlib
import re
from datetime import datetime, timezone

from src.collectors.base import LogCollector
from src.domain.log_entry import LogEntry

_RFC5424 = re.compile(
    r"<(\d+)>(\d+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(.*)"
)
_RFC3164 = re.compile(
    r"<(\d+)>(\w{3}\s+\d+\s+\d+:\d+:\d+)\s+\S+\s+(.*)"
)
_SEVERITY = {
    0: "CRITICAL", 1: "CRITICAL", 2: "CRITICAL",
    3: "ERROR",
    4: "WARNING",
    5: "INFO", 6: "INFO", 7: "INFO",
}


class SyslogCollector(LogCollector):
    def __init__(self, host: str, port: int, source: str) -> None:
        self._host = host
        self._port = port
        self._source = source
        self._queue: asyncio.Queue[bytes] = asyncio.Queue()
        self._transport: asyncio.BaseTransport | None = None
        self._seen: set[str] = set()

    async def connect(self) -> None:
        loop = asyncio.get_running_loop()
        self._transport, _ = await loop.create_datagram_endpoint(
            lambda: _SyslogProtocol(self._queue),
            local_addr=(self._host, self._port),
        )

    async def collect(self) -> list[LogEntry]:
        self._seen.clear()
        entries: list[LogEntry] = []
        while not self._queue.empty():
            raw_bytes = self._queue.get_nowait()
            raw = raw_bytes.decode("utf-8", errors="replace").strip()
            key = hashlib.sha256(raw.encode()).hexdigest()
            if key in self._seen:
                continue
            self._seen.add(key)
            entries.append(self._parse(raw))
        return entries

    async def disconnect(self) -> None:
        if self._transport:
            self._transport.close()

    def _parse(self, raw: str) -> LogEntry:
        now = datetime.now(timezone.utc)

        m = _RFC5424.match(raw)
        if m:
            severity = int(m.group(1)) % 8
            ts_str = m.group(3)
            try:
                ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
            except ValueError:
                ts = now
            return LogEntry(
                timestamp=ts,
                level=_SEVERITY.get(severity, "INFO"),
                source=self._source,
                message=m.group(9),
                raw=raw,
                collected_at=now,
            )

        m = _RFC3164.match(raw)
        if m:
            severity = int(m.group(1)) % 8
            try:
                local_tz = datetime.now().astimezone().tzinfo
                ts = datetime.strptime(
                    f"{now.year} {m.group(2)}", "%Y %b %d %H:%M:%S"
                ).replace(tzinfo=local_tz)
            except ValueError:
                ts = now
            return LogEntry(
                timestamp=ts,
                level=_SEVERITY.get(severity, "INFO"),
                source=self._source,
                message=m.group(3),
                raw=raw,
                collected_at=now,
            )

        return LogEntry(
            timestamp=now, level="INFO", source=self._source,
            message=raw, raw=raw, collected_at=now,
        )


class _SyslogProtocol(asyncio.DatagramProtocol):
    def __init__(self, queue: asyncio.Queue[bytes]) -> None:
        self._queue = queue

    def datagram_received(self, data: bytes, addr: tuple) -> None:
        self._queue.put_nowait(data)
