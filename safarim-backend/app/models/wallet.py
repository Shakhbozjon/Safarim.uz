from __future__ import annotations
import uuid
from datetime import datetime
from sqlalchemy import Integer, Boolean, Text, DateTime, Enum, String, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, Mapped, mapped_column
from app.db.base import Base
from app.models.enums import WalletTxType


class DriverWallet(Base):
    """
    Har bir tasdiqlangan haydovchining hamyoni.
    Balans manfiy bo'lishi mumkin (naqd safarlar tufayli).
    MIN_BALANCE dan past tushsa haydovchi bloklanadi.
    """
    __tablename__ = "driver_wallets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    driver_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), unique=True, nullable=False, index=True
    )
    # So'mda, manfiy bo'lishi mumkin
    balance: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # Bloklash chegarasi (default: -50,000 so'm)
    min_balance: Mapped[int] = mapped_column(Integer, default=-50_000, nullable=False)
    # Hamyon balansi sababli bloklangan
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    driver: Mapped[User] = relationship("User", back_populates="wallet")
    transactions: Mapped[list[WalletTransaction]] = relationship(
        "WalletTransaction", back_populates="wallet", order_by="WalletTransaction.created_at.desc()"
    )


class WalletTransaction(Base):
    """
    Hamyon harakatlari tarixi.
    amount > 0 → kirim, amount < 0 → chiqim
    """
    __tablename__ = "wallet_transactions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    wallet_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("driver_wallets.id"), nullable=False, index=True
    )
    # + kirim, - chiqim
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    tx_type: Mapped[WalletTxType] = mapped_column(Enum(WalletTxType), nullable=False)
    # Qaysi bron bilan bog'liq (ixtiyoriy)
    booking_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("bookings.id"), nullable=True
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    # Operatsiyadan keyingi balans (audit uchun)
    balance_after: Mapped[int] = mapped_column(Integer, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    wallet: Mapped[DriverWallet] = relationship("DriverWallet", back_populates="transactions")


class WalletTopupPayment(Base):
    """
    Haydovchi hamyonini Click/Payme orqali to'ldirish so'rovlari.
    Har bir muvaffaqiyatli to'lov → wallet_service.topup() chaqiriladi.
    """
    __tablename__ = "wallet_topup_payments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    driver_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    # "click" | "payme"
    method: Mapped[str] = mapped_column(String(20), nullable=False)
    # "pending" | "completed" | "cancelled"
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    # Click/Payme dan kelgan transaction ID
    transaction_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
