from datetime import UTC, datetime, timedelta
from typing import Any, Literal

import bcrypt
import jwt

from app.core.config import settings

ALGORITHM = "HS256"

# bcrypt silently ignores/errors on input beyond 72 bytes; reject rather than
# truncate so long passwords don't collide on their shared 72-byte prefix.
MAX_PASSWORD_BYTES = 72


def hash_password(password: str) -> str:
    password_bytes = password.encode("utf-8")
    if len(password_bytes) > MAX_PASSWORD_BYTES:
        raise ValueError(f"Password must not exceed {MAX_PASSWORD_BYTES} bytes.")
    return bcrypt.hashpw(password_bytes, bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    password_bytes = plain_password.encode("utf-8")
    if len(password_bytes) > MAX_PASSWORD_BYTES:
        return False
    return bcrypt.checkpw(password_bytes, hashed_password.encode("utf-8"))


def _create_token(
    subject: str,
    expires_delta: timedelta,
    token_type: Literal["access", "refresh"],
    extra_claims: dict[str, Any] | None = None,
) -> str:
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def create_access_token(subject: str, extra_claims: dict[str, Any] | None = None) -> str:
    return _create_token(
        subject,
        timedelta(minutes=settings.access_token_expire_minutes),
        "access",
        extra_claims,
    )


def create_refresh_token(subject: str, jti: str, extra_claims: dict[str, Any] | None = None) -> str:
    claims = {"jti": jti, **(extra_claims or {})}
    return _create_token(
        subject,
        timedelta(days=settings.refresh_token_expire_days),
        "refresh",
        claims,
    )


def decode_token(token: str) -> dict[str, Any]:
    return jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
