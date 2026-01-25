"""Add index for audit_log action+timestamp

Revision ID: 20260125_add_audit_index
Revises: 1b3e74abc778
Create Date: 2026-01-25
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260125_add_audit_index"
down_revision = "1b3e74abc778"
branch_labels = None
depends_on = None


def upgrade():
    op.create_index('ix_audit_log_action_timestamp', 'audit_log', ['action', 'timestamp'])


def downgrade():
    op.drop_index('ix_audit_log_action_timestamp', table_name='audit_log')