import os

import httpx
from mcp.server.fastmcp import FastMCP

_MCP_PORT: int = int(os.getenv("MCP_PORT", "8081"))
mcp = FastMCP("router-logs", host="0.0.0.0", port=_MCP_PORT)
_BASE_URL: str = os.getenv("LOG_API_URL", "http://localhost:8080")


@mcp.tool()
async def get_status() -> dict:
    """
    Check whether the log collector is running and the router is reachable.
    Returns running status, router reachability, and the last successful poll time.
    """
    async with httpx.AsyncClient() as client:
        try:
            r = await client.get(f"{_BASE_URL}/api/status", timeout=10.0)
            r.raise_for_status()
            return r.json()
        except (httpx.HTTPError, ValueError) as exc:
            return {"error": str(exc), "running": False, "router_reachable": False}


@mcp.tool()
async def get_recent_logs(limit: int = 100) -> list:
    """
    Get the most recent router log entries, newest first.

    Args:
        limit: Number of entries to return (max 1000, default 100).
    """
    async with httpx.AsyncClient() as client:
        try:
            r = await client.get(
                f"{_BASE_URL}/api/logs/recent",
                params={"limit": min(limit, 1000)},
                timeout=30.0,
            )
            r.raise_for_status()
            return r.json()
        except (httpx.HTTPError, ValueError) as exc:
            return [{"error": str(exc)}]


@mcp.tool()
async def search_logs(
    start: str | None = None,
    end: str | None = None,
    level: str | None = None,
    search: str | None = None,
    limit: int = 200,
) -> list:
    """
    Search and filter router log entries.

    Args:
        start: Start of time range as ISO 8601 string (e.g. "2026-05-10T00:00:00+10:00").
        end:   End of time range as ISO 8601 string.
        level: Filter by severity: INFO, WARNING, ERROR, or CRITICAL.
        search: Free-text search within log messages.
        limit: Max entries to return (default 200, max 5000).
    """
    params: dict = {"limit": min(limit, 5000)}
    if start:
        params["start"] = start
    if end:
        params["end"] = end
    if level:
        params["level"] = level
    if search:
        params["search"] = search

    async with httpx.AsyncClient() as client:
        try:
            r = await client.get(f"{_BASE_URL}/api/logs", params=params, timeout=30.0)
            r.raise_for_status()
            return r.json()
        except (httpx.HTTPError, ValueError) as exc:
            return [{"error": str(exc)}]


if __name__ == "__main__":
    mcp.run(transport="sse")
