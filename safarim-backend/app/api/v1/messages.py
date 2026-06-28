from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db, AsyncSessionLocal
from app.models.user import User
from app.schemas.message import MessageResponse, UnreadCountResponse
from app.services import message_service
from app.core.dependencies import get_current_user
from app.core.security import decode_token
from app.core.ws_manager import ws_manager

router = APIRouter()


# ─── REST endpointlar ─────────────────────────────────────────────────────────

@router.get(
    "/{booking_id}",
    response_model=list[MessageResponse],
    summary="Chat tarixi",
)
async def get_chat_history(
    booking_id: str,
    limit: int = Query(50, ge=1, le=100),
    before_id: str | None = Query(None, description="Shu xabardan oldingilarni olish"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await message_service.get_chat_history(db, booking_id, current_user, limit, before_id)


@router.put(
    "/{booking_id}/read",
    summary="Xabarlarni o'qilgan deb belgilash",
)
async def mark_as_read(
    booking_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    count = await message_service.mark_as_read(db, booking_id, current_user)
    return {"marked_read": count}


@router.get(
    "/unread/count",
    response_model=list[UnreadCountResponse],
    summary="Barcha bronlardagi o'qilmagan xabarlar soni",
)
async def get_unread_count(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await message_service.get_unread_count(db, current_user)


# ─── WebSocket ────────────────────────────────────────────────────────────────

@router.websocket("/ws/{booking_id}")
async def chat_websocket(
    websocket: WebSocket,
    booking_id: str,
    token: str = Query(..., description="JWT access token"),
):
    """
    Real-time chat WebSocket.

    Ulanish: ws://localhost:8000/api/v1/messages/ws/{booking_id}?token=<access_token>

    Xabar yuborish (JSON):
        { "content": "Salom!" }

    Keluvchi xabarlar formati:
        { "type": "message",       "data": { ...MessageResponse... } }
        { "type": "read",          "data": { "reader_id": "..." } }
        { "type": "online_status", "data": { "user_id": "...", "online": true } }
        { "type": "error",         "data": { "detail": "..." } }
    """
    # ── 1. Token tekshirish ──
    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        await websocket.close(code=4001, reason="Token yaroqsiz")
        return

    user_id = payload["sub"]

    async with AsyncSessionLocal() as db:
        # ── 2. Foydalanuvchini topish ──
        from sqlalchemy import select
        from app.models.user import User as UserModel
        result = await db.execute(select(UserModel).where(UserModel.id == user_id))
        user = result.scalar_one_or_none()
        if not user or user.is_blocked:
            await websocket.close(code=4003, reason="Ruxsat yo'q")
            return

        # ── 3. Booking kirish huquqini tekshirish ──
        try:
            booking, role = await message_service._get_booking_and_check_access(
                db, booking_id, user
            )
        except HTTPException as e:
            await websocket.close(code=4004, reason=e.detail)
            return

        # ── 4. Ulanish ──
        await ws_manager.connect(websocket, booking_id, user_id)

        # Boshqa tomon online ekanini bildirish
        await ws_manager.send_to_room(
            booking_id,
            {"type": "online_status", "data": {"user_id": user_id, "online": True}},
            exclude_user_id=user_id,
        )

        try:
            while True:
                # ── 5. Xabar qabul qilish ──
                raw = await websocket.receive_json()
                content = raw.get("content", "").strip()

                if not content:
                    await websocket.send_json(
                        {"type": "error", "data": {"detail": "Xabar bo'sh bo'lishi mumkin emas"}}
                    )
                    continue

                if len(content) > 1000:
                    await websocket.send_json(
                        {"type": "error", "data": {"detail": "Xabar juda uzun (maks 1000 belgi)"}}
                    )
                    continue

                # ── 6. DBga saqlash ──
                message = await message_service.send_message(db, booking_id, user, content)

                msg_data = {
                    "type": "message",
                    "data": {
                        "id": str(message.id),
                        "booking_id": str(message.booking_id),
                        "sender": {
                            "id": str(message.sender.id),
                            "full_name": message.sender.full_name,
                            "profile_photo": message.sender.profile_photo,
                        },
                        "content": message.content,
                        "is_read": message.is_read,
                        "read_at": None,
                        "created_at": message.created_at.isoformat(),
                    },
                }

                # ── 7. Yuboruvchiga ham qaytarish ──
                await websocket.send_json(msg_data)

                # ── 8. Boshqa tomonga yuborish ──
                await ws_manager.send_to_room(
                    booking_id, msg_data, exclude_user_id=user_id
                )

        except WebSocketDisconnect:
            ws_manager.disconnect(booking_id, user_id)

            # Boshqa tomon offline bo'lganini bildirish
            await ws_manager.send_to_room(
                booking_id,
                {"type": "online_status", "data": {"user_id": user_id, "online": False}},
            )
