# Roles and permissions seeding utilities.
# This module creates default roles, permissions, and their link entries.

from sqlalchemy.orm import Session
from .models import Role, Permission, RolePermission

# Default roles to create in the system.
DEFAULT_ROLES = [
    ("gestion", "Administrateur"),
    ("commercial", "Ventes"),
    ("support", "Support"),
]

# Default permissions to create in the system.
DEFAULT_PERMS = [
    ("client.read", "List or view clients"),
    ("client.write", "Create or edit clients"),
    ("contract.read", "List or view contracts"),
    ("contract.write", "Create or edit contracts"),
    ("event.read", "List or view events"),
    ("event.write", "Create or edit events"),
    ("user.admin", "Manage accounts and permissions"),
]

# Mapping between each role and the permissions it should have.
# Values are stored as sets for quick membership checking.
ROLE_PERMS = {
    "gestion": {p for p, _ in DEFAULT_PERMS},  # admin receives all permissions
    "commercial": {"client.read", "client.write", "contract.read", "contract.write"},
    "support": {"event.read", "event.write"},
}

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
    code_to_perm = {}

    # Ensure all permissions exist.
    for code, desc in DEFAULT_PERMS:
        perm = db.query(Permission).filter(Permission.code == code).one_or_none()
        if not perm:
            perm = Permission(code=code, description=desc)
            db.add(perm)
            db.flush()  # get perm.id
        code_to_perm[code] = perm

    # Store Role objects by name for later lookup.
    name_to_role = {}

    # Ensure all roles exist.
    for name, desc in DEFAULT_ROLES:
        role = db.query(Role).filter(Role.name == name).one_or_none()
        if not role:
            role = Role(name=name, description=desc)
            db.add(role)
            db.flush()  # get role.id
        name_to_role[name] = role

    # Create role ↔ permission associations.
    for role_name, codes in ROLE_PERMS.items():
        role = name_to_role[role_name]
        for code in codes:
            perm = code_to_perm[code]

            # Avoid duplicate link entries.
            exists = db.query(RolePermission).filter_by(
                role_id=role.id, permission_id=perm.id
            ).one_or_none()

            if not exists:
                db.add(RolePermission(role_id=role.id, permission_id=perm.id))

    # Save all changes to the database.
    db.commit()
