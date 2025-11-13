# EPIC Events CRM – Backend (SQLAlchemy + Typer CLI)

A secure backend architecture built with **Python**, **SQLAlchemy**, **Alembic**, and **Typer CLI**.  
This project provides a complete user/role/permission system (RBAC), contract & event tracking, and CLI tools to manage the system.

---

##  Features

- SQLAlchemy ORM models (Users, Clients, Contracts, Events, Roles, Permissions…)
- Alembic migrations
- Password hashing with bcrypt (Passlib)
- Full RBAC system (roles + permissions)
- Admin tools via Typer CLI
- Secure user creation, promotion, deletion
- Automatic timestamp updates

---

##  Installation

Clone the project:

```bash
git clone https://github.com/USERNAME/REPO.git
cd REPO
```

Create and activate a virtual environment:

```bash
python3 -m venv env
source env/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

---

##  Database setup

Run Alembic migrations:

```bash
alembic upgrade head
```

Check the schema if needed:

```bash
python - <<'PY'
from crm.models import Base
print([t.name for t in Base.metadata.sorted_tables])
PY
```

---

##  RBAC Seeding

Populate roles + permissions:

```bash
python -m crm.cli rbac-seed
```

---

##  User Management (CLI)

### Create a basic user

```bash
python -m crm.cli users create bob@epic.local --full-name "Bob"
```

### Promote a user to a role

```bash
python -m crm.cli users promote bob@epic.local --role-name support
```

### Create an admin (auto-promoted to role “gestion”)

```bash
python -m crm.cli users seed-admin
```

### Delete a user (admin required)

```bash
python -m crm.cli users delete --email bob@epic.local --as-email admin@epic.local
```

---

## Password hashing

Passwords are hashed using **bcrypt** via Passlib:

- `hash_password()` → hash a plaintext password
- `verify_password()` → verify a password

---

## Project structure

```
crm/
 ├── auth.py
 ├── cli.py
 ├── config.py
 ├── db.py
 ├── models.py
 ├── principal.py
 ├── rbac_seed.py
 ├── repositories/
 │     └── user_repo.py
 ├── security.py
 ├── seeds.py
 └── services/
       └── user_service.py

alembic/
 ├── env.py
 └── versions/
```

---

##  Example workflow

This creates Bob → promotes him → deletes him while authenticated as admin.

```bash
python -m crm.cli users seed-admin
python -m crm.cli users create bob@epic.local --full-name "Bob"
python -m crm.cli users promote bob@epic.local --role-name gestion
python -m crm.cli users delete --email bob@epic.local --as-email admin@epic.local
```

---

## Git commands to push your project

```bash
git add .
git commit -m "Complete backend with RBAC + CLI + documentation"
git branch -M main
git remote add origin https://github.com/USERNAME/REPO.git
git push -u origin main
```

---

##  License

MIT License – free to use, modify, and distribute.

password for admin : YxfdEx9ccTsAWF_B new_admin@epic.local
password for testuser : 9YaqJ6nwxcO0Xg06 test@test.com