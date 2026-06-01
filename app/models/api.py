from pydantic import BaseModel
from typing import Any, Optional
import uuid
from datetime import datetime, timezone


class APIError(BaseModel):
    code: str
    message: str
    details: dict = {}


class APIMeta(BaseModel):
    request_id: str
    timestamp: str


class APIResponse(BaseModel):
    success: bool
    data: Optional[Any] = None
    meta: APIMeta
    error: Optional[APIError] = None


def success_response(data: Any, request_id: str | None = None) -> dict:
    return APIResponse(
        success=True,
        data=data,
        meta=APIMeta(
            request_id=request_id or str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc).isoformat(),
        ),
    ).model_dump()


def error_response(
    code: str,
    message: str,
    details: dict | None = None,
    request_id: str | None = None,
) -> dict:
    return APIResponse(
        success=False,
        data=None,
        meta=APIMeta(
            request_id=request_id or str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc).isoformat(),
        ),
        error=APIError(code=code, message=message, details=details or {}),
    ).model_dump()
