"""
EPIC Events CRM Package.

A secure CRM backend for managing clients, contracts, and events
with role-based access control (RBAC).
"""

__version__ = "1.0.0"
__author__ = "Epic Events"

# Main entry points
from .auth import authenticate, login_cli, logout, get_current_principal
from .db import get_db
from .principal import Principal

__all__ = [
    "authenticate",
    "login_cli", 
    "logout",
    "get_current_principal",
    "get_db",
    "Principal",
]