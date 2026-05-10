from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    collector_type: str = "syslog"

    router_ip: str = "192.168.0.1"
    router_username: str = "admin"
    router_password: str = ""

    router_login_path: str = "/cgi-bin/login.cgi"
    router_login_username_field: str = "username"
    router_login_password_field: str = "password"
    router_log_path: str = "/maintenance/logs"
    http_scraper_parser: str = "optus"

    syslog_port: int = 514
    syslog_protocol: str = "udp"

    poll_interval_seconds: int = 30
    api_port: int = 8080
    database_path: str = "/data/logs.db"


def get_settings() -> Settings:
    return Settings()
