from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.core.config import settings
from app.api.core.logging import get_logger
from app.api.db.session import get_db, check_db_connection
from app.api.models.client import Client
from app.api.models.integration import Integration

logger = get_logger(__name__)

router = APIRouter(prefix="", tags=["health"])


# Response schemas
class HealthResponse(BaseModel):
    """Basic health check response."""

    status: str
    timestamp: str
    version: str


class ReadinessResponse(BaseModel):
    """Readiness check response with component status."""

    status: str
    timestamp: str
    version: str
    components: Dict[str, Any]


class StatusResponse(BaseModel):
    """Detailed status response with metrics."""

    status: str
    timestamp: str
    version: str
    environment: str
    uptime_seconds: float
    components: Dict[str, Any]
    metrics: Dict[str, Any]


# Application start time for uptime calculation
_app_start_time = datetime.utcnow()


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Basic Health Check",
    description="Returns basic health status of the application. Always returns 200 OK if the application is running.",
)
def health_check() -> HealthResponse:
    """
    Basic health check endpoint.

    Returns:
        HealthResponse: Basic health status
    """
    return HealthResponse(
        status="ok",
        timestamp=datetime.utcnow().isoformat(),
        version=settings.app_version,
    )


@router.get(
    "/health/ready",
    response_model=ReadinessResponse,
    status_code=status.HTTP_200_OK,
    summary="Readiness Check",
    description="Returns readiness status including database connectivity. Use this for Kubernetes readiness probes.",
)
def readiness_check(db: Session = Depends(get_db)) -> ReadinessResponse:
    """
    Readiness check endpoint.

    Verifies that all required services are available and the application
    is ready to serve traffic.

    Args:
        db: Database session

    Returns:
        ReadinessResponse: Readiness status with component checks
    """
    logger.info("readiness_check_requested")

    # Check database connection
    db_status = "healthy"
    db_connected = check_db_connection()

    if not db_connected:
        db_status = "unhealthy"
        logger.warning("readiness_check_database_unhealthy")

    components = {
        "database": {
            "status": db_status,
            "connected": db_connected,
        },
        "api": {
            "status": "healthy",
        },
    }

    # Overall status is healthy only if all components are healthy
    overall_status = "ready" if db_connected else "not_ready"

    return ReadinessResponse(
        status=overall_status,
        timestamp=datetime.utcnow().isoformat(),
        version=settings.app_version,
        components=components,
    )


@router.get(
    "/status",
    response_model=StatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Detailed Status",
    description="Returns detailed status information including metrics and component health.",
)
def status_check(db: Session = Depends(get_db)) -> StatusResponse:
    """
    Detailed status endpoint.

    Provides comprehensive information about the application status,
    including metrics and component health.

    Args:
        db: Database session

    Returns:
        StatusResponse: Detailed status with metrics
    """
    logger.info("status_check_requested")

    # Calculate uptime
    uptime = (datetime.utcnow() - _app_start_time).total_seconds()

    # Check database
    db_connected = check_db_connection()

    # Get metrics
    try:
        total_clients = db.query(Client).count()
        active_clients = db.query(Client).filter(Client.is_active == True).count()
        total_integrations = db.query(Integration).count()

        # Get recent integration (last hour)
        one_hour_ago = datetime.utcnow()
        from datetime import timedelta

        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        recent_integrations = (
            db.query(Integration).filter(Integration.created_at >= one_hour_ago).count()
        )

    except Exception as e:
        logger.error("status_check_metrics_failed", error=str(e))
        total_clients = 0
        active_clients = 0
        total_integrations = 0
        recent_integrations = 0

    components = {
        "database": {
            "status": "healthy" if db_connected else "unhealthy",
            "connected": db_connected,
            "url": settings.database_url.split("@")[-1] if "@" in settings.database_url else "unknown",
        },
        "api": {
            "status": "healthy",
            "version": settings.app_version,
        },
        "external_api": {
            "base_url": settings.external_api_url,
            "timeout": settings.external_api_timeout,
        },
    }

    metrics = {
        "clients": {
            "total": total_clients,
            "active": active_clients,
            "inactive": total_clients - active_clients,
        },
        "integrations": {
            "total": total_integrations,
            "last_hour": recent_integrations,
        },
    }

    return StatusResponse(
        status="operational",
        timestamp=datetime.utcnow().isoformat(),
        version=settings.app_version,
        environment=settings.environment,
        uptime_seconds=uptime,
        components=components,
        metrics=metrics,
    )
