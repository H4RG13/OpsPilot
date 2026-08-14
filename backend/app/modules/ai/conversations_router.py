import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.database import get_db
from app.core.rate_limit import rate_limit
from app.modules.ai.copilot_service import CopilotService
from app.modules.ai.dependencies import get_ai_service
from app.modules.ai.models import AIConversation
from app.modules.ai.schemas import (
    ConversationCreate,
    ConversationResponse,
    MessageCreate,
    StructuredAIAnswer,
)
from app.modules.ai.service import AIService
from app.modules.auth.dependencies import AuthContext, get_current_context
from app.shared.exceptions import NotFoundError
from app.shared.pagination import Page, PageParams

router = APIRouter(prefix="/ai/conversations", tags=["ai"])


async def _get_owned_conversation(
    db: AsyncSession, organization_id: uuid.UUID, user_id: uuid.UUID, conversation_id: uuid.UUID
) -> AIConversation:
    stmt = (
        select(AIConversation)
        .options(selectinload(AIConversation.messages))
        .where(
            AIConversation.id == conversation_id,
            AIConversation.organization_id == organization_id,
            AIConversation.user_id == user_id,
        )
    )
    conversation = (await db.execute(stmt)).scalar_one_or_none()
    if conversation is None:
        raise NotFoundError("Conversation was not found.", code="CONVERSATION_NOT_FOUND")
    return conversation


@router.post("", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    data: ConversationCreate,
    context: AuthContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
) -> ConversationResponse:
    conversation = AIConversation(
        organization_id=context.organization_id, user_id=context.user.id, title=data.title
    )
    db.add(conversation)
    await db.commit()
    await db.refresh(conversation)
    return ConversationResponse.model_validate(conversation)


@router.get("", response_model=Page[ConversationResponse])
async def list_conversations(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    context: AuthContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
) -> Page:
    params = PageParams(page=page, page_size=page_size)
    conditions = (
        AIConversation.organization_id == context.organization_id,
        AIConversation.user_id == context.user.id,
    )

    total = (
        await db.execute(select(func.count()).select_from(AIConversation).where(*conditions))
    ).scalar_one()

    items = list(
        (
            await db.execute(
                select(AIConversation)
                .where(*conditions)
                .order_by(AIConversation.created_at.desc())
                .offset(params.offset)
                .limit(params.page_size)
            )
        )
        .scalars()
        .all()
    )

    return Page(items=items, total=total, page=params.page, page_size=params.page_size)


@router.post(
    "/{conversation_id}/messages",
    response_model=StructuredAIAnswer,
    dependencies=[
        Depends(
            rate_limit(
                "ai_chat", settings.ai_chat_rate_limit_per_minute, window_seconds=60
            )
        )
    ],
)
async def send_message(
    conversation_id: uuid.UUID,
    data: MessageCreate,
    context: AuthContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
    ai_service: AIService = Depends(get_ai_service),
) -> StructuredAIAnswer:
    conversation = await _get_owned_conversation(
        db, context.organization_id, context.user.id, conversation_id
    )
    copilot = CopilotService(ai_service)
    return await copilot.ask(
        db,
        organization_id=context.organization_id,
        user_id=context.user.id,
        conversation=conversation,
        user_message=data.content,
        allow_tool_writes=data.allow_ai_actions,
    )
