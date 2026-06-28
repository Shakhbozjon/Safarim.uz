from fastapi import APIRouter, Depends, Header, Request, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from app.db.session import get_db
from app.models.payment import Payment
from app.schemas.payment import (
    InitiatePaymentRequest, InitiatePaymentResponse,
    PaymentStatusResponse, ClickCallbackRequest, ClickResponse,
    PaymeRequest, PaymeResponse,
)
from app.services import payment_service
from app.core.dependencies import get_current_user
from sqlalchemy import select

router = APIRouter()


@router.post(
    "/initiate",
    response_model=InitiatePaymentResponse,
    summary="Online to'lovni boshlash (Click yoki Payme)",
)
async def initiate_payment(
    data: InitiatePaymentRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await payment_service.initiate_payment(
        db, current_user, data.booking_id, data.method
    )
    return result


@router.get(
    "/{booking_id}",
    response_model=PaymentStatusResponse,
    summary="To'lov holati",
)
async def get_payment_status(
    booking_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        uid = uuid.UUID(booking_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Noto'g'ri ID")

    result = await db.execute(select(Payment).where(Payment.booking_id == uid))
    payment = result.scalar_one_or_none()
    if not payment:
        raise HTTPException(status_code=404, detail="To'lov topilmadi")
    return payment


# ─── Click Webhook ────────────────────────────────────────────────────────────

@router.post(
    "/click/callback",
    response_model=ClickResponse,
    summary="Click webhook (Click tomonidan chaqiriladi)",
    include_in_schema=False,  # Swagger da ko'rsatmaslik
)
async def click_callback(
    data: ClickCallbackRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await payment_service.handle_click_callback(db, data.model_dump())
    return result


# ─── Payme Webhook ────────────────────────────────────────────────────────────

@router.post(
    "/payme/callback",
    summary="Payme webhook (Payme tomonidan chaqiriladi)",
    include_in_schema=False,
)
async def payme_callback(
    request: PaymeRequest,
    authorization: str = Header(...),
    db: AsyncSession = Depends(get_db),
):
    # Payme autentifikatsiyasi
    if not payment_service.verify_payme_auth(authorization):
        return {
            "jsonrpc": "2.0",
            "id": request.id,
            "error": {
                "code": -32504,
                "message": {"ru": "Недостаточно прав", "uz": "Ruxsat yo'q"},
            }
        }

    return await payment_service.handle_payme_callback(
        db, request.id, request.method, request.params
    )
