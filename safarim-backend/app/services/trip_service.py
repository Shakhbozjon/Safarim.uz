from datetime import date, datetime, time, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from sqlalchemy.orm import selectinload
from fastapi import HTTPException, status

from app.models.trip import Trip, TripWaypoint
from app.models.driver import DriverProfile
from app.models.user import User
from app.models.booking import Booking
from app.models.enums import (
    TripStatus, BookingStatus, BookingPaymentStatus, DriverStatus, CancelledBy,
    PaymentType, PaymentMethod, NotificationRefType,
)
from app.schemas.trip import TripCreate, TripSearchParams, TripDriverInfo, TripResponse, WaypointResponse, LocationBrief
from app.core.timeutils import now_tashkent_naive
from app.services import notification_service, wallet_service


def _load_options():
    """Trip uchun barcha kerakli ma'lumotlarni yuklash."""
    return [
        selectinload(Trip.driver).selectinload(User.driver_profile),
        selectinload(Trip.from_region),
        selectinload(Trip.from_district),
        selectinload(Trip.to_region),
        selectinload(Trip.to_district),
        selectinload(Trip.waypoints).selectinload(TripWaypoint.region),
        selectinload(Trip.waypoints).selectinload(TripWaypoint.district),
    ]


def serialize_trip(trip: Trip) -> TripResponse:
    """Trip modelini TripResponse ga aylantirish."""
    dp = trip.driver.driver_profile

    driver_info = TripDriverInfo(
        id=trip.driver.id,
        full_name=trip.driver.full_name,
        profile_photo=trip.driver.profile_photo,
        talk_level=trip.driver.talk_level,
        rating_avg=dp.rating_avg if dp else 0.0,
        rating_count=dp.rating_count if dp else 0,
        total_trips=dp.total_trips if dp else 0,
    )

    waypoints = [
        WaypointResponse(
            id=wp.id,
            region=LocationBrief(id=wp.region.id, name_uz=wp.region.name_uz, name_ru=wp.region.name_ru),
            district=LocationBrief(id=wp.district.id, name_uz=wp.district.name_uz, name_ru=wp.district.name_ru) if wp.district else None,
            address=wp.address,
            order_index=wp.order_index,
            price_from_start=wp.price_from_start,
            arrival_time=wp.arrival_time,
        )
        for wp in sorted(trip.waypoints, key=lambda w: w.order_index)
    ]

    return TripResponse(
        id=trip.id,
        driver=driver_info,
        from_region=LocationBrief(id=trip.from_region.id, name_uz=trip.from_region.name_uz, name_ru=trip.from_region.name_ru),
        from_district=LocationBrief(id=trip.from_district.id, name_uz=trip.from_district.name_uz, name_ru=trip.from_district.name_ru) if trip.from_district else None,
        from_address=trip.from_address,
        to_region=LocationBrief(id=trip.to_region.id, name_uz=trip.to_region.name_uz, name_ru=trip.to_region.name_ru),
        to_district=LocationBrief(id=trip.to_district.id, name_uz=trip.to_district.name_uz, name_ru=trip.to_district.name_ru) if trip.to_district else None,
        to_address=trip.to_address,
        departure_date=trip.departure_date,
        departure_time=trip.departure_time,
        total_seats=trip.total_seats,
        available_seats=trip.available_seats,
        price_per_seat=trip.price_per_seat,
        payment_type=trip.payment_type,
        smoking_allowed=trip.smoking_allowed,
        pets_allowed=trip.pets_allowed,
        women_only=trip.women_only,
        luggage_size=trip.luggage_size,
        description=trip.description,
        has_waypoints=trip.has_waypoints,
        waypoints=waypoints,
        status=trip.status,
        share_token=trip.share_token,
        created_at=trip.created_at,
    )


def _pause_error(dp: DriverProfile) -> str | None:
    """Haydovchi e'lon qila olmaydigan bo'lsa sabab matnini qaytaradi, aks holda None.

    Ikki xil pauza bor: `is_on_pause` (haydovchi o'zi qo'ygan) va `paused_until`
    (soxta belgilash jarimasi — vaqt o'tguncha avtomatik).
    """
    now = datetime.utcnow()
    if dp.paused_until is not None and dp.paused_until > now:
        return (
            f"E'lonlaringiz {dp.paused_until:%Y-%m-%d %H:%M} gacha vaqtincha to'xtatilgan "
            "(qoidabuzarlik jarimasi)."
        )
    if dp.is_on_pause:
        return "Siz pauzadasiz. Avval pauzadan chiqing"
    return None


async def create_trip(db: AsyncSession, user: User, data: TripCreate) -> Trip:
    # Haydovchi tasdiqlanganmi?
    result = await db.execute(
        select(DriverProfile).where(
            DriverProfile.user_id == user.id,
            DriverProfile.status == DriverStatus.approved,
        )
    )
    driver = result.scalar_one_or_none()
    if not driver:
        raise HTTPException(status_code=403, detail="Faqat tasdiqlangan haydovchi safar e'lon qila oladi")
    perr = _pause_error(driver)
    if perr:
        raise HTTPException(status_code=403, detail=perr)

    # O'rinlar soni tekshirish
    if data.total_seats > driver.vehicle_seats:
        raise HTTPException(
            status_code=400,
            detail=f"Avtomobilingizda maksimal {driver.vehicle_seats} o'rin bor",
        )

    # Bir yo'nalishda bir kunda bitta safar (duplicate tekshirish)
    result = await db.execute(
        select(Trip).where(
            Trip.driver_id == user.id,
            Trip.from_region_id == data.from_region_id,
            Trip.to_region_id == data.to_region_id,
            Trip.departure_date == data.departure_date,
            Trip.status == TripStatus.active,
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Bu yo'nalishda shu kunda safar allaqachon mavjud")

    dep_time = time.fromisoformat(data.departure_time)
    has_waypoints = bool(data.waypoints and len(data.waypoints) > 0)

    trip = Trip(
        driver_id=user.id,
        from_region_id=data.from_region_id,
        from_district_id=data.from_district_id,
        from_address=data.from_address,
        to_region_id=data.to_region_id,
        to_district_id=data.to_district_id,
        to_address=data.to_address,
        departure_date=data.departure_date,
        departure_time=dep_time,
        total_seats=data.total_seats,
        available_seats=data.total_seats,
        price_per_seat=data.price_per_seat,
        payment_type=data.payment_type,
        smoking_allowed=data.smoking_allowed,
        pets_allowed=data.pets_allowed,
        women_only=data.women_only,
        luggage_size=data.luggage_size,
        description=data.description,
        has_waypoints=has_waypoints,
    )
    db.add(trip)
    await db.flush()

    # Waypointlar
    if data.waypoints:
        for wp_data in sorted(data.waypoints, key=lambda x: x.order_index):
            arr_time = None
            if wp_data.arrival_time:
                try:
                    arr_time = time.fromisoformat(wp_data.arrival_time)
                except ValueError:
                    pass

            db.add(TripWaypoint(
                trip_id=trip.id,
                region_id=wp_data.region_id,
                district_id=wp_data.district_id,
                address=wp_data.address,
                order_index=wp_data.order_index,
                price_from_start=wp_data.price_from_start,
                arrival_time=arr_time,
            ))

    await db.commit()

    result = await db.execute(
        select(Trip).options(*_load_options()).where(Trip.id == trip.id)
    )
    return result.scalar_one()


async def search_trips(db: AsyncSession, params: TripSearchParams) -> list[Trip]:
    # 1. To'g'ridan-to'g'ri safarlar
    direct_condition = and_(
        Trip.from_region_id == params.from_region_id,
        Trip.to_region_id == params.to_region_id,
    )

    # 2. Oraliq to'xtashli safarlar (waypoint orqali)
    from_wp = select(TripWaypoint.trip_id).where(
        TripWaypoint.region_id == params.from_region_id
    ).scalar_subquery()

    to_wp = select(TripWaypoint.trip_id).where(
        TripWaypoint.region_id == params.to_region_id
    ).scalar_subquery()

    waypoint_condition = and_(
        Trip.has_waypoints == True,
        Trip.id.in_(from_wp),
        Trip.id.in_(to_wp),
    )

    # Jarima pauzasidagi haydovchilar e'lonlari qidiruvda ko'rinmaydi
    paused_driver_ids = select(DriverProfile.user_id).where(
        DriverProfile.paused_until > datetime.utcnow()
    ).scalar_subquery()

    query = (
        select(Trip)
        .options(*_load_options())
        .where(
            Trip.status == TripStatus.active,
            Trip.departure_date == params.departure_date,
            Trip.departure_date >= date.today(),   # o'tib ketgan safar chiqmasin
            Trip.available_seats >= params.seats,
            Trip.driver_id.notin_(paused_driver_ids),
            or_(direct_condition, waypoint_condition),
        )
    )

    # Filtrlar
    if params.payment_type and params.payment_type != PaymentType.any:
        query = query.where(
            or_(Trip.payment_type == params.payment_type, Trip.payment_type == PaymentType.any)
        )
    if params.women_only:
        query = query.where(Trip.women_only == True)
    if params.max_price:
        query = query.where(Trip.price_per_seat <= params.max_price)

    # Saralash
    if params.sort == "price_asc":
        query = query.order_by(Trip.price_per_seat.asc())
    elif params.sort == "price_desc":
        query = query.order_by(Trip.price_per_seat.desc())
    else:  # time_asc (default)
        query = query.order_by(Trip.departure_time.asc())

    result = await db.execute(query)
    return result.scalars().all()


async def get_trip(db: AsyncSession, trip_id: str) -> Trip:
    import uuid as uuid_lib
    try:
        uid = uuid_lib.UUID(trip_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Noto'g'ri ID")

    result = await db.execute(
        select(Trip).options(*_load_options()).where(Trip.id == uid)
    )
    trip = result.scalar_one_or_none()
    if not trip:
        raise HTTPException(status_code=404, detail="Safar topilmadi")
    return trip


async def get_trip_by_share_token(db: AsyncSession, token: str) -> Trip:
    result = await db.execute(
        select(Trip).options(*_load_options()).where(Trip.share_token == token)
    )
    trip = result.scalar_one_or_none()
    if not trip:
        raise HTTPException(status_code=404, detail="Safar topilmadi")
    return trip


async def get_my_trips(db: AsyncSession, user: User) -> list[Trip]:
    # Lazy expiry — Celery ishlamasa ham vaqti o'tgan bo'sh safarlar tozalanadi
    await expire_due_trips(db, driver_id=user.id)

    result = await db.execute(
        select(Trip)
        .options(*_load_options())
        .where(Trip.driver_id == user.id)
        .order_by(Trip.departure_date.desc(), Trip.departure_time.desc())
    )
    return result.scalars().all()


# Safar vaqti o'tganidan keyin shu soatlardan so'ng "tugagan" deb hisoblanadi
TRIP_EXPIRY_GRACE_HOURS = 3


async def expire_due_trips(db: AsyncSession, driver_id=None) -> int:
    """Vaqti o'tgan, yo'lovchi yig'ilmagan safarlarni `expired` qiladi.

    `driver_id` berilsa faqat shu haydovchi safarlari (dashboard lazy expiry).
    Berilmasa — barchasi (Celery task). Tasdiqlangan bron bor safarlarga tegmaydi.
    O'zgarish bo'lganda commit qiladi. Expired qilingan safarlar sonini qaytaradi.
    """
    now = now_tashkent_naive()
    today = now.date()
    grace = timedelta(hours=TRIP_EXPIRY_GRACE_HOURS)

    query = select(Trip).where(
        Trip.status.in_([TripStatus.active, TripStatus.full]),
        Trip.departure_date <= today,
    )
    if driver_id is not None:
        query = query.where(Trip.driver_id == driver_id)

    trips = (await db.execute(query)).scalars().all()

    expired_count = 0
    changed = False

    for trip in trips:
        departure_dt = datetime.combine(trip.departure_date, trip.departure_time)
        if now < departure_dt + grace:
            continue  # safar hali o'tmagan / davom etmoqda

        # Javobsiz qolgan pending bronlarni bekor qilish
        pending = (await db.execute(
            select(Booking).where(
                Booking.trip_id == trip.id,
                Booking.status == BookingStatus.pending,
            )
        )).scalars().all()
        for booking in pending:
            from app.services.booking_service import flag_refund_due
            booking.status = BookingStatus.cancelled
            booking.cancelled_by = CancelledBy.driver
            booking.cancellation_reason = "Safar vaqti o'tdi — so'rov avtomatik bekor qilindi"
            booking.cancelled_at = now
            online_paid = (
                booking.payment_method != PaymentMethod.cash
                and booking.payment_status == BookingPaymentStatus.paid
            )
            refund = booking.total_price if online_paid else 0
            booking.refund_amount = refund
            await flag_refund_due(db, booking, refund)
            # Komissiya safar tugaganda ushiladi — bu pending bronlarda komissiya yo'q
            await notification_service.create(
                db,
                user_id=booking.passenger_id,
                title="So'rov bekor qilindi",
                body="Safar vaqti o'tib ketdi, broningiz avtomatik bekor qilindi.",
                ref_type=NotificationRefType.booking,
                ref_id=booking.id,
            )
            changed = True

        # Real bron bormi? (pending/cancelled dan boshqa har qanday — tasdiq
        # bosqichidagi yoki yakunlangan safarlar `expired` bo'lib qolmasin)
        real = await db.scalar(
            select(func.count()).select_from(Booking).where(
                Booking.trip_id == trip.id,
                Booking.status.notin_([BookingStatus.pending, BookingStatus.cancelled]),
            )
        )
        if real and real > 0:
            continue  # real safar — tasdiq oqimi orqali yakunlanadi

        # Yo'lovchi yig'ilmadi → expired (jazosiz)
        trip.status = TripStatus.expired
        await notification_service.create(
            db,
            user_id=trip.driver_id,
            title="Safarga yo'lovchi yig'ilmadi",
            body="Safaringiz muddati tugadi. Istasangiz uni bir tugma bilan qayta e'lon qilishingiz mumkin.",
            ref_type=NotificationRefType.system,
        )
        expired_count += 1
        changed = True

    if changed:
        await db.commit()

    return expired_count


async def cancel_trip(db: AsyncSession, trip_id: str, user: User, reason: str | None) -> Trip:
    trip = await get_trip(db, trip_id)

    if trip.driver_id != user.id:
        raise HTTPException(status_code=403, detail="Bu safar sizniki emas")
    # Aktiv yoki to'lib ketgan (full) safarni bekor qilish mumkin
    if trip.status not in (TripStatus.active, TripStatus.full):
        raise HTTPException(status_code=400, detail="Bu safarni bekor qilib bo'lmaydi")

    # Barcha aktiv bronlarni bekor qilish
    result = await db.execute(
        select(Booking).where(
            Booking.trip_id == trip.id,
            Booking.status.in_([BookingStatus.pending, BookingStatus.confirmed]),
        )
    )
    bookings = result.scalars().all()

    # Jo'nash vaqtidan keyin bronli safarni bekor qilib bo'lmaydi —
    # aks holda haydovchi komissiyadan qochib qutuladi (tasdiq oqimi hal qiladi)
    departure_dt = datetime.combine(trip.departure_date, trip.departure_time)
    if bookings and now_tashkent_naive() >= departure_dt:
        raise HTTPException(
            status_code=400,
            detail="Safar vaqti boshlangan — endi bekor qilib bo'lmaydi. Safar holatini tasdiq so'rovida belgilang.",
        )

    from app.services.booking_service import flag_refund_due

    now = datetime.utcnow()
    for booking in bookings:
        booking.status = BookingStatus.cancelled
        booking.cancelled_by = CancelledBy.driver
        booking.cancellation_reason = reason or "Haydovchi safarni bekor qildi"
        booking.cancelled_at = now

        # Refund faqat online to'langan bronда — naqdda hech narsa olinmagan
        online_paid = (
            booking.payment_method != PaymentMethod.cash
            and booking.payment_status == BookingPaymentStatus.paid
        )
        refund = booking.total_price if online_paid else 0
        booking.refund_amount = refund
        await flag_refund_due(db, booking, refund)

        # Komissiya faqat safar tugaganda ushiladi — tugamagan bron bekor qilinsa
        # qaytariladigan komissiya yo'q.

        # Har bir yo'lovchiga bildirishnoma
        refund_note = f" {refund:,} so'm qaytariladi." if refund > 0 else ""
        await notification_service.create(
            db,
            user_id=booking.passenger_id,
            title="Safar bekor qilindi",
            body=f"Haydovchi safarni bekor qildi.{refund_note}",
            ref_type=NotificationRefType.booking,
            ref_id=booking.id,
        )

    trip.status = TripStatus.cancelled
    trip.cancellation_reason = reason
    trip.cancelled_at = now

    # Haydovchi reytingiga ta'sir (bekor qilish uchun) — Sprint 6 da to'liq
    if bookings:
        dp_result = await db.execute(
            select(DriverProfile).where(DriverProfile.user_id == user.id)
        )
        dp = dp_result.scalar_one_or_none()
        if dp:
            dp.warning_count += 1

    await db.commit()

    result = await db.execute(
        select(Trip).options(*_load_options()).where(Trip.id == trip.id)
    )
    return result.scalar_one()


async def duplicate_trip(
    db: AsyncSession,
    user: User,
    trip_id: str,
    new_date: date,
    new_time: str | None = None,
) -> Trip:
    """Eski safarni (masalan, expired) yangi sana bilan qayta e'lon qiladi."""
    src = await get_trip(db, trip_id)

    if src.driver_id != user.id:
        raise HTTPException(status_code=403, detail="Bu safar sizniki emas")

    # Haydovchi hali tasdiqlangan va pauzada emasligini tekshirish
    dp_result = await db.execute(
        select(DriverProfile).where(
            DriverProfile.user_id == user.id,
            DriverProfile.status == DriverStatus.approved,
        )
    )
    dp = dp_result.scalar_one_or_none()
    if not dp:
        raise HTTPException(status_code=403, detail="Faqat tasdiqlangan haydovchi safar e'lon qila oladi")
    perr = _pause_error(dp)
    if perr:
        raise HTTPException(status_code=403, detail=perr)

    dep_time = time.fromisoformat(new_time) if new_time else src.departure_time

    # Bir yo'nalishda shu kunda aktiv safar bo'lmasin
    dup_result = await db.execute(
        select(Trip).where(
            Trip.driver_id == user.id,
            Trip.from_region_id == src.from_region_id,
            Trip.to_region_id == src.to_region_id,
            Trip.departure_date == new_date,
            Trip.status == TripStatus.active,
        )
    )
    if dup_result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Bu yo'nalishda shu kunda safar allaqachon mavjud")

    new_trip = Trip(
        driver_id=user.id,
        from_region_id=src.from_region_id,
        from_district_id=src.from_district_id,
        from_address=src.from_address,
        to_region_id=src.to_region_id,
        to_district_id=src.to_district_id,
        to_address=src.to_address,
        departure_date=new_date,
        departure_time=dep_time,
        total_seats=src.total_seats,
        available_seats=src.total_seats,
        price_per_seat=src.price_per_seat,
        payment_type=src.payment_type,
        smoking_allowed=src.smoking_allowed,
        pets_allowed=src.pets_allowed,
        women_only=src.women_only,
        luggage_size=src.luggage_size,
        description=src.description,
        has_waypoints=src.has_waypoints,
    )
    db.add(new_trip)
    await db.flush()

    # Oraliq to'xtashlarni ham nusxalash
    for wp in src.waypoints:
        db.add(TripWaypoint(
            trip_id=new_trip.id,
            region_id=wp.region_id,
            district_id=wp.district_id,
            address=wp.address,
            order_index=wp.order_index,
            price_from_start=wp.price_from_start,
            arrival_time=wp.arrival_time,
        ))

    await db.commit()

    result = await db.execute(
        select(Trip).options(*_load_options()).where(Trip.id == new_trip.id)
    )
    return result.scalar_one()
