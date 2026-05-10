import hashlib
from datetime import datetime, timezone

import aiosqlite

from src.domain.log_entry import LogEntry
from src.repository.base import LogReader, LogWriter

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS log_entries (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp    TEXT NOT NULL,
    level        TEXT NOT NULL,
    source       TEXT NOT NULL,
    message      TEXT NOT NULL,
    raw          TEXT NOT NULL,
    raw_hash     TEXT NOT NULL,
    collected_at TEXT NOT NULL
);
"""
_CREATE_DEDUP_INDEX = """
CREATE UNIQUE INDEX IF NOT EXISTS idx_dedup
    ON log_entries (timestamp, raw_hash);
"""
_CREATE_QUERY_INDEX = """
CREATE INDEX IF NOT EXISTS idx_query
    ON log_entries (timestamp, source, level);
"""


class SQLiteLogRepository(LogWriter, LogReader):
    def __init__(self, db_path: str) -> None:
        self._db_path = db_path

    async def init(self) -> None:
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute("PRAGMA journal_mode=WAL")
            await db.execute(_CREATE_TABLE)
            await db.execute(_CREATE_DEDUP_INDEX)
            await db.execute(_CREATE_QUERY_INDEX)
            await db.commit()

    async def save(self, entries: list[LogEntry]) -> None:
        if not entries:
            return
        rows = [
            (
                entry.timestamp.astimezone(timezone.utc).isoformat(),
                entry.level,
                entry.source,
                entry.message,
                entry.raw,
                hashlib.sha256(entry.raw.encode()).hexdigest(),
                entry.collected_at.astimezone(timezone.utc).isoformat(),
            )
            for entry in entries
        ]
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute("PRAGMA journal_mode=WAL")
            await db.executemany(
                """INSERT OR IGNORE INTO log_entries
                   (timestamp, level, source, message, raw, raw_hash, collected_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                rows,
            )
            await db.commit()

    async def get_recent(self, limit: int) -> list[LogEntry]:
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute("PRAGMA journal_mode=WAL")
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM log_entries ORDER BY timestamp DESC LIMIT ?",
                (limit,),
            )
            return [_row_to_entry(r) for r in await cursor.fetchall()]

    async def query(
        self,
        start: datetime | None,
        end: datetime | None,
        level: str | None,
        search: str | None,
        limit: int,
    ) -> list[LogEntry]:
        clauses: list[str] = []
        params: list[str | int] = []
        if start:
            clauses.append("timestamp >= ?")
            params.append(start.isoformat())
        if end:
            clauses.append("timestamp <= ?")
            params.append(end.isoformat())
        if level:
            clauses.append("level = ?")
            params.append(level.upper())
        if search:
            clauses.append("message LIKE ?")
            params.append(f"%{search}%")
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        params.append(limit)
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute("PRAGMA journal_mode=WAL")
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                f"SELECT * FROM log_entries {where} ORDER BY timestamp DESC LIMIT ?",
                params,
            )
            return [_row_to_entry(r) for r in await cursor.fetchall()]


def _row_to_entry(row: aiosqlite.Row) -> LogEntry:
    return LogEntry(
        id=row["id"],
        timestamp=datetime.fromisoformat(row["timestamp"]),
        level=row["level"],
        source=row["source"],
        message=row["message"],
        raw=row["raw"],
        collected_at=datetime.fromisoformat(row["collected_at"]),
    )
