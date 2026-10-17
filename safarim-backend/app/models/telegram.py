from __future__ import annotations
import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base
from app.models.enums import TelegramLinkPurpose


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

    # Kontakt kelganda raqamni solishtiramizmi yoki almashtiramizmi
    purpose: Mapped[TelegramLinkPurpose] = mapped_column(
        Enum(TelegramLinkPurpose, name="telegramlinkpurpose"),
        nullable=False,
        default=TelegramLinkPurpose.verify,
        server_default=TelegramLinkPurpose.verify.value,
    )

    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship("User")


class TelegramSignup(Base):
    """Botda ro'yxatdan o'tish jarayonidagi oraliq holat (qoralama).

    Ro'yxatdan o'tish bir necha xabardan iborat: raqam → ism → (haydovchi
    bo'lsa) mashina, rang, raqam, o'rinlar. Har xabar boshqa gunicorn
    workeriga tushishi mumkin, shuning uchun holat xotirada emas, bazada.
    Ro'yxatdan o'tish tugagach yozuv o'chiriladi.
    """
    __tablename__ = "telegram_signups"

    chat_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    # "passenger" | "driver"
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    # Qaysi savolga javob kutilyapti: contact | name | make | model | color | plate | seats
    step: Mapped[str] = mapped_column(String(16), nullable=False)
    # Yig'ilgan javoblar (telefon, ism, mashina...)
    data: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class TelegramLoginToken(Base):
    """Botdagi «Saytga kirish» tugmasi uchun bir martalik token.

    Botda ro'yxatdan o'tgan odamning paroli yo'q — saytga shu token bilan
    kiradi. Token qisqa muddatli va faqat BIR marta ishlaydi. Alohida jadval
    (TelegramLinkToken emas): u yerdagi tokenlar chat bo'yicha ham qidiriladi
    va kontakt oqimiga aralashib qolmasin.
    """
    __tablename__ = "telegram_login_tokens"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    token: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship("User")
