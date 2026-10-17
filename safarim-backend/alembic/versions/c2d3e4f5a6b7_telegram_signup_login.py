"""Botda ro'yxatdan o'tish qoralamasi va saytga kirish tokenlari

`telegram_signups` — bir necha xabarlik ro'yxatdan o'tishning oraliq holati
(har xabar boshqa workerga tushishi mumkin, xotirada saqlab bo'lmaydi).

`telegram_login_tokens` — botdagi «Saytga kirish» tugmasi uchun bir martalik,
qisqa muddatli token: botda ro'yxatdan o'tgan odamning paroli yo'q.

Faqat YANGI jadvallar — mavjudlariga tegilmaydi.

Revision ID: c2d3e4f5a6b7
Revises: b1c2d3e4f5a6
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "c2d3e4f5a6b7"
down_revision = "b1c2d3e4f5a6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "telegram_signups",
        sa.Column("chat_id", sa.String(32), primary_key=True),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("step", sa.String(16), nullable=False),
        sa.Column("data", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_table(
        "telegram_login_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("token", sa.String(64), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("used_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_telegram_login_tokens_token", "telegram_login_tokens", ["token"], unique=True)
    op.create_index("ix_telegram_login_tokens_user_id", "telegram_login_tokens", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_telegram_login_tokens_user_id", table_name="telegram_login_tokens")
    op.drop_index("ix_telegram_login_tokens_token", table_name="telegram_login_tokens")
    op.drop_table("telegram_login_tokens")
    op.drop_table("telegram_signups")
