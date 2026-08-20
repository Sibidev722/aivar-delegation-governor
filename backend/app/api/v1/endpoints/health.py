from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Response, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from app.config import settings
from app.db.session import DatabaseSession

router = APIRouter()


class LivenessResponse(BaseModel):
    status: str = Field(json_schema_extra={"example": "healthy"})
    service: str = Field(json_schema_extra={"example": "Delegation Chain Governor"})
    version: str = Field(json_schema_extra={"example": "1.0.0"})
    environment: str = Field(json_schema_extra={"example": "development"})
    timestamp: str = Field(json_schema_extra={"example": "2026-08-19T10:00:00Z"})


class ReadinessDatabaseInfo(BaseModel):
    status: str = Field(json_schema_extra={"example": "connected"})
    latency_ms: float = Field(json_schema_extra={"example": 1.25})
    database_name: str = Field(json_schema_extra={"example": "delegation_governor"})


class ReadinessResponse(BaseModel):
    status: str = Field(json_schema_extra={"example": "ready"})
    service: str = Field(json_schema_extra={"example": "Delegation Chain Governor"})
    database: ReadinessDatabaseInfo
    error: Optional[str] = Field(default=None, json_schema_extra={"example": "Database connection is not available"})
    timestamp: str = Field(json_schema_extra={"example": "2026-08-19T10:00:00Z"})


@router.get(
    "",
    response_model=LivenessResponse,
    summary="Liveness Probe",
    description="Returns 200 OK if the backend HTTP process is active and responsive."
)
async def get_health_liveness() -> LivenessResponse:
    return LivenessResponse(
        status="healthy",
        service=settings.PROJECT_NAME,
        version=settings.VERSION,
        environment=settings.ENVIRONMENT,
        timestamp=datetime.now(timezone.utc).isoformat()
    )


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    responses={
        200: {"description": "Service Ready - Database connected", "model": ReadinessResponse},
        503: {"description": "Service Unavailable - Database connection failed", "model": ReadinessResponse}
    },
    summary="Readiness Probe",
    description="Verifies database connectivity and readiness to serve requests."
)
async def get_health_readiness():
    is_healthy, latency_ms, error = await DatabaseSession.check_health()

    if not is_healthy:
        content = {
            "status": "unhealthy",
            "service": settings.PROJECT_NAME,
            "database": {
                "status": "disconnected",
                "latency_ms": latency_ms,
                "database_name": settings.MONGODB_DB_NAME
            },
            "error": "Database connection is not available",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        return JSONResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content=content)

    return ReadinessResponse(
        status="ready",
        service=settings.PROJECT_NAME,
        database=ReadinessDatabaseInfo(
            status="connected",
            latency_ms=latency_ms,
            database_name=settings.MONGODB_DB_NAME
        ),
        timestamp=datetime.now(timezone.utc).isoformat()
    )
