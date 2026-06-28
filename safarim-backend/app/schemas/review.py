import uuid
from datetime import datetime
from pydantic import BaseModel, field_validator
from app.models.enums import ReviewerType


class ReviewCreate(BaseModel):
    rating: int
    comment: str | None = None

    @field_validator("rating")
    @classmethod
    def validate_rating(cls, v: int) -> int:
        if v < 1 or v > 5:
            raise ValueError("Baho 1 dan 5 gacha bo'lishi kerak")
        return v


class ReviewerInfo(BaseModel):
    id: uuid.UUID
    full_name: str
    profile_photo: str | None

    model_config = {"from_attributes": True}


class ReviewResponse(BaseModel):
    id: uuid.UUID
    booking_id: uuid.UUID
    reviewer: ReviewerInfo
    reviewee: ReviewerInfo
    reviewer_type: ReviewerType
    rating: int
    comment: str | None
    is_visible: bool
    review_deadline: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


class DriverReviewsResponse(BaseModel):
    driver_id: uuid.UUID
    rating_avg: float
    rating_count: int
    total_trips: int
    reviews: list[ReviewResponse]
