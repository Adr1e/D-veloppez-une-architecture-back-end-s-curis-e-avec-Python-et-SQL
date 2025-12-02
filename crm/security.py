"""Password hashing, verification and data encryption utilities."""

from __future__ import annotations

import os

# Suppress the bcrypt version warning from passlib
# This occurs with bcrypt >= 4.1 where __about__ was removed
import logging
logging.getLogger("passlib.handlers.bcrypt").setLevel(logging.ERROR)

import warnings
warnings.filterwarnings("ignore", message=".*trapped.*error reading bcrypt version.*")

from passlib.context import CryptContext
from cryptography.fernet import Fernet


# =============================================================================
# PASSWORD HASHING (bcrypt)
# =============================================================================

# Password hashing context configured to use bcrypt.
_pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    """
    Hash a plain text password using bcrypt.

    Args:
        plain: The password provided by the user.

    Returns:
        A bcrypt hashed version of the password.
    """
    return _pwd_ctx.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """
    Check if a plain text password matches a stored hashed password.

    Args:
        plain: The password provided by the user.
        hashed: The stored bcrypt hash.

    Returns:
        True if the password is correct, False otherwise.
    """
    return _pwd_ctx.verify(plain, hashed)


# =============================================================================
# DATA ENCRYPTION (Fernet/AES)
# =============================================================================

# Encryption key (must be set via environment variable in production)
ENCRYPTION_KEY = os.environ.get("EPICEVENTS_ENCRYPTION_KEY")

if not ENCRYPTION_KEY:
    # Auto-generate key for development only
    ENCRYPTION_KEY = Fernet.generate_key().decode()
    print("[WARNING] Clé de chiffrement auto-générée. "
          "Définissez EPICEVENTS_ENCRYPTION_KEY en production.")

_fernet = Fernet(ENCRYPTION_KEY.encode())


def encrypt(data: str) -> str:
    """
    Encrypt a string using Fernet (AES-128).

    Args:
        data: The plain text data to encrypt.

    Returns:
        The encrypted data as a base64 string.
    """
    if not data:
        return data
    return _fernet.encrypt(data.encode()).decode()


def decrypt(data: str) -> str:
    """
    Decrypt a string using Fernet (AES-128).

    Args:
        data: The encrypted data.

    Returns:
        The decrypted plain text.
    """
    if not data:
        return data
    return _fernet.decrypt(data.encode()).decode()


def generate_encryption_key() -> str:
    """
    Generate a new Fernet encryption key.

    Returns:
        A valid Fernet key as a string.
    """
    return Fernet.generate_key().decode()


# =============================================================================
# ENCRYPTED FIELD DECORATOR
# =============================================================================

class EncryptedString:
    """
    Descriptor decorator for automatic field encryption/decryption.

    Usage in models:
        _email_encrypted = Column(String(512))
        email = EncryptedString("email")
    """

    def __init__(self, column_name: str):
        """
        Initialize the descriptor.

        Args:
            column_name: The base name of the field (without _encrypted suffix).
        """
        self.column_name = f"_{column_name}_encrypted"

    def __set_name__(self, owner, name):
        self.public_name = name

    def __get__(self, obj, objtype=None):
        """Decrypt and return the field value."""
        if obj is None:
            return self
        encrypted_value = getattr(obj, self.column_name, None)
        return decrypt(encrypted_value) if encrypted_value else None

    def __set__(self, obj, value):
        """Encrypt and store the field value."""
        encrypted_value = encrypt(value) if value else None
        setattr(obj, self.column_name, encrypted_value)