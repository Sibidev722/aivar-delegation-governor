from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AgentAExecutionRequest(BaseModel):
    """
    User request to initiate multi-agent pipeline via Agent A (Coordinator).
    """
    task_type: str = Field(
        default="financial_analysis_task",
        json_schema_extra={"example": "financial_analysis_task"},
        description="Registered server policy task name"
    )
    originating_user: str = Field(
        default="USER-001",
        json_schema_extra={"example": "USER-001"},
        description="Originating user identifier"
    )
    customer_id: str = Field(
        default="CUST-101",
        json_schema_extra={"example": "CUST-101"},
        description="Target customer identifier"
    )
    operation: str = Field(
        default="READ_SUMMARY",
        json_schema_extra={"example": "READ_SUMMARY"},
        description="Target operation: READ_SUMMARY | READ_METRICS | READ_FINANCIALS | WRITE_RECORD"
    )
    user_prompt: Optional[str] = Field(
        default=None,
        description="Natural-language task prompt provided by user (e.g. 'Analyze the financial performance of CUST-101')"
    )
    use_llm: bool = Field(
        default=True,
        description="Whether to use the LLM provider for structured reasoning"
    )
    simulate_attack: Optional[str] = Field(
        default=None,
        description="Optional simulation flag: 'escalate_write_to_b' | 'escalate_cust_to_b'"
    )


class AgentBExecutionRequest(BaseModel):
    """
    Inter-agent request payload dispatched from Agent A to Agent B (Planner).
    """
    task_id: str
    chain_id: str
    originating_user: str
    token: str = Field(description="Signed child delegation token intended for Agent B")
    customer_id: str
    task_type: str
    operation: str = Field(default="READ_SUMMARY")
    user_prompt: Optional[str] = None
    use_llm: bool = True
    task_context: Dict[str, Any] = Field(default_factory=dict)
    simulate_attack: Optional[str] = None


class AgentCExecutionRequest(BaseModel):
    """
    Inter-agent request payload dispatched from Agent B to Agent C (Worker).
    """
    task_id: str
    chain_id: str
    originating_user: str
    token: str = Field(description="Signed child delegation token intended for Agent C")
    customer_id: str
    operation: str = Field(default="READ_SUMMARY")
    user_prompt: Optional[str] = None
    use_llm: bool = True
    task_context: Dict[str, Any] = Field(default_factory=dict)
    simulate_attack: Optional[str] = None


class AgentExecutionResponse(BaseModel):
    """
    Standard agent execution response with complete reconstructed delegation chain and reasoning.
    """
    status: str = "completed"
    task_id: str
    chain_id: str
    delegation_chain: List[str] = Field(
        default_factory=list,
        json_schema_extra={"example": ["USER-001", "agent_a", "agent_b", "agent_c"]}
    )
    operation: str = "READ_SUMMARY"
    customer_id: str
    authorization: str = "ALLOWED"
    data: Any
    audit_event_id: Optional[str] = None
    llm_reasoning: Optional[str] = None
