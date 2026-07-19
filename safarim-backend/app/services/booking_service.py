from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from fastapi import HTTPException, status

from app.models.booking import Booking
from app.models.trip import Trip, TripWaypoint
from app.models.driver import DriverProfile
from app.models.user import User
from app.models.payment import DriverMonthlyCommission
from app.models.enums import (
    BookingStatus, BookingPaymentStatus, TripStatus,
    CancelledBy, PaymentMethod, DriverStatus,
    CONFIRM_YES, CONFIRM_NO,
)
from app.schemas.booking import BookingCreate
from app.core.security import calculate_commission
from app.core.config import settings
from app.core.timeutils import now_tashkent_naive
from app.services import notification_service, wallet_service
from app.models.enums import NotificationRefType


def _load_options():
    return [
        selectinload(Booking.passenger),
        selectinload(Booking.trip).selectinload(Trip.from_region),
        selectinload(Booking.trip).selectinload(Trip.to_region),
        selectinload(Booking.trip).selectinload(Trip.from_district),
        selectinload(Booking.trip).selectinload(Trip.to_district),
        selectinload(Booking.trip).selectinload(Trip.driver).selectinload(User.driver_profile),
        selectinload(Booking.from_waypoint),
        selectinload(Booking.to_waypoint),
        selectinload(Booking.payment),
    ]


async def create_booking(db: AsyncSession, passenger: User, data: BookingCreate) -> Booking:
    # Safar mavjudmi? (row-lock: parallel bronlarda oversell oldini oladi)
    result = await db.execute(
        select(Trip)
        .options(selectinload(Trip.driver).selectinload(User.driver_profile))
        .where(Trip.id == data.trip_id)
        .with_for_update(of=Trip)
    )
    trip = result.scalar_one_or_none()
    if not trip:
        raise HTTPException(status_code=404, detail="Safar topilmadi")

    if trip.status != TripStatus.active:
        raise HTTPException(status_code=400, detail="Bu safar aktiv emas")

    # Haydovchi o'z safariga bron qila olmaydi
    if trip.driver_id == passenger.id:
        raise HTTPException(status_code=400, detail="O'z safaringizga joy band qila olmaysiz")

    # Bir safarga bir yo'lovchi faqat bir marta bron qila oladi
    existing = await db.execute(
        select(Booking).where(
            Booking.trip_id == data.trip_id,
            Booking.passenger_id == passenger.id,
            Booking.status.in_([BookingStatus.pending, BookingStatus.confirmed]),
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Bu safarni allaqachon band qilgansiz")

    # Bo'sh o'rinlar yetarlimi?
    if trip.available_seats < data.seats_count:
        raise HTTPException(
            status_code=400,
            detail=f"Yetarli o'rin yo'q. Mavjud: {trip.available_seats} ta",
        )

    # Narx hisoblash
    price_per_seat = trip.price_per_seat

    # Waypoint bilan bron
    if data.from_waypoint_id and data.to_waypoint_id:
        from_wp_result = await db.execute(
            select(TripWaypoint).where(
                TripWaypoint.id == data.from_waypoint_id,
                TripWaypoint.trip_id == trip.id,
            )
        )
        to_wp_result = await db.execute(
            select(TripWaypoint).where(
                TripWaypoint.id == data.to_waypoint_id,
                TripWaypoint.trip_id == trip.id,
            )
        )
        from_wp = from_wp_result.scalar_one_or_none()
        to_wp = to_wp_result.scalar_one_or_none()

        if not from_wp or not to_wp:
            raise HTTPException(status_code=400, detail="Waypoint topilmadi")
        if from_wp.order_index >= to_wp.order_index:
            raise HTTPException(status_code=400, detail="Noto'g'ri yo'nalish: boshlanish nuqtasi oxiridan keyin kelishi kerak")

        price_per_seat = to_wp.price_from_start - from_wp.price_from_start

    total_price = price_per_seat * data.seats_count
    commission_rate, commission_amount = calculate_commission(total_price)
    driver_amount = total_price - commission_amount

    booking = Booking(
        trip_id=trip.id,
        passenger_id=passenger.id,
        seats_count=data.seats_count,
        from_waypoint_id=data.from_waypoint_id,
        to_waypoint_id=data.to_waypoint_id,
        price_per_seat=price_per_seat,
        total_price=total_price,
        commission_rate=commission_rate,
        commission_amount=commission_amount,
        driver_amount=driver_amount,
        payment_method=data.payment_method,
        payment_status=BookingPaymentStatus.pending,
        status=BookingStatus.confirmed,  # carpooling'da avtomatik tasdiqlanadi
    )
    db.add(booking)

    # Bo'sh o'rinlarni kamaytirish
    trip.available_seats -= data.seats_count
    if trip.available_seats == 0:
        trip.status = TripStatus.full

    # ── Wallet operatsiyasi ──────────────────────────────────────────────────
    if data.payment_method == PaymentMethod.cash:
        # Naqd: hamyon bloklangan bo'lsa yangi bron qabul qilinmaydi
        driver_wallet = await wallet_service.get_or_create(db, trip.driver_id)
        if driver_wallet.is_blocked:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Haydovchi hozir naqd bronlarni qabul qila olmaydi (hamyon to'ldirilishi kerak)",
            )
        # Komissiya bron paytida EMAS — safar tugagach (complete_booking) ushiladi.
        # Shunday qilib haydovchi safardan oldin qarzga tushmaydi.

    # Haydovchiga bildirishnoma: yangi bron
    await notification_service.create(
        db,
        user_id=trip.driver_id,
        title="Yangi bron! 🎉",
        body=f"{passenger.full_name} {data.seats_count} ta joy band qildi.",
        ref_type=NotificationRefType.booking,
        ref_id=booking.id,
    )

    await db.commit()

    result = await db.execute(
        select(Booking).options(*_load_options()).where(Booking.id == booking.id)
    )
    return result.scalar_one()


async def _update_monthly_commission(db: AsyncSession, driver_id, amount: int) -> None:
    month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    result = await db.execute(
        select(DriverMonthlyCommission).where(
            DriverMonthlyCommission.driver_id == driver_id,
            DriverMonthlyCommission.month == month_start,
        )
    )
    record = result.scalar_one_or_none()
    if record:
        record.total_cash_bookings += 1
        record.total_commission += amount
    else:
        db.add(DriverMonthlyCommission(
            driver_id=driver_id,
            month=month_start,
            total_cash_bookings=1,
            total_commission=amount,
        ))


async def flag_refund_due(db: AsyncSession, booking: Booking, refund_amount: int) -> None:
    """Online to'langan bron bekor bo'ldi → refund navbatga: status + admin xabari.

    Pilotда avtomatik pul qaytarish yo'q — admin Click/Payme kabinetidan qo'lda
    qaytaradi. Bu funksiya faqat belgilaydi va adminга Telegram xabar yuboradi.
    """
    from app.services.sms_service import sms_service

    if refund_amount <= 0:
        return
    booking.payment_status = BookingPaymentStatus.refunded
    await sms_service.notify_admin(
        f"💸 <b>Refund kerak (qo'lda)</b>\n\n"
        f"Bron: <code>{booking.id}</code>\n"
        f"Miqdor: <b>{refund_amount:,} so'm</b>\n"
        f"Usul: <b>{booking.payment_method.value}</b>\n"
        f"Yo'lovchiga Click/Payme kabineti orqali qaytaring."
    )


async def cancel_booking(
    db: AsyncSession,
    booking_id: str,
    user: User,
    reason: str | None,
) -> Booking:
    import uuid as uuid_lib
    result = await db.execute(
        select(Booking)
        .options(selectinload(Booking.trip))
        .where(Booking.id == uuid_lib.UUID(booking_id))
        .with_for_update(of=Booking)
    )
    booking = result.scalar_one_or_none()
    if not booking:
        raise HTTPException(status_code=404, detail="Bron topilmadi")

    # Faqat yo'lovchi yoki haydovchi bekor qila oladi
    is_passenger = booking.passenger_id == user.id
    is_driver = booking.trip.driver_id == user.id

    if not is_passenger and not is_driver:
        raise HTTPException(status_code=403, detail="Bu bronni bekor qilish huquqingiz yo'q")

    if booking.status not in [BookingStatus.pending, BookingStatus.confirmed]:
        raise HTTPException(status_code=400, detail="Bu bronni bekor qilib bo'lmaydi")

    # departure_date/time mahalliy (Toshkent) vaqtda — solishtirish ham shunda
    now_local = now_tashkent_naive()
    departure_dt = datetime.combine(booking.trip.departure_date, booking.trip.departure_time)

    # Jo'nash vaqtidan keyin bekor qilib bo'lmaydi — safar bo'ldi/bo'lmadi
    # masalasi tasdiq (confirmation/no-show) oqimi orqali hal qilinadi
    if now_local >= departure_dt:
        raise HTTPException(
            status_code=400,
            detail="Safar vaqti boshlangan — endi bekor qilib bo'lmaydi. Safar bo'lmagan bo'lsa, tasdiq so'ralganda 'Yo'q' deb belgilang.",
        )

    hours_left = (departure_dt - now_local).total_seconds() / 3600

    # Refund faqat haqiqatan online to'langan bronda bo'ladi (naqdda pul olinmagan)
    online_paid = (
        booking.payment_method != PaymentMethod.cash
        and booking.payment_status == BookingPaymentStatus.paid
    )

    # Refund hisoblash
    if is_driver:
        # Haydovchi bekor qilsa — yo'lovchiga 100%
        refund_amount = booking.total_price if online_paid else 0
        cancelled_by = CancelledBy.driver
    else:
        # Yo'lovchi bekor qilsa
        cancelled_by = CancelledBy.passenger
        if not online_paid:
            refund_amount = 0
        elif hours_left >= 24:
            refund_amount = booking.total_price        # 100%
        else:
            refund_amount = booking.total_price // 2  # 50%

    booking.status = BookingStatus.cancelled
    booking.cancelled_by = cancelled_by
    booking.cancellation_reason = reason
    booking.cancelled_at = datetime.utcnow()
    booking.refund_amount = refund_amount
    await flag_refund_due(db, booking, refund_amount)

    # Bildirishnomalar
    if is_driver:
        # Yo'lovchiga xabar
        refund_note = f" {refund_amount:,} so'm qaytariladi." if refund_amount > 0 else ""
        await notification_service.create(
            db,
            user_id=booking.passenger_id,
            title="Bron bekor qilindi",
            body=f"Haydovchi bronni bekor qildi.{refund_note}",
            ref_type=NotificationRefType.booking,
            ref_id=booking.id,
        )
    else:
        # Haydovchiga xabar
        trip_result2 = await db.execute(
            select(Trip).where(Trip.id == booking.trip_id)
        )
        trip2 = trip_result2.scalar_one_or_none()
        if trip2:
            await notification_service.create(
                db,
                user_id=trip2.driver_id,
                title="Yo'lovchi bronni bekor qildi",
                body=f"{user.full_name} bronni bekor qildi.",
                ref_type=NotificationRefType.booking,
                ref_id=booking.id,
            )

    # O'rinlarni qaytarish (row-lock: parallel bron/bekor bilan to'qnashmasin)
    trip_result = await db.execute(
        select(Trip).where(Trip.id == booking.trip_id).with_for_update(of=Trip)
    )
    trip = trip_result.scalar_one()
    trip.available_seats += booking.seats_count
    if trip.status == TripStatus.full:
        trip.status = TripStatus.active

    # Eslatma: komissiya faqat safar tugaganda (complete_booking) ushiladi.
    # Tugamagan (pending/confirmed) bron bekor qilinsa — ushlangan komissiya yo'q,
    # demak qaytariladigan narsa ham yo'q.

    await db.commit()

    result = await db.execute(
        select(Booking).options(*_load_options()).where(Booking.id == booking.id)
    )
    return result.scalar_one()


# ─────────────────────────────────────────────────────────────────────────────
#  Ikki tomonlama safar tasdiqi
#
#  Hal qilish jadvali (qator = yo'lovchi javobi, ustun = haydovchi javobi):
#
#                 Haydovchi Ha    Haydovchi Yo'q     Haydovchi Jim
#   Yo'lovchi Ha   ✅ bo'ldi       ✅ bo'ldi+strike    ✅ bo'ldi
#   Yo'lovchi Yo'q ⚠️ nizo         ❌ bo'lmadi         ❌ bo'lmadi
#   Yo'lovchi Jim  ✅ bo'ldi       🔁→❌ (48s)          ✅ bo'ldi (48s)
#
#  - Ikkala jim → bo'ldi (komissiya himoyasi: haydovchi qochib qutula olmaydi)
#  - Haydovchi ochiq "Yo'q" + yo'lovchi jim → yo'lovchidan qayta so'raladi;
#    48 soatda javob bermasa → bo'lmadi (haydovchiga ishoniladi)
#  - Yo'lovchi "Ha" + haydovchi "Yo'q" → soxtalik ushlandi (strike + komissiya baribir)
# ─────────────────────────────────────────────────────────────────────────────


async def _apply_completion(db: AsyncSession, booking: Booking, driver_id) -> None:
    """Safar bo'ldi → status, statistika, hamyon (komissiya/daromad)."""
    booking.status = BookingStatus.completed
    booking.completed_at = datetime.utcnow()

    dp_result = await db.execute(
        select(DriverProfile).where(DriverProfile.user_id == driver_id)
    )
    dp = dp_result.scalar_one_or_none()
    if dp:
        dp.total_trips += 1

    # Online to'lov faqat payment-provider callback'i booking.payment_status=paid
    # qilganda "to'langan" hisoblanadi — bu yerda uni o'zimiz paid qilmaymiz.
    online_paid = (
        booking.payment_method != PaymentMethod.cash
        and booking.payment_status == BookingPaymentStatus.paid
    )

    if online_paid:
        # Online (haqiqatan to'langan): haydovchi ulushini hamyonga o'tkazish
        await wallet_service.add_earning(
            db, driver_id, booking.driver_amount, booking_id=booking.id
        )
    else:
        # Naqd yoki to'lanmagan online (pul qo'lda berilgan) —
        # platforma komissiyasini hamyondan ushib qolish
        booking.payment_status = BookingPaymentStatus.paid
        await wallet_service.deduct_commission(
            db, driver_id, booking.commission_amount, booking_id=booking.id
        )
        await _update_monthly_commission(db, driver_id, booking.commission_amount)


async def _apply_not_happened(db: AsyncSession, booking: Booking) -> None:
    """Safar bo'lmadi → komissiya yo'q (tugamadi). Online to'langan bo'lsa yo'lovchiga qaytarma."""
    online_paid = (
        booking.payment_method != PaymentMethod.cash
        and booking.payment_status == BookingPaymentStatus.paid
    )
    refund = booking.total_price if online_paid else 0
    if booking.driver_confirmed == CONFIRM_NO:
        # Haydovchi "kelmadi" dedi → no-show
        booking.status = BookingStatus.no_show
        booking.no_show_reported_at = datetime.utcnow()
    else:
        # Yo'lovchi "bo'lmadi" dedi (haydovchi jim) → bekor
        booking.status = BookingStatus.cancelled
        booking.cancelled_by = CancelledBy.passenger
        booking.cancelled_at = datetime.utcnow()
    booking.refund_amount = refund
    await flag_refund_due(db, booking, refund)
    # Komissiya ushilmaydi — safar tugamadi


async def _record_fake_confirmation(db: AsyncSession, driver_id) -> None:
    """Soxta belgilash ushlandi → strike +1; chegaraga yetganda jarima pauzasi."""
    dp_result = await db.execute(
        select(DriverProfile).where(DriverProfile.user_id == driver_id)
    )
    dp = dp_result.scalar_one_or_none()
    if not dp:
        return

    now = datetime.utcnow()
    # Davriy reset — oxirgi resetdan FAKE_CONFIRMATION_RESET_MONTHS oy o'tgan bo'lsa nolga
    reset_after = timedelta(days=30 * settings.FAKE_CONFIRMATION_RESET_MONTHS)
    if dp.fake_count_reset_at is None or (now - dp.fake_count_reset_at) > reset_after:
        dp.fake_confirmation_count = 0
        dp.fake_count_reset_at = now

    dp.fake_confirmation_count += 1

    if dp.fake_confirmation_count >= settings.FAKE_CONFIRMATION_BLOCK_THRESHOLD:
        # Jarima pauzasi: e'lonlar belgilangan kunga qidiruvda ko'rinmaydi
        dp.paused_until = now + timedelta(days=settings.FAKE_CONFIRMATION_PAUSE_DAYS)
        dp.fake_confirmation_count = 0          # penaltidan keyin nolga
        dp.fake_count_reset_at = now
        await notification_service.create(
            db,
            user_id=driver_id,
            title="E'lonlaringiz vaqtincha yashirildi ⛔",
            body=(
                f"Soxta safar belgilash takror aniqlandi. E'lonlaringiz "
                f"{settings.FAKE_CONFIRMATION_PAUSE_DAYS} kunga qidiruvda ko'rinmaydi."
            ),
            ref_type=NotificationRefType.system,
        )
    else:
        left = settings.FAKE_CONFIRMATION_BLOCK_THRESHOLD - dp.fake_confirmation_count
        await notification_service.create(
            db,
            user_id=driver_id,
            title="Ogohlantirish: soxta belgilash ⚠️",
            body=(
                "Yo'lovchi safar bo'lganini tasdiqladi, lekin siz 'bo'lmadi' degandingiz. "
                f"Komissiya baribir hisoblandi. Yana {left} marta takrorlansa e'lonlaringiz vaqtincha yashiriladi."
            ),
            ref_type=NotificationRefType.system,
        )


async def _resolve_confirmation(db: AsyncSession, booking: Booking, driver_id, final: bool) -> bool:
    """Tasdiq holatini hal qilishga urinish. Hal bo'lsa True qaytaradi.

    `final=False` — qo'lda tasdiq paytida (faqat aniq holatlar hal qilinadi).
    `final=True`  — 48 soat o'tdi, qolgan (jim) holatlar ham yopiladi.
    """
    d = booking.driver_confirmed
    p = booking.passenger_confirmed

    if p == CONFIRM_YES:
        # Yo'lovchi "bo'ldi" dedi → bo'ldi (haydovchi inkor qilsa ham)
        await _apply_completion(db, booking, driver_id)
        if d == CONFIRM_NO:
            await _record_fake_confirmation(db, driver_id)  # soxtalik ushlandi
        return True

    if p == CONFIRM_NO:
        if d == CONFIRM_YES:
            booking.status = BookingStatus.disputed       # nizo → admin
            return True
        if d == CONFIRM_NO:
            await _apply_not_happened(db, booking)         # ikkalasi "yo'q" → bo'lmadi
            return True
        # Haydovchi hali jim — u "Ha" desa nizo bo'lishi mumkin, shuning uchun kutamiz
        if not final:
            return False
        await _apply_not_happened(db, booking)             # 48s: yo'lovchi yo'q + haydovchi jim → bo'lmadi
        return True

    # Yo'lovchi jim (p is None)
    if d == CONFIRM_YES:
        # Haydovchi "bo'ldi" dedi (komissiyaga rozi) → darhol bo'ldi
        await _apply_completion(db, booking, driver_id)
        return True

    # p jim, d ∈ {Yo'q, jim} — yo'lovchidan javob kutiladi
    if not final:
        return False

    # ── 48 soat o'tdi (avtomatik hal) ──
    if d == CONFIRM_NO:
        await _apply_not_happened(db, booking)            # qayta so'ralgan, jim qoldi → haydovchiga ishoniladi
    else:
        await _apply_completion(db, booking, driver_id)   # ikkala jim → bo'ldi (komissiya himoyasi)
    return True


async def _ensure_window_open(db: AsyncSession, booking: Booking, trip: Trip) -> None:
    """Tasdiq oynasini ochish: so'rov vaqtini belgilash + ikki tomonga bildirishnoma."""
    if booking.confirmation_requested_at is not None:
        return
    booking.confirmation_requested_at = datetime.utcnow()
    if booking.status == BookingStatus.confirmed:
        booking.status = BookingStatus.awaiting_confirmation
    for uid in (booking.passenger_id, trip.driver_id):
        await notification_service.create(
            db,
            user_id=uid,
            title="Safaringiz bo'ldimi?",
            body="Iltimos tasdiqlang: safar amalga oshdimi? (Ha / Yo'q)",
            ref_type=NotificationRefType.booking,
            ref_id=booking.id,
        )


async def confirm_booking(
    db: AsyncSession, booking_id: str, user: User, confirmed: bool
) -> Booking:
    """Yo'lovchi yoki haydovchi safar bo'lgan/bo'lmaganini tasdiqlaydi."""
    import uuid as uuid_lib
    result = await db.execute(
        select(Booking)
        .options(selectinload(Booking.trip))
        .where(Booking.id == uuid_lib.UUID(booking_id))
        .with_for_update(of=Booking)
    )
    booking = result.scalar_one_or_none()
    if not booking:
        raise HTTPException(status_code=404, detail="Bron topilmadi")

    is_driver = booking.trip.driver_id == user.id
    is_passenger = booking.passenger_id == user.id
    if not is_driver and not is_passenger:
        raise HTTPException(status_code=403, detail="Bu bronni tasdiqlash huquqingiz yo'q")

    if booking.status not in (BookingStatus.confirmed, BookingStatus.awaiting_confirmation):
        raise HTTPException(status_code=400, detail="Bu bron tasdiq bosqichida emas")

    # Safar vaqti hali kelmagan bo'lsa tasdiqlab bo'lmaydi (mahalliy vaqtda)
    departure_dt = datetime.combine(booking.trip.departure_date, booking.trip.departure_time)
    if now_tashkent_naive() < departure_dt:
        raise HTTPException(status_code=400, detail="Safar vaqti hali kelmagan")

    # Tasdiq oynasini boshlash (agar hali boshlanmagan bo'lsa)
    if booking.confirmation_requested_at is None:
        booking.confirmation_requested_at = datetime.utcnow()
    if booking.status == BookingStatus.confirmed:
        booking.status = BookingStatus.awaiting_confirmation

    answer = CONFIRM_YES if confirmed else CONFIRM_NO
    if is_driver:
        booking.driver_confirmed = answer
        # Haydovchi "yo'q" dedi-yu yo'lovchi hali jim → yo'lovchidan qayta so'rash
        if answer == CONFIRM_NO and booking.passenger_confirmed is None:
            booking.driver_denied_reprompt_at = datetime.utcnow()
            await notification_service.create(
                db,
                user_id=booking.passenger_id,
                title="Haydovchi safar bo'lmadi dedi",
                body="Agar safar bo'lgan bo'lsa, iltimos e'tiroz bildiring — aks holda safar bo'lmagan deb hisoblanadi.",
                ref_type=NotificationRefType.booking,
                ref_id=booking.id,
            )
    else:
        booking.passenger_confirmed = answer
        # Yo'lovchi "yo'q" dedi-yu haydovchi hali jim → haydovchiga xabar (u nizo ochishi mumkin)
        if answer == CONFIRM_NO and booking.driver_confirmed is None:
            await notification_service.create(
                db,
                user_id=booking.trip.driver_id,
                title="Yo'lovchi safar bo'lmadi dedi",
                body="Agar safar bo'lgan bo'lsa, tasdiqlang — aks holda safar bo'lmagan deb hisoblanadi.",
                ref_type=NotificationRefType.booking,
                ref_id=booking.id,
            )

    await _resolve_confirmation(db, booking, booking.trip.driver_id, final=False)

    await db.commit()

    result = await db.execute(
        select(Booking).options(*_load_options()).where(Booking.id == booking.id)
    )
    return result.scalar_one()


async def complete_booking(db: AsyncSession, booking_id: str, driver: User) -> Booking:
    """Haydovchi 'Tugatish' bosdi = safar bo'ldi deb tasdiqlash."""
    return await confirm_booking(db, booking_id, driver, confirmed=True)


async def report_no_show(db: AsyncSession, booking_id: str, driver: User) -> Booking:
    """Haydovchi 'Kelmadi' bosdi = safar bo'lmadi deb belgilash."""
    return await confirm_booking(db, booking_id, driver, confirmed=False)


# ─── Celery uchun ommaviy hal qilish ────────────────────────────────────────

async def request_due_confirmations(db: AsyncSession) -> int:
    """Jo'nash + grace o'tgan tasdiqlangan bronlar uchun tasdiq oynasini ochadi."""
    now_local = now_tashkent_naive()
    grace = timedelta(hours=settings.CONFIRMATION_GRACE_HOURS)

    rows = (await db.execute(
        select(Booking).options(selectinload(Booking.trip)).where(
            Booking.status == BookingStatus.confirmed,
            Booking.confirmation_requested_at.is_(None),
        )
    )).scalars().all()

    opened = 0
    for booking in rows:
        trip = booking.trip
        departure_dt = datetime.combine(trip.departure_date, trip.departure_time)
        if now_local < departure_dt + grace:
            continue
        await _ensure_window_open(db, booking, trip)
        opened += 1
    if opened:
        await db.commit()
    return opened


async def admin_resolve_dispute(
    db: AsyncSession, booking_id: str, happened: bool, admin: User
) -> Booking:
    """Admin nizoni hal qiladi (yo'lovchi "Yo'q" + haydovchi "Ha").

    happened=True  → safar bo'ldi (haydovchi haq edi).
    happened=False → safar bo'lmadi: haydovchi yolg'on "bo'ldi" degan → strike.
    """
    import uuid as uuid_lib
    from app.models.admin import AdminAction
    from app.models.enums import AdminActionType

    result = await db.execute(
        select(Booking).options(selectinload(Booking.trip)).where(
            Booking.id == uuid_lib.UUID(booking_id)
        ).with_for_update(of=Booking)
    )
    booking = result.scalar_one_or_none()
    if not booking:
        raise HTTPException(status_code=404, detail="Bron topilmadi")
    if booking.status != BookingStatus.disputed:
        raise HTTPException(status_code=400, detail="Bu bron nizo holatida emas")

    driver_id = booking.trip.driver_id

    if happened:
        await _apply_completion(db, booking, driver_id)
        title, body = "Nizo hal qilindi: safar bo'ldi deb tasdiqlandi", \
            "Admin tekshiruvidan so'ng safar amalga oshgan deb belgilandi."
    else:
        await _apply_not_happened(db, booking)
        await _record_fake_confirmation(db, driver_id)   # haydovchi yolg'on "bo'ldi" degan
        db.add(AdminAction(
            admin_id=admin.id,
            action_type=AdminActionType.warn_driver,
            target_user_id=driver_id,
            reason="Nizo: safar bo'lmagan deb topildi (soxta tasdiq)",
        ))
        title, body = "Nizo hal qilindi: safar bo'lmagan deb topildi", \
            "Admin tekshiruvidan so'ng safar amalga oshmagan deb belgilandi."

    # Ikkala tomonga xabar
    for uid in (booking.passenger_id, driver_id):
        await notification_service.create(
            db, user_id=uid, title=title, body=body,
            ref_type=NotificationRefType.booking, ref_id=booking.id,
        )

    await db.commit()

    result = await db.execute(
        select(Booking).options(*_load_options()).where(Booking.id == booking.id)
    )
    return result.scalar_one()


async def resolve_due_confirmations(db: AsyncSession) -> int:
    """48 soatlik oynasi o'tgan, tasdiq kutilayotgan bronlarni avtomatik hal qiladi."""
    cutoff = datetime.utcnow() - timedelta(hours=settings.CONFIRMATION_WINDOW_HOURS)
    rows = (await db.execute(
        select(Booking).options(selectinload(Booking.trip)).where(
            Booking.status == BookingStatus.awaiting_confirmation,
            Booking.confirmation_requested_at.is_not(None),
            Booking.confirmation_requested_at <= cutoff,
        ).with_for_update(of=Booking, skip_locked=True)
    )).scalars().all()

    resolved = 0
    for booking in rows:
        if await _resolve_confirmation(db, booking, booking.trip.driver_id, final=True):
            resolved += 1
    if resolved:
        await db.commit()
    return resolved


async def get_my_bookings(db: AsyncSession, passenger: User) -> list[Booking]:
    result = await db.execute(
        select(Booking)
        .options(*_load_options())
        .where(Booking.passenger_id == passenger.id)
        .order_by(Booking.created_at.desc())
    )
    return result.scalars().all()


async def get_driver_bookings(db: AsyncSession, driver: User) -> list[Booking]:
    """Haydovchi safarlariga kelgan bronlar."""
    result = await db.execute(
        select(Booking)
        .options(*_load_options())
        .join(Trip, Booking.trip_id == Trip.id)
        .where(Trip.driver_id == driver.id)
        .order_by(Booking.created_at.desc())
    )
    return result.scalars().all()


async def get_booking(db: AsyncSession, booking_id: str, user: User) -> Booking:
    import uuid as uuid_lib
    result = await db.execute(
        select(Booking)
        .options(*_load_options(), selectinload(Booking.trip))
        .where(Booking.id == uuid_lib.UUID(booking_id))
    )
    booking = result.scalar_one_or_none()
    if not booking:
        raise HTTPException(status_code=404, detail="Bron topilmadi")

    # Faqat tegishli tomonlar ko'ra oladi
    is_passenger = booking.passenger_id == user.id
    is_driver = booking.trip.driver_id == user.id
    if not is_passenger and not is_driver and not user.is_admin:
        raise HTTPException(status_code=403, detail="Ruxsat yo'q")

    return booking


def serialize_booking(booking: Booking, current_user: User, trip_serializer=None) -> dict:
    """
    Telefon raqamni faqat confirmed/completed holatda ko'rsatish.
    """
    show_phone = booking.status in [
        BookingStatus.confirmed, BookingStatus.awaiting_confirmation,
        BookingStatus.disputed, BookingStatus.completed, BookingStatus.no_show,
    ]

    # Joriy foydalanuvchi hali safar tasdig'ini berishi kerakmi?
    needs_my_confirmation = False
    if booking.status == BookingStatus.awaiting_confirmation and booking.trip is not None:
        if booking.trip.driver_id == current_user.id and booking.driver_confirmed is None:
            needs_my_confirmation = True
        elif booking.passenger_id == current_user.id and booking.passenger_confirmed is None:
            needs_my_confirmation = True

    # Trip qisqacha ma'lumoti (marshrut, sana, haydovchi) — dashboard/ro'yxat uchun
    trip = booking.trip
    trip_data = None
    if trip is not None:
        dp = getattr(trip.driver, "driver_profile", None) if getattr(trip, "driver", None) else None
        def _loc(x):
            return {"id": x.id, "name_uz": x.name_uz, "name_ru": x.name_ru} if x else None
        trip_data = {
            "id": trip.id,
            "from_region": _loc(trip.from_region),
            "to_region": _loc(trip.to_region),
            "from_district": _loc(trip.from_district),
            "to_district": _loc(trip.to_district),
            "departure_date": trip.departure_date,
            "departure_time": trip.departure_time,
            "price_per_seat": trip.price_per_seat,
            "status": trip.status,
            "driver": {
                "id": trip.driver.id,
                "full_name": trip.driver.full_name,
                "profile_photo": trip.driver.profile_photo,
                "talk_level": trip.driver.talk_level,
                "rating_avg": dp.rating_avg if dp else 0.0,
                "rating_count": dp.rating_count if dp else 0,
                "total_trips": dp.total_trips if dp else 0,
            } if getattr(trip, "driver", None) else None,
        }

    return {
        "id": booking.id,
        "trip_id": booking.trip_id,
        "trip": trip_data,
        "passenger": {
            "id": booking.passenger.id,
            "full_name": booking.passenger.full_name,
            "phone": booking.passenger.phone if show_phone else None,
            "profile_photo": booking.passenger.profile_photo,
        },
        "seats_count": booking.seats_count,
        "price_per_seat": booking.price_per_seat,
        "total_price": booking.total_price,
        "commission_rate": booking.commission_rate,
        "commission_amount": booking.commission_amount,
        "driver_amount": booking.driver_amount,
        "payment_method": booking.payment_method,
        "payment_status": booking.payment_status,
        "status": booking.status,
        "cancelled_by": booking.cancelled_by,
        "cancellation_reason": booking.cancellation_reason,
        "cancelled_at": booking.cancelled_at,
        "refund_amount": booking.refund_amount,
        "no_show_reported_at": booking.no_show_reported_at,
        "completed_at": booking.completed_at,
        "driver_confirmed": booking.driver_confirmed,
        "passenger_confirmed": booking.passenger_confirmed,
        "confirmation_requested_at": booking.confirmation_requested_at,
        "needs_my_confirmation": needs_my_confirmation,
        "created_at": booking.created_at,
        "driver_phone": booking.trip.driver.phone if (show_phone and hasattr(booking.trip, "driver")) else None,
    }
