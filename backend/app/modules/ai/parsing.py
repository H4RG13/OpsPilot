from pydantic import ValidationError as PydanticValidationError

from app.modules.ai.schemas import StructuredAIAnswer


def parse_structured_answer(content: str | None) -> StructuredAIAnswer:
    """Parse a model's final response into the spec Section 12 structured shape,
    falling back to the raw text rather than failing the request if the model
    didn't return valid matching JSON."""
    if not content:
        return StructuredAIAnswer(answer="")
    try:
        return StructuredAIAnswer.model_validate_json(content)
    except (PydanticValidationError, ValueError):
        return StructuredAIAnswer(answer=content)
