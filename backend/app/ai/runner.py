import logging
from typing import Any, Dict, Type, TypeVar

from pydantic import BaseModel, ValidationError

from app.ai.client import AIResult, ai_client

logger = logging.getLogger("talentloop.ai.runner")

T = TypeVar("T", bound=BaseModel)


class AIValidationError(Exception):
    def __init__(self, message: str, raw_output: str, original_error: Exception):
        super().__init__(message)
        self.raw_output = raw_output
        self.original_error = original_error


async def run_structured(
    prompt_name: str,
    variables: dict[str, Any],
    schema: type[T],
    temperature: float = 0.0
) -> tuple[T, AIResult]:
    """
    Executes a structured model call with strict Pydantic validation.
    On validation failure, retries EXACTLY ONCE with the validation error
    quoted back to the model. On a second failure, raises AIValidationError.
    """
    # 1. Initial Attempt
    result = await ai_client.generate(
        prompt_name=prompt_name,
        variables=variables,
        temperature=temperature,
        json_schema=schema
    )

    try:
        validated = schema.model_validate_json(result.raw_text)
        result.parsed = validated
        return validated, result
    except (ValidationError, Exception) as first_err:
        logger.warning(
            f"Model output failed schema validation for {prompt_name}: {first_err}. "
            "Executing bounded retry (1 of 1)..."
        )

        # 2. Retry with explicit correction instruction
        retry_vars = variables.copy()
        correction_note = (
            f"\n\nCRITICAL: Your previous response failed schema validation with error:\n{first_err}\n"
            "Please return valid JSON conforming strictly to the requested schema with no surrounding text."
        )
        retry_vars["_correction_instruction"] = correction_note

        retry_result = await ai_client.generate(
            prompt_name=prompt_name,
            variables=retry_vars,
            temperature=temperature,
            json_schema=schema
        )

        try:
            validated = schema.model_validate_json(retry_result.raw_text)
            retry_result.parsed = validated
            return validated, retry_result
        except Exception as second_err:
            logger.error(
                f"Model response failed schema validation on retry for {prompt_name}: {second_err}"
            )
            raise AIValidationError(
                message=f"Model response failed validation for {prompt_name} after 1 retry: {second_err}",
                raw_output=retry_result.raw_text,
                original_error=second_err
            ) from second_err
