import uuid
from datetime import datetime
from pydantic import BaseModel
from app.models.enums import PaymentMethod, PaymentStatus


class InitiatePaymentRequest(BaseModel):
    booking_id: str
    method: PaymentMethod  # faqat click yoki payme (cash uchun kerak emas)


class InitiatePaymentResponse(BaseModel):
    payment_url: str
    booking_id: str
    amount: int
    method: PaymentMethod


class PaymentStatusResponse(BaseModel):
    id: uuid.UUID
    booking_id: uuid.UUID
    amount: int
    commission: int
    driver_amount: int
    method: PaymentMethod
    status: PaymentStatus
    transaction_id: str | None
    paid_at: datetime | None
    refund_amount: int

    model_config = {"from_attributes": True}


# ─── Click schemas ────────────────────────────────────────────────────────────

class ClickCallbackRequest(BaseModel):
    """Click tomonidan keluvchi callback."""
    click_trans_id: int
    service_id: int
    click_paydoc_id: int
    merchant_trans_id: str   # booking_id
    merchant_prepare_id: int | None = None
    amount: float
    action: int              # 0 = prepare, 1 = complete
    error: int
    error_note: str
    sign_time: str
    sign_string: str


class ClickResponse(BaseModel):
    click_trans_id: int
    merchant_trans_id: str
    merchant_prepare_id: int | None = None
    merchant_confirm_id: int | None = None
    error: int
    error_note: str


# ─── Payme schemas (JSON-RPC) ─────────────────────────────────────────────────

class PaymeRequest(BaseModel):
    jsonrpc: str = "2.0"
    id: int
    method: str
    params: dict


class PaymeError(BaseModel):
    code: int
    message: dict  # {"ru": "...", "uz": "..."}
    data: str | None = None


class PaymeResponse(BaseModel):
    jsonrpc: str = "2.0"
    id: int
    result: dict | None = None
    error: PaymeError | None = None
