from functools import lru_cache
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    Uses pydantic-settings for validation and type conversion.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application Settings
    app_name: str = Field(default="Integration Platform API", description="Application name")
    app_version: str = Field(default="0.1.0", description="Application version")
    environment: str = Field(default="development", description="Environment (development, staging, production)")
    debug: bool = Field(default=False, description="Debug mode")
    log_level: str = Field(default="INFO", description="Logging level")

    # Server Configuration
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, description="Server port")
    reload: bool = Field(default=False, description="Auto-reload on code changes")

    # Database Configuration
    database_url: str = Field(
        default="postgresql://postgres:postgres@localhost:5432/integration_platform",
        description="PostgreSQL database URL",
    )
    database_pool_size: int = Field(default=5, description="Database connection pool size")
    database_max_overflow: int = Field(default=10, description="Max overflow connections")

    # Security
    secret_key: str = Field(
        default="dev-secret-key-change-in-production-min-32-characters",
        min_length=32,
        description="Secret key for signing tokens",
    )
    encryption_key: str = Field(
        default="dev-encryption-key-change-in-prod",
        description="Encryption key for Fernet cipher (must be URL-safe base64-encoded 32-byte key)",
    )
    api_key_length: int = Field(default=32, description="Length of generated API keys")

    # External API Configuration
    external_api_url: str = Field(
        default="https://jsonplaceholder.typicode.com",
        description="Base URL for external API",
    )
    external_api_timeout: int = Field(default=30, description="External API timeout in seconds")
    external_api_max_retries: int = Field(default=3, description="Max retries for external API calls")

    # CORS Settings
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        description="Allowed CORS origins",
    )
    cors_credentials: bool = Field(default=True, description="Allow credentials in CORS")
    cors_methods: List[str] = Field(default=["*"], description="Allowed CORS methods")
    cors_headers: List[str] = Field(default=["*"], description="Allowed CORS headers")

    # Rate Limiting
    rate_limit_per_minute: int = Field(default=60, description="Rate limit per minute per client")

    # Monitoring
    enable_metrics: bool = Field(default=True, description="Enable metrics collection")
    metrics_port: int = Field(default=9090, description="Metrics server port")

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse CORS origins from comma-separated string or list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    @field_validator("cors_methods", mode="before")
    @classmethod
    def parse_cors_methods(cls, v):
        """Parse CORS methods from comma-separated string or list."""
        if isinstance(v, str):
            return [method.strip() for method in v.split(",")]
        return v

    @field_validator("cors_headers", mode="before")
    @classmethod
    def parse_cors_headers(cls, v):
        """Parse CORS headers from comma-separated string or list."""
        if isinstance(v, str):
            return [header.strip() for header in v.split(",")]
        return v

    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.environment.lower() == "development"

    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.environment.lower() == "production"

    @property
    def database_url_sync(self) -> str:
        """Get synchronous database URL (for SQLAlchemy)."""
        return self.database_url

    @property
    def database_url_async(self) -> str:
        """Get asynchronous database URL (for async SQLAlchemy)."""
        return self.database_url.replace("postgresql://", "postgresql+asyncpg://")


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    Uses lru_cache to ensure settings are loaded only once.
    """
    return Settings()


# Global settings instance
settings = get_settings()
