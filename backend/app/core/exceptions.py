from datetime import datetime, timezone
from typing import Any, Optional
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.core.logging import logger, request_id_ctx


class GovernanceException(Exception):
    """
    Base exception class for all Governance and Delegation errors.
    """
    status_code: int = status.HTTP_400_BAD_REQUEST
    error_code: str = "GOVERNANCE_ERROR"
    message: str = "A governance violation occurred."

    def __init__(
        self,
        message: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
        chain_id: Optional[str] = None,
        status_code: Optional[int] = None,
        error_code: Optional[str] = None
    ) -> None:
        if message:
            self.message = message
        if status_code:
            self.status_code = status_code
        if error_code:
            self.error_code = error_code
        self.details = details or {}
        self.chain_id = chain_id
        super().__init__(self.message)


# Specific Governance Exceptions mapping to test requirements
class ScopeExpansionForbiddenException(GovernanceException):
    status_code = status.HTTP_403_FORBIDDEN
    error_code = "SCOPE_EXPANSION_FORBIDDEN"
    message = "Child delegation scope exceeds delegator authority."


class InsufficientScopeException(GovernanceException):
    status_code = status.HTTP_403_FORBIDDEN
    error_code = "INSUFFICIENT_OPERATION_SCOPE"
    message = "The provided token does not possess sufficient operational scope."


class DataScopeViolationException(GovernanceException):
    status_code = status.HTTP_403_FORBIDDEN
    error_code = "DATA_SCOPE_VIOLATION"
    message = "Access to the requested customer/resource is prohibited by data scope."


class AudienceMismatchException(GovernanceException):
    status_code = status.HTTP_403_FORBIDDEN
    error_code = "AUDIENCE_MISMATCH"
    message = "Token was issued for a different agent audience."


class InvalidTokenSignatureException(GovernanceException):
    status_code = status.HTTP_401_UNAUTHORIZED
    error_code = "INVALID_ED25519_SIGNATURE"
    message = "Token signature verification failed or token is malformed."


class TokenExpiredException(GovernanceException):
    status_code = status.HTTP_401_UNAUTHORIZED
    error_code = "TOKEN_EXPIRED"
    message = "Delegation token has expired."


class DatabaseConnectionException(GovernanceException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    error_code = "DATABASE_UNAVAILABLE"
    message = "Unable to establish or maintain connection with MongoDB database."


class ConfigurationException(GovernanceException):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code = "CONFIGURATION_ERROR"
    message = "Invalid system configuration."


# LLM-specific Exceptions
class LLMProviderUnavailableException(GovernanceException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    error_code = "LLM_PROVIDER_UNAVAILABLE"
    message = "The configured LLM provider is currently unavailable."


class LLMValidationException(GovernanceException):
    status_code = 422
    error_code = "LLM_VALIDATION_ERROR"
    message = "The LLM response failed structured schema validation."


class LLMTimeoutException(GovernanceException):
    status_code = status.HTTP_504_GATEWAY_TIMEOUT
    error_code = "LLM_TIMEOUT"
    message = "The LLM request timed out before completing."


# Helper to build consistent error payloads
def build_error_response(
    status_code: int,
    error_code: str,
    message: str,
    details: Optional[dict[str, Any]] = None,
    chain_id: Optional[str] = None
) -> JSONResponse:
    payload = {
        "status": "error",
        "error_code": error_code,
        "message": message,
        "request_id": request_id_ctx.get(),
        "chain_id": chain_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "details": details or {},
    }
    return JSONResponse(status_code=status_code, content=payload)


# FastAPI Global Exception Handlers
async def governance_exception_handler(request: Request, exc: GovernanceException) -> JSONResponse:
    logger.warning(
        f"Governance exception [{exc.error_code}]: {exc.message}",
        extra={"extra_data": {"status_code": exc.status_code, "details": exc.details, "chain_id": exc.chain_id}}
    )
    return build_error_response(
        status_code=exc.status_code,
        error_code=exc.error_code,
        message=exc.message,
        details=exc.details,
        chain_id=exc.chain_id
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    errors = exc.errors()
    logger.warning(f"Request validation failed: {errors}")
    return build_error_response(
        status_code=422,
        error_code="VALIDATION_ERROR",
        message="Request payload validation failed.",
        details={"validation_errors": errors}
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    logger.warning(f"HTTP Exception [{exc.status_code}]: {exc.detail}")
    return build_error_response(
        status_code=exc.status_code,
        error_code="HTTP_ERROR",
        message=str(exc.detail)
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception(f"Unhandled server error: {str(exc)}")
    return build_error_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_code="INTERNAL_SERVER_ERROR",
        message="An unexpected internal server error occurred."
    )
