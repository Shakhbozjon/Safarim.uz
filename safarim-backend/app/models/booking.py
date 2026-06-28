from __future__ import annotations
import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Float, Text, DateTime, Enum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, Mapped, mapped_column
from app.db.base import Base
from app.models.enums import PaymentMethod, BookingPaymentStatus, BookingStatus, CancelledBy


class Booking(Base):
    __tablename__ = "bookings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trip_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("trips.id"), nullable=False, index=True)
    passenger_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)

    # O'rinlar soni (1-4)
    seats_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # Waypoint (oddiy safarда NULL)
    from_waypoint_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("trip_waypoints.id"), nullable=True)
    to_waypoint_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("trip_waypoints.id"), nullable=True)

    # Narx (booking vaqtidagi snapshot)
    price_per_seat: Mapped[int] = mapped_column(Integer, nullable=False)
    total_price: Mapped[int] = mapped_column(Integer, nullable=False)
    commission_rate: Mapped[float] = mapped_column(Float, nullable=False)
    commission_amount: Mapped[int] = mapped_column(Integer, nullable=False)
    driver_amount: Mapped[int] = mapped_column(Integer, nullable=False)

    # To'lov
    payment_method: Mapped[PaymentMethod] = mapped_column(Enum(PaymentMethod), nullable=False)
    payment_status: Mapped[BookingPaymentStatus] = mapped_column(Enum(BookingPaymentStatus), default=BookingPaymentStatus.pending)

    # Holat
    status: Mapped[BookingStatus] = mapped_column(Enum(BookingStatus), default=BookingStatus.pending)

    # Bekor qilish
    cancelled_by: Mapped[CancelledBy | None] = mapped_column(Enum(CancelledBy), nullable=True)
    cancellation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    refund_amount: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # No-show (haydovchi bosadi)
    no_show_reported_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Tugash tasdiqi
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # ── Ikki tomonlama safar tasdiqi ─────────────────────────────────────────
    # 'yes' / 'no' / NULL (jim — javob bermadi)
    driver_confirmed: Mapped[str | None] = mapped_column(String(3), nullable=True)
    passenger_confirmed: Mapped[str | None] = mapped_column(String(3), nullable=True)
    # Tasdiq so'rovi yuborilgan vaqt — 48 soatlik oyna shu yerdan sanaladi
    confirmation_requested_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # Haydovchi "bo'lmadi" deganda yo'lovchidan qayta so'ralgan vaqt
    driver_denied_reprompt_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    trip: Mapped[Trip] = relationship("Trip", back_populates="bookings")
    passenger: Mapped[User] = relationship("User", back_populates="bookings", foreign_keys=[passenger_id])
    from_waypoint: Mapped[TripWaypoint | None] = relationship("TripWaypoint", foreign_keys=[from_waypoint_id])
    to_waypoint: Mapped[TripWaypoint | None] = relationship("TripWaypoint", foreign_keys=[to_waypoint_id])
    messages: Mapped[list[Message]] = relationship("Message", back_populates="booking", cascade="all, delete-orphan")
    reviews: Mapped[list[Review]] = relationship("Review", back_populates="booking")
    payment: Mapped[Payment | None] = relationship("Payment", back_populates="booking", uselist=False)
