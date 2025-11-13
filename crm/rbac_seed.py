from __future__ import annotations
from sqlalchemy.orm import Session
from .models import Role, Permission, RolePermission

# List of permissions that exist in the system.
# Each entry contains a unique permission code and a human-readable description.
PERMS = [
    ("users.delete", "Delete users"),
    ("clients.read", "Read client data"),
    ("clients.write", "Create or update client data"),
    ("contracts.read", "Read contract data"),
    ("contracts.write", "Create or update contract data"),
    ("events.read", "Read event information"),
    ("events.write", "Create or update event information"),
]

# Each role maps to a list of permission codes.
# This defines what actions each role is allowed to perform.
ROLES = {
    "gestion": ["users.delete", "clients.read", "clients.write", "contracts.read", "contracts.write", "events.read", "events.write"],
    "vente":   ["clients.read", "clients.write", "contracts.read", "contracts.write"],
    "support": ["events.read", "events.write", "clients.read", "contracts.read"],
}


def seed_rbac(db: Session) -> None:
    """
    Populate the database with roles and permissions.

    Notes:
        - Missing permissions are created.
        - Missing roles are also created.
        - Missing role-permission links are created.
        - Existing data is reused and never duplicated.
    """

    # Create or retrieve all permissions, and store them in a map for quick access.
    perm_map = {}
    for code, desc in PERMS:
        p = db.query(Permission).filter(Permission.code == code).one_or_none()
        if not p:
            # Create the permission if it does not exist.
            p = Permission(code=code, description=desc)
            db.add(p)
            db.flush()
        perm_map[code] = p

    # Create roles and assign permissions.
    for role_name, codes in ROLES.items():
        # Find or create the role.
        r = db.query(Role).filter(Role.name == role_name).one_or_none()
        if not r:
            r = Role(name=role_name, description=f"Role {role_name}")
            db.add(r)
            db.flush()

        # Collect existing assignments to avoid duplicates.
        existing = {(rp.role_id, rp.permission_id) for rp in db.query(RolePermission).all()}

        # Assign each permission to the role if missing.
        for code in codes:
            p = perm_map[code]
            if (r.id, p.id) not in existing:
                db.add(RolePermission(role_id=r.id, permission_id=p.id))

    # Save all changes.
    db.commit()
