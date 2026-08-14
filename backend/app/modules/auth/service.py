import uuid
from datetime import UTC, datetime, timedelta

import jwt
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.modules.audit import service as audit_service
from app.modules.auth.models import RefreshToken
from app.modules.auth.schemas import RegisterRequest, TokenResponse
from app.modules.organizations.models import Organization, OrganizationMember
from app.modules.users.models import User
from app.shared.exceptions import AuthenticationError, ConflictError
from app.shared.permissions import Role

# Precomputed bcrypt hash of a fixed dummy password, verified against on a
# missing-user login attempt so the response takes the same time either way
# and doesn't leak whether an email is registered via a timing side-channel.
_DUMMY_PASSWORD_HASH = hash_password("dummy-password-for-timing-safety")


async def register(db: AsyncSession, data: RegisterRequest) -> tuple[User, Organization, Role]:
    user = User(
        email=data.email.lower(),
        password_hash=hash_password(data.password),
        full_name=data.full_name,
    )
    organization = Organization(name=data.organization_name)

    try:
        db.add_all([user, organization])
        await db.flush()

        membership = OrganizationMember(
            organization_id=organization.id, user_id=user.id, role=Role.OWNER
        )
        db.add(membership)
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise ConflictError(
            "An account with this email already exists.", code="EMAIL_ALREADY_REGISTERED"
        ) from exc

    await audit_service.log_action(
        db,
        organization_id=organization.id,
        user_id=user.id,
        action="auth.register",
        entity_type="user",
        entity_id=user.id,
    )

    return user, organization, Role.OWNER


async def authenticate(db: AsyncSession, email: str, password: str) -> User:
    stmt = select(User).where(User.email == email.lower())
    user = (await db.execute(stmt)).scalar_one_or_none()

    if user is None:
        # Still run a bcrypt comparison so a nonexistent email doesn't
        # resolve measurably faster than a wrong password for a real one.
        verify_password(password, _DUMMY_PASSWORD_HASH)
        raise AuthenticationError("Invalid email or password.", code="INVALID_CREDENTIALS")

    if not verify_password(password, user.password_hash):
        raise AuthenticationError("Invalid email or password.", code="INVALID_CREDENTIALS")

    return user


async def get_primary_membership(db: AsyncSession, user_id: uuid.UUID) -> OrganizationMember:
    stmt = (
        select(OrganizationMember)
        .where(OrganizationMember.user_id == user_id)
        .order_by(OrganizationMember.created_at)
        .limit(1)
    )
    membership = (await db.execute(stmt)).scalar_one_or_none()
    if membership is None:
        raise AuthenticationError(
            "User does not belong to an organization.", code="NO_ORGANIZATION"
        )
    return membership


async def issue_tokens(
    db: AsyncSession, user: User, organization_id: uuid.UUID, role: Role
) -> TokenResponse:
    jti = uuid.uuid4()
    expires_at = datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days)

    db.add(RefreshToken(id=jti, user_id=user.id, expires_at=expires_at))
    await db.commit()

    access_token = create_access_token(
        str(user.id), {"org_id": str(organization_id), "role": role.value}
    )
    refresh_token = create_refresh_token(str(user.id), str(jti))

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.access_token_expire_minutes * 60,
    )


async def rotate_refresh_token(db: AsyncSession, refresh_token: str) -> TokenResponse:
    payload = _decode_refresh_token(refresh_token)

    jti = payload.get("jti")
    user_id = payload.get("sub")
    if not jti or not user_id:
        raise AuthenticationError("Invalid refresh token.", code="REFRESH_TOKEN_INVALID")

    token_row = await db.get(RefreshToken, uuid.UUID(jti))
    if (
        token_row is None
        or token_row.revoked_at is not None
        or _as_utc(token_row.expires_at) < datetime.now(UTC)
    ):
        raise AuthenticationError(
            "Refresh token is invalid or expired.", code="REFRESH_TOKEN_INVALID"
        )

    token_row.revoked_at = datetime.now(UTC)

    user = await db.get(User, uuid.UUID(user_id))
    if user is None:
        raise AuthenticationError("Invalid refresh token.", code="REFRESH_TOKEN_INVALID")

    membership = await get_primary_membership(db, user.id)
    await db.commit()

    return await issue_tokens(db, user, membership.organization_id, Role(membership.role))


async def logout(db: AsyncSession, refresh_token: str) -> None:
    try:
        payload = _decode_refresh_token(refresh_token)
    except AuthenticationError:
        return

    jti = payload.get("jti")
    if not jti:
        return

    token_row = await db.get(RefreshToken, uuid.UUID(jti))
    if token_row is not None and token_row.revoked_at is None:
        token_row.revoked_at = datetime.now(UTC)
        await db.commit()


def _as_utc(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def _decode_refresh_token(refresh_token: str) -> dict:
    try:
        payload = decode_token(refresh_token)
    except jwt.PyJWTError as exc:
        raise AuthenticationError("Invalid refresh token.", code="REFRESH_TOKEN_INVALID") from exc

    if payload.get("type") != "refresh":
        raise AuthenticationError("Invalid refresh token.", code="REFRESH_TOKEN_INVALID")

    return payload
