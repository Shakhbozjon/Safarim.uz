from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import User
from app.schemas.review import ReviewCreate, ReviewResponse, DriverReviewsResponse
from app.services import review_service
from app.core.dependencies import get_current_user

router = APIRouter()


@router.post(
    "/{booking_id}",
    response_model=ReviewResponse,
    status_code=201,
    summary="Baho berish (safar tugagandan keyin)",
)
async def create_review(
    booking_id: str,
    data: ReviewCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await review_service.create_review(db, booking_id, current_user, data)


@router.get(
    "/driver/{user_id}",
    response_model=DriverReviewsResponse,
    summary="Haydovchi reytingi va izohlari",
)
async def get_driver_reviews(
    user_id: str,
    db: AsyncSession = Depends(get_db),
):
    return await review_service.get_driver_reviews(db, user_id)


@router.get(
    "/my",
    response_model=list[ReviewResponse],
    summary="Men bergan baholar",
)
async def get_my_reviews(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await review_service.get_my_given_reviews(db, current_user)
