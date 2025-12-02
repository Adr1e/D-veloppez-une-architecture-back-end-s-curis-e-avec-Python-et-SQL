"""add encrypted columns for client data

Revision ID: 111de9e14d5a
Revises: 4dd0ce4437b3
Create Date: 2025-12-02 13:36:58.160465
"""
from alembic import op
import sqlalchemy as sa

# --- Revision identifiers (required by Alembic) ---
revision = '111de9e14d5a'
down_revision = '4dd0ce4437b3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('clients', schema=None) as batch_op:
        batch_op.add_column(sa.Column('_email_encrypted', sa.String(length=512), nullable=True))
        batch_op.add_column(sa.Column('_full_name_encrypted', sa.String(length=512), nullable=True))
        batch_op.add_column(sa.Column('_phone_encrypted', sa.String(length=512), nullable=True))
        batch_op.drop_column('email')
        batch_op.drop_column('full_name')
        batch_op.drop_column('phone')


def downgrade() -> None:
    with op.batch_alter_table('clients', schema=None) as batch_op:
        batch_op.add_column(sa.Column('phone', sa.VARCHAR(length=32), nullable=True))
        batch_op.add_column(sa.Column('full_name', sa.VARCHAR(length=255), nullable=True))
        batch_op.add_column(sa.Column('email', sa.VARCHAR(length=255), nullable=True))
        batch_op.drop_column('_phone_encrypted')
        batch_op.drop_column('_full_name_encrypted')
        batch_op.drop_column('_email_encrypted')