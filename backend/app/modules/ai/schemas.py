import uuid
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field


class AITaskType(StrEnum):
    SUMMARY = "summary"
    CLASSIFICATION = "classification"
    EXTRACTION = "extraction"
    COMPLAINT_SUMMARY = "complaint_summary"
    BUSINESS_ANALYSIS = "business_analysis"
    MULTI_STEP_REASONING = "multi_step_reasoning"
    COMPLEX_RECOMMENDATIONS = "complex_recommendations"
    IMAGE_ANALYSIS = "image_analysis"


class AIUsageInfo(BaseModel):
    input_tokens: int
    output_tokens: int
    latency_ms: int


class AITextResponse(BaseModel):
    content: str
    model: str
    provider: str
    usage: AIUsageInfo


class AIToolCall(BaseModel):
    id: str
    name: str
    arguments: dict


class AIToolResponse(BaseModel):
    content: str | None
    tool_calls: list[AIToolCall]
    model: str
    provider: str
    usage: AIUsageInfo


class AIUsageRecordResponse(BaseModel):
    id: uuid.UUID
    provider: str
    model: str
    task_type: str
    input_tokens: int
    output_tokens: int
    latency_ms: int
    estimated_cost: Decimal
    created_at: datetime

    model_config = {"from_attributes": True}


class ConversationCreate(BaseModel):
    title: str | None = Field(default=None, max_length=255)


class ConversationResponse(BaseModel):
    id: uuid.UUID
    title: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class MessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=4000)


class MessageResponse(BaseModel):
    id: uuid.UUID
    role: str
    content: str
    model: str | None
    provider: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class Insight(BaseModel):
    title: str
    severity: Literal["low", "medium", "high"]
    evidence: str


class SuggestedTask(BaseModel):
    title: str
    priority: Literal["low", "medium", "high"]


class StructuredAIAnswer(BaseModel):
    """The Copilot's response shape (spec Section 12) — never let the frontend
    depend on unpredictable free-form parsing."""

    answer: str
    insights: list[Insight] = []
    recommendations: list[str] = []
    suggested_tasks: list[SuggestedTask] = []
