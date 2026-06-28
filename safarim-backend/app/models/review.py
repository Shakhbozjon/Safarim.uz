from __future__ import annotations
import uuid
from datetime import datetime
from sqlalchemy import Integer, Text, Boolean, DateTime, Enum, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, Mapped, mapped_column
from app.db.base import Base
from app.models.enums import ReviewerType


class Review(Base):
    __tablename__ = "reviews"
    __table_args__ = (
        UniqueConstraint("booking_id", "reviewer_type", name="uq_review_booking_reviewer_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    booking_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("bookings.id"), nullable=False, index=True)
    reviewer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    reviewee_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    reviewer_type: Mapped[ReviewerType] = mapped_column(Enum(ReviewerType), nullable=False)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 72 soat qoidasi — ikki tomon ham bermagunicha yashirinadi
    is_visible: Mapped[bool] = mapped_column(Boolean, default=False)
    review_deadline: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    booking: Mapped[Booking] = relationship("Booking", back_populates="reviews")
    reviewer: Mapped[User] = relationship("User", back_populates="given_reviews", foreign_keys=[reviewer_id])
    reviewee: Mapped[User] = relationship("User", back_populates="received_reviews", foreign_keys=[reviewee_id])
