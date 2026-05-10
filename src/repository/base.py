from abc import ABC, abstractmethod
from datetime import datetime

from src.domain.log_entry import LogEntry


class LogWriter(ABC):
    @abstractmethod
    async def save(self, entries: list[LogEntry]) -> None: ...


class LogReader(ABC):
    @abstractmethod
    async def get_recent(self, limit: int) -> list[LogEntry]: ...

    @abstractmethod
    async def query(
        self,
        start: datetime | None,
        end: datetime | None,
        level: str | None,
        search: str | None,
        limit: int,
    ) -> list[LogEntry]: ...
