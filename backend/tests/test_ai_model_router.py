from app.core.config import settings
from app.modules.ai.router import ModelRouter
from app.modules.ai.schemas import AITaskType


def test_cheap_task_routes_to_default_model_with_reasoning_fallback():
    chain = ModelRouter().resolve_chain(AITaskType.SUMMARY)
    assert chain == [settings.ai_default_model, settings.ai_reasoning_model]


def test_reasoning_task_routes_to_reasoning_model_with_default_fallback():
    chain = ModelRouter().resolve_chain(AITaskType.BUSINESS_ANALYSIS)
    assert chain == [settings.ai_reasoning_model, settings.ai_default_model]


def test_image_analysis_has_no_fallback():
    chain = ModelRouter().resolve_chain(AITaskType.IMAGE_ANALYSIS)
    assert chain == [settings.ai_vision_model]


def test_custom_task_model_map_is_respected():
    router = ModelRouter({AITaskType.SUMMARY: "custom-model"})
    chain = router.resolve_chain(AITaskType.SUMMARY)
    assert chain[0] == "custom-model"
