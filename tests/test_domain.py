from datetime import datetime, timezone
from src.domain.log_entry import LogEntry


def test_log_entry_id_defaults_to_none():
    now = datetime.now(timezone.utc)
    entry = LogEntry(
        timestamp=now, level="INFO", source="192.168.0.1",
        message="WAN link up", raw="<30>Jan 15 10:00:00 router: WAN link up",
        collected_at=now,
    )
    assert entry.id is None


def test_log_entry_stores_all_fields():
    now = datetime.now(timezone.utc)
    entry = LogEntry(
        timestamp=now, level="ERROR", source="192.168.0.1",
        message="WAN link down", raw="raw line", collected_at=now, id=42,
    )
    assert entry.level == "ERROR"
    assert entry.source == "192.168.0.1"
    assert entry.id == 42
