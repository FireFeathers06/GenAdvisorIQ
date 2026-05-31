from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from app.api.v1.insights import router as insights_router
from app.api.v1.admin import router as admin_router
from app.core.database import mongodb
from app.services.summary_service import refresh_all_summaries
import structlog
import logging
import time
import uuid

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
)

logger = structlog.get_logger()


# ---------------------------------------------------------------------------
# Request logging middleware
# ---------------------------------------------------------------------------

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        start = time.time()
        logger.info("request_started", method=request.method, path=request.url.path)

        response = await call_next(request)

        latency_ms = round((time.time() - start) * 1000, 2)
        logger.info(
            "request_completed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            latency_ms=latency_ms,
        )
        response.headers["X-Request-ID"] = request_id
        return response


# ---------------------------------------------------------------------------
# App lifecycle
# ---------------------------------------------------------------------------

scheduler = AsyncIOScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await mongodb.connect_db()

    # Weekly scan: regenerate summaries only for customers whose last refresh
    # was 3+ months ago (or who have never had a summary generated).
    scheduler.add_job(
        refresh_all_summaries,
        CronTrigger(day_of_week="mon", hour="2", minute="0"),
        id="weekly_summary_refresh",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("startup_complete", version="1.0.0", next_summary_run=str(
        scheduler.get_job("weekly_summary_refresh").next_run_time
    ))

    yield

    scheduler.shutdown(wait=False)
    await mongodb.close_db()
    logger.info("shutdown_complete")


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="GenAdvisorIQ API",
    description="AI-powered financial advisor using Claude & MongoDB",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(RequestLoggingMiddleware)

app.include_router(insights_router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/v1")


@app.get("/", tags=["Health"])
def read_root():
    return {
        "message": "GenAdvisorIQ API",
        "version": "1.0.0",
        "endpoints": {
            "ask": "POST /api/v1/insights/ask",
            "customer": "GET /api/v1/admin/customers/{customer_id}",
            "usage": "GET /api/v1/admin/usage",
            "health": "GET /api/v1/admin/health",
            "docs": "GET /docs",
        },
    }
