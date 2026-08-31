"""Media maydonlari uchun umumiy tiplar."""
from typing import Annotated
from pydantic import BeforeValidator

from app.services.storage_service import photo_url

# Bazadagi MinIO kaliti javobga chiqishdan oldin to'liq manzilga aylanadi.
# Har bir sxemada alohida validator yozish o'rniga bitta tip qayta ishlatiladi.
PhotoUrl = Annotated[str | None, BeforeValidator(photo_url)]
