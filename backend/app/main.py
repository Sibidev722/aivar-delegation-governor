import time
import uuid
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import settings
from app.core.logging import logger, request_id_ctx, chain_id_ctx, task_id_ctx
from app.core.exceptions import (
    GovernanceException,
    governance_exception_handler,
    validation_exception_handler,
    http_exception_handler,
    generic_exception_handler
)
from app.db.session import DatabaseSession
from app.db.indexes import create_database_indexes
from app.db.seed import seed_financial_data
from app.api.v1.api import api_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifecycle manager:
    Initializes database connection, ensures indexes, seeds mock customer data,
    and cleanly handles graceful shutdown.
    """
    logger.info(f"Starting {settings.PROJECT_NAME} v{settings.VERSION} [{settings.ENVIRONMENT}]")
    
    # 1. Connect to MongoDB
    await DatabaseSession.connect()
    
    # 2. Configure Database Indexes
    await create_database_indexes()
    
    # 3. Seed Mock Financial Data
    await seed_financial_data()
    
    yield
    
    # 4. Graceful Disconnect
    logger.info("Shutting down application and closing database connections...")
    await DatabaseSession.disconnect()
    logger.info("Application shutdown complete.")


def create_application() -> FastAPI:
    """
    FastAPI application factory.
    """
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        description=(
            "Centralized Delegation Chain Governor (PS-2.3) implementing scoped permission "
            "propagation, monotonic scope shrinkage, Ed25519 token verification, "
            "and tamper-evident audit logging across multi-agent workflows."
        ),
        docs_url="/docs" if settings.ENVIRONMENT != "production" or settings.DEBUG else None,
        redoc_url="/redoc" if settings.ENVIRONMENT != "production" or settings.DEBUG else None,
        lifespan=lifespan
    )

    # 1. CORS Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "X-Chain-ID", "X-Execution-Time-MS"]
    )

    # 2. Request ID & Distributed Tracing Middleware
    @app.middleware("http")
    async def request_tracing_middleware(request: Request, call_next) -> Response:
        start_time = time.perf_counter()
        
        # Extract or generate Request ID
        incoming_req_id = request.headers.get("X-Request-ID")
        req_id = incoming_req_id if incoming_req_id else str(uuid.uuid4())
        request_id_ctx.set(req_id)

        # Extract optional Chain ID and Task ID from headers if present
        chain_id = request.headers.get("X-Chain-ID")
        if chain_id:
            chain_id_ctx.set(chain_id)
        else:
            chain_id_ctx.set(None)

        task_id = request.headers.get("X-Task-ID")
        if task_id:
            task_id_ctx.set(task_id)
        else:
            task_id_ctx.set(None)

        logger.info(
            f"Incoming request: {request.method} {request.url.path}",
            extra={"extra_data": {"client_host": request.client.host if request.client else None}}
        )

        try:
            response: Response = await call_next(request)
            execution_time_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
            
            # Attach correlation headers to response
            response.headers["X-Request-ID"] = req_id
            if chain_id:
                response.headers["X-Chain-ID"] = chain_id
            response.headers["X-Execution-Time-MS"] = str(execution_time_ms)

            logger.info(
                f"Request completed: {request.method} {request.url.path} -> {response.status_code} ({execution_time_ms}ms)"
            )
            return response
        except Exception as e:
            execution_time_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
            logger.error(
                f"Request failed: {request.method} {request.url.path} after {execution_time_ms}ms: {e}"
            )
            raise e

    # 3. Global Exception Handlers
    app.add_exception_handler(GovernanceException, governance_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)

    # 4. Include API v1 Router
    app.include_router(api_router, prefix="/api/v1")

    # 5. Root status endpoint
    @app.get("/", tags=["Root"])
    async def get_root():
        return {
            "name": settings.PROJECT_NAME,
            "version": settings.VERSION,
            "status": "operational",
            "health_check": "/api/v1/health",
            "readiness_check": "/api/v1/health/ready"
        }

    return app


app = create_application()
