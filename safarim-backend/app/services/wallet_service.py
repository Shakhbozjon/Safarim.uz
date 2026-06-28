"""
Haydovchi hamyon xizmati.

Pul oqimi:
  NAQD safar  → deduct_commission(-)  → balans kamayadi (manfiy bo'lishi mumkin)
  ONLINE safar → add_earning(+)        → balans ko'tariladi
  To'ldirish  → topup(+)              → balans ko'tariladi
  Yechish     → withdraw(-)           → balans kamayadi

Bloklash qoidasi:
  balance ≤ min_balance (-50,000) → hamyon bloklanadi
  balance > 0                     → avtomatik blokdan chiqariladi (admin aralashuvisiz)
"""
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status

from app.models.wallet import DriverWallet, WalletTransaction
from app.models.enums import WalletTxType
from app.core.config import settings


# ─── Ichki yordamchi ─────────────────────────────────────────────────────────

async def get_or_create(db: AsyncSession, driver_id: uuid.UUID) -> DriverWallet:
    """Haydovchi hamyonini oling yoki yangi yarating."""
    result = await db.execute(
        select(DriverWallet).where(DriverWallet.driver_id == driver_id)
    )
    wallet = result.scalar_one_or_none()
    if not wallet:
        wallet = DriverWallet(driver_id=driver_id)
        db.add(wallet)
        await db.flush()   # ID olish uchun (commit qilmasdan)
    return wallet


async def _record(
    db: AsyncSession,
    wallet: DriverWallet,
    amount: int,
    tx_type: WalletTxType,
    description: str,
    booking_id: uuid.UUID | None = None,
) -> tuple[WalletTransaction, bool]:
    """
    Hamyon balansini yangilash + tranzaksiya yozuvi.
    Qaytaradi: (tranzaksiya, avtomatik_blokdan_chiqarildimi)
    """
    wallet.balance += amount
    tx = WalletTransaction(
        wallet_id=wallet.id,
        amount=amount,
        tx_type=tx_type,
        booking_id=booking_id,
        description=description,
        balance_after=wallet.balance,
    )
    db.add(tx)

    auto_unblocked = False

    # Bloklash tekshiruvi
    if wallet.balance <= wallet.min_balance:
        wallet.is_blocked = True
    elif wallet.is_blocked and wallet.balance > 0:
        # Balans musbatga chiqdi → admin aralashuvisiz avtomatik blokdan chiqarish
        wallet.is_blocked = False
        auto_unblocked = True

    return tx, auto_unblocked


# ─── Ochiq interfeys ──────────────────────────────────────────────────────────

async def _maybe_notify_unblocked(db: AsyncSession, driver_id: uuid.UUID) -> None:
    """Hamyon avtomatik blokdan chiqqanda haydovchiga bildirishnoma yuborish."""
    from app.services import notification_service
    await notification_service.create(
        db,
        user_id=driver_id,
        title="Hamyon blokdan chiqarildi ✅",
        body="Balansingiz musbatga chiqdi. Endi naqd bronlarni qabul qila olasiz.",
    )


async def deduct_commission(
    db: AsyncSession,
    driver_id: uuid.UUID,
    amount: int,
    booking_id: uuid.UUID | None = None,
) -> DriverWallet:
    """
    NAQD safar: komissiyani haydovchi hamyonidan ushib qolish.
    Balans manfiy ketishi mumkin — MIN_BALANCE ga yetsa bloklash.
    """
    wallet = await get_or_create(db, driver_id)
    await _record(
        db, wallet,
        amount=-amount,
        tx_type=WalletTxType.cash_commission,
        description=f"Naqd safar komissiyasi: -{amount:,} so'm",
        booking_id=booking_id,
    )
    return wallet


async def add_earning(
    db: AsyncSession,
    driver_id: uuid.UUID,
    amount: int,
    booking_id: uuid.UUID | None = None,
) -> DriverWallet:
    """
    ONLINE safar tugadi: haydovchi ulushini hamyonga o'tkazish.
    Balans musbatga chiqsa → avtomatik blokdan chiqarish.
    """
    wallet = await get_or_create(db, driver_id)
    _, auto_unblocked = await _record(
        db, wallet,
        amount=+amount,
        tx_type=WalletTxType.online_earning,
        description=f"Online safar daromadi: +{amount:,} so'm",
        booking_id=booking_id,
    )
    if auto_unblocked:
        await _maybe_notify_unblocked(db, driver_id)
    return wallet


async def topup(
    db: AsyncSession,
    driver_id: uuid.UUID,
    amount: int,
    check_min: bool = True,
) -> DriverWallet:
    """
    Haydovchi hamyonni to'ldirdi (Click/Payme orqali yoki admin qo'lda).
    check_min=False — admin tomonidan qo'lda to'ldirishda minimal chegara tekshirilmaydi.
    Balans musbatga chiqsa → avtomatik blokdan chiqarish.
    """
    if check_min and amount < settings.WALLET_TOPUP_MIN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Minimal to'ldirish: {settings.WALLET_TOPUP_MIN:,} so'm",
        )
    wallet = await get_or_create(db, driver_id)
    _, auto_unblocked = await _record(
        db, wallet,
        amount=+amount,
        tx_type=WalletTxType.topup,
        description=f"Hamyon to'ldirildi: +{amount:,} so'm",
    )
    if auto_unblocked:
        await _maybe_notify_unblocked(db, driver_id)
    return wallet


async def withdraw(
    db: AsyncSession,
    driver_id: uuid.UUID,
    amount: int,
) -> DriverWallet:
    """
    Haydovchi hamyondan pul yechib oldi.
    Faqat musbat balans bo'lganda mumkin.
    """
    wallet = await get_or_create(db, driver_id)
    if wallet.balance < amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Yetarli balans yo'q. Mavjud: {wallet.balance:,} so'm",
        )
    await _record(
        db, wallet,
        amount=-amount,
        tx_type=WalletTxType.withdrawal,
        description=f"Yechib olindi: -{amount:,} so'm",
    )
    return wallet


async def refund_commission(
    db: AsyncSession,
    driver_id: uuid.UUID,
    amount: int,
    booking_id: uuid.UUID | None = None,
) -> DriverWallet:
    """
    Bron bekor qilindi — naqd komissiya qaytarildi.
    Balans musbatga chiqsa → avtomatik blokdan chiqarish.
    """
    wallet = await get_or_create(db, driver_id)
    _, auto_unblocked = await _record(
        db, wallet,
        amount=+amount,
        tx_type=WalletTxType.refund,
        description=f"Bekor qilingan bron qaytarmasi: +{amount:,} so'm",
        booking_id=booking_id,
    )
    if auto_unblocked:
        await _maybe_notify_unblocked(db, driver_id)
    return wallet


async def get_wallet_info(db: AsyncSession, driver_id: uuid.UUID) -> dict:
    """Hamyon holati + so'nggi 20 ta tranzaksiya."""
    wallet = await get_or_create(db, driver_id)
    result = await db.execute(
        select(WalletTransaction)
        .where(WalletTransaction.wallet_id == wallet.id)
        .order_by(WalletTransaction.created_at.desc())
        .limit(20)
    )
    txs = result.scalars().all()

    return {
        "balance": wallet.balance,
        "min_balance": wallet.min_balance,
        "is_blocked": wallet.is_blocked,
        "transactions": [
            {
                "id": str(t.id),
                "amount": t.amount,
                "tx_type": t.tx_type,
                "description": t.description,
                "balance_after": t.balance_after,
                "booking_id": str(t.booking_id) if t.booking_id else None,
                "created_at": t.created_at,
            }
            for t in txs
        ],
    }
