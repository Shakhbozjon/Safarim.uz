import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.db.session import get_db
from app.core.dependencies import get_current_user
from app.services import notification_service

router = APIRouter()


# ─── Schema ───────────────────────────────────────────────────────────────────

class NotificationOut(BaseModel):
    id: uuid.UUID
    title: str
    body: str
    ref_type: str | None
    ref_id: uuid.UUID | None
    is_read: bool
    read_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class UnreadCountOut(BaseModel):
    count: int


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.get(
    "",
    response_model=list[NotificationOut],
    summary="Mening bildirishnomalarim",
)
async def get_notifications(
    limit: int = 30,
    offset: int = 0,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await notification_service.get_my_notifications(db, user.id, limit, offset)


@router.get(
    "/unread-count",
    response_model=UnreadCountOut,
    summary="O'qilmagan bildirishnomalar soni",
)
async def unread_count(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    count = await notification_service.get_unread_count(db, user.id)
    return {"count": count}


@router.put(
    "/read-all",
    summary="Hammasini o'qilgan deb belgilash",
)
async def read_all(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    updated = await notification_service.mark_all_read(db, user.id)
    return {"updated": updated}


@router.put(
    "/{notif_id}/read",
    summary="Bittasini o'qilgan deb belgilash",
)
async def read_one(
    notif_id: uuid.UUID,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ok = await notification_service.mark_read(db, notif_id, user.id)
    if not ok:
        raise HTTPException(status_code=404, detail="Bildirishnoma topilmadi")
    return {"ok": True}
