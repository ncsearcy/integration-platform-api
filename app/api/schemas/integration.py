from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.api.models.integration import IntegrationStatus


class IntegrationBase(BaseModel):
    """Base schema for integration with common fields."""

    status: IntegrationStatus = Field(
        default=IntegrationStatus.PENDING, description="Integration status"
    )
    external_endpoint: str | None = Field(None, description="External API endpoint called")
    request_method: str | None = Field(None, description="HTTP method used")


class IntegrationCreate(IntegrationBase):
    """Schema for creating a new integration."""

    client_id: int = Field(..., gt=0, description="Client ID")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "client_id": 1,
                "external_endpoint": "/api/v1/users",
                "request_method": "GET",
            }
        }
    )


class IntegrationUpdate(BaseModel):
    """Schema for updating an integration."""

    status: IntegrationStatus | None = Field(None, description="Integration status")
    response_data: dict[str, Any] | None = Field(None, description="Normalized response data")
    error_message: str | None = Field(None, description="Error message if failed")
    error_code: str | None = Field(None, description="Error code if failed")
    started_at: datetime | None = Field(None, description="When integration started")
    completed_at: datetime | None = Field(None, description="When integration completed")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "success",
                "response_data": {"users": [{"id": 1, "name": "John Doe"}]},
                "completed_at": "2024-01-01T00:05:00",
            }
        }
    )


class Integration(IntegrationBase):
    """Schema for integration in API responses."""

    id: int
    client_id: int
    response_data: dict[str, Any] | None = Field(None, description="Normalized response data")
    error_message: str | None
    error_code: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "client_id": 1,
                "status": "success",
                "external_endpoint": "/api/v1/users",
                "request_method": "GET",
                "response_data": {"users": [{"id": 1, "name": "John Doe"}], "count": 1},
                "error_message": None,
                "error_code": None,
                "started_at": "2024-01-01T00:00:00",
                "completed_at": "2024-01-01T00:05:00",
                "created_at": "2024-01-01T00:00:00",
            }
        },
    )


class IntegrationWithClient(Integration):
    """Schema for integration with client details."""

    client_name: str = Field(..., description="Client name")

    model_config = ConfigDict(from_attributes=True)


class IntegrationList(BaseModel):
    """Schema for paginated list of integrations."""

    items: list[Integration]
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
                        "client_id": 1,
                        "status": "success",
                        "external_endpoint": "/api/v1/users",
                        "request_method": "GET",
                        "response_data": {"users": [], "count": 0},
                        "error_message": None,
                        "error_code": None,
                        "started_at": "2024-01-01T00:00:00",
                        "completed_at": "2024-01-01T00:05:00",
                        "created_at": "2024-01-01T00:00:00",
                    }
                ],
                "total": 1,
                "page": 1,
                "page_size": 50,
                "pages": 1,
            }
        }
    )


class IntegrationSync(BaseModel):
    """Schema for triggering an integration sync."""

    endpoint: str | None = Field(None, description="Optional specific endpoint to call")
    method: str = Field(default="GET", description="HTTP method")
    params: dict[str, Any] | None = Field(None, description="Optional query parameters")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "endpoint": "/posts",
                "method": "GET",
                "params": {"userId": 1},
            }
        }
    )


class IntegrationSyncResponse(BaseModel):
    """Schema for integration sync response."""

    integration_id: int
    status: IntegrationStatus
    message: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "integration_id": 1,
                "status": "success",
                "message": "Integration sync completed successfully",
            }
        }
    )
