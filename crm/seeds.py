"""
Roles and permissions seeding utilities.

This module creates default roles, permissions, and their link entries.
It unifies all RBAC configuration in a single place to avoid inconsistencies.
"""

from sqlalchemy.orm import Session
from .models import Role, Permission, RolePermission


# =============================================================================
# DEFAULT ROLES
# =============================================================================
# Each role corresponds to a department in Epic Events.

DEFAULT_ROLES = [
    ("gestion", "Équipe de gestion (administrateurs)"),
    ("commercial", "Équipe commerciale (ventes)"),
    ("support", "Équipe support (organisation événements)"),
]


# =============================================================================
# DEFAULT PERMISSIONS
# =============================================================================
# Unified permission codes using singular nouns (client, contract, event, user).

DEFAULT_PERMISSIONS = [
    # Client permissions
    ("client.read", "Lire les informations des clients"),
    ("client.write", "Créer ou modifier des clients"),
    
    # Contract permissions
    ("contract.read", "Lire les informations des contrats"),
    ("contract.write", "Créer ou modifier des contrats"),
    
    # Event permissions
    ("event.read", "Lire les informations des événements"),
    ("event.write", "Créer ou modifier des événements"),
    
    # User/admin permissions
    ("user.read", "Lire la liste des collaborateurs"),
    ("user.write", "Créer ou modifier des collaborateurs"),
    ("user.delete", "Supprimer des collaborateurs"),
]


# =============================================================================
# ROLE-PERMISSION MAPPING
# =============================================================================
# Based on the specification (cahier des charges):
#
# GESTION (admin):
#   - CRUD on collaborators (users)
#   - Create and modify ALL contracts
#   - Filter and modify events (to assign support contact)
#   - Read access to everything
#
# COMMERCIAL (sales):
#   - Create clients (auto-assigned to them)
#   - Update THEIR OWN clients
#   - Update contracts of THEIR OWN clients
#   - Filter contracts (unsigned, unpaid)
#   - Create events for clients who signed a contract
#   - Read access to everything
#
# SUPPORT:
#   - Filter events (assigned to them)
#   - Update THEIR OWN events
#   - Read access to everything

ROLE_PERMISSIONS = {
    "gestion": {
        "client.read",
        "client.write",
        "contract.read",
        "contract.write",
        "event.read",
        "event.write",
        "user.read",
        "user.write",
        "user.delete",
    },
    "commercial": {
        "client.read",
        "client.write",      # With ownership check in service layer
        "contract.read",
        "contract.write",    # With ownership check in service layer
        "event.read",
        "event.write",       # Only create, with signed contract check
    },
    "support": {
        "client.read",
        "contract.read",
        "event.read",
        "event.write",       # With ownership check in service layer
    },
}


# =============================================================================
# SEEDING FUNCTION
# =============================================================================

def seed_rbac(db: Session) -> None:
    """
    Populate the database with default roles, permissions, and associations.

    This function:
    - Ensures all default permissions exist.
    - Ensures all default roles exist.
    - Links each role with the correct permissions.
    - Commits all changes.

    Args:
        db: SQLAlchemy session used for database operations.
    """
    # Store Permission objects by code for later lookup.
    code_to_perm: dict = {}

    # Ensure all permissions exist.
    for code, description in DEFAULT_PERMISSIONS:
        perm = db.query(Permission).filter(Permission.code == code).one_or_none()
        if perm is None:
            perm = Permission(code=code, description=description)
            db.add(perm)
            db.flush()  # Get perm.id immediately
        else:
            # Update description if it changed
            if perm.description != description:
                perm.description = description
        code_to_perm[code] = perm

    # Store Role objects by name for later lookup.
    name_to_role: dict = {}

    # Ensure all roles exist.
    for name, description in DEFAULT_ROLES:
        role = db.query(Role).filter(Role.name == name).one_or_none()
        if role is None:
            role = Role(name=name, description=description)
            db.add(role)
            db.flush()  # Get role.id immediately
        else:
            # Update description if it changed
            if role.description != description:
                role.description = description
        name_to_role[name] = role

    # Create role-permission associations.
    for role_name, permission_codes in ROLE_PERMISSIONS.items():
        role = name_to_role[role_name]
        
        for code in permission_codes:
            perm = code_to_perm[code]

            # Avoid duplicate entries
            exists = (
                db.query(RolePermission)
                .filter_by(role_id=role.id, permission_id=perm.id)
                .one_or_none()
            )

            if exists is None:
                db.add(RolePermission(role_id=role.id, permission_id=perm.id))

    # Save all changes to the database.
    db.commit()