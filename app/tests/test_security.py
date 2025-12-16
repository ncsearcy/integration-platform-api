"""
Tests for security module.
"""

import pytest
from app.api.core.security import (
    SecurityManager,
    EncryptionError,
    encrypt_credentials,
    decrypt_credentials,
    generate_api_key,
)


def test_generate_api_key():
    """Test API key generation."""
    key1 = generate_api_key("pk")
    key2 = generate_api_key("sk")

    # Check format
    assert key1.startswith("pk_")
    assert key2.startswith("sk_")

    # Check uniqueness
    assert key1 != key2

    # Check length (prefix + underscore + hex)
    assert len(key1) > 10


def test_encrypt_decrypt_credentials():
    """Test credential encryption and decryption."""
    original_creds = {
        "api_key": "secret_key_123",
        "api_secret": "secret_value_456",
        "username": "testuser",
    }

    # Encrypt
    encrypted = encrypt_credentials(original_creds)
    assert isinstance(encrypted, str)
    assert len(encrypted) > 0
    assert encrypted != str(original_creds)

    # Decrypt
    decrypted = decrypt_credentials(encrypted)
    assert decrypted == original_creds


def test_encrypt_empty_credentials():
    """Test encrypting empty credentials."""
    empty_creds = {}

    encrypted = encrypt_credentials(empty_creds)
    decrypted = decrypt_credentials(encrypted)

    assert decrypted == empty_creds


def test_decrypt_invalid_token():
    """Test decrypting invalid token raises error."""
    with pytest.raises(EncryptionError):
        decrypt_credentials("invalid_token")


def test_security_manager_singleton():
    """Test that security manager returns same instance."""
    from app.api.core.security import get_security_manager

    manager1 = get_security_manager()
    manager2 = get_security_manager()

    assert manager1 is manager2


def test_generate_fernet_key():
    """Test Fernet key generation."""
    key = SecurityManager.generate_fernet_key()

    assert isinstance(key, str)
    assert len(key) > 0

    # Should be valid base64
    import base64

    try:
        base64.urlsafe_b64decode(key)
    except Exception:
        pytest.fail("Generated key is not valid base64")
