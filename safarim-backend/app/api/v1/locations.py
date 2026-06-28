from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.models.location import Region, District
from app.schemas.location import RegionResponse, RegionWithDistrictsResponse, DistrictResponse

router = APIRouter()


@router.get(
    "/regions",
    response_model=list[RegionResponse],
    summary="Barcha viloyatlar ro'yxati",
)
async def get_regions(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Region).order_by(Region.order))
    return result.scalars().all()


@router.get(
    "/regions/{region_id}/districts",
    response_model=list[DistrictResponse],
    summary="Viloyat tumanlari",
)
async def get_districts(region_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Region).where(Region.id == region_id))
    region = result.scalar_one_or_none()
    if not region:
        raise HTTPException(status_code=404, detail="Viloyat topilmadi")

    result = await db.execute(
        select(District)
        .where(District.region_id == region_id)
        .order_by(District.name_uz)
    )
    return result.scalars().all()


@router.get(
    "/regions/all",
    response_model=list[RegionWithDistrictsResponse],
    summary="Barcha viloyatlar va tumanlar (bitta so'rovda)",
)
async def get_all_with_districts(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Region)
        .options(selectinload(Region.districts))
        .order_by(Region.order)
    )
    return result.scalars().all()
