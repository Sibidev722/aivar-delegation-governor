import time
import uuid
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, status

from app.core.logging import logger
from app.core.exceptions import (
    GovernanceException,
    AudienceMismatchException,
    TokenExpiredException,
    LLMProviderUnavailableException
)
from app.models.agent import (
    AgentAExecutionRequest,
    AgentBExecutionRequest,
    AgentCExecutionRequest,
    AgentExecutionResponse
)
from app.models.token import DataScope
from app.services.governor_service import GovernorService
from app.services.agent_client import AgentHTTPClient
from app.llm import (
    default_llm_provider,
    AgentAPlan,
    AgentBPlan,
    AgentCToolRequest,
    AGENT_A_SYSTEM_PROMPT,
    AGENT_B_SYSTEM_PROMPT,
    AGENT_C_SYSTEM_PROMPT,
    build_agent_a_prompt,
    build_agent_b_prompt,
    build_agent_c_prompt
)

router = APIRouter()


# ==============================================================================
# Agent A (Coordinator)
# ==============================================================================

@router.post(
    "/agent-a/execute",
    response_model=AgentExecutionResponse,
    status_code=status.HTTP_200_OK,
    summary="Agent A Execution (Coordinator)",
    description=(
        "Entrypoint for User requests. Agent A uses Gemini LLM to reason on task requirements, "
        "acquires server-policy root token, derives scoped child token for Agent B, and dispatches "
        "a real HTTP call to Agent B."
    )
)
async def execute_agent_a(request: AgentAExecutionRequest) -> AgentExecutionResponse:
    task_id = f"task_{uuid.uuid4().hex[:8]}"
    prompt_text = request.user_prompt or f"Analyze the financial {request.operation} for customer {request.customer_id}"
    logger.info(
        f"Agent A received task '{request.task_type}' for user '{request.originating_user}', customer '{request.customer_id}'",
        extra={"extra_data": {"task_id": task_id, "user": request.originating_user, "prompt": prompt_text}}
    )

    # Step 1: LLM Reasoning for Agent A Orchestration Plan
    import re
    from app.services.scope_engine import normalize_customer_id

    match = re.search(r'CUST-\d+', prompt_text, re.IGNORECASE)
    extracted_cid = match.group(0) if match else request.customer_id
    normalized_cid = normalize_customer_id(extracted_cid)

    target_task_type = request.task_type
    target_customer = normalized_cid
    requested_scopes = ["financials:read:all"] if request.operation == "READ_FINANCIALS" else ["financials:read:summary"]
    requested_customers = [normalized_cid]
    plan_reasoning = "Deterministic orchestrator fallback"

    if request.use_llm:
        try:
            a_plan: AgentAPlan = await default_llm_provider.generate_structured(
                prompt=build_agent_a_prompt(prompt_text, normalized_cid),
                system_prompt=AGENT_A_SYSTEM_PROMPT,
                schema=AgentAPlan,
                task_id=task_id
            )
            target_task_type = a_plan.task_type
            target_customer = normalize_customer_id(a_plan.customer_id)
            requested_scopes = [a_plan.requested_scope]
            requested_customers = [normalize_customer_id(c) for c in a_plan.requested_data_scope.customer_ids]
            plan_reasoning = a_plan.reasoning_summary
            logger.info(f"Agent A Gemini reasoning: {plan_reasoning}")
        except LLMProviderUnavailableException as e:
            logger.info(f"LLM Provider unavailable ({e.message}), using deterministic policy plan.")
        except Exception as e:
            logger.warning(f"Agent A LLM generation error: {e}")
            raise

    # Step 2: Request Root Token from Governor (Server-Side Policy Enforced)
    token_a, claims_a = await GovernorService.create_root_token(
        task_name=target_task_type,
        target_agent="agent_a",
        user_id=request.originating_user
    )

    # Step 3: Handle Security Attack Simulations (Attacks bypass LLM to test Governor)
    if request.simulate_attack == "escalate_write_to_b":
        requested_scopes = ["financials:write:record"]
    elif request.simulate_attack == "escalate_cust_to_b":
        requested_customers = ["CUST-999_UNAUTHORIZED"]
    elif request.operation == "READ_METRICS" and not request.use_llm:
        requested_scopes = ["financials:read:metrics"]

    # Step 4: Ask Governor to derive child token for Agent B (Governor enforces monotonicity)
    token_b, claims_b = await GovernorService.derive_child_token(
        parent_token=token_a,
        delegator_agent="agent_a",
        delegatee_agent="agent_b",
        requested_scopes=requested_scopes,
        requested_data_scope=DataScope(customer_ids=requested_customers)
    )

    # Step 5: Dispatch Real HTTP Request to Agent B
    agent_b_payload = {
        "task_id": task_id,
        "chain_id": claims_a.chain_id,
        "originating_user": request.originating_user,
        "token": token_b,
        "customer_id": target_customer,
        "task_type": target_task_type,
        "operation": request.operation,
        "user_prompt": prompt_text,
        "use_llm": request.use_llm,
        "task_context": {
            "coordinator": "agent_a",
            "root_jti": claims_a.jti,
            "child_jti": claims_b.jti,
            "agent_a_reasoning": plan_reasoning
        },
        "simulate_attack": request.simulate_attack
    }

    logger.info(
        f"Agent A dispatching HTTP call to Agent B for chain [{claims_a.chain_id}]",
        extra={"extra_data": {"chain_id": claims_a.chain_id, "child_token_id": claims_b.jti}}
    )

    agent_b_response = await AgentHTTPClient.post_to_agent(
        endpoint_path="/api/v1/agents/agent-b/execute",
        payload=agent_b_payload
    )

    # Step 6: Dynamically reconstruct execution delegation chain
    delegation_chain = [request.originating_user, "agent_a"]
    if isinstance(agent_b_response, dict) and "delegation_chain" in agent_b_response:
        delegation_chain.extend(agent_b_response["delegation_chain"])
    else:
        delegation_chain.extend(["agent_b", "agent_c"])

    result_data = (
        agent_b_response.get("data", agent_b_response)
        if isinstance(agent_b_response, dict)
        else agent_b_response
    )
    audit_id = agent_b_response.get("audit_event_id") if isinstance(agent_b_response, dict) else None
    combined_reasoning = f"Agent A: {plan_reasoning}"
    if isinstance(agent_b_response, dict) and agent_b_response.get("llm_reasoning"):
        combined_reasoning += f" | {agent_b_response['llm_reasoning']}"

    return AgentExecutionResponse(
        status="completed",
        task_id=task_id,
        chain_id=claims_a.chain_id,
        delegation_chain=delegation_chain,
        operation=request.operation,
        customer_id=target_customer,
        authorization="ALLOWED",
        data=result_data,
        audit_event_id=audit_id,
        llm_reasoning=combined_reasoning
    )


# ==============================================================================
# Agent B (Planner)
# ==============================================================================

@router.post(
    "/agent-b/execute",
    response_model=AgentExecutionResponse,
    status_code=status.HTTP_200_OK,
    summary="Agent B Execution (Planner)",
    description=(
        "Receives delegation from Agent A, validates token audience (agent_b) and chain, "
        "uses Gemini LLM to plan scoped sub-task, derives child token for Agent C from Governor, "
        "and dispatches real HTTP call to Agent C."
    )
)
async def execute_agent_b(request: AgentBExecutionRequest) -> AgentExecutionResponse:
    logger.info(
        f"Agent B received task [{request.task_id}] for chain [{request.chain_id}]",
        extra={"extra_data": {"chain_id": request.chain_id, "customer_id": request.customer_id}}
    )

    if request.simulate_attack == "delay_expiry":
        logger.warning("Simulating agent delay for mid-chain token expiration test...")
        time.sleep(1.2)

    # Step 1: Validate Received Token (Verifies Signature, Expiration, and Audience == agent_b)
    claims_b = GovernorService.verify_token(request.token, expected_audience="agent_b")

    # Step 2: Validate Chain Integrity
    if claims_b.chain_id != request.chain_id:
        raise GovernanceException(
            message=f"Chain ID mismatch: token chain '{claims_b.chain_id}' does not match request chain '{request.chain_id}'",
            error_code="CHAIN_INTEGRITY_MISMATCH",
            status_code=status.HTTP_400_BAD_REQUEST,
            chain_id=request.chain_id
        )

    # Step 3: LLM Reasoning for Agent B Sub-Task Decomposition
    plan_reasoning = "Deterministic planner fallback"
    child_scopes = ["financials:read:summary"]
    child_customers = [request.customer_id]

    if request.use_llm:
        try:
            b_plan: AgentBPlan = await default_llm_provider.generate_structured(
                prompt=build_agent_b_prompt(
                    request.user_prompt or request.task_type,
                    claims_b.scopes[0] if claims_b.scopes else "financials:read:all",
                    request.customer_id
                ),
                system_prompt=AGENT_B_SYSTEM_PROMPT,
                schema=AgentBPlan,
                task_id=request.task_id,
                chain_id=request.chain_id
            )
            child_scopes = [b_plan.requested_scope]
            child_customers = [normalize_customer_id(c) for c in b_plan.requested_data_scope.customer_ids]
            plan_reasoning = b_plan.reasoning_summary
            logger.info(f"Agent B Gemini reasoning: {plan_reasoning}")
        except LLMProviderUnavailableException as e:
            logger.info(f"LLM Provider unavailable ({e.message}), using deterministic sub-scope.")
            if request.operation == "READ_METRICS":
                child_scopes = ["financials:read:metrics"]
            elif request.operation == "READ_FINANCIALS":
                child_scopes = ["financials:read:all"]
        except Exception as e:
            logger.warning(f"Agent B LLM generation error: {e}")
            raise
    else:
        if request.operation == "READ_METRICS":
            child_scopes = ["financials:read:metrics"]
        elif request.operation == "READ_FINANCIALS":
            child_scopes = ["financials:read:all"]

    # Handle attack simulation overrides
    if request.simulate_attack == "escalate_write_to_c":
        child_scopes = ["financials:write:record"]
    elif request.simulate_attack == "escalate_cust_to_c":
        child_customers = ["CUST-999_UNAUTHORIZED"]

    # Step 4: Ask Governor to derive child token for Agent C (aud: agent_c)
    token_c, claims_c = await GovernorService.derive_child_token(
        parent_token=request.token,
        delegator_agent="agent_b",
        delegatee_agent="agent_c",
        requested_scopes=child_scopes,
        requested_data_scope=DataScope(customer_ids=child_customers)
    )

    # Step 5: Dispatch Real HTTP Request to Agent C
    agent_c_payload = {
        "task_id": request.task_id,
        "chain_id": request.chain_id,
        "originating_user": request.originating_user,
        "token": token_c,
        "customer_id": request.customer_id,
        "operation": request.operation if request.simulate_attack != "write_attack" else "WRITE_RECORD",
        "user_prompt": request.user_prompt,
        "use_llm": request.use_llm,
        "task_context": {
            "coordinator": "agent_a",
            "planner": "agent_b",
            "parent_token_id": claims_b.jti,
            "child_token_id": claims_c.jti,
            "agent_b_reasoning": plan_reasoning
        },
        "simulate_attack": request.simulate_attack
    }

    logger.info(
        f"Agent B dispatching HTTP call to Agent C for chain [{request.chain_id}]",
        extra={"extra_data": {"chain_id": request.chain_id, "child_token_id": claims_c.jti}}
    )

    agent_c_response = await AgentHTTPClient.post_to_agent(
        endpoint_path="/api/v1/agents/agent-c/execute",
        payload=agent_c_payload
    )

    delegation_chain = ["agent_b"]
    if isinstance(agent_c_response, dict) and "delegation_chain" in agent_c_response:
        delegation_chain.extend(agent_c_response["delegation_chain"])
    else:
        delegation_chain.append("agent_c")

    result_data = (
        agent_c_response.get("data", agent_c_response)
        if isinstance(agent_c_response, dict)
        else agent_c_response
    )
    audit_id = agent_c_response.get("audit_event_id") if isinstance(agent_c_response, dict) else None
    combined_reasoning = f"Agent B: {plan_reasoning}"
    if isinstance(agent_c_response, dict) and agent_c_response.get("llm_reasoning"):
        combined_reasoning += f" | {agent_c_response['llm_reasoning']}"

    return AgentExecutionResponse(
        status="completed",
        task_id=request.task_id,
        chain_id=request.chain_id,
        delegation_chain=delegation_chain,
        operation=request.operation,
        customer_id=request.customer_id,
        authorization="ALLOWED",
        data=result_data,
        audit_event_id=audit_id,
        llm_reasoning=combined_reasoning
    )


# ==============================================================================
# Agent C (Worker)
# ==============================================================================

@router.post(
    "/agent-c/execute",
    response_model=AgentExecutionResponse,
    status_code=status.HTTP_200_OK,
    summary="Agent C Execution (Worker)",
    description=(
        "Receives delegation from Agent B, validates token audience (agent_c) and chain, "
        "uses Gemini LLM to select tool operation, and calls Governor-gated tool gateway "
        "(/api/v1/governor/tools/execute) to execute tool."
    )
)
async def execute_agent_c(request: AgentCExecutionRequest) -> AgentExecutionResponse:
    logger.info(
        f"Agent C received task [{request.task_id}] for operation '{request.operation}' on customer '{request.customer_id}'",
        extra={"extra_data": {"chain_id": request.chain_id, "customer_id": request.customer_id}}
    )

    # Step 1: Validate Received Token (Verifies Signature, Expiry, and Audience == agent_c)
    claims_c = GovernorService.verify_token(request.token, expected_audience="agent_c")

    # Step 2: Validate Chain Integrity
    if claims_c.chain_id != request.chain_id:
        raise GovernanceException(
            message=f"Chain ID mismatch: token chain '{claims_c.chain_id}' does not match request chain '{request.chain_id}'",
            error_code="CHAIN_INTEGRITY_MISMATCH",
            status_code=status.HTTP_400_BAD_REQUEST,
            chain_id=request.chain_id
        )

    # Step 3: LLM Reasoning for Agent C Financial Tool Selection
    plan_reasoning = "Deterministic worker fallback"
    target_operation = request.operation
    target_customer = request.customer_id
    target_resource = "customer_financials"

    if request.use_llm:
        try:
            c_plan: AgentCToolRequest = await default_llm_provider.generate_structured(
                prompt=build_agent_c_prompt(
                    request.user_prompt or "Financial analysis execution",
                    request.operation,
                    request.customer_id
                ),
                system_prompt=AGENT_C_SYSTEM_PROMPT,
                schema=AgentCToolRequest,
                task_id=request.task_id,
                chain_id=request.chain_id
            )
            target_operation = c_plan.operation
            target_customer = normalize_customer_id(c_plan.customer_id)
            target_resource = c_plan.resource
            plan_reasoning = c_plan.reasoning_summary
            logger.info(f"Agent C Gemini reasoning: {plan_reasoning}")
        except LLMProviderUnavailableException as e:
            logger.info(f"LLM Provider unavailable ({e.message}), using requested operation.")
        except Exception as e:
            logger.warning(f"Agent C LLM generation error: {e}")
            raise

    # Handle attack simulation overrides (Attacks test Governor PEP enforcement)
    if request.simulate_attack == "write_attack":
        target_operation = "WRITE_RECORD"
    elif request.simulate_attack == "cross_customer_attack":
        target_customer = "CUST-102"

    # Step 4: Call Governor-Gated Tool Gateway via HTTP
    tool_gateway_payload = {
        "task_id": request.task_id,
        "agent_id": "agent_c",
        "token": request.token,
        "operation": target_operation,
        "resource": target_resource,
        "customer_id": target_customer,
        "request_id": str(uuid.uuid4()),
        "payload": {"summary": "Unauthorized update attempt"} if target_operation == "WRITE_RECORD" else None
    }

    logger.info(
        f"Agent C calling Governor Tool Gateway for operation '{target_operation}' on customer '{target_customer}'",
        extra={"extra_data": {"chain_id": request.chain_id, "token_id": claims_c.jti}}
    )

    tool_response = await AgentHTTPClient.post_to_agent(
        endpoint_path="/api/v1/governor/tools/execute",
        payload=tool_gateway_payload
    )

    result_data = (
        tool_response.get("data", tool_response)
        if isinstance(tool_response, dict)
        else tool_response
    )
    audit_id = tool_response.get("audit_event_id") if isinstance(tool_response, dict) else None

    return AgentExecutionResponse(
        status="completed",
        task_id=request.task_id,
        chain_id=request.chain_id,
        delegation_chain=["agent_c"],
        operation=target_operation,
        customer_id=target_customer,
        authorization="ALLOWED",
        data=result_data,
        audit_event_id=audit_id,
        llm_reasoning=f"Agent C: {plan_reasoning}"
    )
