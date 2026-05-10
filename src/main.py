import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI

from src.api import routes
from src.collector_status import CollectorStatus
from src.collectors.factory import CollectorFactory
from src.config import get_settings
from src.repository.sqlite_repository import SQLiteLogRepository

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()

    repository = SQLiteLogRepository(settings.database_path)
    await repository.init()

    collector = CollectorFactory.create(settings)
    await collector.connect()

    status = CollectorStatus(running=True)
    app.state.reader = repository
    app.state.writer = repository
    app.state.status = status

    async def _loop() -> None:
        while True:
            try:
                entries = await collector.collect()
                if entries:
                    await repository.save(entries)
                status.last_success = datetime.now(timezone.utc)
                status.router_reachable = True
                status.last_error = None
            except Exception as exc:
                logger.error("Collection error: %s", exc)
                status.last_error = str(exc)
                status.router_reachable = False
            await asyncio.sleep(settings.poll_interval_seconds)

    task = asyncio.create_task(_loop())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    await collector.disconnect()
    status.running = False


app = FastAPI(title="Router Log Capture", lifespan=lifespan)
app.include_router(routes.router)
