from abc import ABC, abstractmethod
from typing import Optional, Type, TypeVar
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class LLMProvider(ABC):
    """
    Abstract interface for LLM providers generating structured Pydantic outputs.
    Ensures agent implementations remain decoupled from concrete provider SDKs.
    """

    @abstractmethod
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
        Generate structured output validated against the specified Pydantic schema.

        Args:
            prompt: User/task context prompt string.
            system_prompt: System role instructions and safety boundaries.
            schema: Target Pydantic BaseModel class for validation.
            temperature: Sampling temperature (default 0.0 for deterministic output).
            request_id: Optional correlation tracking ID.
            task_id: Optional task tracking ID.
            chain_id: Optional delegation chain ID.

        Returns:
            Validated Pydantic model instance.

        Raises:
            GovernanceException / LLMException on failure or validation error.
        """
        pass
