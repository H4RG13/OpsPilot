import json
import uuid

from sqlalchemy import select

from app.modules.ai.copilot_service import CopilotService
from app.modules.ai.models import AIConversation, AIMessage
from app.modules.ai.schemas import AIToolCall, AIToolResponse, AIUsageInfo
from app.modules.ai.service import AIService
from app.modules.organizations.models import Organization
from app.modules.users.models import User

STRUCTURED_ANSWER_JSON = json.dumps(
    {
        "answer": "Revenue decreased 21.7%.",
        "insights": [{"title": "Product A decline", "severity": "high", "evidence": "-32%"}],
        "recommendations": ["Investigate Product A"],
        "suggested_tasks": [{"title": "Investigate Product A", "priority": "high"}],
    }
)


def _tool_response(
    content: str | None, tool_calls: list[AIToolCall] | None = None
) -> AIToolResponse:
    return AIToolResponse(
        content=content,
        tool_calls=tool_calls or [],
        model="gpt-oss-120b",
        provider="fake",
        usage=AIUsageInfo(input_tokens=20, output_tokens=10, latency_ms=50),
    )


class ScriptedProvider:
    def __init__(self, tool_responses, text_response=None):
        self._tool_responses = list(tool_responses)
        self._text_response = text_response
        self.tool_names_called: list[str] = []

    async def generate_with_tools(self, *, model, messages, tools, **kwargs):
        return self._tool_responses.pop(0)

    async def generate_text(self, *, model, messages, **kwargs):
        return self._text_response


async def _make_org_and_user(db_session):
    org = Organization(id=uuid.uuid4(), name="Acme")
    user = User(id=uuid.uuid4(), email="u@example.com", password_hash="x", full_name="U")
    db_session.add_all([org, user])
    await db_session.commit()
    return org.id, user.id


async def _make_conversation(db_session, org_id, user_id) -> AIConversation:
    conversation = AIConversation(id=uuid.uuid4(), organization_id=org_id, user_id=user_id)
    db_session.add(conversation)
    await db_session.commit()
    await db_session.refresh(conversation, attribute_names=["messages"])
    return conversation


async def test_direct_structured_answer_with_no_tool_calls(db_session):
    org_id, user_id = await _make_org_and_user(db_session)
    conversation = await _make_conversation(db_session, org_id, user_id)

    provider = ScriptedProvider([_tool_response(STRUCTURED_ANSWER_JSON)])
    copilot = CopilotService(AIService(provider))

    answer = await copilot.ask(
        db_session,
        organization_id=org_id,
        user_id=user_id,
        conversation=conversation,
        user_message="Why did revenue drop?",
    )

    assert answer.answer == "Revenue decreased 21.7%."
    assert answer.insights[0].severity == "high"
    assert answer.suggested_tasks[0].title == "Investigate Product A"

    messages = (
        (await db_session.execute(select(AIMessage).order_by(AIMessage.created_at)))
        .scalars()
        .all()
    )
    assert [m.role for m in messages] == ["user", "assistant"]
    assert messages[1].model == "gpt-oss-120b"


async def test_tool_call_round_then_final_answer(db_session):
    org_id, user_id = await _make_org_and_user(db_session)
    conversation = await _make_conversation(db_session, org_id, user_id)

    tool_call = AIToolCall(
        id="call_1",
        name="get_revenue_summary",
        arguments={"start_date": "2026-01-01", "end_date": "2026-01-31"},
    )
    provider = ScriptedProvider(
        [
            _tool_response(None, tool_calls=[tool_call]),
            _tool_response(STRUCTURED_ANSWER_JSON),
        ]
    )
    copilot = CopilotService(AIService(provider))

    answer = await copilot.ask(
        db_session,
        organization_id=org_id,
        user_id=user_id,
        conversation=conversation,
        user_message="Why did revenue drop?",
    )

    assert answer.answer == "Revenue decreased 21.7%."


async def test_malformed_json_falls_back_to_raw_content(db_session):
    org_id, user_id = await _make_org_and_user(db_session)
    conversation = await _make_conversation(db_session, org_id, user_id)

    provider = ScriptedProvider([_tool_response("not valid json")])
    copilot = CopilotService(AIService(provider))

    answer = await copilot.ask(
        db_session,
        organization_id=org_id,
        user_id=user_id,
        conversation=conversation,
        user_message="Hi",
    )

    assert answer.answer == "not valid json"
    assert answer.insights == []
    assert answer.suggested_tasks == []


async def test_exceeding_max_tool_rounds_forces_final_text_answer(db_session):
    org_id, user_id = await _make_org_and_user(db_session)
    conversation = await _make_conversation(db_session, org_id, user_id)

    # get_at_risk_customers has only an optional `limit` arg, so empty
    # arguments validate successfully — every round genuinely succeeds and
    # still requests another tool call, forcing MAX_TOOL_ROUNDS to exhaust.
    tool_call = AIToolCall(id="call_1", name="get_at_risk_customers", arguments={})
    provider = ScriptedProvider(
        tool_responses=[
            _tool_response(None, tool_calls=[tool_call]),
            _tool_response(None, tool_calls=[tool_call]),
            _tool_response(None, tool_calls=[tool_call]),
        ],
        text_response=_tool_response(STRUCTURED_ANSWER_JSON),
    )
    copilot = CopilotService(AIService(provider))

    answer = await copilot.ask(
        db_session,
        organization_id=org_id,
        user_id=user_id,
        conversation=conversation,
        user_message="Hi",
    )

    assert answer.answer == "Revenue decreased 21.7%."
