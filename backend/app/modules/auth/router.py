from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.audit import service as audit_service
from app.modules.auth import service
from app.modules.auth.dependencies import AuthContext, get_current_context
from app.modules.auth.schemas import (
    LoginRequest,
    LogoutRequest,
    MeResponse,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)

router = APIRouter(prefix="/auth", tags=["auth"])
me_router = APIRouter(tags=["users"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(data: RegisterRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    user, organization, role = await service.register(db, data)
    return await service.issue_tokens(db, user, organization.id, role)


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    user = await service.authenticate(db, data.email, data.password)
    membership = await service.get_primary_membership(db, user.id)
    tokens = await service.issue_tokens(db, user, membership.organization_id, membership.role)
    await audit_service.log_action(
        db,
        organization_id=membership.organization_id,
        user_id=user.id,
        action="auth.login",
        entity_type="user",
        entity_id=user.id,
    )
    return tokens


@router.post("/refresh", response_model=TokenResponse)
async def refresh(data: RefreshRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    return await service.rotate_refresh_token(db, data.refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(data: LogoutRequest, db: AsyncSession = Depends(get_db)) -> None:
    await service.logout(db, data.refresh_token)


@me_router.get("/me", response_model=MeResponse)
async def me(context: AuthContext = Depends(get_current_context)) -> MeResponse:
    return MeResponse(
        user=UserResponse.model_validate(context.user),
        organization_id=context.organization_id,
        role=context.role,
    )
