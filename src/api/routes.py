import csv
import io
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates

from src.collector_status import CollectorStatus
from src.repository.base import LogReader

router = APIRouter()
_templates = Jinja2Templates(directory=Path(__file__).parent / "templates")


def _reader(request: Request) -> LogReader:
    return request.app.state.reader


def _status(request: Request) -> CollectorStatus:
    return request.app.state.status


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return _templates.TemplateResponse(request, "index.html")


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.get("/api/status")
async def get_status(status: CollectorStatus = Depends(_status)):
    return {
        "running": status.running,
        "router_reachable": status.router_reachable,
        "last_success": status.last_success.isoformat() if status.last_success else None,
        "last_error": status.last_error,
    }


@router.get("/api/logs/recent")
async def get_recent(
    limit: int = Query(default=100, le=1000),
    reader: LogReader = Depends(_reader),
):
    entries = await reader.get_recent(limit)
    return [_to_dict(e) for e in entries]


@router.get("/api/logs")
async def query_logs(
    start: datetime | None = None,
    end: datetime | None = None,
    level: str | None = None,
    search: str | None = None,
    limit: int = Query(default=500, le=5000),
    reader: LogReader = Depends(_reader),
):
    entries = await reader.query(start, end, level, search, limit)
    return [_to_dict(e) for e in entries]


@router.get("/api/export")
async def export_logs(
    format: str = Query(default="json"),
    start: datetime | None = None,
    end: datetime | None = None,
    level: str | None = None,
    search: str | None = None,
    reader: LogReader = Depends(_reader),
):
    if format not in ("json", "csv"):
        raise HTTPException(status_code=400, detail=f"Invalid format '{format}'. Use 'json' or 'csv'.")

    entries = await reader.query(start, end, level, search, limit=1_000_000)
    dicts = [_to_dict(e) for e in entries]

    if format == "csv":
        buf = io.StringIO()
        if dicts:
            writer = csv.DictWriter(buf, fieldnames=list(dicts[0].keys()))
            writer.writeheader()
            writer.writerows(dicts)
        return StreamingResponse(
            iter([buf.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=logs.csv"},
        )
    return dicts


def _to_dict(entry) -> dict:
    return {
        "id": entry.id,
        "timestamp": entry.timestamp.isoformat(),
        "level": entry.level,
        "source": entry.source,
        "message": entry.message,
        "raw": entry.raw,
        "collected_at": entry.collected_at.isoformat(),
    }
