import json
import secrets
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

from app.api.core.config import settings
from app.api.core.logging import get_logger

logger = get_logger(__name__)


class EncryptionError(Exception):
    """Raised when encryption/decryption fails."""

    pass


class SecurityManager:
    """
    Manages encryption/decryption of sensitive data and API key generation.

    Uses Fernet symmetric encryption for storing credentials securely.
    """

    def __init__(self):
        """Initialize the security manager with encryption key."""
        try:
            # Generate a proper Fernet key if the default is being used
            if settings.encryption_key.startswith("your-encryption-key"):
                logger.warning(
                    "using_default_encryption_key",
                    message="Default encryption key detected. Generate a proper key for production!",
                )
                # Generate a temporary key for development
                self._fernet_key = Fernet.generate_key()
            else:
                # Use the configured key (must be URL-safe base64-encoded 32 bytes)
                self._fernet_key = settings.encryption_key.encode()

            self._fernet = Fernet(self._fernet_key)
            logger.info("security_manager_initialized")

        except Exception as e:
            logger.error("security_manager_init_failed", error=str(e), exc_info=True)
            raise EncryptionError(f"Failed to initialize security manager: {e}") from e

    def generate_api_key(self, prefix: str = "pk") -> str:
        """
        Generate a secure API key.

        Args:
            prefix: Prefix for the API key (default: "pk" for "public key")

        Returns:
            str: Generated API key in format "{prefix}_{random_hex}"

        Example:
            >>> security.generate_api_key("pk")
            'pk_a1b2c3d4e5f6...'
        """
        random_bytes = secrets.token_hex(settings.api_key_length // 2)
        api_key = f"{prefix}_{random_bytes}"

        logger.info("api_key_generated", prefix=prefix, length=len(api_key))
        return api_key

    def encrypt_credentials(self, credentials: dict[str, Any]) -> str:
        """
        Encrypt credentials dictionary.

        Args:
            credentials: Dictionary containing sensitive credentials

        Returns:
            str: Encrypted credentials as a string

        Raises:
            EncryptionError: If encryption fails

        Example:
            >>> creds = {"api_key": "secret123", "api_secret": "secret456"}
            >>> encrypted = security.encrypt_credentials(creds)
        """
        try:
            # Convert credentials to JSON string
            credentials_json = json.dumps(credentials)

            # Encrypt the JSON string
            encrypted_bytes = self._fernet.encrypt(credentials_json.encode())

            # Return as string (base64 encoded)
            encrypted_str = encrypted_bytes.decode()

            logger.info(
                "credentials_encrypted",
                num_fields=len(credentials),
                encrypted_length=len(encrypted_str),
            )

            return encrypted_str

        except Exception as e:
            logger.error("encryption_failed", error=str(e), exc_info=True)
            raise EncryptionError(f"Failed to encrypt credentials: {e}") from e

    def decrypt_credentials(self, encrypted_credentials: str) -> dict[str, Any]:
        """
        Decrypt credentials string.

        Args:
            encrypted_credentials: Encrypted credentials string

        Returns:
            Dict[str, Any]: Decrypted credentials dictionary

        Raises:
            EncryptionError: If decryption fails or credentials are invalid

        Example:
            >>> encrypted = "gAAAAAB..."
            >>> creds = security.decrypt_credentials(encrypted)
            >>> print(creds["api_key"])
        """
        try:
            # Decrypt the string
            decrypted_bytes = self._fernet.decrypt(encrypted_credentials.encode())

            # Convert back to JSON
            credentials_json = decrypted_bytes.decode()

            # Parse JSON to dictionary
            credentials = json.loads(credentials_json)

            logger.debug(
                "credentials_decrypted",
                num_fields=len(credentials),
            )

            return credentials

        except InvalidToken:
            logger.error("decryption_failed_invalid_token")
            raise EncryptionError(
                "Invalid encryption token - credentials may be corrupted"
            ) from None
        except json.JSONDecodeError as e:
            logger.error("decryption_failed_invalid_json", error=str(e))
            raise EncryptionError("Decrypted data is not valid JSON") from e
        except Exception as e:
            logger.error("decryption_failed", error=str(e), exc_info=True)
            raise EncryptionError(f"Failed to decrypt credentials: {e}") from e

    def rotate_encryption_key(self, old_key: bytes, new_key: bytes, encrypted_data: str) -> str:
        """
        Rotate encryption key by re-encrypting data with new key.

        Args:
            old_key: Old Fernet key
            new_key: New Fernet key
            encrypted_data: Data encrypted with old key

        Returns:
            str: Data re-encrypted with new key

        Raises:
            EncryptionError: If key rotation fails
        """
        try:
            # Decrypt with old key
            old_fernet = Fernet(old_key)
            decrypted_bytes = old_fernet.decrypt(encrypted_data.encode())

            # Encrypt with new key
            new_fernet = Fernet(new_key)
            encrypted_bytes = new_fernet.encrypt(decrypted_bytes)

            logger.info("encryption_key_rotated")
            return encrypted_bytes.decode()

        except Exception as e:
            logger.error("key_rotation_failed", error=str(e), exc_info=True)
            raise EncryptionError(f"Failed to rotate encryption key: {e}") from e

    @staticmethod
    def generate_fernet_key() -> str:
        """
        Generate a new Fernet encryption key.

        Returns:
            str: URL-safe base64-encoded 32-byte key

        Example:
            >>> key = SecurityManager.generate_fernet_key()
            >>> print(key)  # Use this in your .env file as ENCRYPTION_KEY
        """
        key = Fernet.generate_key()
        return key.decode()


# Global security manager instance
_security_manager: SecurityManager | None = None


def get_security_manager() -> SecurityManager:
    """
    Get the global security manager instance.

    Returns:
        SecurityManager: Singleton security manager instance
    """
    global _security_manager

    if _security_manager is None:
        _security_manager = SecurityManager()

    return _security_manager


# Convenience functions
def encrypt_credentials(credentials: dict[str, Any]) -> str:
    """Encrypt credentials using the global security manager."""
    return get_security_manager().encrypt_credentials(credentials)


def decrypt_credentials(encrypted_credentials: str) -> dict[str, Any]:
    """Decrypt credentials using the global security manager."""
    return get_security_manager().decrypt_credentials(encrypted_credentials)


def generate_api_key(prefix: str = "pk") -> str:
    """Generate an API key using the global security manager."""
    return get_security_manager().generate_api_key(prefix)
