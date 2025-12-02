"""add company to encrypted columns

Revision ID: 4cd1e98ae925
Revises: 111de9e14d5a
Create Date: 2025-12-02 13:58:37.314386
"""
from alembic import op
import sqlalchemy as sa

# --- Revision identifiers (required by Alembic) ---
revision = '4cd1e98ae925'
down_revision = '111de9e14d5a'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('clients', schema=None) as batch_op:
        batch_op.add_column(sa.Column('_company_encrypted', sa.String(length=512), nullable=True))
        batch_op.drop_column('company')


def downgrade() -> None:
    with op.batch_alter_table('clients', schema=None) as batch_op:
        batch_op.add_column(sa.Column('company', sa.VARCHAR(length=255), nullable=True))
        batch_op.drop_column('_company_encrypted')