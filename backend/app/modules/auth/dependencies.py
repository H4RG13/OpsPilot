import uuid
from dataclasses import dataclass

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import decode_token
from app.modules.organizations.models import OrganizationMember
from app.modules.users.models import User
from app.shared.exceptions import AuthenticationError, AuthorizationError
from app.shared.permissions import Role, has_minimum_role

bearer_scheme = HTTPBearer(auto_error=False)


@dataclass
class AuthContext:
    user: User
    organization_id: uuid.UUID
    role: Role


async def get_current_context(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> AuthContext:
    if credentials is None:
        raise AuthenticationError("Missing authentication credentials.", code="NOT_AUTHENTICATED")

    try:
        payload = decode_token(credentials.credentials)
    except jwt.PyJWTError as exc:
        raise AuthenticationError("Invalid or expired access token.", code="INVALID_TOKEN") from exc

    if payload.get("type") != "access":
        raise AuthenticationError("Invalid or expired access token.", code="INVALID_TOKEN")

    user_id = payload.get("sub")
    org_id = payload.get("org_id")
    if not user_id or not org_id:
        raise AuthenticationError("Invalid or expired access token.", code="INVALID_TOKEN")

    stmt = (
        select(OrganizationMember)
        .options(selectinload(OrganizationMember.user))
        .where(
            OrganizationMember.user_id == uuid.UUID(user_id),
            OrganizationMember.organization_id == uuid.UUID(org_id),
        )
    )
    membership = (await db.execute(stmt)).scalar_one_or_none()
    if membership is None:
        raise AuthenticationError(
            "You are no longer a member of this organization.", code="NOT_A_MEMBER"
        )

    return AuthContext(
        user=membership.user,
        organization_id=membership.organization_id,
        role=Role(membership.role),
    )


def require_role(minimum_role: Role):
    async def _check(context: AuthContext = Depends(get_current_context)) -> AuthContext:
        if not has_minimum_role(context.role, minimum_role):
            raise AuthorizationError(
                f"This action requires the '{minimum_role.value}' role or higher.",
                code="INSUFFICIENT_ROLE",
            )
        return context

    return _check
