from app.llm.provider import LLMProvider
from app.llm.gemini_provider import GeminiProvider
from app.llm.schemas import (
    AgentAPlan,
    AgentBPlan,
    AgentCToolRequest,
    LLMExecutionMetadata
)
from app.llm.prompts import (
    AGENT_A_SYSTEM_PROMPT,
    AGENT_B_SYSTEM_PROMPT,
    AGENT_C_SYSTEM_PROMPT,
    build_agent_a_prompt,
    build_agent_b_prompt,
    build_agent_c_prompt
)

# Global default LLM provider instance
default_llm_provider = GeminiProvider()

__all__ = [
    "LLMProvider",
    "GeminiProvider",
    "default_llm_provider",
    "AgentAPlan",
    "AgentBPlan",
    "AgentCToolRequest",
    "LLMExecutionMetadata",
    "AGENT_A_SYSTEM_PROMPT",
    "AGENT_B_SYSTEM_PROMPT",
    "AGENT_C_SYSTEM_PROMPT",
    "build_agent_a_prompt",
    "build_agent_b_prompt",
    "build_agent_c_prompt"
]
