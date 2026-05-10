import pytest

from src.collectors.factory import CollectorFactory
from src.collectors.http_scraper import HTTPScraper
from src.collectors.sagemcom_collector import SagemcomCollector
from src.collectors.syslog_collector import SyslogCollector
from src.config import Settings


def test_creates_syslog_collector():
    s = Settings(collector_type="syslog", router_ip="192.168.0.1")
    collector = CollectorFactory.create(s)
    assert isinstance(collector, SyslogCollector)


def test_creates_http_scraper():
    s = Settings(
        collector_type="http_scraper",
        router_ip="192.168.0.1",
        http_scraper_parser="optus",
    )
    collector = CollectorFactory.create(s)
    assert isinstance(collector, HTTPScraper)


def test_creates_sagemcom_collector():
    s = Settings(
        collector_type="sagemcom",
        router_ip="192.168.0.1",
        router_username="admin",
        router_password="pass",
    )
    collector = CollectorFactory.create(s)
    assert isinstance(collector, SagemcomCollector)


def test_raises_on_unknown_collector_type():
    s = Settings(collector_type="ftp_collector")
    with pytest.raises(ValueError, match="Unknown collector type"):
        CollectorFactory.create(s)


def test_raises_on_unknown_parser():
    s = Settings(collector_type="http_scraper", http_scraper_parser="cisco")
    with pytest.raises(ValueError, match="Unknown parser"):
        CollectorFactory.create(s)
