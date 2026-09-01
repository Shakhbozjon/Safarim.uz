from __future__ import annotations
import uuid
import secrets
from datetime import datetime, date, time
from sqlalchemy import String, Boolean, Integer, Text, DateTime, Date, Time, Enum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, Mapped, mapped_column
from app.db.base import Base
from app.models.enums import PaymentType, TripStatus, LuggageSize


class Trip(Base):
    __tablename__ = "trips"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    driver_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)

    # Yo'nalish
    from_region_id: Mapped[int] = mapped_column(Integer, ForeignKey("regions.id"), nullable=False)
    from_district_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("districts.id"), nullable=True)
    from_address: Mapped[str | None] = mapped_column(String(255), nullable=True)

    to_region_id: Mapped[int] = mapped_column(Integer, ForeignKey("regions.id"), nullable=False)
    to_district_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("districts.id"), nullable=True)
    to_address: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Vaqt
    departure_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    departure_time: Mapped[time] = mapped_column(Time, nullable=False)

    # Sig'im va narx
    total_seats: Mapped[int] = mapped_column(Integer, nullable=False)
    available_seats: Mapped[int] = mapped_column(Integer, nullable=False)
    price_per_seat: Mapped[int] = mapped_column(Integer, nullable=False)

    # To'lov turi
    payment_type: Mapped[PaymentType] = mapped_column(Enum(PaymentType), default=PaymentType.any)

    # Preferences
    smoking_allowed: Mapped[bool] = mapped_column(Boolean, default=False)
    pets_allowed: Mapped[bool] = mapped_column(Boolean, default=False)
    women_only: Mapped[bool] = mapped_column(Boolean, default=False)
    luggage_size: Mapped[LuggageSize] = mapped_column(Enum(LuggageSize), default=LuggageSize.medium)

    # Qo'shimcha
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    has_waypoints: Mapped[bool] = mapped_column(Boolean, default=False)
    share_token: Mapped[str] = mapped_column(
        String(32), unique=True, nullable=False, default=lambda: secrets.token_urlsafe(16)
    )

    # Holat
    status: Mapped[TripStatus] = mapped_column(Enum(TripStatus), default=TripStatus.active)
    cancellation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    driver: Mapped[User] = relationship("User", back_populates="trips", foreign_keys=[driver_id])
    from_region: Mapped[Region] = relationship("Region", foreign_keys=[from_region_id])
    from_district: Mapped[District | None] = relationship("District", foreign_keys=[from_district_id])
    to_region: Mapped[Region] = relationship("Region", foreign_keys=[to_region_id])
    to_district: Mapped[District | None] = relationship("District", foreign_keys=[to_district_id])
    waypoints: Mapped[list[TripWaypoint]] = relationship(
        "TripWaypoint", back_populates="trip", order_by="TripWaypoint.order_index", cascade="all, delete-orphan"
    )
    bookings: Mapped[list[Booking]] = relationship("Booking", back_populates="trip")


class TripWaypoint(Base):
    __tablename__ = "trip_waypoints"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trip_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("trips.id"), nullable=False, index=True)
    region_id: Mapped[int] = mapped_column(Integer, ForeignKey("regions.id"), nullable=False)
    district_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("districts.id"), nullable=True)
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)
    price_from_start: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    arrival_time: Mapped[time | None] = mapped_column(Time, nullable=True)

    # Relationships
    trip: Mapped[Trip] = relationship("Trip", back_populates="waypoints")
    region: Mapped[Region] = relationship("Region", foreign_keys=[region_id])
    district: Mapped[District | None] = relationship("District", foreign_keys=[district_id])
