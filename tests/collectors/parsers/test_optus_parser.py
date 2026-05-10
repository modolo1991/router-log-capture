from src.collectors.parsers.optus_parser import OptusParser

SAMPLE_HTML = """
<html><body>
<table>
  <tr><th>Timestamp</th><th>Level</th><th>Message</th></tr>
  <tr><td>2026-01-15T10:00:00+00:00</td><td>Error</td><td>WAN connection lost</td></tr>
  <tr><td>2026-01-15T10:01:30+00:00</td><td>Warning</td><td>DNS lookup failed</td></tr>
  <tr><td>2026-01-15T10:02:00+00:00</td><td>Info</td><td>WAN reconnected</td></tr>
</table>
</body></html>
"""

EMPTY_TABLE_HTML = """
<html><body>
<table><tr><th>Timestamp</th><th>Level</th><th>Message</th></tr></table>
</body></html>
"""

NO_TABLE_HTML = "<html><body><p>No logs available.</p></body></html>"


def test_parse_returns_correct_count():
    entries = OptusParser().parse(SAMPLE_HTML, source="http://192.168.0.1")
    assert len(entries) == 3


def test_parse_error_level_mapping():
    entries = OptusParser().parse(SAMPLE_HTML, source="http://192.168.0.1")
    assert entries[0].level == "ERROR"


def test_parse_warning_level_mapping():
    entries = OptusParser().parse(SAMPLE_HTML, source="http://192.168.0.1")
    assert entries[1].level == "WARNING"


def test_parse_info_level_mapping():
    entries = OptusParser().parse(SAMPLE_HTML, source="http://192.168.0.1")
    assert entries[2].level == "INFO"


def test_parse_message_content():
    entries = OptusParser().parse(SAMPLE_HTML, source="http://192.168.0.1")
    assert entries[0].message == "WAN connection lost"


def test_parse_source_is_passed_through():
    entries = OptusParser().parse(SAMPLE_HTML, source="http://192.168.0.1")
    assert entries[0].source == "http://192.168.0.1"


def test_parse_empty_table_returns_empty_list():
    entries = OptusParser().parse(EMPTY_TABLE_HTML, source="http://192.168.0.1")
    assert entries == []


def test_parse_no_table_returns_empty_list():
    entries = OptusParser().parse(NO_TABLE_HTML, source="http://192.168.0.1")
    assert entries == []


def test_parse_crit_alias_maps_to_critical():
    html = """<html><body><table>
      <tr><th>T</th><th>L</th><th>M</th></tr>
      <tr><td>2026-01-15T10:00:00+00:00</td><td>Crit</td><td>system failure</td></tr>
    </table></body></html>"""
    entries = OptusParser().parse(html, source="http://192.168.0.1")
    assert entries[0].level == "CRITICAL"


def test_parse_warn_alias_maps_to_warning():
    html = """<html><body><table>
      <tr><th>T</th><th>L</th><th>M</th></tr>
      <tr><td>2026-01-15T10:00:00+00:00</td><td>Warn</td><td>high load</td></tr>
    </table></body></html>"""
    entries = OptusParser().parse(html, source="http://192.168.0.1")
    assert entries[0].level == "WARNING"


def test_parse_notice_alias_maps_to_info():
    html = """<html><body><table>
      <tr><th>T</th><th>L</th><th>M</th></tr>
      <tr><td>2026-01-15T10:00:00+00:00</td><td>Notice</td><td>service started</td></tr>
    </table></body></html>"""
    entries = OptusParser().parse(html, source="http://192.168.0.1")
    assert entries[0].level == "INFO"


def test_parse_debug_alias_maps_to_info():
    html = """<html><body><table>
      <tr><th>T</th><th>L</th><th>M</th></tr>
      <tr><td>2026-01-15T10:00:00+00:00</td><td>Debug</td><td>verbose output</td></tr>
    </table></body></html>"""
    entries = OptusParser().parse(html, source="http://192.168.0.1")
    assert entries[0].level == "INFO"
