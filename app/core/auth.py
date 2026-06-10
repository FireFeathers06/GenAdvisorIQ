# app/core/auth.py — FastAPI dependency resolving the authenticated advisor
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from bson import ObjectId

from app.core.database import mongodb
from app.core.security import decode_token
from app.models.database import Agent

_bearer = HTTPBearer(auto_error=False)


async def get_current_advisor(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> Agent:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Not authenticated",
                            headers={"WWW-Authenticate": "Bearer"})

    advisor_id = decode_token(credentials.credentials, expected_type="access")
    if not advisor_id:
        raise HTTPException(status_code=401, detail="Invalid or expired token",
                            headers={"WWW-Authenticate": "Bearer"})

    doc = await mongodb.get_db()["agents"].find_one({"_id": ObjectId(advisor_id)})
    if not doc:
        raise HTTPException(status_code=401, detail="Advisor account not found",
                            headers={"WWW-Authenticate": "Bearer"})

    return Agent(**doc)
