import asyncio
import json
import time
from typing import Any, Callable, Dict, Optional, Type, TypeVar
from pydantic import BaseModel, ValidationError

from app.config import settings
from app.core.logging import logger
from app.core.exceptions import (
    LLMProviderUnavailableException,
    LLMValidationException,
    LLMTimeoutException
)
from app.llm.provider import LLMProvider

T = TypeVar("T", bound=BaseModel)


class GeminiProvider(LLMProvider):
    """
    Production-grade Google Gemini LLM Provider implementing structured JSON generation
    using the official google-genai SDK.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        timeout_seconds: Optional[float] = None
    ) -> None:
        self._api_key = api_key or settings.GEMINI_API_KEY
        self._model_name = model_name or settings.GEMINI_MODEL
        self._timeout = timeout_seconds or settings.LLM_TIMEOUT_SECONDS
        self._mock_handler: Optional[Callable[[str, Type[T]], Any]] = None
        self._client: Any = None

    def _get_client(self) -> Any:
        """
        Lazily initialize the google-genai client.
        """
        if self._client is None:
            if not self._api_key:
                raise LLMProviderUnavailableException(
                    message="GEMINI_API_KEY is not configured in backend environment."
                )
            try:
                from google import genai
                self._client = genai.Client(api_key=self._api_key)
            except Exception as e:
                logger.error(f"Failed to initialize google-genai client: {e}")
                raise LLMProviderUnavailableException(
                    message=f"Failed to initialize Gemini SDK client: {str(e)}"
                )
        return self._client

    def set_mock_handler(self, handler: Optional[Callable[[str, Type[T]], Any]]) -> None:
        """
        Testing hook allowing unit test suite to inject controlled LLM behavior
        (e.g., simulating malformed outputs, timeouts, or specific adversarial outputs).
        """
        self._mock_handler = handler

    async def generate_structured(
        self,
        prompt: str,
        system_prompt: str,
        schema: Type[T],
        temperature: float = 0.0,
        request_id: Optional[str] = None,
        task_id: Optional[str] = None,
        chain_id: Optional[str] = None
    ) -> T:
        """
        Generate structured output from Google Gemini validated against the target Pydantic schema.
        """
        start_time = time.perf_counter()

        # 1. Check for testing mock hook
        if self._mock_handler is not None:
            mock_res = self._mock_handler(prompt, schema)
            if isinstance(mock_res, Exception):
                raise mock_res
            if isinstance(mock_res, schema):
                return mock_res
            if isinstance(mock_res, str):
                try:
                    return schema.model_validate_json(mock_res)
                except ValidationError as ve:
                    raise LLMValidationException(
                        message=f"Mock LLM output failed schema validation: {ve}",
                        details={"errors": ve.errors()}
                    )

        # 2. Verify API Key Presence
        if not self._api_key:
            raise LLMProviderUnavailableException(
                message="GEMINI_API_KEY is not configured. Real LLM invocation requires an active key.",
                details={"configured_model": self._model_name}
            )

        client = self._get_client()
        from google.genai import types

        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=schema,
            system_instruction=system_prompt,
            temperature=temperature
        )

        retries = 0
        last_error = None

        while retries <= settings.LLM_MAX_RETRIES:
            try:
                logger.info(
                    f"Dispatching structured LLM request to Gemini [{self._model_name}] (attempt {retries + 1})...",
                    extra={"extra_data": {
                        "model": self._model_name,
                        "schema": schema.__name__,
                        "request_id": request_id,
                        "chain_id": chain_id,
                        "task_id": task_id
                    }}
                )

                # Real async invocation with timeout
                response = await asyncio.wait_for(
                    client.aio.models.generate_content(
                        model=self._model_name,
                        contents=prompt,
                        config=config
                    ),
                    timeout=self._timeout
                )

                duration_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
                raw_text = response.text

                if not raw_text:
                    raise LLMValidationException(
                        message="Gemini returned an empty response.",
                        details={"model": self._model_name}
                    )

                # Validate and parse structured response into target Pydantic schema
                try:
                    parsed_instance = schema.model_validate_json(raw_text)
                    logger.info(
                        f"Gemini generation successful for {schema.__name__} in {duration_ms}ms.",
                        extra={"extra_data": {
                            "duration_ms": duration_ms,
                            "model": self._model_name,
                            "schema": schema.__name__
                        }}
                    )
                    return parsed_instance
                except ValidationError as ve:
                    logger.warning(f"Gemini output failed schema validation: {ve}")
                    raise LLMValidationException(
                        message=f"Gemini response did not match {schema.__name__} schema: {ve}",
                        details={"raw_output": raw_text[:200], "validation_errors": ve.errors()}
                    )

            except asyncio.TimeoutError:
                duration_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
                logger.error(f"Gemini request timed out after {duration_ms}ms.")
                raise LLMTimeoutException(
                    message=f"Gemini request timed out after {self._timeout}s."
                )
            except (LLMValidationException, LLMTimeoutException):
                raise
            except Exception as e:
                last_error = e
                logger.warning(f"Transient error communicating with Gemini API: {e} (retry {retries})")
                retries += 1
                if retries <= settings.LLM_MAX_RETRIES:
                    await asyncio.sleep(0.5 * retries)

        # Max retries exhausted
        duration_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
        logger.error(f"Gemini API request failed after {retries} retries in {duration_ms}ms: {last_error}")
        raise LLMProviderUnavailableException(
            message=f"Gemini API request failed: {str(last_error)}",
            details={"model": self._model_name, "retries": retries}
        )
