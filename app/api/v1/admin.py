from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from app.models.api import success_response, error_response
from app.services.database_service import DatabaseService
from app.services.llm_service import CLAUDE_PRICING
from app.services.summary_service import refresh_customer_summary, refresh_all_summaries
from app.models.database import ApiUsage
from bson.errors import InvalidId
from bson import ObjectId
from datetime import datetime
import structlog
import time

logger = structlog.get_logger()

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/customers/{customer_id}", summary="Get customer financial profile")
async def get_customer_profile(customer_id: str, request: Request):
    request_id: str = getattr(request.state, "request_id", None)
    start_time = time.time()
    status_code = 200

    try:
        try:
            ObjectId(customer_id)
        except InvalidId:
            status_code = 400
            raise HTTPException(status_code=400, detail="Invalid customer ID format")

        context = await DatabaseService.get_customer_context(customer_id)
        if "error" in context:
            status_code = 404
            raise HTTPException(status_code=404, detail=context["error"])

        return success_response(context, request_id=request_id)

    except HTTPException as exc:
        status_code = exc.status_code
        code = {400: "INVALID_ID", 404: "CUSTOMER_NOT_FOUND"}.get(exc.status_code, "SERVER_ERROR")
        return error_response(code, exc.detail, request_id=request_id)
    except Exception as e:
        status_code = 500
        logger.error("customer_profile_error", error=str(e), customer_id=customer_id)
        return error_response("SERVER_ERROR", str(e), request_id=request_id)
    finally:
        response_time = (time.time() - start_time) * 1000
        user_id = None
        try:
            user_id = ObjectId(customer_id)
        except Exception:
            pass
        await DatabaseService.insert_api_usage(ApiUsage(
            endpoint=f"/api/v1/admin/customers/{customer_id}",
            method="GET",
            user_id=user_id,
            timestamp=datetime.now().isoformat(),
            status_code=status_code,
            response_time_ms=response_time,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        ))


@router.get("/usage", summary="API usage statistics")
async def get_usage_stats(request: Request):
    request_id: str = getattr(request.state, "request_id", None)
    try:
        stats = await DatabaseService.get_usage_stats()
        return success_response({
            "total": {
                "requests": stats.get("total_requests", 0),
                "tokens": stats.get("total_tokens", 0),
                "cost_usd": round(stats.get("total_cost", 0.0), 4),
            },
            "today": {
                "requests": stats.get("requests_today", 0),
                "tokens": stats.get("tokens_today", 0),
                "cost_usd": round(stats.get("cost_today", 0.0), 4),
            },
            "pricing": CLAUDE_PRICING,
        }, request_id=request_id)
    except Exception as e:
        logger.error("usage_stats_error", error=str(e))
        return error_response("SERVER_ERROR", str(e), request_id=request_id)


@router.post("/customers/{customer_id}/refresh-summary", summary="Refresh AI summary for one customer")
async def refresh_summary(customer_id: str, request: Request):
    """Regenerate the advisor-facing summary for a single customer immediately."""
    request_id: str = getattr(request.state, "request_id", None)
    try:
        ObjectId(customer_id)
    except InvalidId:
        return error_response("INVALID_ID", "Invalid customer ID format", request_id=request_id)

    ok, metrics = await refresh_customer_summary(customer_id)
    if not ok:
        return error_response(
            "SUMMARY_FAILED",
            "Could not generate summary — customer may not exist or Claude call failed.",
            request_id=request_id,
        )
    customer = await DatabaseService.get_customer(customer_id)
    return success_response({
        "customer_id": customer_id,
        "summary": customer.summary if customer else None,
        "metrics": metrics,
    }, request_id=request_id)


@router.post("/refresh-summaries", summary="Trigger summary refresh (due customers by default)")
async def trigger_refresh_all(
    background_tasks: BackgroundTasks,
    request: Request,
    force: bool = False,
):
    """
    Queue a background refresh of AI summaries. Returns immediately.

    - Default (`force=false`): only refreshes customers whose summary was last
      generated 3+ months ago or has never been generated.
    - `force=true`: regenerates every customer regardless of last refresh date.

    The same due-only logic also runs automatically every Monday at 02:00 UTC.
    """
    request_id: str = getattr(request.state, "request_id", None)

    if force:
        count = len(await DatabaseService.get_all_customer_ids())
        label = "all"
    else:
        count = len(await DatabaseService.get_customers_due_for_summary_refresh(months=3))
        label = "due"

    background_tasks.add_task(refresh_all_summaries, force)
    logger.info("summary_batch_triggered_manually", mode=label, count=count, request_id=request_id)
    return success_response(
        {"message": f"Summary refresh started for {count} {label} customers. Check server logs for progress."},
        request_id=request_id,
    )


@router.get("/health", tags=["Health"], summary="Health check")
async def health_check(request: Request):
    request_id: str = getattr(request.state, "request_id", None)
    start_time = time.time()
    status_code = 200

    try:
        await DatabaseService.get_global_variables()
        return success_response(
            {"status": "healthy", "api": "running", "mongodb": "connected"},
            request_id=request_id,
        )
    except Exception as e:
        status_code = 500
        return success_response(
            {"status": "unhealthy", "api": "running", "mongodb": f"disconnected — {e}"},
            request_id=request_id,
        )
    finally:
        response_time = (time.time() - start_time) * 1000
        await DatabaseService.insert_api_usage(ApiUsage(
            endpoint="/api/v1/admin/health",
            method="GET",
            timestamp=datetime.now().isoformat(),
            status_code=status_code,
            response_time_ms=response_time,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        ))
