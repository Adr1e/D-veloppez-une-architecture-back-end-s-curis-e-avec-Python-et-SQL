"""SQLAlchemy ORM models.

Design goals:
- Keep model definitions minimal & explicit.
- Name foreign keys clearly and set reasonable ondelete behaviors.
- RBAC (roles/permissions/departments) is normalized (no hard-coded roles).
"""
from __future__ import annotations

from sqlalchemy import (
    Column,
    Integer,
    String,
    Numeric,
    DateTime,
    Text,
    ForeignKey,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import declarative_base, relationship

# Base class used by all ORM models.
Base = declarative_base()


# Business entities: users, clients, contracts, events.
class User(Base):
    """Application user stored in the database."""

    __tablename__ = "users"

    # Primary key.
    id = Column(Integer, primary_key=True)

    # Basic identity fields.
    email = Column(String(255), nullable=False, unique=True)
    full_name = Column(String(255))

    # Hashed password (never store plain text).
    password_hash = Column(String(255), nullable=False)

    # Organizational information.
    employee_number = Column(String(32), unique=True)
    role_id = Column(Integer, ForeignKey("roles.id", ondelete="SET NULL"))
    department_id = Column(
        Integer, ForeignKey("departments.id", ondelete="SET NULL")
    )

    # Link to role and department for RBAC.
    role = relationship("Role", back_populates="users", lazy="joined")
    department = relationship("Department", back_populates="users", lazy="joined")

    # Clients managed by this user as sales contact.
    sales_clients = relationship(
        "Client",
        back_populates="sales_contact",
        foreign_keys="Client.sales_contact_id",
        lazy="selectin",
    )

    # Contracts created or followed by this user.
    sales_contracts = relationship(
        "Contract",
        back_populates="sales_contact",
        foreign_keys="Contract.sales_contact_id",
        lazy="selectin",
    )

    # Events where this user is the support contact.
    support_events = relationship(
        "Event",
        back_populates="support_contact",
        foreign_keys="Event.support_contact_id",
        lazy="selectin",
    )


class Client(Base):
    """Client of the company."""

    __tablename__ = "clients"

    # Primary key.
    id = Column(Integer, primary_key=True)

    # Contact and company information.
    email = Column(String(255), unique=True)
    full_name = Column(String(255))
    company = Column(String(255))
    phone = Column(String(32))

    # Sales person responsible for this client.
    sales_contact_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))

    # Creation and update timestamps.
    created_at = Column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),  # Automatically updates on row change.
    )

    # Link back to the sales contact.
    sales_contact = relationship(
        "User",
        back_populates="sales_clients",
        foreign_keys=[sales_contact_id],
        lazy="joined",
    )

    # All contracts related to this client.
    contracts = relationship(
        "Contract",
        back_populates="client",
        lazy="selectin",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class Contract(Base):
    """Contract signed or proposed for a client."""

    __tablename__ = "contracts"

    # Primary key.
    id = Column(Integer, primary_key=True)

    # Link to client and sales contact.
    client_id = Column(
        Integer, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False
    )
    sales_contact_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))

    # Financial information.
    total_amount = Column(Numeric(10, 2), nullable=False)
    amount_due = Column(Numeric(10, 2), nullable=False)

    # Contract lifecycle status.
    status = Column(
        String(32), nullable=False
    )  # Example: "pending", "signed", "canceled".
    signed_at = Column(DateTime, nullable=True)

    # Creation and update timestamps.
    created_at = Column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),  # Automatically updates on row change.
    )

    # Link back to client and sales contact.
    client = relationship("Client", back_populates="contracts", lazy="joined")
    sales_contact = relationship(
        "User", back_populates="sales_contracts", lazy="joined"
    )

    # Events that belong to this contract.
    events = relationship(
        "Event",
        back_populates="contract",
        lazy="selectin",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class Event(Base):
    """Event scheduled for a contract (for example a support session)."""

    __tablename__ = "events"

    # Primary key.
    id = Column(Integer, primary_key=True)

    # Link to contract and support contact.
    contract_id = Column(
        Integer, ForeignKey("contracts.id", ondelete="CASCADE"), nullable=False
    )
    support_contact_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))

    # Event details.
    event_date = Column(DateTime)
    location = Column(String(255))
    attendees = Column(Integer)
    notes = Column(Text)

    # Creation and update timestamps.
    created_at = Column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),  # Automatically updates on row change.
    )

    # Relations to contract and support user.
    contract = relationship("Contract", back_populates="events", lazy="joined")
    support_contact = relationship(
        "User", back_populates="support_events", lazy="joined"
    )


# RBAC entities: departments, roles, permissions.
class Department(Base):
    """Department in the company (for example sales or support)."""

    __tablename__ = "departments"

    # Primary key.
    id = Column(Integer, primary_key=True)

    # Unique department name.
    name = Column(String(128), nullable=False, unique=True)

    # Users that belong to this department.
    users = relationship("User", back_populates="department", lazy="selectin")


class Role(Base):
    """Role used for RBAC (for example 'gestion', 'support')."""

    __tablename__ = "roles"

    # Primary key.
    id = Column(Integer, primary_key=True)

    # Role code and description.
    name = Column(String(64), nullable=False, unique=True)
    description = Column(String(255))

    # Users that have this role.
    users = relationship("User", back_populates="role", lazy="selectin")

    # Permissions attached to this role.
    permissions = relationship(
        "Permission",
        secondary="role_permissions",
        back_populates="roles",
        lazy="selectin",
    )


class Permission(Base):
    """Permission code used by RBAC checks."""

    __tablename__ = "permissions"

    # Primary key.
    id = Column(Integer, primary_key=True)

    # Unique permission code and description.
    code = Column(String(128), nullable=False, unique=True)
    description = Column(String(255))

    # Roles that include this permission.
    roles = relationship(
        "Role",
        secondary="role_permissions",
        back_populates="permissions",
        lazy="selectin",
    )


class RolePermission(Base):
    """Association table between roles and permissions."""

    __tablename__ = "role_permissions"

    # Composite primary key: one row per (role, permission) pair.
    role_id = Column(
        Integer, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True
    )
    permission_id = Column(
        Integer, ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True
    )

    # Enforce uniqueness at the database level.
    __table_args__ = (UniqueConstraint("role_id", "permission_id"),)
