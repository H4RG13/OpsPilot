from app.core.config import settings
from app.modules.ai.schemas import AITaskType

# Section 26 of the spec: cheapest model that reliably completes the task.
DEFAULT_TASK_MODEL_MAP: dict[AITaskType, str] = {
    AITaskType.SUMMARY: settings.ai_default_model,
    AITaskType.CLASSIFICATION: settings.ai_default_model,
    AITaskType.EXTRACTION: settings.ai_default_model,
    AITaskType.COMPLAINT_SUMMARY: settings.ai_default_model,
    AITaskType.BUSINESS_ANALYSIS: settings.ai_reasoning_model,
    AITaskType.MULTI_STEP_REASONING: settings.ai_reasoning_model,
    AITaskType.COMPLEX_RECOMMENDATIONS: settings.ai_reasoning_model,
    AITaskType.IMAGE_ANALYSIS: settings.ai_vision_model,
}


class ModelRouter:
    """Maps a task type to an ordered [primary, fallback] model chain (spec Section 26)."""

    def __init__(self, task_model_map: dict[AITaskType, str] | None = None):
        self._task_model_map = task_model_map or DEFAULT_TASK_MODEL_MAP

    def resolve_chain(self, task_type: AITaskType) -> list[str]:
        primary = self._task_model_map[task_type]

        if task_type == AITaskType.IMAGE_ANALYSIS:
            # There is only one vision-capable model configured; no text fallback applies.
            return [primary]

        fallback = (
            settings.ai_reasoning_model
            if primary == settings.ai_default_model
            else settings.ai_default_model
        )
        return [primary] if primary == fallback else [primary, fallback]


model_router = ModelRouter()
