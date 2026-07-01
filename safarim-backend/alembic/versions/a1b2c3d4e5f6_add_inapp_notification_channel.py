"""add_inapp_notification_channel

Revision ID: a1b2c3d4e5f6
Revises: 7db340a808db
Create Date: 2026-06-03 18:00:00.000000

"""
from typing import Sequence, Union
from alembic import op

revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '7db340a808db'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE notificationchannel ADD VALUE IF NOT EXISTS 'inapp'")


def downgrade() -> None:
    # PostgreSQL enum qiymatini o'chirish mumkin emas — downgrade qilinmaydi
    pass
