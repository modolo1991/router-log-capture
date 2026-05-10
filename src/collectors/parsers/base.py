from abc import ABC, abstractmethod

from src.domain.log_entry import LogEntry


class LogParser(ABC):
    @abstractmethod
    def parse(self, raw_response: str, source: str) -> list[LogEntry]: ...
