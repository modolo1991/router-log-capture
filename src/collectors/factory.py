from src.collectors.base import LogCollector
from src.collectors.http_scraper import HTTPScraper
from src.collectors.parsers.optus_parser import OptusParser
from src.collectors.sagemcom_collector import SagemcomCollector
from src.collectors.syslog_collector import SyslogCollector
from src.config import Settings

_PARSERS = {
    "optus": OptusParser,
}


class CollectorFactory:
    @staticmethod
    def create(settings: Settings) -> LogCollector:
        if settings.collector_type == "syslog":
            return SyslogCollector(
                host="0.0.0.0",
                port=settings.syslog_port,
                source=settings.router_ip,
            )
        if settings.collector_type == "http_scraper":
            parser_cls = _PARSERS.get(settings.http_scraper_parser)
            if parser_cls is None:
                raise ValueError(
                    f"Unknown parser '{settings.http_scraper_parser}'. "
                    f"Available: {list(_PARSERS)}"
                )
            return HTTPScraper(
                router_ip=settings.router_ip,
                login_path=settings.router_login_path,
                username=settings.router_username,
                password=settings.router_password,
                log_path=settings.router_log_path,
                parser=parser_cls(),
                username_field=settings.router_login_username_field,
                password_field=settings.router_login_password_field,
            )
        if settings.collector_type == "sagemcom":
            return SagemcomCollector(
                router_ip=settings.router_ip,
                username=settings.router_username,
                password=settings.router_password,
            )
        raise ValueError(
            f"Unknown collector type '{settings.collector_type}'. "
            f"Use 'syslog', 'http_scraper', or 'sagemcom'."
        )
