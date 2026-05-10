from datetime import datetime, timezone

from bs4 import BeautifulSoup

from src.collectors.parsers.base import LogParser
from src.domain.log_entry import LogEntry


class OptusParser(LogParser):
    """
    Parses log HTML from the Optus FAST5366LTE-A router admin page.
    Expected format: HTML <table> where each data row has cells:
      [timestamp (ISO 8601), level string, message string].
    If the actual router response differs, override _extract_rows()
    or _parse_cells() in a subclass without touching the rest of the system.
    """

    _LEVEL_MAP: dict[str, str] = {
        "critical": "CRITICAL", "crit": "CRITICAL",
        "error": "ERROR", "err": "ERROR",
        "warning": "WARNING", "warn": "WARNING",
        "notice": "INFO", "info": "INFO", "debug": "INFO",
    }

    def parse(self, raw_response: str, source: str) -> list[LogEntry]:
        soup = BeautifulSoup(raw_response, "html.parser")
        now = datetime.now(timezone.utc)
        entries: list[LogEntry] = []
        for row in self._extract_rows(soup):
            cells = [c.get_text(strip=True) for c in row.find_all(["td", "th"])]
            if len(cells) < 2:
                continue
            raw_line = " | ".join(cells)
            ts, level, message = self._parse_cells(cells, now)
            entries.append(LogEntry(
                timestamp=ts, level=level, source=source,
                message=message, raw=raw_line, collected_at=now,
            ))
        return entries

    def _extract_rows(self, soup: BeautifulSoup) -> list:
        table = soup.find("table")
        if not table:
            return []
        rows = table.find_all("tr")
        return rows[1:] if rows else []

    def _parse_cells(
        self, cells: list[str], fallback_ts: datetime
    ) -> tuple[datetime, str, str]:
        ts = fallback_ts
        level = "INFO"
        message = " ".join(cells)

        if len(cells) >= 3:
            try:
                ts = datetime.fromisoformat(cells[0])
            except ValueError:
                pass
            level = self._LEVEL_MAP.get(cells[1].lower(), "INFO")
            message = cells[2]
        elif len(cells) == 2:
            level = self._LEVEL_MAP.get(cells[0].lower(), "INFO")
            message = cells[1]

        return ts, level, message
