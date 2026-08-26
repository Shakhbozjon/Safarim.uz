from __future__ import annotations
import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class TelegramLinkToken(Base):
    """Sayt sessiyasini Telegram hisobiga bog'lovchi bir martalik token.

    Foydalanuvchi saytda "Telegram orqali tasdiqlash" ni bosadi → shu token
    yaratiladi va `t.me/<bot>?start=<token>` havolasiga qo'yiladi. Bot `/start`
    da tokenni oladi va qaysi hisob tasdiqlanayotganini biladi.

    Tokensiz ham raqamni tekshirish mumkin edi, lekin u holda bot faqat
    "bu raqam kimniki" ni biladi — saytda kim kirganini emas. Token ikkalasini
    bog'laydi: birovning raqami bilan ochilgan hisobni o'sha raqam egasi
    bilmasdan tasdiqlab yuborishining oldini oladi.
    """
    __tablename__ = "telegram_link_tokens"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    token: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    # `/start` kelganda to'ldiriladi. Kontakt keyingi alohida xabarda keladi —
    # oradagi holat shu yerda saqlanadi, xotirada emas: prod'da gunicorn bir
    # nechta worker bilan ishlaydi va ikki xabar turli workerlarga tushishi mumkin.
    chat_id: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)

    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship("User")
