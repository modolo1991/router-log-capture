#!/usr/bin/env python3
"""Interactive setup wizard — run once per machine to generate .env."""
import getpass
import json
import os
import subprocess
from pathlib import Path


def _choose(question: str, options: list[tuple[str, str]], default: int = 1) -> str:
    """Present a numbered menu and return the value of the chosen option.

    options: list of (label, value) pairs
    default: 1-based index of the default choice
    """
    print(f"\n{question}")
    for i, (label, _) in enumerate(options, 1):
        marker = "  <-- default" if i == default else ""
        print(f"  {i}) {label}{marker}")
    while True:
        answer = input(f"Enter number [1-{len(options)}] (press Enter for default): ").strip()
        if not answer:
            return options[default - 1][1]
        try:
            idx = int(answer) - 1
            if 0 <= idx < len(options):
                return options[idx][1]
        except ValueError:
            pass
        print(f"  Please enter a number between 1 and {len(options)}.")


def _prompt(question: str, default: str = "") -> str:
    suffix = f" (default: {default})" if default else ""
    answer = input(f"{question}{suffix}: ").strip()
    return answer if answer else default


def _prompt_secret(question: str) -> str:
    while True:
        answer = getpass.getpass(f"{question}: ").strip()
        if answer:
            return answer
        print("  Password cannot be empty, please try again.")


_MCP_URL = "http://localhost:8081/sse"


def _detect_mcp_clients() -> list[tuple[str, str]]:
    home = Path.home()
    found = []
    if (home / ".claude").exists():
        found.append(("Claude Code", "claude_code"))
    if (home / ".codex").exists():
        found.append(("Codex", "codex"))
    if (home / ".cursor").exists():
        found.append(("Cursor", "cursor"))
    if (home / ".continue").exists():
        found.append(("Continue.dev", "continue"))
    return found


def _configure_claude_code() -> str:
    import sys
    # Windows reads MCPs from ~/.claude.json; other platforms use ~/.claude/settings.json
    if sys.platform == "win32":
        path = Path.home() / ".claude.json"
    else:
        path = Path.home() / ".claude" / "settings.json"
    settings: dict = {}
    if path.exists():
        try:
            with open(path, encoding="utf-8") as f:
                settings = json.load(f)
        except json.JSONDecodeError:
            print(f"  Warning: {path} contains invalid JSON — will overwrite with merged config.")
    if settings.get("mcpServers", {}).get("router-logs", {}).get("url") == _MCP_URL:
        return "already configured"
    settings.setdefault("mcpServers", {})["router-logs"] = {"type": "sse", "url": _MCP_URL}
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2)
    return "configured"


def _configure_codex() -> str:
    subprocess.run(["codex", "mcp", "remove", "router-logs"], capture_output=True)
    result = subprocess.run(
        ["codex", "mcp", "add", "router-logs", "--url", _MCP_URL],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        return f"failed — {result.stderr.strip()}"
    return "configured"


def _configure_cursor() -> str:
    path = Path.home() / ".cursor" / "mcp.json"
    config: dict = {}
    if path.exists():
        try:
            with open(path, encoding="utf-8") as f:
                config = json.load(f)
        except json.JSONDecodeError:
            print(f"  Warning: {path} contains invalid JSON — will overwrite with merged config.")
    if config.get("mcpServers", {}).get("router-logs", {}).get("url") == _MCP_URL:
        return "already configured"
    config.setdefault("mcpServers", {})["router-logs"] = {"url": _MCP_URL}
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)
    return "configured"


def _configure_continue() -> str:
    path = Path.home() / ".continue" / "config.json"
    config: dict = {}
    if path.exists():
        try:
            with open(path, encoding="utf-8") as f:
                config = json.load(f)
        except json.JSONDecodeError:
            print(f"  Warning: {path} contains invalid JSON — will overwrite with merged config.")
    servers: list = config.setdefault("experimental", {}).setdefault(
        "modelContextProtocolServers", []
    )
    if any(s.get("transport", {}).get("url") == _MCP_URL for s in servers):
        return "already configured"
    servers.append({"transport": {"type": "sse", "url": _MCP_URL}})
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)
    return "configured"


_CLIENT_FUNCS: dict = {
    "claude_code": _configure_claude_code,
    "codex": _configure_codex,
    "cursor": _configure_cursor,
    "continue": _configure_continue,
}


def _configure_mcp_clients() -> None:
    print()
    print("=" * 40)
    print("  AI Assistant Integration (MCP)")
    print("=" * 40)

    detected = _detect_mcp_clients()

    if not detected:
        print("\nNo supported AI assistants detected on this machine.")
        print("If you install one later, run python setup.py again.")
        print(f"\nManual configuration URL: {_MCP_URL}")
        return

    print("\nDetected AI assistants:")
    for i, (label, _) in enumerate(detected, 1):
        print(f"  {i}) {label}")

    print()
    answer = input(
        "Configure them to access your router logs? [Y/n]\n"
        "(You can skip this and run python setup.py again at any time): "
    ).strip().lower()

    if answer == "n":
        print("\nSkipped. Run python setup.py again whenever you're ready.")
        print(f"Manual URL: {_MCP_URL}")
        return

    if len(detected) == 1:
        selected = detected
    else:
        print("\nWhich ones? Enter numbers separated by commas (press Enter for all):")
        for i, (label, _) in enumerate(detected, 1):
            print(f"  {i}) {label}")
        choice = input("Selection: ").strip()
        if not choice:
            selected = detected
        else:
            indices = [
                int(p.strip()) - 1
                for p in choice.split(",")
                if p.strip().isdigit()
            ]
            selected = [detected[i] for i in indices if 0 <= i < len(detected)] or detected

    print()
    for label, key in selected:
        status = _CLIENT_FUNCS[key]()
        print(f"  {label}: {status}")

    print()
    print("Note: MCP only works while Docker is running (docker compose up -d).")
    print("Ask your AI assistant about your router logs to get started.")
    print(f"\nManual configuration URL (for other tools): {_MCP_URL}")


def main() -> None:
    print()
    print("=" * 40)
    print("  Router Log Capture  --  Setup Wizard")
    print("=" * 40)

    collector_type = _choose(
        "What type of router do you have?",
        [
            ("Sagemcom-based (e.g. Optus FAST5366LTE-A)", "sagemcom"),
            ("Syslog — router pushes logs to this machine (e.g. D-Link)", "syslog"),
            ("HTTP scraper — logs behind a web login page", "http_scraper"),
        ],
        default=1,
    )

    router_ip = _prompt("\nRouter IP address", "192.168.0.1")
    poll_interval = _prompt("How often to check for new logs (seconds)", "30")
    api_port = _prompt("Port for the web UI", "8080")
    timezone = _choose(
        "What timezone are you in?",
        [
            ("Australia/Brisbane (AEST, no daylight saving)", "Australia/Brisbane"),
            ("Australia/Sydney (AEST/AEDT)", "Australia/Sydney"),
            ("Australia/Perth (AWST)", "Australia/Perth"),
            ("UTC", "UTC"),
        ],
        default=1,
    )

    lines = [
        f"COLLECTOR_TYPE={collector_type}",
        f"TZ={timezone}",
        f"ROUTER_IP={router_ip}",
        f"POLL_INTERVAL_SECONDS={poll_interval}",
        f"API_PORT={api_port}",
        "DATABASE_PATH=/data/logs.db",
    ]

    if collector_type == "sagemcom":
        print("\n-- Sagemcom router credentials --")
        username = _prompt("Router admin username", "admin")
        password = _prompt_secret("Router admin password")
        lines += [
            f"ROUTER_USERNAME={username}",
            f"ROUTER_PASSWORD={password}",
        ]

    elif collector_type == "syslog":
        print("\n-- Syslog settings --")
        print("  Your router needs to be configured to send syslog to this machine's IP.")
        syslog_port = _prompt("Syslog listen port", "514")
        syslog_protocol = _choose(
            "Syslog transport protocol:",
            [("UDP (most common)", "udp"), ("TCP", "tcp")],
            default=1,
        )
        lines += [
            f"SYSLOG_PORT={syslog_port}",
            f"SYSLOG_PROTOCOL={syslog_protocol}",
        ]

    elif collector_type == "http_scraper":
        print("\n-- HTTP scraper settings --")
        username = _prompt("Router admin username", "admin")
        password = _prompt_secret("Router admin password")
        login_path = _prompt("Login page path", "/cgi-bin/login.cgi")
        username_field = _prompt("Login form — username field name", "username")
        password_field = _prompt("Login form — password field name", "password")
        log_path = _prompt("Log page path", "/maintenance/logs")
        lines += [
            f"ROUTER_USERNAME={username}",
            f"ROUTER_PASSWORD={password}",
            f"ROUTER_LOGIN_PATH={login_path}",
            f"ROUTER_LOGIN_USERNAME_FIELD={username_field}",
            f"ROUTER_LOGIN_PASSWORD_FIELD={password_field}",
            f"ROUTER_LOG_PATH={log_path}",
            "HTTP_SCRAPER_PARSER=optus",
        ]

    env_path = ".env"
    if os.path.exists(env_path):
        print(f"\n.env already exists.")
        answer = input("Overwrite it with the new settings? [y/N]: ").strip().lower()
        if answer != "y":
            print("Cancelled — your existing .env was not changed.")
            return

    with open(env_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print(f"\nConfiguration saved.")
    print("\nTo start the app, run:")
    print("\n    docker compose up -d")
    print(f"\nThen open http://localhost:{api_port} in your browser.")

    _configure_mcp_clients()


if __name__ == "__main__":
    main()
