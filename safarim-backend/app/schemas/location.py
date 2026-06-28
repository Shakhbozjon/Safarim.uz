from pydantic import BaseModel


class DistrictResponse(BaseModel):
    id: int
    name_uz: str
    name_ru: str
    slug: str

    model_config = {"from_attributes": True}


class RegionResponse(BaseModel):
    id: int
    name_uz: str
    name_ru: str
    slug: str
    order: int

    model_config = {"from_attributes": True}


class RegionWithDistrictsResponse(RegionResponse):
    districts: list[DistrictResponse]
