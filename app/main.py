from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from app.core.config import settings
from app.core.ratelimit import limiter
from app.api.v1.insights import router as insights_router
from app.api.v1.admin import router as admin_router
from app.api.v1.chat import router as chat_router
from app.api.v1.copilot import router as copilot_router
from app.api.v1.advisor import router as advisor_router
from app.api.v1.auth import router as auth_router
from app.core.database import mongodb
from app.services.summary_service import refresh_all_summaries
import structlog
import logging
import time
import uuid
import os

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

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        if request.url.path.startswith("/ui"):
            # unsafe-eval is required by Babel standalone (removed in Phase 5's
            # Vite build); connect-src 'self' still blocks data exfiltration.
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://unpkg.com https://cdn.jsdelivr.net; "
                "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
                "font-src https://fonts.gstatic.com; "
                "img-src 'self' data:; "
                "connect-src 'self'"
            )
        return response


app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(SecurityHeadersMiddleware)

# Rate limiting — default 120 req/min per IP; stricter limits on login and chat
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# Host header validation (set ALLOWED_HOSTS in .env for production)
_hosts = [h.strip() for h in settings.allowed_hosts.split(",") if h.strip()]
if _hosts and _hosts != ["*"]:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=_hosts)

# CORS — only enabled when an explicit allowlist is configured; the SPA is
# served same-origin and needs no CORS by default
_origins = [o.strip() for o in settings.cors_allowed_origins.split(",") if o.strip()]
if _origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["Authorization", "Content-Type"],
    )

app.include_router(auth_router, prefix="/api/v1")
app.include_router(insights_router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/v1")
app.include_router(chat_router, prefix="/api/v1")
app.include_router(copilot_router, prefix="/api/v1")
app.include_router(advisor_router, prefix="/api/v1")

_static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/ui", StaticFiles(directory=_static_dir, html=True), name="frontend")


@app.get("/", tags=["Health"])
def read_root():
    return {
        "message": "GenAdvisorIQ API",
        "version": "1.0.0",
        "ui": "GET /ui/GenAdvisorIQ.html",
        "endpoints": {
            "ask": "POST /api/v1/insights/ask",
            "chat": "POST /api/v1/chat/complete",
            "copilot": "POST /api/v1/copilot/ask (SSE)",
            "customer": "GET /api/v1/admin/customers/{customer_id}",
            "usage": "GET /api/v1/admin/usage",
            "health": "GET /api/v1/admin/health",
            "docs": "GET /docs",
        },
    }
