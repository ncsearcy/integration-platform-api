from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.api.db.session import Base

if TYPE_CHECKING:
    from app.api.models.integration import Integration


class Client(Base):
    """
    Client model for storing external client information.

    Stores client registration data and encrypted credentials for
    accessing external APIs.
    """

    __tablename__ = "clients"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Client information
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # API credentials
    api_key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)

    # Encrypted credentials (stored as encrypted JSON)
    encrypted_credentials: Mapped[str | None] = mapped_column(Text, nullable=True)

    # External API configuration
    external_api_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    external_api_timeout: Mapped[int] = mapped_column(Integer, default=30, nullable=False)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    integrations: Mapped[list["Integration"]] = relationship(
        "Integration", back_populates="client", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Client(id={self.id}, name='{self.name}', is_active={self.is_active})>"
