from datetime import datetime, timezone

from src.collectors.parsers.sagemcom_parser import SagemcomParser

_SRC = "http://192.168.0.1"
_NOW = datetime(2026, 5, 10, 12, 0, 0, tzinfo=timezone.utc)


def _parse(raw: str) -> list:
    return SagemcomParser().parse(raw, source=_SRC)


def test_empty_input_returns_empty_list():
    assert _parse("") == []


def test_blank_lines_are_skipped():
    assert _parse("\n\n  \n") == []


def test_rfc3164_error_priority():
    # priority 3 → severity 3 → ERROR
    entries = _parse("<3>May 10 12:00:00 router kern.err: disk full")
    assert len(entries) == 1
    assert entries[0].level == "ERROR"


def test_rfc3164_warning_priority():
    entries = _parse("<4>May 10 12:00:00 router daemon.warn: high load")
    assert entries[0].level == "WARNING"


def test_rfc3164_info_priority():
    entries = _parse("<6>May 10 12:00:00 router daemon.info: started")
    assert entries[0].level == "INFO"


def test_rfc3164_critical_priority():
    # priority 0 → severity 0 → CRITICAL
    entries = _parse("<0>May 10 12:00:00 router kern.emerg: kernel panic")
    assert entries[0].level == "CRITICAL"


def test_rfc3164_priority_wraps_modulo_8():
    # facility=1, severity=2 → 1*8+2=10; 10%8=2 → CRITICAL
    entries = _parse("<10>May 10 12:00:00 router kern.crit: oops")
    assert entries[0].level == "CRITICAL"


def test_rfc3164_message_extracted():
    # Everything after hostname is the message (process tag included per RFC 3164)
    entries = _parse("<6>May 10 12:00:00 router daemon.info: WAN connected")
    assert entries[0].message == "daemon.info: WAN connected"


def test_rfc3164_source_passed_through():
    entries = _parse("<6>May 10 12:00:00 router daemon.info: test")
    assert entries[0].source == _SRC


def test_rfc3164_raw_preserved():
    raw = "<6>May 10 12:00:00 router daemon.info: test"
    entries = _parse(raw)
    assert entries[0].raw == raw


def test_plain_timestamp_line_parsed_as_info():
    entries = _parse("May 10 12:00:00 router WAN link up")
    assert entries[0].level == "INFO"


def test_plain_timestamp_message_extracted():
    entries = _parse("May 10 12:00:00 router WAN link up")
    assert entries[0].message == "WAN link up"


def test_fallback_line_parsed_as_info():
    entries = _parse("some unrecognised log line")
    assert entries[0].level == "INFO"
    assert entries[0].message == "some unrecognised log line"


def test_multiple_lines_all_returned():
    raw = "<6>May 10 12:00:00 router a: first\n<3>May 10 12:00:01 router b: second"
    entries = _parse(raw)
    assert len(entries) == 2


def test_collected_at_is_set():
    entries = _parse("<6>May 10 12:00:00 router a: msg")
    assert entries[0].collected_at is not None


# ---------------------------------------------------------------------------
# Sagemcom native format: DD.MM.YYYY HH:MM:SS LEVEL message
# ---------------------------------------------------------------------------

def test_sagemcom_native_timestamp_parsed():
    entries = _parse("30.04.2026 22:42:22 INF WIFI 1 device connected")
    from datetime import datetime
    local_tz = datetime.now().astimezone().tzinfo
    ts = entries[0].timestamp
    # Timestamp should reflect router local time, not be shifted by UTC offset
    assert ts.astimezone(local_tz).hour == 22
    assert ts.astimezone(local_tz).day == 30
    assert ts.astimezone(local_tz).month == 4


def test_sagemcom_native_inf_maps_to_info():
    entries = _parse("30.04.2026 22:42:22 INF WIFI 1 device connected")
    assert entries[0].level == "INFO"


def test_sagemcom_native_wrn_maps_to_warning():
    entries = _parse("30.04.2026 22:42:22 WRN SYS 0 high load")
    assert entries[0].level == "WARNING"


def test_sagemcom_native_err_maps_to_error():
    entries = _parse("30.04.2026 22:42:22 ERR WAN 0 link down")
    assert entries[0].level == "ERROR"


def test_sagemcom_native_crt_maps_to_critical():
    entries = _parse("30.04.2026 22:42:22 CRT SYS 0 kernel panic")
    assert entries[0].level == "CRITICAL"


def test_sagemcom_native_message_extracted():
    entries = _parse("30.04.2026 22:42:22 INF WIFI 1 device connected")
    assert entries[0].message == "WIFI 1 device connected"


def test_sagemcom_native_timestamp_differs_per_line():
    raw = "30.04.2026 22:42:22 INF WIFI 1 first\n01.05.2026 08:00:00 INF WAN 0 second"
    entries = _parse(raw)
    assert entries[0].timestamp != entries[1].timestamp
