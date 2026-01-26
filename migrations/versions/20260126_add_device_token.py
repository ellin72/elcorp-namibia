"""
Migration: Add DeviceToken table for multi-device logout support
"""

from alembic import op
import sqlalchemy as sa


def upgrade():
    """Create device_token table."""
    op.create_table(
        'device_token',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('device_id', sa.String(100), nullable=False),
        sa.Column('refresh_token', sa.Text(), nullable=False),
        sa.Column('user_agent', sa.String(500), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('last_used', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for performance
    op.create_index(op.f('ix_device_token_user_id'), 'device_token', ['user_id'], unique=False)
    op.create_index(op.f('ix_device_token_device_id'), 'device_token', ['device_id'], unique=False)
    op.create_index(op.f('ix_device_token_expires_at'), 'device_token', ['expires_at'], unique=False)


def downgrade():
    """Drop device_token table."""
    op.drop_table('device_token')
