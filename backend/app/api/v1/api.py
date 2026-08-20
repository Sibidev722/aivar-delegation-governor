from fastapi import APIRouter
from app.api.v1.endpoints import health, governor, tools, agents, audit

api_router = APIRouter()

# Health and readiness routes
api_router.include_router(health.router, prefix="/health", tags=["Health"])

# Governor token and public key routes
api_router.include_router(governor.router, prefix="/governor", tags=["Delegation Governor"])

# Governor-gated tool execution gateway
api_router.include_router(tools.router, prefix="/governor/tools", tags=["Tool Gateway"])

# Multi-Agent endpoints (Agent A, Agent B, Agent C)
api_router.include_router(agents.router, prefix="/agents", tags=["Agents"])

# Tamper-Evident Hash-Chained Audit Ledger
api_router.include_router(audit.router, prefix="/audit", tags=["Audit Ledger"])
