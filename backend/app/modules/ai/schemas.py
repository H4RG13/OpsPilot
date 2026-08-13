import uuid
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel


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
