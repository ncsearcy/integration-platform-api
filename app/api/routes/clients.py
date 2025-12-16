from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.core.logging import get_logger
from app.api.db.session import get_db
from app.api.schemas.client import (
    Client,
    ClientCreate,
    ClientUpdate,
    ClientWithCredentials,
    ClientList,
)
from app.api.services.integration_services import IntegrationService

logger = get_logger(__name__)

router = APIRouter(prefix="/clients", tags=["clients"])


def get_integration_service(db: Session = Depends(get_db)) -> IntegrationService:
    """Dependency to get integration service."""
    return IntegrationService(db)


@router.post(
    "",
    response_model=Client,
    status_code=status.HTTP_201_CREATED,
    summary="Create Client",
    description="Register a new client with optional encrypted credentials.",
)
def create_client(
    client_data: ClientCreate,
    service: IntegrationService = Depends(get_integration_service),
) -> Client:
    """
    Create a new client.

    Args:
        client_data: Client creation data
        service: Integration service

    Returns:
        Client: Created client (without sensitive credentials)
    """
    logger.info("create_client_requested", name=client_data.name)

    try:
        db_client = service.create_client(
            name=client_data.name,
            description=client_data.description,
            external_api_url=client_data.external_api_url,
            external_api_timeout=client_data.external_api_timeout,
            is_active=client_data.is_active,
            credentials=client_data.credentials,
        )

        # Convert to response schema (without encrypted credentials)
        response = Client.model_validate(db_client)
        response.has_credentials = db_client.encrypted_credentials is not None

        logger.info("client_created", client_id=db_client.id, name=db_client.name)
        return response

    except Exception as e:
        logger.error("create_client_failed", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create client: {str(e)}",
        )


@router.get(
    "",
    response_model=ClientList,
    summary="List Clients",
    description="Get a paginated list of clients.",
)
def list_clients(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    is_active: bool | None = Query(None, description="Filter by active status"),
    service: IntegrationService = Depends(get_integration_service),
) -> ClientList:
    """
    Get paginated list of clients.

    Args:
        page: Page number (starting from 1)
        page_size: Number of items per page
        is_active: Optional filter for active clients
        service: Integration service

    Returns:
        ClientList: Paginated list of clients
    """
    logger.info("list_clients_requested", page=page, page_size=page_size, is_active=is_active)

    skip = (page - 1) * page_size

    try:
        clients = service.get_clients(skip=skip, limit=page_size, is_active=is_active)

        # Count total for pagination
        from app.api.models.client import Client as ClientModel

        query = service.db.query(ClientModel)
        if is_active is not None:
            query = query.filter(ClientModel.is_active == is_active)
        total = query.count()

        # Convert to response schemas
        items = []
        for client in clients:
            item = Client.model_validate(client)
            item.has_credentials = client.encrypted_credentials is not None
            items.append(item)

        pages = (total + page_size - 1) // page_size

        return ClientList(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            pages=pages,
        )

    except Exception as e:
        logger.error("list_clients_failed", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list clients: {str(e)}",
        )


@router.get(
    "/{client_id}",
    response_model=Client,
    summary="Get Client",
    description="Get a specific client by ID.",
)
def get_client(
    client_id: int,
    service: IntegrationService = Depends(get_integration_service),
) -> Client:
    """
    Get client by ID.

    Args:
        client_id: Client ID
        service: Integration service

    Returns:
        Client: Client details

    Raises:
        HTTPException: If client not found
    """
    logger.info("get_client_requested", client_id=client_id)

    client = service.get_client(client_id)
    if not client:
        logger.warning("client_not_found", client_id=client_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Client {client_id} not found",
        )

    response = Client.model_validate(client)
    response.has_credentials = client.encrypted_credentials is not None

    return response


@router.get(
    "/{client_id}/credentials",
    response_model=ClientWithCredentials,
    summary="Get Client with Credentials",
    description="Get client with decrypted credentials (admin only).",
)
def get_client_credentials(
    client_id: int,
    service: IntegrationService = Depends(get_integration_service),
) -> ClientWithCredentials:
    """
    Get client with decrypted credentials.

    NOTE: This endpoint should be protected with authentication in production.

    Args:
        client_id: Client ID
        service: Integration service

    Returns:
        ClientWithCredentials: Client with decrypted credentials

    Raises:
        HTTPException: If client not found
    """
    logger.info("get_client_credentials_requested", client_id=client_id)

    client = service.get_client(client_id)
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Client {client_id} not found",
        )

    credentials = service.get_client_credentials(client_id)

    response = ClientWithCredentials.model_validate(client)
    response.credentials = credentials
    response.has_credentials = credentials is not None

    logger.info("client_credentials_retrieved", client_id=client_id)
    return response


@router.put(
    "/{client_id}",
    response_model=Client,
    summary="Update Client",
    description="Update an existing client.",
)
def update_client(
    client_id: int,
    client_data: ClientUpdate,
    service: IntegrationService = Depends(get_integration_service),
) -> Client:
    """
    Update a client.

    Args:
        client_id: Client ID
        client_data: Client update data
        service: Integration service

    Returns:
        Client: Updated client

    Raises:
        HTTPException: If client not found
    """
    logger.info("update_client_requested", client_id=client_id)

    client = service.update_client(
        client_id=client_id,
        name=client_data.name,
        description=client_data.description,
        external_api_url=client_data.external_api_url,
        external_api_timeout=client_data.external_api_timeout,
        is_active=client_data.is_active,
        credentials=client_data.credentials,
    )

    if not client:
        logger.warning("client_not_found_for_update", client_id=client_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Client {client_id} not found",
        )

    response = Client.model_validate(client)
    response.has_credentials = client.encrypted_credentials is not None

    logger.info("client_updated", client_id=client_id)
    return response


@router.delete(
    "/{client_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Client",
    description="Delete a client and all associated integrations.",
)
def delete_client(
    client_id: int,
    service: IntegrationService = Depends(get_integration_service),
) -> None:
    """
    Delete a client.

    Args:
        client_id: Client ID
        service: Integration service

    Raises:
        HTTPException: If client not found
    """
    logger.info("delete_client_requested", client_id=client_id)

    deleted = service.delete_client(client_id)
    if not deleted:
        logger.warning("client_not_found_for_delete", client_id=client_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Client {client_id} not found",
        )

    logger.info("client_deleted", client_id=client_id)
