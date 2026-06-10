# app/core/security.py — password hashing (werkzeug-compatible scrypt) and JWT helpers
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

import jwt

from app.core.config import settings

ACCESS_TOKEN_TTL = timedelta(minutes=settings.jwt_access_ttl_minutes)
REFRESH_TOKEN_TTL = timedelta(days=settings.jwt_refresh_ttl_days)
_ALGORITHM = "HS256"

# scrypt parameters matching werkzeug's generate_password_hash defaults,
# so existing hashes in the agents collection keep working.
_SCRYPT_N, _SCRYPT_R, _SCRYPT_P = 32768, 8, 1


# ---------------------------------------------------------------------------
# Password hashing — format: "scrypt:N:r:p$salt$hexdigest" (werkzeug-compatible)
# ---------------------------------------------------------------------------

def hash_password(password: str) -> str:
    salt = secrets.token_hex(8)
    digest = hashlib.scrypt(
        password.encode(), salt=salt.encode(),
        n=_SCRYPT_N, r=_SCRYPT_R, p=_SCRYPT_P, maxmem=132 * 1024 * 1024,
    ).hex()
    return f"scrypt:{_SCRYPT_N}:{_SCRYPT_R}:{_SCRYPT_P}${salt}${digest}"


def verify_password(password: str, stored: str) -> bool:
    try:
        method, salt, digest = stored.split("$", 2)
        if not method.startswith("scrypt:"):
            return False
        _, n, r, p = method.split(":")
        computed = hashlib.scrypt(
            password.encode(), salt=salt.encode(),
            n=int(n), r=int(r), p=int(p), maxmem=132 * 1024 * 1024,
        ).hex()
        return hmac.compare_digest(computed, digest)
    except Exception:
        return False


# ---------------------------------------------------------------------------
# JWT
# ---------------------------------------------------------------------------

def create_token(advisor_id: str, token_type: str) -> str:
    ttl = ACCESS_TOKEN_TTL if token_type == "access" else REFRESH_TOKEN_TTL
    now = datetime.now(timezone.utc)
    payload = {
        "sub": advisor_id,
        "type": token_type,
        "iat": now,
        "exp": now + ttl,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=_ALGORITHM)


def decode_token(token: str, expected_type: str) -> str | None:
    """Return the advisor_id if the token is valid and of the expected type."""
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[_ALGORITHM])
        if payload.get("type") != expected_type:
            return None
        return payload.get("sub")
    except jwt.InvalidTokenError:
        return None
