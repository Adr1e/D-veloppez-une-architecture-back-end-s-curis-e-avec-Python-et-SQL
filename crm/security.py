"""Password hashing and verification utilities."""

from passlib.context import CryptContext

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
