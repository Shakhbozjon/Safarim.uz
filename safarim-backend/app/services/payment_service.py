import hashlib
import base64
import uuid as uuid_lib
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException

from app.models.booking import Booking
from app.models.payment import Payment, DriverMonthlyCommission
from app.models.wallet import WalletTopupPayment
from app.models.trip import Trip
from app.models.enums import (
    PaymentMethod, PaymentStatus, BookingStatus, BookingPaymentStatus,
)
from app.core.config import settings
from app.core.security import calculate_commission

# Wallet topup transaction param prefiksi (booking ID dan ajratish uchun)
WALLET_TOPUP_PREFIX = "wt_"


# ─── URL generatorlar ─────────────────────────────────────────────────────────

def get_click_url(booking_id: str, amount: int) -> str:
    """Click to'lov sahifasi URL."""
    return (
        f"https://my.click.uz/services/pay"
        f"?service_id={settings.CLICK_SERVICE_ID}"
        f"&merchant_id={settings.CLICK_MERCHANT_ID}"
        f"&amount={amount}"
        f"&transaction_param={booking_id}"
        f"&return_url=https://safarim.uz/payment/result"
        f"&card_type=uzcard"
    )


def get_payme_url(booking_id: str, amount: int) -> str:
    """Payme checkout URL. Amount tiyinda (1 so'm = 100 tiyin)."""
    params = f"m={settings.PAYME_ID};ac.booking_id={booking_id};a={amount * 100}"
    encoded = base64.b64encode(params.encode()).decode()
    return f"https://checkout.paycom.uz/{encoded}"


# ─── Wallet topup URL generatorlar ───────────────────────────────────────────

def get_click_wallet_url(topup_id: str, amount: int) -> str:
    """Click to'lov URL — hamyon to'ldirish uchun. transaction_param = wt_{topup_id}"""
    return (
        f"https://my.click.uz/services/pay"
        f"?service_id={settings.CLICK_SERVICE_ID}"
        f"&merchant_id={settings.CLICK_MERCHANT_ID}"
        f"&amount={amount}"
        f"&transaction_param={WALLET_TOPUP_PREFIX}{topup_id}"
        f"&return_url=https://safarim.uz/driver?topup=done"
        f"&card_type=uzcard"
    )


def get_payme_wallet_url(topup_id: str, amount: int) -> str:
    """Payme checkout URL — hamyon to'ldirish uchun."""
    params = f"m={settings.PAYME_ID};ac.topup_id={topup_id};a={amount * 100}"
    encoded = base64.b64encode(params.encode()).decode()
    return f"https://checkout.paycom.uz/{encoded}"


async def initiate_wallet_topup(
    db: AsyncSession,
    driver_id: uuid_lib.UUID,
    amount: int,
    method: str,  # "click" | "payme"
) -> dict:
    """Hamyon to'ldirish: WalletTopupPayment yaratish + to'lov URL qaytarish."""
    topup = WalletTopupPayment(
        driver_id=driver_id,
        amount=amount,
        method=method,
        status="pending",
    )
    db.add(topup)
    await db.commit()
    await db.refresh(topup)

    topup_id = str(topup.id)
    if method == "click":
        url = get_click_wallet_url(topup_id, amount)
    else:
        url = get_payme_wallet_url(topup_id, amount)

    return {"payment_url": url, "topup_id": topup_id, "amount": amount}


async def _complete_wallet_topup(db: AsyncSession, topup_id: str, transaction_id: str) -> bool:
    """
    Click/Payme callback muvaffaqiyatli bo'lganda hamyonni to'ldirish.
    Qaytaradi: True (birinchi marta), False (allaqachon bajarilgan)
    """
    from app.services import wallet_service
    try:
        uid = uuid_lib.UUID(topup_id)
    except ValueError:
        return False

    result = await db.execute(
        select(WalletTopupPayment).where(WalletTopupPayment.id == uid)
    )
    topup = result.scalar_one_or_none()
    if not topup:
        return False
    if topup.status == "completed":
        return False  # Idempotent

    topup.status = "completed"
    topup.transaction_id = transaction_id
    topup.completed_at = datetime.utcnow()

    await wallet_service.topup(db, topup.driver_id, topup.amount, check_min=False)
    # wallet_service.topup ichida db.commit qilinmaydi — caller commit qiladi
    return True


# ─── Click verifikatsiya ───────────────────────────────────────────────────────

def verify_click_sign(
    click_trans_id: int,
    service_id: int,
    merchant_trans_id: str,
    amount: float,
    action: int,
    sign_time: str,
    sign_string: str,
) -> bool:
    raw = (
        f"{click_trans_id}"
        f"{service_id}"
        f"{settings.CLICK_SECRET_KEY}"
        f"{merchant_trans_id}"
        f"{amount}"
        f"{action}"
        f"{sign_time}"
    )
    expected = hashlib.md5(raw.encode()).hexdigest()
    return expected == sign_string


# ─── Payme verifikatsiya ───────────────────────────────────────────────────────

def verify_payme_auth(authorization: str) -> bool:
    try:
        scheme, credentials = authorization.split(" ", 1)
        if scheme.lower() != "basic":
            return False
        decoded = base64.b64decode(credentials).decode()
        login, key = decoded.split(":", 1)
        return login == "Paycom" and key == settings.PAYME_KEY
    except Exception:
        return False


# ─── To'lov boshlash ──────────────────────────────────────────────────────────

async def initiate_payment(
    db: AsyncSession,
    user,
    booking_id: str,
    method: PaymentMethod,
) -> dict:
    result = await db.execute(
        select(Booking)
        .where(Booking.id == uuid_lib.UUID(booking_id))
    )
    booking = result.scalar_one_or_none()
    if not booking:
        raise HTTPException(status_code=404, detail="Bron topilmadi")
    if booking.passenger_id != user.id:
        raise HTTPException(status_code=403, detail="Bu bron sizniki emas")
    if booking.status not in [BookingStatus.pending, BookingStatus.confirmed]:
        raise HTTPException(status_code=400, detail="Bu bron uchun to'lov qilib bo'lmaydi")
    if booking.payment_status == BookingPaymentStatus.paid:
        raise HTTPException(status_code=400, detail="Bu bron allaqachon to'langan")

    # Mavjud payment bormi?
    existing = await db.execute(
        select(Payment).where(Payment.booking_id == booking.id)
    )
    payment = existing.scalar_one_or_none()

    if not payment:
        rate, commission = calculate_commission(booking.total_price)
        payment = Payment(
            booking_id=booking.id,
            amount=booking.total_price,
            commission=commission,
            driver_amount=booking.total_price - commission,
            method=method,
            status=PaymentStatus.pending,
        )
        db.add(payment)
        await db.commit()
        await db.refresh(payment)

    if method == PaymentMethod.click:
        url = get_click_url(str(booking.id), booking.total_price)
    else:
        url = get_payme_url(str(booking.id), booking.total_price)

    return {
        "payment_url": url,
        "booking_id": str(booking.id),
        "amount": booking.total_price,
        "method": method,
    }


# ─── Click callback ───────────────────────────────────────────────────────────

async def handle_click_callback(db: AsyncSession, data: dict) -> dict:
    """
    action=0 → PREPARE: tekshirish
    action=1 → COMPLETE: to'lovni tasdiqlash
    """
    booking_id = data["merchant_trans_id"]
    action = data["action"]
    click_trans_id = data["click_trans_id"]
    amount = data["amount"]
    sign_time = data["sign_time"]
    sign_string = data["sign_string"]
    service_id = data["service_id"]

    # Imzo tekshirish
    if not verify_click_sign(
        click_trans_id, service_id, booking_id,
        amount, action, sign_time, sign_string
    ):
        return {"click_trans_id": click_trans_id, "merchant_trans_id": booking_id,
                "error": -1, "error_note": "SIGN CHECK FAILED"}

    # Wallet topup ekanmi?
    if booking_id.startswith(WALLET_TOPUP_PREFIX):
        topup_id = booking_id[len(WALLET_TOPUP_PREFIX):]
        try:
            topup_uid = uuid_lib.UUID(topup_id)
        except ValueError:
            return {"click_trans_id": click_trans_id, "merchant_trans_id": booking_id,
                    "error": -5, "error_note": "TOPUP NOT FOUND"}
        result = await db.execute(
            select(WalletTopupPayment).where(WalletTopupPayment.id == topup_uid)
        )
        topup = result.scalar_one_or_none()
        if not topup:
            return {"click_trans_id": click_trans_id, "merchant_trans_id": booking_id,
                    "error": -5, "error_note": "TOPUP NOT FOUND"}
        # Miqdor topup yaratilganda belgilangan summaga mos bo'lishi shart
        if abs(float(topup.amount) - float(amount)) > 1:
            return {"click_trans_id": click_trans_id, "merchant_trans_id": booking_id,
                    "error": -2, "error_note": "INCORRECT AMOUNT"}
        if action == 0:
            # PREPARE
            return {
                "click_trans_id": click_trans_id,
                "merchant_trans_id": booking_id,
                "merchant_prepare_id": topup.id.int & 0x7FFFFFFF,
                "error": 0,
                "error_note": "Success",
            }
        elif action == 1:
            # COMPLETE
            done = await _complete_wallet_topup(db, topup_id, str(click_trans_id))
            await db.commit()
            return {
                "click_trans_id": click_trans_id,
                "merchant_trans_id": booking_id,
                "merchant_confirm_id": 1,
                "error": 0,
                "error_note": "Success" if done else "Already completed",
            }
        return {"click_trans_id": click_trans_id, "merchant_trans_id": booking_id,
                "error": -8, "error_note": "INVALID ACTION"}

    # Bron mavjudmi?
    try:
        uid = uuid_lib.UUID(booking_id)
    except ValueError:
        return {"click_trans_id": click_trans_id, "merchant_trans_id": booking_id,
                "error": -5, "error_note": "BOOKING NOT FOUND"}

    result = await db.execute(select(Booking).where(Booking.id == uid))
    booking = result.scalar_one_or_none()
    if not booking:
        return {"click_trans_id": click_trans_id, "merchant_trans_id": booking_id,
                "error": -5, "error_note": "BOOKING NOT FOUND"}

    # Miqdor to'g'rimi?
    if abs(float(booking.total_price) - float(amount)) > 1:
        return {"click_trans_id": click_trans_id, "merchant_trans_id": booking_id,
                "error": -2, "error_note": "INCORRECT AMOUNT"}

    # Payment topish
    pay_result = await db.execute(select(Payment).where(Payment.booking_id == uid))
    payment = pay_result.scalar_one_or_none()
    if not payment:
        return {"click_trans_id": click_trans_id, "merchant_trans_id": booking_id,
                "error": -9, "error_note": "TRANSACTION NOT FOUND"}

    if action == 0:
        # PREPARE
        if booking.status == BookingStatus.cancelled:
            return {"click_trans_id": click_trans_id, "merchant_trans_id": booking_id,
                    "error": -3, "error_note": "BOOKING CANCELLED"}
        payment.transaction_id = str(click_trans_id)
        await db.commit()
        return {
            "click_trans_id": click_trans_id,
            "merchant_trans_id": booking_id,
            "merchant_prepare_id": payment.id.int & 0x7FFFFFFF,
            "error": 0,
            "error_note": "Success",
        }

    elif action == 1:
        # COMPLETE
        if booking.payment_status == BookingPaymentStatus.paid:
            return {"click_trans_id": click_trans_id, "merchant_trans_id": booking_id,
                    "merchant_confirm_id": payment.id.int & 0x7FFFFFFF,
                    "error": 0, "error_note": "Already paid"}

        payment.status = PaymentStatus.completed
        payment.paid_at = datetime.utcnow()
        booking.payment_status = BookingPaymentStatus.paid
        booking.status = BookingStatus.confirmed
        await db.commit()

        return {
            "click_trans_id": click_trans_id,
            "merchant_trans_id": booking_id,
            "merchant_confirm_id": payment.id.int & 0x7FFFFFFF,
            "error": 0,
            "error_note": "Success",
        }

    return {"click_trans_id": click_trans_id, "merchant_trans_id": booking_id,
            "error": -8, "error_note": "INVALID ACTION"}


# ─── Payme JSON-RPC handler ───────────────────────────────────────────────────

PAYME_ERRORS = {
    "invalid_amount":       {"code": -31001, "message": {"ru": "Неверная сумма", "uz": "Noto'g'ri summa"}},
    "transaction_not_found":{"code": -31003, "message": {"ru": "Транзакция не найдена", "uz": "Tranzaksiya topilmadi"}},
    "invalid_account":      {"code": -31050, "message": {"ru": "Неверный аккаунт", "uz": "Noto'g'ri account"}},
    "already_done":         {"code": -31060, "message": {"ru": "Уже выполнено", "uz": "Allaqachon bajarilgan"}},
    "cancelled":            {"code": -31007, "message": {"ru": "Отменено", "uz": "Bekor qilingan"}},
    "method_not_found":     {"code": -32601, "message": {"ru": "Метод не найден", "uz": "Metod topilmadi"}},
}


async def handle_payme_callback(db: AsyncSession, request_id: int, method: str, params: dict) -> dict:
    """Payme JSON-RPC barcha metodlarini qayta ishlash."""

    if method == "CheckPerformTransaction":
        return await _payme_check_perform(db, request_id, params)
    elif method == "CreateTransaction":
        return await _payme_create(db, request_id, params)
    elif method == "PerformTransaction":
        return await _payme_perform(db, request_id, params)
    elif method == "CancelTransaction":
        return await _payme_cancel(db, request_id, params)
    elif method == "CheckTransaction":
        return await _payme_check(db, request_id, params)
    else:
        return _payme_error(request_id, PAYME_ERRORS["method_not_found"])


def _payme_ok(request_id: int, result: dict) -> dict:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _payme_error(request_id: int, error: dict) -> dict:
    return {"jsonrpc": "2.0", "id": request_id, "error": error}


async def _payme_check_perform(db: AsyncSession, request_id: int, params: dict) -> dict:
    account = params.get("account", {})
    amount = params.get("amount")  # tiyinda

    # Wallet topup ekanmi?
    topup_id = account.get("topup_id")
    if topup_id:
        try:
            result = await db.execute(
                select(WalletTopupPayment).where(
                    WalletTopupPayment.id == uuid_lib.UUID(topup_id)
                )
            )
            topup = result.scalar_one_or_none()
        except (ValueError, Exception):
            return _payme_error(request_id, PAYME_ERRORS["invalid_account"])
        if not topup or topup.status == "cancelled":
            return _payme_error(request_id, PAYME_ERRORS["invalid_account"])
        expected = topup.amount * 100
        if abs(expected - amount) > 100:
            return _payme_error(request_id, PAYME_ERRORS["invalid_amount"])
        return _payme_ok(request_id, {"allow": True})

    booking_id = account.get("booking_id")
    if not booking_id:
        return _payme_error(request_id, PAYME_ERRORS["invalid_account"])

    try:
        uid = uuid_lib.UUID(booking_id)
    except ValueError:
        return _payme_error(request_id, PAYME_ERRORS["invalid_account"])

    result = await db.execute(select(Booking).where(Booking.id == uid))
    booking = result.scalar_one_or_none()
    if not booking or booking.status == BookingStatus.cancelled:
        return _payme_error(request_id, PAYME_ERRORS["invalid_account"])

    # Miqdor tekshirish (tiyinda)
    expected_tiyin = booking.total_price * 100
    if abs(expected_tiyin - amount) > 100:
        return _payme_error(request_id, PAYME_ERRORS["invalid_amount"])

    return _payme_ok(request_id, {"allow": True})


async def _payme_create(db: AsyncSession, request_id: int, params: dict) -> dict:
    account = params.get("account", {})
    amount = params.get("amount")
    payme_id = params.get("id")
    time_ms = params.get("time")
    create_time = int(time_ms) if time_ms else int(datetime.utcnow().timestamp() * 1000)

    # Wallet topup ekanmi?
    topup_id = account.get("topup_id")
    if topup_id:
        try:
            result = await db.execute(
                select(WalletTopupPayment).where(
                    WalletTopupPayment.id == uuid_lib.UUID(topup_id)
                )
            )
            topup = result.scalar_one_or_none()
        except (ValueError, Exception):
            return _payme_error(request_id, PAYME_ERRORS["invalid_account"])
        if not topup:
            return _payme_error(request_id, PAYME_ERRORS["invalid_account"])
        # Miqdor topup yaratilganda belgilangan summaga mos bo'lishi shart (tiyinda)
        if amount is None or abs(topup.amount * 100 - amount) > 100:
            return _payme_error(request_id, PAYME_ERRORS["invalid_amount"])
        if topup.transaction_id and topup.transaction_id != payme_id:
            return _payme_error(request_id, PAYME_ERRORS["already_done"])
        topup.transaction_id = payme_id
        await db.commit()
        return _payme_ok(request_id, {
            "create_time": create_time,
            "transaction": str(topup.id),
            "state": 1,
        })

    booking_id = account.get("booking_id")
    try:
        uid = uuid_lib.UUID(booking_id)
    except (ValueError, TypeError):
        return _payme_error(request_id, PAYME_ERRORS["invalid_account"])

    result = await db.execute(select(Booking).where(Booking.id == uid))
    booking = result.scalar_one_or_none()
    if not booking:
        return _payme_error(request_id, PAYME_ERRORS["invalid_account"])

    # Miqdor bron summasiga mos bo'lishi shart (tiyinda)
    if amount is None or abs(booking.total_price * 100 - amount) > 100:
        return _payme_error(request_id, PAYME_ERRORS["invalid_amount"])

    # Mavjud payment tekshirish
    pay_result = await db.execute(select(Payment).where(Payment.booking_id == uid))
    payment = pay_result.scalar_one_or_none()

    if not payment:
        rate, commission = calculate_commission(booking.total_price)
        payment = Payment(
            booking_id=booking.id,
            amount=booking.total_price,
            commission=commission,
            driver_amount=booking.total_price - commission,
            method=PaymentMethod.payme,
            status=PaymentStatus.pending,
            transaction_id=payme_id,
        )
        db.add(payment)
    elif payment.transaction_id and payment.transaction_id != payme_id:
        return _payme_error(request_id, PAYME_ERRORS["already_done"])
    else:
        payment.transaction_id = payme_id

    await db.commit()
    create_time = int(time_ms) if time_ms else int(datetime.utcnow().timestamp() * 1000)

    return _payme_ok(request_id, {
        "create_time": create_time,
        "transaction": str(payment.id),
        "state": 1,
    })


async def _payme_perform(db: AsyncSession, request_id: int, params: dict) -> dict:
    payme_id = params.get("id")

    # Wallet topup ekanmi?
    topup_result = await db.execute(
        select(WalletTopupPayment).where(WalletTopupPayment.transaction_id == payme_id)
    )
    topup = topup_result.scalar_one_or_none()
    if topup:
        if topup.status == "completed":
            return _payme_ok(request_id, {
                "transaction": str(topup.id),
                "perform_time": int(topup.completed_at.timestamp() * 1000),
                "state": 2,
            })
        done = await _complete_wallet_topup(db, str(topup.id), payme_id)
        await db.commit()
        return _payme_ok(request_id, {
            "transaction": str(topup.id),
            "perform_time": int(datetime.utcnow().timestamp() * 1000),
            "state": 2,
        })

    pay_result = await db.execute(
        select(Payment).where(Payment.transaction_id == payme_id)
    )
    payment = pay_result.scalar_one_or_none()
    if not payment:
        return _payme_error(request_id, PAYME_ERRORS["transaction_not_found"])

    booking_result = await db.execute(select(Booking).where(Booking.id == payment.booking_id))
    booking = booking_result.scalar_one_or_none()

    if payment.status == PaymentStatus.completed:
        return _payme_ok(request_id, {
            "transaction": str(payment.id),
            "perform_time": int(payment.paid_at.timestamp() * 1000),
            "state": 2,
        })

    perform_time = int(datetime.utcnow().timestamp() * 1000)
    payment.status = PaymentStatus.completed
    payment.paid_at = datetime.utcnow()

    if booking:
        booking.payment_status = BookingPaymentStatus.paid
        booking.status = BookingStatus.confirmed

    await db.commit()

    return _payme_ok(request_id, {
        "transaction": str(payment.id),
        "perform_time": perform_time,
        "state": 2,
    })


async def _payme_cancel(db: AsyncSession, request_id: int, params: dict) -> dict:
    payme_id = params.get("id")
    reason = params.get("reason", 0)

    pay_result = await db.execute(
        select(Payment).where(Payment.transaction_id == payme_id)
    )
    payment = pay_result.scalar_one_or_none()
    if not payment:
        return _payme_error(request_id, PAYME_ERRORS["transaction_not_found"])

    cancel_time = int(datetime.utcnow().timestamp() * 1000)
    state = -1 if payment.status == PaymentStatus.pending else -2

    payment.status = PaymentStatus.refunded
    payment.refunded_at = datetime.utcnow()

    await db.commit()

    return _payme_ok(request_id, {
        "transaction": str(payment.id),
        "cancel_time": cancel_time,
        "state": state,
    })


async def _payme_check(db: AsyncSession, request_id: int, params: dict) -> dict:
    payme_id = params.get("id")

    pay_result = await db.execute(
        select(Payment).where(Payment.transaction_id == payme_id)
    )
    payment = pay_result.scalar_one_or_none()
    if not payment:
        return _payme_error(request_id, PAYME_ERRORS["transaction_not_found"])

    state_map = {
        PaymentStatus.pending: 1,
        PaymentStatus.completed: 2,
        PaymentStatus.refunded: -2,
        PaymentStatus.failed: -1,
    }

    return _payme_ok(request_id, {
        "create_time": int(payment.created_at.timestamp() * 1000),
        "perform_time": int(payment.paid_at.timestamp() * 1000) if payment.paid_at else 0,
        "cancel_time": int(payment.refunded_at.timestamp() * 1000) if payment.refunded_at else 0,
        "transaction": str(payment.id),
        "state": state_map.get(payment.status, 0),
        "reason": None,
    })


# ─── Naqd pul — oylik komissiya ───────────────────────────────────────────────

async def record_cash_commission(db: AsyncSession, booking: Booking) -> None:
    """Naqd pul bron tugaganda haydovchi oylik komissiyasini yangilash."""
    trip_result = await db.execute(
        select(Trip).where(Trip.id == booking.trip_id)
    )
    trip = trip_result.scalar_one_or_none()
    if not trip:
        return

    month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    result = await db.execute(
        select(DriverMonthlyCommission).where(
            DriverMonthlyCommission.driver_id == trip.driver_id,
            DriverMonthlyCommission.month == month_start,
        )
    )
    commission_record = result.scalar_one_or_none()

    if not commission_record:
        commission_record = DriverMonthlyCommission(
            driver_id=trip.driver_id,
            month=month_start,
            total_cash_bookings=0,
            total_commission=0,
        )
        db.add(commission_record)

    commission_record.total_cash_bookings += 1
    commission_record.total_commission += booking.commission_amount
    await db.flush()
