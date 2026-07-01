"""add wallet_topup_payments table

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-06-04
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = 'c3d4e5f6a7b8'
down_revision = 'b2c3d4e5f6a7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'wallet_topup_payments',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('driver_id', UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('amount', sa.Integer(), nullable=False),
        sa.Column('method', sa.String(20), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('transaction_id', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False,
                  server_default=sa.func.now()),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_wallet_topup_payments_driver_id',
                    'wallet_topup_payments', ['driver_id'])
    op.create_index('ix_wallet_topup_payments_transaction_id',
                    'wallet_topup_payments', ['transaction_id'])


def downgrade() -> None:
    op.drop_table('wallet_topup_payments')
