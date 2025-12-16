import sys
from pathlib import Path

# Add parent directory to path to allow imports when run directly
if __name__ == "__main__":
    parent_dir = str(Path(__file__).parent.parent)
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)

import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.core.config import settings
from app.api.core.logging import get_logger, set_request_id, setup_logging
from app.api.db.session import init_db
from app.api.routes import clients, health, integrations

# Setup logging
setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan events.

    Handles startup and shutdown events for the application.
    """
    # Startup
    logger.info(
        "application_starting",
        app_name=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
    )

    # Initialize database
    try:
        init_db()
        logger.info("database_initialized_successfully")
    except Exception as e:
        logger.error("database_initialization_failed", error=str(e), exc_info=True)
        # Continue anyway - the application can still run, health checks will fail

    logger.info("application_started")

    yield

    # Shutdown
    logger.info("application_shutting_down")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    description="Backend service for managing client integrations, external API syncs, and observability",
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs" if settings.is_development else None,
    redoc_url="/redoc" if settings.is_development else None,
)


# ============= Middleware =============


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    """
    Middleware for logging all requests with unique request IDs.
    """
    # Generate unique request ID
    request_id = str(uuid.uuid4())
    set_request_id(request_id)

    # Log request
    logger.info(
        "request_received",
        method=request.method,
        path=request.url.path,
        client_host=request.client.host if request.client else None,
    )

    try:
        response = await call_next(request)

        # Log response
        logger.info(
            "request_completed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
        )

        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id

        return response

    except Exception as e:
        logger.error(
            "request_failed",
            method=request.method,
            path=request.url.path,
            error=str(e),
            exc_info=True,
        )
        raise


# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=settings.cors_credentials,
    allow_methods=settings.cors_methods_list,
    allow_headers=settings.cors_headers_list,
)


# ============= Exception Handlers =============


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Global exception handler for unhandled exceptions.
    """
    logger.error(
        "unhandled_exception",
        method=request.method,
        path=request.url.path,
        error=str(exc),
        exc_info=True,
    )

    return JSONResponse(
        status_code=500,
        content={
            "detail": "An internal server error occurred",
            "type": "internal_server_error",
        },
    )


# ============= Routes =============

# Include routers
app.include_router(health.router)
app.include_router(clients.router, prefix="/api/v1")
app.include_router(integrations.router, prefix="/api/v1")


# Root endpoint
@app.get("/", tags=["root"])
def root():
    """
    Root endpoint with API information.
    """
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "docs_url": "/docs" if settings.is_development else None,
        "health_check": "/health",
        "api_prefix": "/api/v1",
        "endpoints": {
            "clients": "/api/v1/clients",
            "integrations": "/api/v1/integrations",
            "health": "/health",
            "readiness": "/health/ready",
            "status": "/status",
        },
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        log_level=settings.log_level.lower(),
    )
