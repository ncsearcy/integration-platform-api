from functools import lru_cache

from pydantic import Field
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
        # Don't try to parse strings as JSON for list fields
        env_parse_enums=True,
    )

    # Application Settings
    app_name: str = Field(default="Integration Platform API", description="Application name")
    app_version: str = Field(default="0.1.0", description="Application version")
    environment: str = Field(
        default="development", description="Environment (development, staging, production)"
    )
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
    external_api_max_retries: int = Field(
        default=3, description="Max retries for external API calls"
    )

    # CORS Settings (stored as strings, parsed to lists)
    cors_origins: str = Field(
        default="http://localhost:3000,http://localhost:8000",
        description="Allowed CORS origins (comma-separated)",
    )
    cors_credentials: bool = Field(default=True, description="Allow credentials in CORS")
    cors_methods: str = Field(default="*", description="Allowed CORS methods (comma-separated)")
    cors_headers: str = Field(default="*", description="Allowed CORS headers (comma-separated)")

    # Rate Limiting
    rate_limit_per_minute: int = Field(default=60, description="Rate limit per minute per client")

    # Monitoring
    enable_metrics: bool = Field(default=True, description="Enable metrics collection")
    metrics_port: int = Field(default=9090, description="Metrics server port")

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS origins as a list."""
        if not self.cors_origins:
            return []
        if "," in self.cors_origins:
            return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]
        return [self.cors_origins.strip()] if self.cors_origins.strip() else []

    @property
    def cors_methods_list(self) -> list[str]:
        """Parse CORS methods as a list."""
        if not self.cors_methods:
            return []
        if self.cors_methods.strip() == "*":
            return ["*"]
        if "," in self.cors_methods:
            return [method.strip() for method in self.cors_methods.split(",") if method.strip()]
        return [self.cors_methods.strip()] if self.cors_methods.strip() else []

    @property
    def cors_headers_list(self) -> list[str]:
        """Parse CORS headers as a list."""
        if not self.cors_headers:
            return []
        if self.cors_headers.strip() == "*":
            return ["*"]
        if "," in self.cors_headers:
            return [header.strip() for header in self.cors_headers.split(",") if header.strip()]
        return [self.cors_headers.strip()] if self.cors_headers.strip() else []

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


@lru_cache
def get_settings() -> Settings:
    """
    Get cached settings instance.
    Uses lru_cache to ensure settings are loaded only once.
    """
    return Settings()


# Global settings instance
settings = get_settings()
