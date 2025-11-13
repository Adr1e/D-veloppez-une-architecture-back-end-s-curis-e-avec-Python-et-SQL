# crm/services/__init__.py
from .user_service import (
    get_user_by_email,
    create_user,
    promote_user_to_role,
    set_password,
    delete_user,
)

__all__ = [
    "get_user_by_email",
    "create_user",
    "promote_user_to_role",
    "set_password",
    "delete_user",
]
