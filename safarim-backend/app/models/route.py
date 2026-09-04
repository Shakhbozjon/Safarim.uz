from __future__ import annotations
import uuid
from datetime import datetime, time
from sqlalchemy import String, Boolean, Integer, Text, DateTime, Time, Enum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, Mapped, mapped_column
from app.db.base import Base
from app.models.enums import PaymentType, LuggageSize


class DriverRoute(Base):
    """Haydovchining doimiy yo'nalishi — har kuni bir xil safarni to'liq forma
    bilan qayta e'lon qilmaslik uchun shablon.

    Haydovchining o'zi belgilaydi (safar e'lon qilishda "bu mening doimiy
    yo'nalishim"), tarixdan taxmin qilinmaydi. Hozircha bitta haydovchida
    bitta yo'nalish — bor-kel ikki tomon shu qatorning ichida
    (`departure_time` — borish, `return_time` — qaytish).
    """

    __tablename__ = "driver_routes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    driver_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, unique=True, index=True
    )

    # Yo'nalish
    from_region_id: Mapped[int] = mapped_column(Integer, ForeignKey("regions.id"), nullable=False)
    from_district_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("districts.id"), nullable=True)
    from_address: Mapped[str | None] = mapped_column(String(255), nullable=True)

    to_region_id: Mapped[int] = mapped_column(Integer, ForeignKey("regions.id"), nullable=False)
    to_district_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("districts.id"), nullable=True)
    to_address: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Vaqtlar — qaytish ixtiyoriy
    departure_time: Mapped[time] = mapped_column(Time, nullable=False)
    return_time: Mapped[time | None] = mapped_column(Time, nullable=True)

    # Sig'im va narx (oxirgi ishlatilgani — e'lon qilishda tasdiqlanadi)
    total_seats: Mapped[int] = mapped_column(Integer, nullable=False)
    price_per_seat: Mapped[int] = mapped_column(Integer, nullable=False)

    payment_type: Mapped[PaymentType] = mapped_column(Enum(PaymentType), default=PaymentType.any)
    smoking_allowed: Mapped[bool] = mapped_column(Boolean, default=False)
    pets_allowed: Mapped[bool] = mapped_column(Boolean, default=False)
    women_only: Mapped[bool] = mapped_column(Boolean, default=False)
    luggage_size: Mapped[LuggageSize] = mapped_column(Enum(LuggageSize), default=LuggageSize.medium)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Oraliq to'xtashlar — alohida jadval o'rniga suratga olingan ro'yxat:
    # [{region_id, district_id, address, order_index, price_from_start, arrival_time}]
    waypoints: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    from_region = relationship("Region", foreign_keys=[from_region_id])
    from_district = relationship("District", foreign_keys=[from_district_id])
    to_region = relationship("Region", foreign_keys=[to_region_id])
    to_district = relationship("District", foreign_keys=[to_district_id])
