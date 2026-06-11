# app/api/v1/copilot.py — grounded advisor copilot: SSE streaming + tool-use loop.
#
# The browser sends only the conversation history and a scope; all context
# (book snapshot, client data) is assembled server-side. Events emitted:
#   {"type": "text", "text": "..."}            incremental response tokens
#   {"type": "tool", "name": ..., "label": ...} a drill-down tool is running
#   {"type": "done", "usage": ..., "budget": ...}
#   {"type": "error", "message": "..."}
import json
import re
from datetime import datetime, timezone
from typing import List, Optional

from anthropic import AsyncAnthropic
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.core.auth import get_current_advisor
from app.core.config import settings
from app.core.ratelimit import limiter
from app.models.database import Agent, ApiUsage
from app.services.copilot_service import (
    COPILOT_TOOLS,
    build_system_blocks,
    run_copilot_tool,
    tool_status_label,
)
from app.services.database_service import DatabaseService
from app.services.llm_service import calculate_cost
from app.services.usage_service import tokens_used_today
import structlog

logger = structlog.get_logger()

router = APIRouter(prefix="/copilot", tags=["AI Copilot"])

MAX_TOOL_ROUNDS = 6
_SCOPE_RE = re.compile(r"^(book|client:[0-9a-f]{24})$")


class CopilotMessage(BaseModel):
    role: str
    content: str


class CopilotAskRequest(BaseModel):
    messages: List[CopilotMessage]
    scope: Optional[str] = "book"


def _validate(req: CopilotAskRequest):
    if not req.messages:
        raise HTTPException(status_code=400, detail="messages must not be empty")
    if len(req.messages) > settings.chat_max_messages:
        raise HTTPException(status_code=400,
                            detail=f"Too many messages (max {settings.chat_max_messages})")
    total_chars = sum(len(m.content) for m in req.messages)
    if total_chars > settings.chat_max_request_chars:
        raise HTTPException(status_code=413,
                            detail=f"Message payload too large (max {settings.chat_max_request_chars} characters)")
    for m in req.messages:
        if m.role not in ("user", "assistant"):
            raise HTTPException(status_code=400, detail=f"Invalid role '{m.role}'")
    if req.scope and not _SCOPE_RE.match(req.scope):
        raise HTTPException(status_code=400, detail="scope must be 'book' or 'client:<id>'")


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"


@router.post("/ask", summary="Grounded copilot chat (SSE stream)")
@limiter.limit("20/minute")
async def copilot_ask(
    req: CopilotAskRequest,
    request: Request,
    advisor: Agent = Depends(get_current_advisor),
):
    _validate(req)

    advisor_id = str(advisor.id)
    used = await tokens_used_today(advisor_id)
    if used >= settings.chat_daily_token_budget:
        logger.warning("copilot_budget_exceeded", advisor_id=advisor_id, used=used)
        raise HTTPException(status_code=429,
                            detail="Daily AI token budget exhausted. Resets at midnight UTC.")

    system_blocks, client_names = await build_system_blocks(advisor, req.scope)
    client = AsyncAnthropic(api_key=settings.claude_api_key)
    messages = [{"role": m.role, "content": m.content} for m in req.messages]

    async def event_stream():
        totals = {"input": 0, "output": 0, "cache_read": 0, "cache_write": 0}
        try:
            for _ in range(MAX_TOOL_ROUNDS):
                async with client.messages.stream(
                    model=settings.claude_model,
                    max_tokens=settings.chat_max_output_tokens,
                    system=system_blocks,
                    tools=COPILOT_TOOLS,
                    messages=messages,
                ) as stream:
                    async for event in stream:
                        if (event.type == "content_block_delta"
                                and event.delta.type == "text_delta"):
                            yield _sse({"type": "text", "text": event.delta.text})
                    final = await stream.get_final_message()

                totals["input"] += final.usage.input_tokens
                totals["output"] += final.usage.output_tokens
                totals["cache_read"] += getattr(final.usage, "cache_read_input_tokens", 0) or 0
                totals["cache_write"] += getattr(final.usage, "cache_creation_input_tokens", 0) or 0

                if final.stop_reason != "tool_use":
                    break

                tool_results = []
                for block in final.content:
                    if block.type != "tool_use":
                        continue
                    yield _sse({
                        "type": "tool",
                        "name": block.name,
                        "label": tool_status_label(block.name, block.input, client_names),
                    })
                    result = await run_copilot_tool(block.name, block.input, advisor_id)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    })
                messages.append({"role": "assistant", "content": final.content})
                messages.append({"role": "user", "content": tool_results})
            else:
                logger.warning("copilot_tool_rounds_exhausted", advisor_id=advisor_id)

            total_tokens = totals["input"] + totals["output"]
            cost = calculate_cost(
                settings.claude_model, totals["input"], totals["output"],
                cache_read_tokens=totals["cache_read"],
                cache_write_tokens=totals["cache_write"],
            )
            await DatabaseService.insert_api_usage(ApiUsage(
                endpoint="/api/v1/copilot/ask",
                method="POST",
                advisor_id=ObjectId(advisor_id),
                timestamp=datetime.now(timezone.utc).isoformat(),
                status_code=200,
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
                tokens_used=total_tokens,
                cost_usd=cost["total_cost"],
            ))
            yield _sse({
                "type": "done",
                "usage": {
                    "input_tokens": totals["input"],
                    "output_tokens": totals["output"],
                    "cache_read_tokens": totals["cache_read"],
                    "cache_write_tokens": totals["cache_write"],
                    "cost_usd": cost["total_cost"],
                },
                "budget": {
                    "daily_limit": settings.chat_daily_token_budget,
                    "used_today": used + total_tokens,
                },
            })
        except Exception as e:
            logger.error("copilot_stream_error", advisor_id=advisor_id, error=str(e))
            yield _sse({"type": "error",
                        "message": "AI service error — please try again."})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
