"""Field-level encryption for sensitive data stored in MongoDB.

Encrypts: client DB URIs, customer phone numbers, customer emails.
Uses Fernet symmetric encryption (AES-128-CBC).

Usage:
    encryptor = FieldEncryptor(settings.encryption_key)
    encrypted = encryptor.encrypt("mongodb+srv://user:pass@cluster...")
    original  = encryptor.decrypt(encrypted)

Generate a key:
    python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
"""

import logging

from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)

# Prefix to identify encrypted values (so we don't double-encrypt)
_ENCRYPTED_PREFIX = "enc::"


class FieldEncryptor:
    """Encrypt/decrypt sensitive string fields using Fernet."""

    def __init__(self, key: str):
        if not key:
            raise ValueError(
                "ENCRYPTION_KEY is required. Generate one with:\n"
                '  python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"'
            )
        self._fernet = Fernet(key.encode() if isinstance(key, str) else key)

    def encrypt(self, value: str) -> str:
        """Encrypt a plaintext string. Returns prefixed encrypted string."""
        if not value:
            return value
        # Don't double-encrypt
        if value.startswith(_ENCRYPTED_PREFIX):
            return value
        encrypted = self._fernet.encrypt(value.encode()).decode()
        return f"{_ENCRYPTED_PREFIX}{encrypted}"

    def decrypt(self, value: str) -> str:
        """Decrypt an encrypted string. Returns plaintext."""
        if not value:
            return value
        # If not encrypted, return as-is (backwards compatible)
        if not value.startswith(_ENCRYPTED_PREFIX):
            return value
        token = value[len(_ENCRYPTED_PREFIX):]
        try:
            return self._fernet.decrypt(token.encode()).decode()
        except InvalidToken:
            logger.error("Failed to decrypt value — wrong ENCRYPTION_KEY or corrupted data")
            raise ValueError("Decryption failed. Check ENCRYPTION_KEY.")

    def is_encrypted(self, value: str) -> bool:
        """Check if a value is already encrypted."""
        return value.startswith(_ENCRYPTED_PREFIX) if value else False


# Singleton — initialized when needed
_encryptor: FieldEncryptor | None = None


def get_encryptor() -> FieldEncryptor:
    """Get the global encryptor instance. Lazy-initialized from settings."""
    global _encryptor
    if _encryptor is None:
        from app.config import settings
        _encryptor = FieldEncryptor(settings.encryption_key)
    return _encryptor


def encrypt_sensitive_fields(data: dict, fields: list[str]) -> dict:
    """Encrypt specific fields in a dict before writing to MongoDB."""
    enc = get_encryptor()
    result = data.copy()
    for field in fields:
        # Support nested fields like "database.connection_uri"
        parts = field.split(".")
        obj = result
        for part in parts[:-1]:
            if part in obj and isinstance(obj[part], dict):
                obj = obj[part]
            else:
                break
        else:
            key = parts[-1]
            if key in obj and isinstance(obj[key], str) and obj[key]:
                obj[key] = enc.encrypt(obj[key])
    return result


def decrypt_sensitive_fields(data: dict, fields: list[str]) -> dict:
    """Decrypt specific fields in a dict after reading from MongoDB."""
    enc = get_encryptor()
    result = data.copy()
    for field in fields:
        parts = field.split(".")
        obj = result
        for part in parts[:-1]:
            if part in obj and isinstance(obj[part], dict):
                obj = obj[part]
            else:
                break
        else:
            key = parts[-1]
            if key in obj and isinstance(obj[key], str) and obj[key]:
                obj[key] = enc.decrypt(obj[key])
    return result
