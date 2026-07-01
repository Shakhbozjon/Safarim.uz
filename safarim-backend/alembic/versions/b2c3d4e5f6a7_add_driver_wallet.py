"""add_driver_wallet

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-06-04 10:00:00.000000

"""
from typing import Sequence, Union
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, ENUM
from alembic import op

revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # WalletTxType enum
    op.execute("""
        CREATE TYPE wallettxtype AS ENUM (
            'cash_commission',
            'online_earning',
            'topup',
            'withdrawal',
            'refund'
        )
    """)

    # driver_wallets jadvali
    op.create_table(
        'driver_wallets',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('driver_id', UUID(as_uuid=True),
                  sa.ForeignKey('users.id'), nullable=False, unique=True),
        sa.Column('balance', sa.Integer, nullable=False, server_default='0'),
        sa.Column('min_balance', sa.Integer, nullable=False, server_default='-50000'),
        sa.Column('is_blocked', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime, server_default=sa.text('now()')),
    )
    op.create_index('ix_driver_wallets_driver_id', 'driver_wallets', ['driver_id'])

    # wallet_transactions jadvali
    op.create_table(
        'wallet_transactions',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('wallet_id', UUID(as_uuid=True),
                  sa.ForeignKey('driver_wallets.id'), nullable=False),
        sa.Column('amount', sa.Integer, nullable=False),
        # create_type=False — enum yuqorida op.execute bilan yaratilgan (ikki marta yaratmaslik)
        sa.Column('tx_type', ENUM('cash_commission', 'online_earning', 'topup',
                                  'withdrawal', 'refund', name='wallettxtype',
                                  create_type=False),
                  nullable=False),
        sa.Column('booking_id', UUID(as_uuid=True),
                  sa.ForeignKey('bookings.id'), nullable=True),
        sa.Column('description', sa.Text, nullable=False),
        sa.Column('balance_after', sa.Integer, nullable=False),
        sa.Column('created_at', sa.DateTime, server_default=sa.text('now()')),
    )
    op.create_index('ix_wallet_transactions_wallet_id', 'wallet_transactions', ['wallet_id'])

    # Mavjud tasdiqlangan haydovchilar uchun avtomatik hamyon yaratish
    op.execute("""
        INSERT INTO driver_wallets (id, driver_id, balance, min_balance, is_blocked, created_at, updated_at)
        SELECT
            gen_random_uuid(),
            u.id,
            0,
            -50000,
            false,
            now(),
            now()
        FROM users u
        JOIN driver_profiles dp ON dp.user_id = u.id
        WHERE u.is_driver = true
          AND dp.status = 'approved'
          AND NOT EXISTS (
              SELECT 1 FROM driver_wallets dw WHERE dw.driver_id = u.id
          )
    """)


def downgrade() -> None:
    op.drop_table('wallet_transactions')
    op.drop_table('driver_wallets')
    op.execute("DROP TYPE IF EXISTS wallettxtype")
