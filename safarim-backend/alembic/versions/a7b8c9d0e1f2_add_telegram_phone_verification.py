"""add_telegram_phone_verification

Telegram orqali telefon tasdiqlash:
  - telegram_link_tokens jadvali (sayt sessiyasini Telegram hisobiga bog'lash)
  - AdminActionType ga verify_phone (admin qo'lda tasdiqlaganda jurnalga yozish)
  - MAVJUD foydalanuvchilarning is_phone_verified bayrog'i false ga qaytariladi

Oxirgi qadam haqida: ro'yxatdan o'tishda bu bayroq hech qanday tekshiruvsiz
true qilinardi, ya'ni profilda tekshirilmagan raqamga "Telefon tasdiqlangan"
deb yozib qo'yilgan edi. Bayroq rost bo'lishi uchun hamma qaytadan tasdiqlaydi.
Adminlar bundan mustasno — ular tizimga kira olishi kerak.

Revision ID: a7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-08-26 10:30:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = 'a7b8c9d0e1f2'
down_revision: Union[str, None] = 'f6a7b8c9d0e1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'telegram_link_tokens',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('token', sa.String(length=64), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('chat_id', sa.String(length=32), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('used_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_telegram_link_tokens_token', 'telegram_link_tokens', ['token'], unique=True)
    op.create_index('ix_telegram_link_tokens_user_id', 'telegram_link_tokens', ['user_id'])
    op.create_index('ix_telegram_link_tokens_chat_id', 'telegram_link_tokens', ['chat_id'])

    op.execute("ALTER TYPE adminactiontype ADD VALUE IF NOT EXISTS 'verify_phone'")

    # Tekshirilmagan raqamlar "tasdiqlangan" bo'lib qolmasin
    op.execute("UPDATE users SET is_phone_verified = false WHERE is_admin = false")


def downgrade() -> None:
    op.drop_index('ix_telegram_link_tokens_chat_id', table_name='telegram_link_tokens')
    op.drop_index('ix_telegram_link_tokens_user_id', table_name='telegram_link_tokens')
    op.drop_index('ix_telegram_link_tokens_token', table_name='telegram_link_tokens')
    op.drop_table('telegram_link_tokens')
    # PostgreSQL enum qiymatini o'chirib bo'lmaydi; is_phone_verified qaytarilmaydi
