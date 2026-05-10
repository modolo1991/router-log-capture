from dataclasses import dataclass
from datetime import datetime


@dataclass
class CollectorStatus:
    running: bool = False
    router_reachable: bool = False
    last_success: datetime | None = None
    last_error: str | None = None
