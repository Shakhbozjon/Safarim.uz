from __future__ import annotations
import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, Enum, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, Mapped, mapped_column
from app.db.base import Base
from app.models.enums import TalkLevel, AdminRole


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    phone: Mapped[str] = mapped_column(String(13), unique=True, nullable=False, index=True)
    email: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    profile_photo: Mapped[str | None] = mapped_column(String, nullable=True)
    talk_level: Mapped[TalkLevel] = mapped_column(Enum(TalkLevel), default=TalkLevel.normal)
    is_phone_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    is_email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    is_driver: Mapped[bool] = mapped_column(Boolean, default=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    admin_role: Mapped[AdminRole | None] = mapped_column(Enum(AdminRole), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False)
    block_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    telegram_chat_id: Mapped[str | None] = mapped_column(String(50), unique=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Relationships
    driver_profile: Mapped[DriverProfile | None] = relationship("DriverProfile", back_populates="user", foreign_keys="DriverProfile.user_id", uselist=False)
    trips: Mapped[list[Trip]] = relationship("Trip", back_populates="driver", foreign_keys="Trip.driver_id")
    bookings: Mapped[list[Booking]] = relationship("Booking", back_populates="passenger", foreign_keys="Booking.passenger_id")
    sent_messages: Mapped[list[Message]] = relationship("Message", back_populates="sender")
    notifications: Mapped[list[Notification]] = relationship("Notification", back_populates="user")
    given_reviews: Mapped[list[Review]] = relationship("Review", back_populates="reviewer", foreign_keys="Review.reviewer_id")
    received_reviews: Mapped[list[Review]] = relationship("Review", back_populates="reviewee", foreign_keys="Review.reviewee_id")
    monthly_commissions: Mapped[list[DriverMonthlyCommission]] = relationship("DriverMonthlyCommission", back_populates="driver")
    admin_actions_done: Mapped[list[AdminAction]] = relationship("AdminAction", back_populates="admin", foreign_keys="AdminAction.admin_id")
    wallet: Mapped[DriverWallet | None] = relationship("DriverWallet", back_populates="driver", uselist=False)
