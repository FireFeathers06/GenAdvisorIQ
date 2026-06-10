from fastapi import APIRouter, Depends, HTTPException, Request
from app.models.query import QueryRequest
from app.models.api import success_response, error_response
from app.core.auth import get_current_advisor
from app.services.query_service import process_query
from app.services.database_service import DatabaseService
from app.models.database import Agent, ApiUsage
from bson.errors import InvalidId
from bson import ObjectId
from datetime import datetime
import structlog
import time

logger = structlog.get_logger()

router = APIRouter(prefix="/insights", tags=["AI Insights"])


@router.post("/ask", summary="Get personalized financial advice")
async def ask(query: QueryRequest, request: Request,
              advisor: Agent = Depends(get_current_advisor)):
    request_id: str = getattr(request.state, "request_id", None)
    start_time = time.time()
    status_code = 200

    try:
        try:
            ObjectId(query.customer_id)
        except InvalidId:
            status_code = 400
            raise HTTPException(status_code=400, detail="Invalid customer ID format")

        customer = await DatabaseService.get_customer(query.customer_id)
        if not customer or str(customer.agent_id) != str(advisor.id):
            status_code = 404
            raise HTTPException(status_code=404, detail=f"Customer {query.customer_id} not found")

        result = await process_query(query)

        if result.get("status") == "error":
            status_code = 500
            raise HTTPException(status_code=500, detail="AI processing error")

        logger.info("insight_generated", customer_id=query.customer_id, request_id=request_id)
        return success_response(result, request_id=request_id)

    except HTTPException as exc:
        status_code = exc.status_code
        code = {400: "INVALID_ID", 404: "CUSTOMER_NOT_FOUND"}.get(exc.status_code, "SERVER_ERROR")
        return error_response(code, exc.detail, request_id=request_id)
    except Exception as e:
        status_code = 500
        logger.error("insight_error", error=str(e), customer_id=query.customer_id)
        return error_response("SERVER_ERROR", "Unexpected server error", request_id=request_id)
    finally:
        response_time = (time.time() - start_time) * 1000
        tokens = cost = user_id = None
        try:
            user_id = ObjectId(query.customer_id)
            if "result" in dir() and isinstance(result, dict) and "metrics" in result:
                tokens = result["metrics"].get("total_tokens")
                cost = result["metrics"].get("cost", {}).get("total_cost")
        except Exception:
            pass
        await DatabaseService.insert_api_usage(ApiUsage(
            endpoint="/api/v1/insights/ask",
            method="POST",
            user_id=user_id,
            timestamp=datetime.now().isoformat(),
            status_code=status_code,
            response_time_ms=response_time,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            request_size_bytes=int(request.headers.get("content-length", 0)) or None,
            tokens_used=tokens,
            cost_usd=cost,
        ))
