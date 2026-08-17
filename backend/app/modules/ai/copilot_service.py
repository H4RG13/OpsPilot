import json
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ai.models import AIConversation, AIMessage
from app.modules.ai.parsing import parse_structured_answer
from app.modules.ai.schemas import AITaskType, StructuredAIAnswer
from app.modules.ai.service import AIService
from app.modules.ai.tools.base import ToolContext
from app.modules.ai.tools.registry import execute_tool, get_tool_schemas

MAX_TOOL_ROUNDS = 3

SYSTEM_PROMPT = (
    "You are an AI Operations Copilot for a business analytics platform. "
    "Answer the user's question about their business data using the available "
    "tools to fetch real numbers — never fabricate metrics. "
    "Respond ONLY with a JSON object of this exact shape: "
    '{"answer": string, '
    '"insights": [{"title": string, "severity": "low"|"medium"|"high", "evidence": string}], '
    '"recommendations": [string], '
    '"suggested_tasks": [{"title": string, "priority": "low"|"medium"|"high"}]}'
)


class CopilotService:
    def __init__(self, ai_service: AIService):
        self._ai_service = ai_service

    async def ask(
        self,
        db: AsyncSession,
        *,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        conversation: AIConversation,
        user_message: str,
        allow_tool_writes: bool = False,
    ) -> StructuredAIAnswer:
        db.add(AIMessage(conversation_id=conversation.id, role="user", content=user_message))
        await db.commit()

        tool_ctx = ToolContext(
            organization_id=organization_id, user_id=user_id, allow_writes=allow_tool_writes
        )

        messages: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]
        for past in conversation.messages:
            messages.append({"role": past.role, "content": past.content})
        messages.append({"role": "user", "content": user_message})

        tool_schemas = get_tool_schemas(tool_ctx.allow_writes)
        final_response = None

        for _ in range(MAX_TOOL_ROUNDS):
            response = await self._ai_service.generate_with_tools(
                db,
                organization_id=organization_id,
                user_id=user_id,
                task_type=AITaskType.BUSINESS_ANALYSIS,
                messages=messages,
                tools=tool_schemas,
            )
            if not response.tool_calls:
                final_response = response
                break

            messages.append(
                {
                    "role": "assistant",
                    "content": response.content or "",
                    "tool_calls": [
                        {
                            "id": call.id,
                            "type": "function",
                            "function": {
                                "name": call.name,
                                "arguments": json.dumps(call.arguments),
                            },
                        }
                        for call in response.tool_calls
                    ],
                }
            )
            for call in response.tool_calls:
                result = await execute_tool(db, tool_ctx, call.name, call.arguments)
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.id,
                        "name": call.name,
                        "content": json.dumps(result),
                    }
                )
        else:
            final_response = await self._ai_service.generate_text(
                db,
                organization_id=organization_id,
                user_id=user_id,
                task_type=AITaskType.BUSINESS_ANALYSIS,
                messages=messages,
            )

        structured = parse_structured_answer(final_response.content)

        db.add(
            AIMessage(
                conversation_id=conversation.id,
                role="assistant",
                content=structured.answer,
                model=final_response.model,
                provider=final_response.provider,
                input_tokens=final_response.usage.input_tokens,
                output_tokens=final_response.usage.output_tokens,
            )
        )
        await db.commit()

        return structured
