import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.api.db.session import Base

if TYPE_CHECKING:
    from app.api.models.client import Client


class IntegrationStatus(str, enum.Enum):
    """Status of an integration sync."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"


class Integration(Base):
    """
    Integration model for storing external API sync results.

    Tracks API calls to external services, stores normalized responses,
    and maintains sync status.
    """

    __tablename__ = "integrations"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Foreign key to client
    client_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Integration metadata
    status: Mapped[IntegrationStatus] = mapped_column(
        Enum(IntegrationStatus, native_enum=False, length=20),
        default=IntegrationStatus.PENDING,
        nullable=False,
        index=True,
    )

    # External API details
    external_endpoint: Mapped[str | None] = mapped_column(Text, nullable=True)
    request_method: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Response data (stored as JSON text - normalized)
    response_data: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Error information
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_code: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Timestamps
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    client: Mapped["Client"] = relationship("Client", back_populates="integrations")

    def __repr__(self) -> str:
        return f"<Integration(id={self.id}, client_id={self.client_id}, status={self.status})>"
