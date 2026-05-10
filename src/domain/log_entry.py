from dataclasses import dataclass
from datetime import datetime


@dataclass
class LogEntry:
    timestamp: datetime
    level: str
    source: str
    message: str
    raw: str
    collected_at: datetime
    id: int | None = None
