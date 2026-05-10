from datetime import timezone
from src.collectors.syslog_collector import SyslogCollector


def _collector() -> SyslogCollector:
    return SyslogCollector(host="0.0.0.0", port=5514, source="192.168.0.1")


def test_parse_rfc3164_extracts_message():
    c = _collector()
    raw = "<34>Jan 15 10:15:30 myrouter kernel: eth0: link down"
    entry = c._parse(raw)
    assert entry is not None
    assert "eth0" in entry.message
    assert entry.source == "192.168.0.1"
    assert entry.raw == raw


def test_parse_rfc3164_severity_2_maps_to_critical():
    # priority 34 → facility 4, severity 2 → CRITICAL
    c = _collector()
    entry = c._parse("<34>Jan 15 10:15:30 router kernel: link down")
    assert entry is not None
    assert entry.level == "CRITICAL"


def test_parse_rfc5424_extracts_message():
    c = _collector()
    raw = "<165>1 2026-01-15T10:15:30Z myrouter myapp 1234 - - Connection established"
    entry = c._parse(raw)
    assert entry is not None
    assert "Connection" in entry.message


def test_parse_rfc5424_severity_5_maps_to_info():
    # priority 165 → severity 5 → INFO
    c = _collector()
    entry = c._parse("<165>1 2026-01-15T10:15:30Z router app 1 - - msg")
    assert entry is not None
    assert entry.level == "INFO"


def test_parse_severity_3_maps_to_error():
    # priority 3 → severity 3 → ERROR
    c = _collector()
    entry = c._parse("<3>Jan 15 10:15:30 router kernel: disk error")
    assert entry is not None
    assert entry.level == "ERROR"


def test_parse_severity_4_maps_to_warning():
    # priority 4 → severity 4 → WARNING
    c = _collector()
    entry = c._parse("<4>Jan 15 10:15:30 router kernel: high temperature")
    assert entry is not None
    assert entry.level == "WARNING"


def test_parse_unknown_format_returns_info_entry():
    c = _collector()
    raw = "unparseable garbage log line"
    entry = c._parse(raw)
    assert entry is not None
    assert entry.level == "INFO"
    assert entry.message == raw


async def test_collect_drains_queue():
    c = _collector()
    c._queue.put_nowait(b"<165>1 2026-01-15T10:00:00Z r a 1 - - msg1")
    c._queue.put_nowait(b"<165>1 2026-01-15T10:00:01Z r a 1 - - msg2")
    entries = await c.collect()
    assert len(entries) == 2
    assert c._queue.empty()


async def test_collect_deduplicates():
    c = _collector()
    raw = b"<165>1 2026-01-15T10:00:00Z r a 1 - - identical"
    c._queue.put_nowait(raw)
    first = await c.collect()
    c._queue.put_nowait(raw)
    second = await c.collect()
    assert len(first) == 1
    assert len(second) == 0
