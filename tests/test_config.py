from src.config import Settings


def test_default_collector_type():
    s = Settings(_env_file=None)
    assert s.collector_type == "syslog"


def test_default_syslog_port():
    s = Settings(_env_file=None)
    assert s.syslog_port == 514


def test_default_poll_interval():
    s = Settings(_env_file=None)
    assert s.poll_interval_seconds == 30


def test_env_override_via_init():
    s = Settings(collector_type="http_scraper", router_ip="10.0.0.1")
    assert s.collector_type == "http_scraper"
    assert s.router_ip == "10.0.0.1"


def test_env_override_via_monkeypatch(monkeypatch):
    monkeypatch.setenv("COLLECTOR_TYPE", "http_scraper")
    monkeypatch.setenv("ROUTER_IP", "172.16.0.1")
    s = Settings()
    assert s.collector_type == "http_scraper"
    assert s.router_ip == "172.16.0.1"


def test_get_settings_returns_settings_instance():
    from src.config import get_settings
    s = get_settings()
    assert isinstance(s, Settings)
