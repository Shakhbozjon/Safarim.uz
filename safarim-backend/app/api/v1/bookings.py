from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import User
from app.schemas.booking import BookingCreate, BookingResponse, CancelBookingRequest, ConfirmBookingRequest
from app.services import booking_service
from app.core.dependencies import get_current_user, get_current_driver

router = APIRouter()


@router.post(
    "/",
    status_code=201,
    summary="Joy band qilish",
)
async def create_booking(
    data: BookingCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    booking = await booking_service.create_booking(db, current_user, data)
    return booking_service.serialize_booking(booking, current_user)


@router.get(
    "/my",
    summary="Mening bronlarim (yo'lovchi sifatida)",
)
async def get_my_bookings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    bookings = await booking_service.get_my_bookings(db, current_user)
    return [booking_service.serialize_booking(b, current_user) for b in bookings]


@router.get(
    "/driver",
    summary="Mening safarlarimga kelgan bronlar (haydovchi sifatida)",
)
async def get_driver_bookings(
    current_user: User = Depends(get_current_driver),
    db: AsyncSession = Depends(get_db),
):
    bookings = await booking_service.get_driver_bookings(db, current_user)
    return [booking_service.serialize_booking(b, current_user) for b in bookings]


@router.get(
    "/{booking_id}",
    summary="Bron tafsilotlari",
)
async def get_booking(
    booking_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    booking = await booking_service.get_booking(db, booking_id, current_user)
    return booking_service.serialize_booking(booking, current_user)


@router.post(
    "/{booking_id}/cancel",
    summary="Bronni bekor qilish",
)
async def cancel_booking(
    booking_id: str,
    data: CancelBookingRequest = CancelBookingRequest(),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    booking = await booking_service.cancel_booking(db, booking_id, current_user, data.reason)
    return booking_service.serialize_booking(booking, current_user)


@router.post(
    "/{booking_id}/confirm",
    summary="Safar bo'ldi/bo'lmadi tasdiqi (yo'lovchi yoki haydovchi)",
)
async def confirm_booking(
    booking_id: str,
    data: ConfirmBookingRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    booking = await booking_service.confirm_booking(db, booking_id, current_user, data.confirmed)
    return booking_service.serialize_booking(booking, current_user)


@router.post(
    "/{booking_id}/complete",
    summary="Safarni tugallash (haydovchi 'bo'ldi' deydi)",
)
async def complete_booking(
    booking_id: str,
    current_user: User = Depends(get_current_driver),
    db: AsyncSession = Depends(get_db),
):
    booking = await booking_service.complete_booking(db, booking_id, current_user)
    return booking_service.serialize_booking(booking, current_user)


@router.post(
    "/{booking_id}/no-show",
    summary="Yo'lovchi kelmadi (haydovchi belgilaydi)",
)
async def report_no_show(
    booking_id: str,
    current_user: User = Depends(get_current_driver),
    db: AsyncSession = Depends(get_db),
):
    booking = await booking_service.report_no_show(db, booking_id, current_user)
    return booking_service.serialize_booking(booking, current_user)
