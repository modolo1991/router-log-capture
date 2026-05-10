import re
from datetime import datetime, timezone

from src.collectors.parsers.base import LogParser
from src.domain.log_entry import LogEntry

# Sagemcom native format: "DD.MM.YYYY HH:MM:SS LEVEL rest of message"
_SAGEMCOM = re.compile(r"(\d{2}\.\d{2}\.\d{4} \d{2}:\d{2}:\d{2}) (\w+) (.*)")

_RFC3164 = re.compile(r"<(\d+)>(\w{3}\s+\d+\s+\d+:\d+:\d+)\s+\S+\s+(.*)")
_PLAIN_TS = re.compile(r"(\w{3}\s+\d+\s+\d+:\d+:\d+)\s+\S+\s+(.*)")

_SEVERITY: dict[int, str] = {
    0: "CRITICAL", 1: "CRITICAL", 2: "CRITICAL",
    3: "ERROR",
    4: "WARNING",
    5: "INFO", 6: "INFO", 7: "INFO",
}

_SAGEMCOM_LEVEL: dict[str, str] = {
    "INF": "INFO",
    "WRN": "WARNING",
    "ERR": "ERROR",
    "CRT": "CRITICAL",
    "DBG": "INFO",
}


class SagemcomParser(LogParser):
    """Parses the raw syslog text file downloaded from a Sagemcom router."""

    def parse(self, raw_response: str, source: str) -> list[LogEntry]:
        now = datetime.now(timezone.utc)
        entries: list[LogEntry] = []
        for line in raw_response.splitlines():
            line = line.strip()
            if not line:
                continue
            entries.append(self._parse_line(line, source, now))
        return entries

    def _parse_line(self, raw: str, source: str, now: datetime) -> LogEntry:
        m = _SAGEMCOM.match(raw)
        if m:
            level = _SAGEMCOM_LEVEL.get(m.group(2), "INFO")
            try:
                # Router timestamps are in local time — interpret them as such
                local_tz = datetime.now().astimezone().tzinfo
                ts = datetime.strptime(m.group(1), "%d.%m.%Y %H:%M:%S").replace(tzinfo=local_tz)
            except ValueError:
                ts = now
            return LogEntry(
                timestamp=ts, level=level, source=source,
                message=m.group(3), raw=raw, collected_at=now,
            )

        m = _RFC3164.match(raw)
        if m:
            severity = int(m.group(1)) % 8
            level = _SEVERITY.get(severity, "INFO")
            try:
                ts = datetime.strptime(
                    f"{now.year} {m.group(2)}", "%Y %b %d %H:%M:%S"
                ).replace(tzinfo=timezone.utc)
            except ValueError:
                ts = now
            return LogEntry(
                timestamp=ts, level=level, source=source,
                message=m.group(3), raw=raw, collected_at=now,
            )

        m = _PLAIN_TS.match(raw)
        if m:
            try:
                ts = datetime.strptime(
                    f"{now.year} {m.group(1)}", "%Y %b %d %H:%M:%S"
                ).replace(tzinfo=timezone.utc)
            except ValueError:
                ts = now
            return LogEntry(
                timestamp=ts, level="INFO", source=source,
                message=m.group(2), raw=raw, collected_at=now,
            )

        return LogEntry(
            timestamp=now, level="INFO", source=source,
            message=raw, raw=raw, collected_at=now,
        )
