# Import standard and external modules
import secrets
import typer
from sqlalchemy.orm import Session

# Import internal modules
from .db import get_db
from .models import User, Role
from .services.user_service import delete_user
from .security import hash_password
from .seeds import seed_rbac
from .auth import login_cli, logout, get_current_principal

# Create the main Typer application
app = typer.Typer(help="EPIC CRM CLI")

# Create a sub-application for user-related commands
users_app = typer.Typer(help="Users commands")


@users_app.command("create")
def users_create(
    email: str,
    full_name: str = typer.Option("", "--full-name"),
    password: str = typer.Option(
        None, "--password", help="Plain password (will be hashed)"
    ),
    employee_number: str = typer.Option(None, "--employee-number"),
):
    """
    Create a basic user account.

    Notes:
        - The user has no role by default.
        - If no password is provided, a random one is generated.
        - The password is always stored hashed.
    """
    with get_db() as db:  # type: Session
        existing = db.query(User).filter(User.email == email).one_or_none()

        # If the user already exists, do nothing.
        if existing:
            typer.echo(f"Already exists: {email}")
            raise typer.Exit(0)

        show_pw = False
        if not password:
            # Generate a random password when not provided
            password = secrets.token_urlsafe(12)
            show_pw = True

        # Create a new user object
        user = User(
            email=email,
            full_name=full_name or None,
            password_hash=hash_password(password),
            employee_number=employee_number or None,
        )

        db.add(user)
        db.commit()

        # Show the generated password only when auto-created
        if show_pw:
            typer.echo(f"Created: {email} (generated password: {password})")
        else:
            typer.echo(f"Created: {email}")


@users_app.command("seed-admin")
def users_seed_admin(
    email: str = "admin@epic.local",
    full_name: str = "Admin",
    password: str = typer.Option(None, "--password"),
):
    """
    Create or ensure the main admin user.

    Notes:
        - The admin role is 'gestion'.
        - Creates the role if it does not exist.
        - Assigns the role to the admin user.
        - Generates a password if none is provided.
    """
    with get_db() as db:  # type: Session
        # Ensure the admin role exists
        role = db.query(Role).filter(Role.name == "gestion").one_or_none()
        if not role:
            role = Role(name="gestion", description="Administrator")
            db.add(role)
            db.flush()

        # Look for the admin account
        user = db.query(User).filter(User.email == email).one_or_none()

        if not user:
            show_pw = False
            if not password:
                # Generate a secure password if not provided
                password = secrets.token_urlsafe(12)
                show_pw = True

            # Create the admin user
            user = User(
                email=email,
                full_name=full_name,
                password_hash=hash_password(password),
                employee_number="A-000",
                role_id=role.id,
            )
            db.add(user)
            db.commit()

            # Inform about the generated password
            if show_pw:
                typer.echo(f"Admin created: {email} (password: {password})")
            else:
                typer.echo(f"Admin created: {email}")

        else:
            # Ensure the user has the admin role
            if user.role_id != role.id:
                user.role_id = role.id
                db.commit()
                typer.echo(f"Admin updated: {email}")
            else:
                typer.echo(f"Admin already exists: {email}")


@users_app.command("promote")
def users_promote(email: str, role_name: str = "gestion"):
    """
    Assign a role to a user.

    Notes:
        - Creates the role if missing.
        - Updates the user's role_id field.
    """
    with get_db() as db:  # type: Session
        user = db.query(User).filter(User.email == email).one_or_none()

        # The user must exist
        if not user:
            typer.echo(f"User not found: {email}")
            raise typer.Exit(code=1)

        # Ensure the target role exists
        role = db.query(Role).filter(Role.name == role_name).one_or_none()
        if not role:
            role = Role(name=role_name, description=f"Role {role_name}")
            db.add(role)
            db.flush()

        # Assign the role
        user.role_id = role.id
        db.commit()
        typer.echo(f"{email} promoted to {role_name}")


@users_app.command("delete")
def users_delete(
    email: str = typer.Option(..., "--email", help="Email to delete"),
):
    """
    Delete a user.

    Notes:
        - Only authenticated users with the right permissions/role
          (checked in the service layer) can delete users.
        - The acting user is retrieved from the persisted JWT token.
    """
    # Get the currently authenticated principal from JWT
    principal = get_current_principal()

    with get_db() as db:
        ok = delete_user(db, principal=principal, email=email)

        # Show the deletion result
        if ok:
            typer.echo(f"Deleted {email}")
        else:
            typer.echo(f"User not found: {email}")


@app.command("rbac-seed")
def rbac_seed_cmd():
    """
    Populate the database with default roles and permissions.

    Notes:
        - Uses the seed_rbac() helper.
        - Creates missing roles, permissions, and links.
    """
    with get_db() as db:
        seed_rbac(db)
        typer.echo("RBAC seed: OK")


@app.command("login")
def login_cmd():
    """
    Authenticate a user and store a JWT token locally.

    Example:
        epic-crm login
    """
    login_cli()


@app.command("logout")
def logout_cmd():
    """
    Remove the stored JWT token (logout).

    Example:
        epic-crm logout
    """
    logout()
    typer.echo("Logged out")


# Attach the users sub-command group to the main CLI application
app.add_typer(users_app, name="users")


def main():
    """Entry point for command-line usage."""
    app()


# Run the CLI when executed directly
if __name__ == "__main__":
    main()
