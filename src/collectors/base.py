from abc import ABC, abstractmethod

from src.domain.log_entry import LogEntry


class LogCollector(ABC):
    @abstractmethod
    async def connect(self) -> None: ...

    @abstractmethod
    async def collect(self) -> list[LogEntry]: ...

    @abstractmethod
    async def disconnect(self) -> None: ...
