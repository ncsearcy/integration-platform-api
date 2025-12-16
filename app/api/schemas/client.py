from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ClientBase(BaseModel):
    """Base schema for client with common fields."""

    name: str = Field(..., min_length=1, max_length=255, description="Client name")
    description: str | None = Field(None, description="Client description")
    external_api_url: str | None = Field(None, description="External API URL")
    external_api_timeout: int = Field(
        default=30, ge=1, le=300, description="API timeout in seconds"
    )
    is_active: bool = Field(default=True, description="Whether client is active")


class ClientCreate(ClientBase):
    """Schema for creating a new client."""

    credentials: dict[str, Any] | None = Field(
        None, description="Client credentials (will be encrypted)"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Acme Corporation",
                "description": "Main client for Acme Corp integrations",
                "external_api_url": "https://api.acme.com",
                "external_api_timeout": 30,
                "is_active": True,
                "credentials": {"api_key": "secret_key_123", "api_secret": "secret_value_456"},
            }
        }
    )


class ClientUpdate(BaseModel):
    """Schema for updating an existing client."""

    name: str | None = Field(None, min_length=1, max_length=255, description="Client name")
    description: str | None = Field(None, description="Client description")
    external_api_url: str | None = Field(None, description="External API URL")
    external_api_timeout: int | None = Field(
        None, ge=1, le=300, description="API timeout in seconds"
    )
    is_active: bool | None = Field(None, description="Whether client is active")
    credentials: dict[str, Any] | None = Field(
        None, description="Client credentials (will be encrypted)"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Acme Corporation Updated",
                "is_active": False,
            }
        }
    )


class ClientInDB(ClientBase):
    """Schema for client as stored in database."""

    id: int
    api_key: str
    encrypted_credentials: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class Client(ClientBase):
    """Schema for client in API responses (without sensitive data)."""

    id: int
    api_key: str
    created_at: datetime
    updated_at: datetime
    has_credentials: bool = Field(
        default=False, description="Whether client has credentials stored"
    )

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "name": "Acme Corporation",
                "description": "Main client for Acme Corp integrations",
                "external_api_url": "https://api.acme.com",
                "external_api_timeout": 30,
                "is_active": True,
                "api_key": "pk_1234567890abcdef",
                "created_at": "2024-01-01T00:00:00",
                "updated_at": "2024-01-01T00:00:00",
                "has_credentials": True,
            }
        },
    )


class ClientWithCredentials(Client):
    """Schema for client with decrypted credentials (admin only)."""

    credentials: dict[str, Any] | None = Field(None, description="Decrypted credentials")

    model_config = ConfigDict(from_attributes=True)


class ClientList(BaseModel):
    """Schema for paginated list of clients."""

    items: list[Client]
    total: int
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=100)
    pages: int

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "items": [
                    {
                        "id": 1,
                        "name": "Acme Corporation",
                        "description": "Main client",
                        "external_api_url": "https://api.acme.com",
                        "external_api_timeout": 30,
                        "is_active": True,
                        "api_key": "pk_1234567890abcdef",
                        "created_at": "2024-01-01T00:00:00",
                        "updated_at": "2024-01-01T00:00:00",
                        "has_credentials": True,
                    }
                ],
                "total": 1,
                "page": 1,
                "page_size": 50,
                "pages": 1,
            }
        }
    )
