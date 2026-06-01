from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
from anthropic import AsyncAnthropic
from app.core.config import settings

router = APIRouter(prefix="/chat", tags=["AI Chat"])


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatCompleteRequest(BaseModel):
    messages: List[ChatMessage]


@router.post("/complete", summary="Proxy chat completion to Claude")
async def chat_complete(req: ChatCompleteRequest):
    client = AsyncAnthropic(api_key=settings.claude_api_key)
    message = await client.messages.create(
        model=settings.claude_model,
        max_tokens=1500,
        messages=[{"role": m.role, "content": m.content} for m in req.messages],
    )
    return {
        "content": message.content[0].text,
        "input_tokens": message.usage.input_tokens,
        "output_tokens": message.usage.output_tokens,
    }
