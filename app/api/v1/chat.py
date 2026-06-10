# app/api/v1/chat.py — authenticated Claude proxy with per-advisor guardrails
from datetime import datetime, timezone
from typing import List

from anthropic import AsyncAnthropic
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from app.core.auth import get_current_advisor
from app.core.config import settings
from app.core.database import mongodb
from app.core.ratelimit import limiter
from app.models.database import Agent, ApiUsage
from app.services.database_service import DatabaseService
from app.services.llm_service import calculate_cost
import structlog

logger = structlog.get_logger()

router = APIRouter(prefix="/chat", tags=["AI Chat"])


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatCompleteRequest(BaseModel):
    messages: List[ChatMessage]


async def _tokens_used_today(advisor_id: str) -> int:
    """Sum of chat tokens consumed by this advisor since midnight UTC."""
    db = mongodb.get_db()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    pipeline = [
        {"$match": {
            "advisor_id": ObjectId(advisor_id),
            "endpoint": "/api/v1/chat/complete",
            "timestamp": {"$gte": today},
        }},
        {"$group": {"_id": None, "tokens": {"$sum": "$tokens_used"}}},
    ]
    result = await db["api_usage"].aggregate(pipeline).to_list(length=1)
    return int(result[0]["tokens"]) if result else 0


def _validate_payload(req: ChatCompleteRequest):
    if not req.messages:
        raise HTTPException(status_code=400, detail="messages must not be empty")
    if len(req.messages) > settings.chat_max_messages:
        raise HTTPException(
            status_code=400,
            detail=f"Too many messages (max {settings.chat_max_messages})",
        )
    total_chars = sum(len(m.content) for m in req.messages)
    if total_chars > settings.chat_max_request_chars:
        raise HTTPException(
            status_code=413,
            detail=f"Message payload too large (max {settings.chat_max_request_chars} characters)",
        )
    for m in req.messages:
        if m.role not in ("user", "assistant"):
            raise HTTPException(status_code=400, detail=f"Invalid role '{m.role}'")


@router.post("/complete", summary="Proxy chat completion to Claude")
@limiter.limit("20/minute")
async def chat_complete(
    req: ChatCompleteRequest,
    request: Request,
    advisor: Agent = Depends(get_current_advisor),
):
    _validate_payload(req)

    advisor_id = str(advisor.id)
    used = await _tokens_used_today(advisor_id)
    if used >= settings.chat_daily_token_budget:
        logger.warning("chat_budget_exceeded", advisor_id=advisor_id, used=used)
        raise HTTPException(
            status_code=429,
            detail="Daily AI token budget exhausted. Resets at midnight UTC.",
        )

    client = AsyncAnthropic(api_key=settings.claude_api_key)
    message = await client.messages.create(
        model=settings.claude_model,
        max_tokens=settings.chat_max_output_tokens,
        messages=[{"role": m.role, "content": m.content} for m in req.messages],
    )

    input_tokens = message.usage.input_tokens
    output_tokens = message.usage.output_tokens
    total_tokens = input_tokens + output_tokens
    cost = calculate_cost(settings.claude_model, input_tokens, output_tokens)

    await DatabaseService.insert_api_usage(ApiUsage(
        endpoint="/api/v1/chat/complete",
        method="POST",
        advisor_id=ObjectId(advisor_id),
        timestamp=datetime.now(timezone.utc).isoformat(),
        status_code=200,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        tokens_used=total_tokens,
        cost_usd=cost["total_cost"],
    ))

    return {
        "content": message.content[0].text,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "budget": {
            "daily_limit": settings.chat_daily_token_budget,
            "used_today": used + total_tokens,
        },
    }
