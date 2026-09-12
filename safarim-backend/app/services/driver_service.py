from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload
from fastapi import HTTPException, status

from app.models.user import User
from app.models.driver import DriverProfile
from app.models.payment import DriverMonthlyCommission
from app.models.enums import DriverStatus, AdminActionType, NotificationRefType
from app.models.admin import AdminAction
from app.schemas.driver import DriverApplyRequest, UpdatePreferencesRequest
from app.core.config import settings
from app.services import notification_service, wallet_service


async def apply_driver(
    db: AsyncSession,
    user: User,
    data: DriverApplyRequest,
    license_key: str | None = None,
    tech_passport_key: str | None = None,
) -> DriverProfile:
    # Shu foydalanuvchining mavjud yozuvi (bo'lsa)
    existing = (await db.execute(
        select(DriverProfile).where(DriverProfile.user_id == user.id)
    )).scalar_one_or_none()

    if existing and existing.status == DriverStatus.pending:
        raise HTTPException(status_code=400, detail="Arizangiz ko'rib chiqilmoqda")
    if existing and existing.status == DriverStatus.approved:
        raise HTTPException(status_code=400, detail="Siz allaqachon haydovchi sifatida tasdiqlangansiz")

    # Avtomobil raqami BOSHQA odamda band emasligini tekshirish.
    # ⚠️ Ilgari bu yerda o'z yozuvi ham hisobga olinardi: rad etilgan haydovchi
    # o'z mashinasi bilan qaytib kelsa, "bu raqam allaqachon ro'yxatdan o'tgan"
    # deb rad etilardi va boshqa hech qachon ariza bera olmasdi.
    result = await db.execute(
        select(DriverProfile).where(
            DriverProfile.vehicle_plate == data.vehicle_plate,
            DriverProfile.user_id != user.id,
        )
    )
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="Bu avtomobil raqami allaqachon ro'yxatdan o'tgan")

    # Rad etilgan haydovchi qayta ariza bersa avtomatika ishlamaydi —
    # adminning "yo'q" qarori o'z-o'zidan bekor bo'lib qolmasin.
    was_rejected = bool(existing and existing.status == DriverStatus.rejected)

    if existing:
        # Rad etilgan yozuv yangilanadi — yangisi yaratilmaydi.
        # `driver_profiles.user_id` unikal, ya'ni yangi yozuv qo'shish baza
        # cheklovini buzib, foydalanuvchiga 500 bo'lib ko'rinardi.
        # Yangi surat berilmagan bo'lsa eskisi saqlanib qoladi — qayta ariza
        # bergan haydovchining allaqachon yuklangan hujjati yo'qolmasin.
        if license_key is not None:
            existing.license_image = license_key
        if tech_passport_key is not None:
            existing.tech_passport_image = tech_passport_key
        existing.vehicle_make = data.vehicle_make
        existing.vehicle_model = data.vehicle_model
        existing.vehicle_color = data.vehicle_color
        existing.vehicle_plate = data.vehicle_plate
        existing.vehicle_seats = data.vehicle_seats
        existing.status = DriverStatus.pending
        existing.rejection_reason = None
        driver = existing
    else:
        driver = DriverProfile(
            user_id=user.id,
            license_image=license_key,
            tech_passport_image=tech_passport_key,
            vehicle_make=data.vehicle_make,
            vehicle_model=data.vehicle_model,
            vehicle_color=data.vehicle_color,
            vehicle_plate=data.vehicle_plate,
            vehicle_seats=data.vehicle_seats,
            status=DriverStatus.pending,
        )
        db.add(driver)

    user.is_driver = True

    # Pilot davri: haydovchi kutmaydi. verified_at/verified_by ATAYLAB bo'sh
    # qoldiriladi — hech kim tekshirmadi, demak "Hujjati tekshirilgan" belgisi
    # ham berilmaydi. AdminAction ham yozilmaydi: hech qanday admin harakat
    # qilmadi, jurnal yolg'on gapirmasin.
    auto_approved = settings.AUTO_APPROVE_DRIVERS and not was_rejected
    if auto_approved:
        driver.status = DriverStatus.approved
        driver.verified_at = None
        driver.verified_by = None

    try:
        await db.commit()
    except IntegrityError:
        # Ikki odam bir vaqtda bir xil raqamni yuborsa yuqoridagi tekshiruvdan
        # ikkalasi ham o'tib ketishi mumkin — baza cheklovi ushlaydi, biz esa
        # 500 o'rniga tushunarli javob beramiz.
        await db.rollback()
        raise HTTPException(
            status_code=400, detail="Bu avtomobil raqami allaqachon ro'yxatdan o'tgan"
        )
    await db.refresh(driver)

    if auto_approved:
        # Naqd bandlikda komissiya shu hisobdan yechiladi — approve_driver
        # dagidek, hamyon oldindan ochib qo'yiladi.
        await wallet_service.get_or_create(db, user.id)
        await notification_service.create(
            db,
            user_id=user.id,
            title="Haydovchi profilingiz ochildi",
            body="Endi safar e'lon qilishingiz mumkin. Guvohnomangizni yuklab "
                 "qo'ysangiz, ko'rib chiqqach profilingizda tasdiq belgisi paydo bo'ladi.",
            ref_type=NotificationRefType.system,
        )

    return driver


async def upload_documents(
    db: AsyncSession,
    user: User,
    license_key: str | None = None,
    tech_passport_key: str | None = None,
) -> tuple[DriverProfile, list[str]]:
    """Ariza topshirilgandan KEYIN hujjat yuklash.

    Ishga tushirish davrida hujjat ixtiyoriy — «hozircha o'tkazib yuborish»ni
    bosgan haydovchining tasdiq belgisiga boradigan yagona yo'li shu.

    ⚠️ `status` ATAYLAB o'zgartirilmaydi: haydovchi allaqachon `approved`
    bo'lib safar e'lon qilib yuribdi, hujjat yuklagani uchun uni `pending` ga
    tushirsak — ishidan ayrilgan bo'ladi. Hujjat `verified_by` bo'sh holda
    tushadi, ya'ni avtomatik ravishda adminning `needs_review` navbatiga
    qo'shiladi (qarang: `needs_review_conditions`).

    Qaytaradi: (haydovchi, MinIO'dan o'chiriladigan eski kalitlar).
    Eski faylni chaqiruvchi o'chiradi — `users.py` dagi tartib shunday.
    """
    driver = (await db.execute(
        select(DriverProfile).where(DriverProfile.user_id == user.id)
    )).scalar_one_or_none()

    if not driver:
        raise HTTPException(
            status_code=404, detail="Avval haydovchi arizasini topshiring"
        )
    if driver.status == DriverStatus.rejected:
        raise HTTPException(
            status_code=400,
            detail="Arizangiz rad etilgan — hujjat bilan qaytadan ariza topshiring",
        )
    # Tekshirilgan hujjatni almashtirish yo'li ataylab yopiq: aks holda admin
    # ko'rgan suratni keyin boshqasiga almashtirib qo'yish mumkin bo'lardi.
    if driver.verified_by is not None:
        raise HTTPException(
            status_code=400,
            detail="Hujjatlaringiz allaqachon tekshirilgan. O'zgartirish kerak bo'lsa qo'llab-quvvatlash xizmatiga murojaat qiling",
        )

    had_license = bool(driver.license_image)
    replaced: list[str] = []

    if license_key is not None:
        if driver.license_image:
            replaced.append(driver.license_image)
        driver.license_image = license_key
    if tech_passport_key is not None:
        if driver.tech_passport_image:
            replaced.append(driver.tech_passport_image)
        driver.tech_passport_image = tech_passport_key

    # Bildirishnoma matni guvohnomaga bog'liq: belgi FAQAT guvohnoma
    # ko'rilganda beriladi, texpasport o'zi belgi keltirmaydi.
    if license_key is not None:
        body = (
            "Guvohnomangiz qayta yuklandi. Ko'rib chiqilgach profilingizda "
            "tasdiq belgisi paydo bo'ladi."
            if had_license else
            "Ko'rib chiqilgach profilingizda tasdiq belgisi paydo bo'ladi."
        )
    else:
        body = (
            "Texpasportingiz saqlandi. Tasdiq belgisi uchun haydovchilik "
            "guvohnomangizni ham yuklang."
        )
    await notification_service.create(
        db,
        user_id=user.id,
        title="Hujjatingiz qabul qilindi",
        body=body,
        ref_type=NotificationRefType.system,
    )

    await db.commit()
    await db.refresh(driver)
    return driver, replaced


async def update_preferences(
    db: AsyncSession,
    user: User,
    data: UpdatePreferencesRequest,
) -> DriverProfile:
    result = await db.execute(
        select(DriverProfile).where(DriverProfile.user_id == user.id)
    )
    driver = result.scalar_one_or_none()
    if not driver:
        raise HTTPException(status_code=404, detail="Haydovchi profili topilmadi")
    if driver.status != DriverStatus.approved:
        raise HTTPException(status_code=403, detail="Profil tasdiqlanmagan")

    if data.smoking_allowed is not None:
        driver.smoking_allowed = data.smoking_allowed
    if data.pets_allowed is not None:
        driver.pets_allowed = data.pets_allowed
    if data.music_allowed is not None:
        driver.music_allowed = data.music_allowed
    if data.luggage_size is not None:
        driver.luggage_size = data.luggage_size
    if data.women_only is not None:
        driver.women_only = data.women_only

    await db.commit()
    await db.refresh(driver)
    return driver


async def toggle_pause(db: AsyncSession, user: User, pause: bool) -> DriverProfile:
    result = await db.execute(
        select(DriverProfile).where(DriverProfile.user_id == user.id)
    )
    driver = result.scalar_one_or_none()
    if not driver or driver.status != DriverStatus.approved:
        raise HTTPException(status_code=403, detail="Tasdiqlanmagan haydovchi")

    driver.is_on_pause = pause
    await db.commit()
    await db.refresh(driver)
    return driver


async def get_driver_profile(db: AsyncSession, user: User) -> DriverProfile:
    result = await db.execute(
        select(DriverProfile).where(DriverProfile.user_id == user.id)
    )
    driver = result.scalar_one_or_none()
    if not driver:
        raise HTTPException(status_code=404, detail="Haydovchi profili topilmadi")
    return driver


async def get_monthly_earnings(db: AsyncSession, user: User) -> list[DriverMonthlyCommission]:
    result = await db.execute(
        select(DriverMonthlyCommission)
        .where(DriverMonthlyCommission.driver_id == user.id)
        .order_by(DriverMonthlyCommission.month.desc())
        .limit(12)
    )
    return result.scalars().all()


# ─── Admin funksiyalari ────────────────────────────────────────────────────────

def _driver_uuid(driver_id: str):
    """Noto'g'ri formatdagi id 500 emas, 404 bersin."""
    import uuid as _uuid
    try:
        return _uuid.UUID(driver_id)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=404, detail="Haydovchi topilmadi")


async def get_driver_by_id(db: AsyncSession, driver_id: str) -> DriverProfile:
    """Bitta haydovchi — holatidan qat'i nazar.

    Admin sahifasi ilgari haydovchini faqat "kutayotganlar" ro'yxatidan
    qidirardi: avtomatik tasdiqlash yoqilganda u ro'yxat bo'sh bo'ladi va
    hech kimni ochib bo'lmay qolardi.
    """
    result = await db.execute(
        select(DriverProfile)
        .options(selectinload(DriverProfile.user))
        .where(DriverProfile.id == _driver_uuid(driver_id))
    )
    driver = result.scalar_one_or_none()
    if not driver:
        raise HTTPException(status_code=404, detail="Haydovchi topilmadi")
    return driver


def needs_review_conditions() -> list:
    """Hujjat yuklagan, lekin hali hech kim ko'rmagan haydovchilar.

    Avtomatik tasdiqlashda "kutayotganlar" navbati bo'shab qoladi — adminning
    haqiqiy ish navbati shu bo'ladi.
    """
    return [
        DriverProfile.verified_by.is_(None),
        DriverProfile.license_image.isnot(None),
        DriverProfile.status != DriverStatus.rejected,
    ]


async def get_pending_drivers(db: AsyncSession) -> list[DriverProfile]:
    return await list_drivers(db, status=DriverStatus.pending)


async def list_drivers(
    db: AsyncSession,
    status: DriverStatus | None = None,
    q: str | None = None,
    limit: int = 100,
    needs_review: bool = False,
) -> list[DriverProfile]:
    """Admin uchun haydovchilar ro'yxati.

    Ilgari faqat `pending` ro'yxati bor edi — tasdiqlangan haydovchini
    topishning, mashinasini yoki raqamini ko'rishning yo'li yo'q edi.
    """
    conditions = []
    if status is not None:
        conditions.append(DriverProfile.status == status)
    if needs_review:
        conditions += needs_review_conditions()
    if q:
        needle = f"%{q.strip().lower()}%"
        conditions.append(
            func.lower(DriverProfile.vehicle_plate).like(needle)
            | func.lower(User.full_name).like(needle)
            | User.phone.like(needle)
        )

    query = (
        select(DriverProfile)
        .join(User, DriverProfile.user_id == User.id)
        .options(selectinload(DriverProfile.user))
        .where(*conditions)
        .limit(limit)
    )
    # Navbatdagilar eng eskisidan (kim uzoq kutgan bo'lsa tepada),
    # qolganlar eng yangisidan
    query = query.order_by(
        DriverProfile.created_at.asc()
        if (status == DriverStatus.pending or needs_review)
        else DriverProfile.created_at.desc()
    )
    result = await db.execute(query)
    return result.scalars().all()


async def approve_driver(db: AsyncSession, driver_id: str, admin: User) -> DriverProfile:
    """Hujjatni tasdiqlash — profildagi belgi shundan keyin beriladi.

    Avtomatik ochilgan haydovchi ham shu yerdan o'tadi: uning holati allaqachon
    `approved`, lekin `verified_by` bo'sh — ya'ni hujjatini hech kim ko'rmagan.
    """
    driver = await get_driver_by_id(db, driver_id)
    if driver.verified_by is not None:
        raise HTTPException(status_code=400, detail="Hujjatlari allaqachon tekshirilgan")

    # Avtomatik ochilgan edi (admin hech narsa qilmagan) — matnlar boshqacha
    was_auto = driver.status == DriverStatus.approved

    driver.status = DriverStatus.approved
    driver.verified_at = datetime.utcnow()
    driver.verified_by = admin.id
    driver.rejection_reason = None

    action = AdminAction(
        admin_id=admin.id,
        action_type=AdminActionType.approve_driver,
        target_user_id=driver.user_id,
        reason=(
            "Hujjatlar tekshirildi (hisob avval avtomatik ochilgan edi)"
            if was_auto else "Hujjatlar tekshirildi va tasdiqlandi"
        ),
    )
    db.add(action)

    # Haydovchiga bildirishnoma. Hisobi avval avtomatik ochilgan bo'lsa
    # "tasdiqlandingiz" demaymiz — u allaqachon ishlab yurgan edi, yangilik
    # faqat belgi.
    await notification_service.create(
        db,
        user_id=driver.user_id,
        title="Hujjatlaringiz tekshirildi ✅" if was_auto else "Haydovchilik tasdiqlandi! 🎉",
        body=(
            "Profilingizda tasdiq belgisi paydo bo'ldi — yo'lovchilar safar "
            "tanlayotganda shuni ko'radi."
            if was_auto else
            "Tabriklaymiz! Siz haydovchi sifatida tasdiqlandingiz. Endi safar yarata olasiz."
        ),
        ref_type=NotificationRefType.system,
    )

    # Hamyon avtomatik yaratiladi
    await wallet_service.get_or_create(db, driver.user_id)

    await db.commit()
    await db.refresh(driver)
    return driver


async def reject_driver(db: AsyncSession, driver_id: str, admin: User, reason: str) -> DriverProfile:
    """Haydovchilikdan chiqarish.

    Hujjati tekshirilgan haydovchi bu yerdan o'tmaydi (uning uchun bloklash
    bor). Avtomatik ochilgan, hali tekshirilmagan haydovchini esa rad etish
    yo'li ochiq bo'lishi shart — bu adminning yagona "yo'q" tugmasi.
    """
    driver = await get_driver_by_id(db, driver_id)
    if driver.verified_by is not None:
        raise HTTPException(
            status_code=400,
            detail="Hujjati tekshirilgan haydovchi rad etilmaydi — foydalanuvchini bloklang",
        )

    driver.status = DriverStatus.rejected
    driver.rejection_reason = reason

    # Foydalanuvchi qayta ariza topshira olishi uchun is_driver=False
    result_user = await db.execute(select(User).where(User.id == driver.user_id))
    u = result_user.scalar_one_or_none()
    if u:
        u.is_driver = False

    action = AdminAction(
        admin_id=admin.id,
        action_type=AdminActionType.reject_driver,
        target_user_id=driver.user_id,
        reason=reason,
    )
    db.add(action)

    # Haydovchiga bildirishnoma
    await notification_service.create(
        db,
        user_id=driver.user_id,
        title="Ariza rad etildi",
        body=f"Haydovchilik arizangiz rad etildi. Sabab: {reason}",
        ref_type=NotificationRefType.system,
    )

    await db.commit()
    await db.refresh(driver)
    return driver
