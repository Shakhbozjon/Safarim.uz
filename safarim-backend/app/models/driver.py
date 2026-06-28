from __future__ import annotations
import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, Integer, Float, Text, DateTime, Enum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, Mapped, mapped_column
from app.db.base import Base
from app.models.enums import DriverStatus, LuggageSize


class DriverProfile(Base):
    __tablename__ = "driver_profiles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), unique=True, nullable=False)

    # Hujjat (MinIO path) — faqat haydovchilik guvohnomasi
    license_image: Mapped[str] = mapped_column(String, nullable=False)

    # Avtomobil (1 ta)
    vehicle_make: Mapped[str] = mapped_column(String(50), nullable=False)
    vehicle_model: Mapped[str] = mapped_column(String(50), nullable=False)
    vehicle_year: Mapped[int] = mapped_column(Integer, nullable=False)
    vehicle_color: Mapped[str] = mapped_column(String(30), nullable=False)
    vehicle_plate: Mapped[str] = mapped_column(String(15), unique=True, nullable=False)
    vehicle_seats: Mapped[int] = mapped_column(Integer, nullable=False)

    # Preferences
    smoking_allowed: Mapped[bool] = mapped_column(Boolean, default=False)
    pets_allowed: Mapped[bool] = mapped_column(Boolean, default=False)
    music_allowed: Mapped[bool] = mapped_column(Boolean, default=True)
    luggage_size: Mapped[LuggageSize] = mapped_column(Enum(LuggageSize), default=LuggageSize.medium)
    women_only: Mapped[bool] = mapped_column(Boolean, default=False)

    # Verifikatsiya
    status: Mapped[DriverStatus] = mapped_column(Enum(DriverStatus), default=DriverStatus.pending)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    verified_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    # Reyting
    rating_avg: Mapped[float] = mapped_column(Float, default=0.0)
    rating_count: Mapped[int] = mapped_column(Integer, default=0)
    total_trips: Mapped[int] = mapped_column(Integer, default=0)

    # Holat
    warning_count: Mapped[int] = mapped_column(Integer, default=0)
    is_on_pause: Mapped[bool] = mapped_column(Boolean, default=False)  # haydovchi o'zi qo'ygan pauza

    # ── Soxta safar belgilash jarimasi ──────────────────────────────────────
    # Yo'lovchi "bo'ldi" desa, haydovchi "yo'q" degan bo'lsa → soxtalik ushlanadi
    fake_confirmation_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    fake_count_reset_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # Jarima pauzasi (vaqt o'tguncha e'lonlar ko'rinmaydi) — manual is_on_pause dan alohida
    paused_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="driver_profile", foreign_keys=[user_id])
    verifier: Mapped[User | None] = relationship("User", foreign_keys=[verified_by])
