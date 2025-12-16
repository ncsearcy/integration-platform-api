import json
from datetime import datetime
from typing import Any, Dict

from sqlalchemy.orm import Session

from app.api.core.logging import get_logger
from app.api.core.security import decrypt_credentials, encrypt_credentials, generate_api_key
from app.api.models.client import Client
from app.api.models.integration import Integration, IntegrationStatus
from app.api.services.external_api import ExternalAPIService, ExternalAPIError

logger = get_logger(__name__)


class IntegrationService:
    """
    Service layer for managing integrations and syncing with external APIs.

    Orchestrates client management, credential handling, and API synchronization.
    """

    def __init__(self, db: Session):
        """
        Initialize the integration service.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db
        self.logger = get_logger(self.__class__.__name__)

    # ============= Client Management =============

    def create_client(
        self,
        name: str,
        description: str | None = None,
        external_api_url: str | None = None,
        external_api_timeout: int = 30,
        is_active: bool = True,
        credentials: Dict[str, Any] | None = None,
    ) -> Client:
        """
        Create a new client.

        Args:
            name: Client name
            description: Optional description
            external_api_url: Optional external API URL
            external_api_timeout: API timeout in seconds
            is_active: Whether client is active
            credentials: Optional credentials to encrypt and store

        Returns:
            Client: Created client instance
        """
        self.logger.info("creating_client", name=name, has_credentials=credentials is not None)

        # Generate API key
        api_key = generate_api_key("pk")

        # Encrypt credentials if provided
        encrypted_creds = None
        if credentials:
            encrypted_creds = encrypt_credentials(credentials)
            self.logger.info("credentials_encrypted", num_fields=len(credentials))

        # Create client
        client = Client(
            name=name,
            description=description,
            api_key=api_key,
            encrypted_credentials=encrypted_creds,
            external_api_url=external_api_url,
            external_api_timeout=external_api_timeout,
            is_active=is_active,
        )

        self.db.add(client)
        self.db.commit()
        self.db.refresh(client)

        self.logger.info("client_created", client_id=client.id, name=client.name)
        return client

    def get_client(self, client_id: int) -> Client | None:
        """
        Get client by ID.

        Args:
            client_id: Client ID

        Returns:
            Client | None: Client instance or None if not found
        """
        return self.db.query(Client).filter(Client.id == client_id).first()

    def get_client_by_api_key(self, api_key: str) -> Client | None:
        """
        Get client by API key.

        Args:
            api_key: Client API key

        Returns:
            Client | None: Client instance or None if not found
        """
        return self.db.query(Client).filter(Client.api_key == api_key).first()

    def get_clients(self, skip: int = 0, limit: int = 100, is_active: bool | None = None) -> list[Client]:
        """
        Get list of clients with pagination.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            is_active: Optional filter by active status

        Returns:
            list[Client]: List of clients
        """
        query = self.db.query(Client)

        if is_active is not None:
            query = query.filter(Client.is_active == is_active)

        return query.offset(skip).limit(limit).all()

    def update_client(
        self,
        client_id: int,
        name: str | None = None,
        description: str | None = None,
        external_api_url: str | None = None,
        external_api_timeout: int | None = None,
        is_active: bool | None = None,
        credentials: Dict[str, Any] | None = None,
    ) -> Client | None:
        """
        Update an existing client.

        Args:
            client_id: Client ID
            name: Optional new name
            description: Optional new description
            external_api_url: Optional new external API URL
            external_api_timeout: Optional new timeout
            is_active: Optional new active status
            credentials: Optional new credentials

        Returns:
            Client | None: Updated client or None if not found
        """
        client = self.get_client(client_id)
        if not client:
            return None

        self.logger.info("updating_client", client_id=client_id)

        if name is not None:
            client.name = name
        if description is not None:
            client.description = description
        if external_api_url is not None:
            client.external_api_url = external_api_url
        if external_api_timeout is not None:
            client.external_api_timeout = external_api_timeout
        if is_active is not None:
            client.is_active = is_active

        if credentials is not None:
            client.encrypted_credentials = encrypt_credentials(credentials)
            self.logger.info("client_credentials_updated", client_id=client_id)

        self.db.commit()
        self.db.refresh(client)

        self.logger.info("client_updated", client_id=client_id)
        return client

    def delete_client(self, client_id: int) -> bool:
        """
        Delete a client.

        Args:
            client_id: Client ID

        Returns:
            bool: True if deleted, False if not found
        """
        client = self.get_client(client_id)
        if not client:
            return False

        self.logger.info("deleting_client", client_id=client_id, name=client.name)

        self.db.delete(client)
        self.db.commit()

        self.logger.info("client_deleted", client_id=client_id)
        return True

    def get_client_credentials(self, client_id: int) -> Dict[str, Any] | None:
        """
        Get decrypted client credentials.

        Args:
            client_id: Client ID

        Returns:
            Dict[str, Any] | None: Decrypted credentials or None
        """
        client = self.get_client(client_id)
        if not client or not client.encrypted_credentials:
            return None

        try:
            return decrypt_credentials(client.encrypted_credentials)
        except Exception as e:
            self.logger.error("credential_decryption_failed", client_id=client_id, error=str(e))
            return None

    # ============= Integration Management =============

    async def sync_integration(
        self,
        client_id: int,
        endpoint: str = "/posts",
        method: str = "GET",
        params: Dict[str, Any] | None = None,
    ) -> Integration:
        """
        Sync data from external API for a client.

        Args:
            client_id: Client ID
            endpoint: API endpoint to call
            method: HTTP method
            params: Optional query parameters

        Returns:
            Integration: Created integration record

        Raises:
            ValueError: If client not found or inactive
        """
        # Get client
        client = self.get_client(client_id)
        if not client:
            raise ValueError(f"Client {client_id} not found")

        if not client.is_active:
            raise ValueError(f"Client {client_id} is not active")

        self.logger.info(
            "starting_integration_sync",
            client_id=client_id,
            endpoint=endpoint,
            method=method,
        )

        # Create integration record
        integration = Integration(
            client_id=client_id,
            status=IntegrationStatus.PENDING,
            external_endpoint=endpoint,
            request_method=method,
        )
        self.db.add(integration)
        self.db.commit()
        self.db.refresh(integration)

        try:
            # Update status to in progress
            integration.status = IntegrationStatus.IN_PROGRESS
            integration.started_at = datetime.utcnow()
            self.db.commit()

            # Get client credentials
            credentials = self.get_client_credentials(client_id)

            # Call external API
            api_service = ExternalAPIService(
                base_url=client.external_api_url,
                timeout=client.external_api_timeout,
            )

            response_data = await api_service.call_api(
                endpoint=endpoint,
                method=method,
                params=params,
                credentials=credentials,
            )

            # Store normalized response
            integration.response_data = json.dumps(response_data)
            integration.status = IntegrationStatus.SUCCESS
            integration.completed_at = datetime.utcnow()

            self.logger.info(
                "integration_sync_success",
                integration_id=integration.id,
                client_id=client_id,
            )

        except ExternalAPIError as e:
            integration.status = IntegrationStatus.FAILED
            integration.error_message = str(e)
            integration.error_code = "EXTERNAL_API_ERROR"
            integration.completed_at = datetime.utcnow()

            self.logger.error(
                "integration_sync_failed",
                integration_id=integration.id,
                client_id=client_id,
                error=str(e),
            )

        except Exception as e:
            integration.status = IntegrationStatus.FAILED
            integration.error_message = str(e)
            integration.error_code = "UNEXPECTED_ERROR"
            integration.completed_at = datetime.utcnow()

            self.logger.error(
                "integration_sync_unexpected_error",
                integration_id=integration.id,
                client_id=client_id,
                error=str(e),
                exc_info=True,
            )

        self.db.commit()
        self.db.refresh(integration)

        return integration

    def get_integration(self, integration_id: int) -> Integration | None:
        """Get integration by ID."""
        return self.db.query(Integration).filter(Integration.id == integration_id).first()

    def get_integrations(
        self,
        client_id: int | None = None,
        skip: int = 0,
        limit: int = 100,
        status: IntegrationStatus | None = None,
    ) -> list[Integration]:
        """
        Get list of integrations with filters.

        Args:
            client_id: Optional filter by client ID
            skip: Number of records to skip
            limit: Maximum number of records to return
            status: Optional filter by status

        Returns:
            list[Integration]: List of integrations
        """
        query = self.db.query(Integration)

        if client_id is not None:
            query = query.filter(Integration.client_id == client_id)

        if status is not None:
            query = query.filter(Integration.status == status)

        return query.order_by(Integration.created_at.desc()).offset(skip).limit(limit).all()
