"""Safarga Telegram post ID si qo'shiladi

Guruhga tashlangan e'lon keyin tahrirlanishi kerak (o'rin tugadi, bekor
qilindi). Buning uchun xabar ID si saqlanadi.

Revision ID: a9b0c1d2e3f4
Revises: f8a9b0c1d2e3
"""
from alembic import op
import sqlalchemy as sa

revision = "a9b0c1d2e3f4"
down_revision = "f8a9b0c1d2e3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("trips", sa.Column("telegram_message_id", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("trips", "telegram_message_id")
