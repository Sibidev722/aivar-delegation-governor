from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class ToolExecutionRequest(BaseModel):
    """
    Governor-Gated Tool Execution Request.
    The agent presents its signed delegation token to execute a financial action.
    """
    task_id: str = Field(
        default="task_analysis_01",
        json_schema_extra={"example": "task_financial_q1"}
    )
    agent_id: str = Field(
        json_schema_extra={"example": "agent_c"},
        description="ID of the calling agent (must match token aud)"
    )
    token: str = Field(
        description="Signed Ed25519 delegation token"
    )
    operation: str = Field(
        json_schema_extra={"example": "READ_SUMMARY"},
        description="Operation: READ_SUMMARY | READ_METRICS | READ_FINANCIALS | WRITE_RECORD"
    )
    resource: str = Field(
        default="customer_financials",
        json_schema_extra={"example": "customer_financials"}
    )
    customer_id: str = Field(
        json_schema_extra={"example": "CUST-101"},
        description="Target customer identifier"
    )
    request_id: Optional[str] = Field(
        default=None,
        description="Correlation request ID"
    )
    payload: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Payload for write/update operations"
    )


class ToolExecutionResponse(BaseModel):
    """
    Protected tool execution response returned via Governor gateway.
    """
    status: str = "SUCCESS"
    tool_name: str = "financial_records_tool"
    operation: str
    resource: str
    customer_id: str
    executed_by: str
    chain_id: str
    token_id: str
    data: Any
    audit_event_id: str
