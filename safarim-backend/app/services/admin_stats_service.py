"""Admin dashboard statistikasi.

Ilgari dashboard yettita "jami" raqamdan iborat edi: ular hech qachon
o'zgarmaydi (faqat o'sadi) va ulardan sayt yaxshi ketyaptimi yoki yo'qmi degan
savolga javob chiqmasdi. Bu yerda uchta narsa hisoblanadi:

  1. **Davr** ko'rsatkichlari va o'tgan shuncha kun bilan solishtirish —
     "oxirgi 30 kunda 12 ta safar, avvalgi 30 kunda 7 ta edi".
  2. **Sifat** ko'rsatkichlari — safarlarning nechtasi yakunlangan, nechtasi
     bekor bo'lgan, o'rinlar qanchalik to'lgan. Katta "jami" raqam yomon
     ko'rsatkichni yashirib turishi mumkin.
  3. **Ish navbati** — admin bugun nima qilishi kerak (kutayotgan ariza,
     nizo, to'lanmagan komissiya, bloklangan hamyon).

Kunlik qatorlar Toshkent vaqtida bo'linadi: `created_at` UTC'da saqlanadi,
UTC yarim tuni esa mahalliy soat 05:00 — bo'lmasa kechqurungi yozilishlar
ertangi kunga tushib ketardi.
"""
from datetime import date, datetime, timedelta

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.admin import AdminAction
from app.models.booking import Booking
from app.models.driver import DriverProfile
from app.models.enums import BookingStatus, DriverStatus, TripStatus
from app.models.location import Region
from app.models.payment import DriverMonthlyCommission
from app.models.trip import Trip
from app.models.user import User
from app.models.wallet import DriverWallet

# O'zbekistonda yozgi vaqt yo'q — doimiy +05:00
_TASHKENT_SHIFT = text("interval '5 hours'")

MAX_DAYS = 180
DEFAULT_DAYS = 30


def _local_day(column):
    """UTC timestamp'ni Toshkent kuniga aylantiradi (guruhlash uchun)."""
    return func.date(column + _TASHKENT_SHIFT)


def _delta_pct(current: float | int | None, previous: float | int | None) -> float | None:
    """O'sish foizi. Avvalgi davr nol bo'lsa foiz ma'nosiz — None qaytadi."""
    if not previous:
        return None
    return round((float(current or 0) - float(previous)) / float(previous) * 100, 1)


def _metric(total, period, previous) -> dict:
    return {
        "total": int(total or 0),
        "period": int(period or 0),
        "prev": int(previous or 0),
        "delta_pct": _delta_pct(period, previous),
    }


async def dashboard(db: AsyncSession, days: int = DEFAULT_DAYS) -> dict:
    days = max(1, min(days, MAX_DAYS))

    now = datetime.utcnow()
    start = now - timedelta(days=days)
    prev_start = now - timedelta(days=days * 2)

    async def count(model, *conditions):
        return await db.scalar(select(func.count(model.id)).where(*conditions)) or 0

    async def total_sum(column, *conditions):
        return await db.scalar(select(func.coalesce(func.sum(column), 0)).where(*conditions)) or 0

    # ── KPI ──────────────────────────────────────────────────────────────────
    users = _metric(
        await count(User),
        await count(User, User.created_at >= start),
        await count(User, User.created_at >= prev_start, User.created_at < start),
    )
    drivers = _metric(
        await count(DriverProfile, DriverProfile.status == DriverStatus.approved),
        await count(DriverProfile, DriverProfile.verified_at >= start),
        await count(
            DriverProfile,
            DriverProfile.verified_at >= prev_start,
            DriverProfile.verified_at < start,
        ),
    )
    trips = _metric(
        await count(Trip),
        await count(Trip, Trip.created_at >= start),
        await count(Trip, Trip.created_at >= prev_start, Trip.created_at < start),
    )
    bookings = _metric(
        await count(Booking),
        await count(Booking, Booking.created_at >= start),
        await count(Booking, Booking.created_at >= prev_start, Booking.created_at < start),
    )
    completed = _metric(
        await count(Booking, Booking.status == BookingStatus.completed),
        await count(Booking, Booking.status == BookingStatus.completed, Booking.completed_at >= start),
        await count(
            Booking,
            Booking.status == BookingStatus.completed,
            Booking.completed_at >= prev_start,
            Booking.completed_at < start,
        ),
    )

    # Pul: faqat yakunlangan safarlar hisobga olinadi — band qilish bekor
    # bo'lishi mumkin, u holda hech kim hech kimga pul to'lamaydi.
    done = Booking.status == BookingStatus.completed
    gmv = _metric(
        await total_sum(Booking.total_price, done),
        await total_sum(Booking.total_price, done, Booking.completed_at >= start),
        await total_sum(
            Booking.total_price, done,
            Booking.completed_at >= prev_start, Booking.completed_at < start,
        ),
    )
    commission = _metric(
        await total_sum(Booking.commission_amount, done),
        await total_sum(Booking.commission_amount, done, Booking.completed_at >= start),
        await total_sum(
            Booking.commission_amount, done,
            Booking.completed_at >= prev_start, Booking.completed_at < start,
        ),
    )

    # ── Sifat ────────────────────────────────────────────────────────────────
    finished_states = [
        BookingStatus.completed,
        BookingStatus.cancelled,
        BookingStatus.no_show,
    ]
    finished = await count(
        Booking, Booking.status.in_(finished_states), Booking.created_at >= start
    )
    cancelled = await count(
        Booking, Booking.status == BookingStatus.cancelled, Booking.created_at >= start
    )
    completed_in_period = await count(
        Booking, Booking.status == BookingStatus.completed, Booking.created_at >= start
    )

    seats_offered = await db.scalar(
        select(func.coalesce(func.sum(Trip.total_seats), 0)).where(Trip.created_at >= start)
    ) or 0
    seats_taken = await db.scalar(
        select(func.coalesce(func.sum(Booking.seats_count), 0))
        .select_from(Booking)
        .join(Trip, Booking.trip_id == Trip.id)
        .where(
            Trip.created_at >= start,
            Booking.status.notin_([BookingStatus.cancelled, BookingStatus.no_show]),
        )
    ) or 0
    avg_price = await db.scalar(
        select(func.avg(Booking.price_per_seat)).where(Booking.created_at >= start)
    )

    def _rate(part, whole) -> float | None:
        return round(part / whole * 100, 1) if whole else None

    quality = {
        "completion_rate": _rate(completed_in_period, finished),
        "cancellation_rate": _rate(cancelled, finished),
        "seat_fill_rate": _rate(seats_taken, seats_offered),
        "avg_price": int(avg_price) if avg_price else None,
        "finished_bookings": int(finished),
    }

    # ── Ish navbati ──────────────────────────────────────────────────────────
    alerts = {
        "pending_drivers": await count(DriverProfile, DriverProfile.status == DriverStatus.pending),
        "open_disputes": await count(Booking, Booking.status == BookingStatus.disputed),
        "awaiting_confirmation": await count(
            Booking, Booking.status == BookingStatus.awaiting_confirmation
        ),
        "unpaid_commission": int(await db.scalar(
            select(func.coalesce(func.sum(DriverMonthlyCommission.total_commission), 0))
            .where(DriverMonthlyCommission.is_paid.is_(False))
        ) or 0),
        "blocked_wallets": await db.scalar(
            select(func.count(DriverWallet.id)).where(DriverWallet.is_blocked.is_(True))
        ) or 0,
        "active_trips": await count(
            Trip, Trip.status.in_([TripStatus.active, TripStatus.full, TripStatus.started])
        ),
    }

    # ── Kunlik qatorlar (grafik uchun) ───────────────────────────────────────
    series = await _daily_series(db, start=start, days=days)

    return {
        "period_days": days,
        "range": {"from": (now - timedelta(days=days)).date().isoformat(), "to": now.date().isoformat()},
        "kpi": {
            "users": users,
            "drivers": drivers,
            "trips": trips,
            "bookings": bookings,
            "completed": completed,
            "gmv": gmv,
            "commission": commission,
        },
        "quality": quality,
        "alerts": alerts,
        "series": series,
        "top_routes": await _top_routes(db, start=start),
        "recent_actions": await _recent_actions(db),
    }


async def _daily_series(db: AsyncSession, start: datetime, days: int) -> list[dict]:
    """Har kun uchun: ro'yxatdan o'tganlar, e'lon qilingan safarlar, band qilishlar.

    Uchta guruhlangan so'rov + Python'da birlashtirish. Kun bo'sh bo'lsa ham
    qatorda turadi (nol bilan) — aks holda grafikda kunlar sakrab ketardi.
    """
    async def by_day(model) -> dict[date, int]:
        day = _local_day(model.created_at).label("day")
        rows = await db.execute(
            select(day, func.count(model.id))
            .where(model.created_at >= start)
            .group_by(day)
        )
        return {r[0]: int(r[1]) for r in rows.all()}

    users_by_day = await by_day(User)
    trips_by_day = await by_day(Trip)
    bookings_by_day = await by_day(Booking)

    today = (datetime.utcnow() + timedelta(hours=5)).date()
    out: list[dict] = []
    for i in range(days - 1, -1, -1):
        d = today - timedelta(days=i)
        out.append({
            "date": d.isoformat(),
            "users": users_by_day.get(d, 0),
            "trips": trips_by_day.get(d, 0),
            "bookings": bookings_by_day.get(d, 0),
        })
    return out


async def _top_routes(db: AsyncSession, start: datetime, limit: int = 6) -> list[dict]:
    """Davr ichida eng ko'p e'lon qilingan yo'nalishlar (+ band qilishlar soni)."""
    from_region = Region.__table__.alias("from_region")
    to_region = Region.__table__.alias("to_region")

    booking_count = func.count(Booking.id.distinct())
    rows = await db.execute(
        select(
            from_region.c.name_uz,
            to_region.c.name_uz,
            func.count(Trip.id.distinct()).label("trips"),
            booking_count.label("bookings"),
        )
        .select_from(Trip)
        .join(from_region, Trip.from_region_id == from_region.c.id)
        .join(to_region, Trip.to_region_id == to_region.c.id)
        .outerjoin(
            Booking,
            (Booking.trip_id == Trip.id)
            & (Booking.status != BookingStatus.cancelled),
        )
        .where(Trip.created_at >= start)
        .group_by(from_region.c.name_uz, to_region.c.name_uz)
        .order_by(func.count(Trip.id.distinct()).desc())
        .limit(limit)
    )
    return [
        {"from": r[0], "to": r[1], "trips": int(r[2]), "bookings": int(r[3])}
        for r in rows.all()
    ]


async def _recent_actions(db: AsyncSession, limit: int = 8) -> list[dict]:
    """Oxirgi admin harakatlari — kim nima qilgani ko'rinib tursin."""
    rows = await db.execute(
        select(AdminAction)
        .options(
            selectinload(AdminAction.admin),
            selectinload(AdminAction.target_user),
        )
        .order_by(AdminAction.created_at.desc())
        .limit(limit)
    )
    out = []
    for a in rows.scalars().all():
        out.append({
            "at": a.created_at.isoformat(),
            "admin": a.admin.full_name if a.admin else "—",
            "action": a.action_type.value,
            "target": a.target_user.full_name if a.target_user else None,
            "reason": a.reason,
        })
    return out
