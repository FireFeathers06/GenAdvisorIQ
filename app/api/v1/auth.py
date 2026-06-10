# app/api/v1/auth.py — advisor login / refresh / logout / me
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel

from app.core.auth import get_current_advisor
from app.core.database import mongodb
from app.core.ratelimit import limiter
from app.core.security import REFRESH_TOKEN_TTL, create_token, decode_token, verify_password
from app.models.api import success_response, error_response
from app.models.database import Agent
import structlog

logger = structlog.get_logger()

router = APIRouter(prefix="/auth", tags=["Auth"])

_REFRESH_COOKIE = "gaiq_refresh"


class LoginRequest(BaseModel):
    username: str
    password: str


def _advisor_payload(agent: Agent) -> dict:
    name = f"{agent.first_name} {agent.last_name}".strip()
    return {
        "id": str(agent.id),
        "username": agent.username,
        "name": name,
        "initials": (agent.first_name[:1] + agent.last_name[:1]).upper(),
        "email": agent.email,
        "company": agent.company,
        "role": agent.role,
    }


def _set_refresh_cookie(response: Response, advisor_id: str):
    response.set_cookie(
        key=_REFRESH_COOKIE,
        value=create_token(advisor_id, "refresh"),
        max_age=int(REFRESH_TOKEN_TTL.total_seconds()),
        httponly=True,
        samesite="strict",
        path="/api/v1/auth",
        # secure=True requires TLS; enable when deployed behind HTTPS
    )


@router.post("/login", summary="Advisor login")
@limiter.limit("5/minute")
async def login(body: LoginRequest, request: Request, response: Response):
    request_id: str = getattr(request.state, "request_id", None)
    db = mongodb.get_db()

    ident = body.username.strip().lower()
    doc = await db["agents"].find_one({"$or": [{"username": ident}, {"email": ident}]})

    if not doc or not verify_password(body.password, doc.get("password", "")):
        logger.warning("login_failed", username=ident,
                       ip=request.client.host if request.client else None)
        return error_response("INVALID_CREDENTIALS", "Invalid username or password",
                              request_id=request_id)

    agent = Agent(**doc)
    advisor_id = str(agent.id)
    _set_refresh_cookie(response, advisor_id)
    logger.info("login_success", advisor_id=advisor_id, username=agent.username)

    return success_response({
        "access_token": create_token(advisor_id, "access"),
        "token_type": "bearer",
        "advisor": _advisor_payload(agent),
    }, request_id=request_id)


@router.post("/refresh", summary="Exchange refresh cookie for a new access token")
async def refresh(request: Request, response: Response):
    request_id: str = getattr(request.state, "request_id", None)
    token = request.cookies.get(_REFRESH_COOKIE)
    advisor_id = decode_token(token, expected_type="refresh") if token else None
    if not advisor_id:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    from bson import ObjectId
    doc = await mongodb.get_db()["agents"].find_one({"_id": ObjectId(advisor_id)})
    if not doc:
        raise HTTPException(status_code=401, detail="Advisor account not found")

    agent = Agent(**doc)
    # Rotate the refresh token alongside the access token
    _set_refresh_cookie(response, advisor_id)
    return success_response({
        "access_token": create_token(advisor_id, "access"),
        "token_type": "bearer",
        "advisor": _advisor_payload(agent),
    }, request_id=request_id)


@router.post("/logout", summary="Clear the refresh cookie")
async def logout(request: Request, response: Response):
    request_id: str = getattr(request.state, "request_id", None)
    response.delete_cookie(_REFRESH_COOKIE, path="/api/v1/auth")
    return success_response({"message": "Logged out"}, request_id=request_id)


@router.get("/me", summary="Current advisor profile")
async def me(request: Request, advisor: Agent = Depends(get_current_advisor)):
    request_id: str = getattr(request.state, "request_id", None)
    return success_response({"advisor": _advisor_payload(advisor)}, request_id=request_id)
