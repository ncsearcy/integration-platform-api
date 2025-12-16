from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.core.logging import get_logger
from app.api.db.session import get_db
from app.api.models.integration import IntegrationStatus
from app.api.schemas.integration import (
    Integration,
    IntegrationList,
    IntegrationSync,
    IntegrationSyncResponse,
)
from app.api.services.integration_services import IntegrationService

logger = get_logger(__name__)

router = APIRouter(prefix="/integrations", tags=["integrations"])


def get_integration_service(db: Session = Depends(get_db)) -> IntegrationService:
    """Dependency to get integration service."""
    return IntegrationService(db)


@router.post(
    "/sync/{client_id}",
    response_model=IntegrationSyncResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Sync Integration",
    description="Trigger a synchronization with the external API for a client.",
)
async def sync_integration(
    client_id: int,
    sync_data: IntegrationSync,
    service: IntegrationService = Depends(get_integration_service),
) -> IntegrationSyncResponse:
    """
    Trigger an integration sync for a client.

    Args:
        client_id: Client ID
        sync_data: Sync configuration
        service: Integration service

    Returns:
        IntegrationSyncResponse: Sync operation result

    Raises:
        HTTPException: If client not found or sync fails
    """
    logger.info(
        "sync_integration_requested",
        client_id=client_id,
        endpoint=sync_data.endpoint,
        method=sync_data.method,
    )

    try:
        integration = await service.sync_integration(
            client_id=client_id,
            endpoint=sync_data.endpoint or "/posts",
            method=sync_data.method,
            params=sync_data.params,
        )

        message = (
            "Integration sync completed successfully"
            if integration.status == IntegrationStatus.SUCCESS
            else f"Integration sync failed: {integration.error_message}"
        )

        logger.info(
            "sync_integration_completed",
            integration_id=integration.id,
            client_id=client_id,
            status=integration.status,
        )

        return IntegrationSyncResponse(
            integration_id=integration.id,
            status=integration.status,
            message=message,
        )

    except ValueError as e:
        logger.warning("sync_integration_validation_error", client_id=client_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error("sync_integration_failed", client_id=client_id, error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to sync integration: {str(e)}",
        )


@router.get(
    "",
    response_model=IntegrationList,
    summary="List Integrations",
    description="Get a paginated list of integrations with optional filters.",
)
def list_integrations(
    client_id: int | None = Query(None, description="Filter by client ID"),
    status_filter: IntegrationStatus | None = Query(None, alias="status", description="Filter by status"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    service: IntegrationService = Depends(get_integration_service),
) -> IntegrationList:
    """
    Get paginated list of integrations.

    Args:
        client_id: Optional client ID filter
        status_filter: Optional status filter
        page: Page number
        page_size: Items per page
        service: Integration service

    Returns:
        IntegrationList: Paginated list of integrations
    """
    logger.info(
        "list_integrations_requested",
        client_id=client_id,
        status=status_filter,
        page=page,
        page_size=page_size,
    )

    skip = (page - 1) * page_size

    try:
        integrations = service.get_integrations(
            client_id=client_id,
            skip=skip,
            limit=page_size,
            status=status_filter,
        )

        # Count total for pagination
        from app.api.models.integration import Integration as IntegrationModel

        query = service.db.query(IntegrationModel)
        if client_id is not None:
            query = query.filter(IntegrationModel.client_id == client_id)
        if status_filter is not None:
            query = query.filter(IntegrationModel.status == status_filter)
        total = query.count()

        # Convert to response schemas and parse JSON response_data
        import json

        items = []
        for integration in integrations:
            item = Integration.model_validate(integration)

            # Parse response_data from JSON string to dict
            if integration.response_data:
                try:
                    item.response_data = json.loads(integration.response_data)
                except json.JSONDecodeError:
                    logger.warning(
                        "invalid_response_data_json", integration_id=integration.id
                    )
                    item.response_data = None

            items.append(item)

        pages = (total + page_size - 1) // page_size

        return IntegrationList(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            pages=pages,
        )

    except Exception as e:
        logger.error("list_integrations_failed", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list integrations: {str(e)}",
        )


@router.get(
    "/{integration_id}",
    response_model=Integration,
    summary="Get Integration",
    description="Get a specific integration by ID.",
)
def get_integration(
    integration_id: int,
    service: IntegrationService = Depends(get_integration_service),
) -> Integration:
    """
    Get integration by ID.

    Args:
        integration_id: Integration ID
        service: Integration service

    Returns:
        Integration: Integration details

    Raises:
        HTTPException: If integration not found
    """
    logger.info("get_integration_requested", integration_id=integration_id)

    integration = service.get_integration(integration_id)
    if not integration:
        logger.warning("integration_not_found", integration_id=integration_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Integration {integration_id} not found",
        )

    # Parse response_data
    import json

    response = Integration.model_validate(integration)
    if integration.response_data:
        try:
            response.response_data = json.loads(integration.response_data)
        except json.JSONDecodeError:
            logger.warning("invalid_response_data_json", integration_id=integration_id)
            response.response_data = None

    return response
