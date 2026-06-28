"""Umumiy validatorlar — O'zbekiston avtomobil davlat raqami va boshqalar."""
import re

# O'zbekiston fuqarolik avtomobil raqami formatlari (bo'sh joy/chiziqsiz, katta harf):
#   01A123BC   — viloyat(2 raqam) + 1 harf + 3 raqam + 2 harf
#   01123ABC   — viloyat(2 raqam) + 3 raqam + 3 harf
#   30BB777AA  — viloyat(2 raqam) + 2 harf + 3 raqam + 2 harf
_UZ_PLATE_PATTERNS = [
    re.compile(r"^\d{2}[A-Z]\d{3}[A-Z]{2}$"),
    re.compile(r"^\d{2}\d{3}[A-Z]{3}$"),
    re.compile(r"^\d{2}[A-Z]{2}\d{3}[A-Z]{2}$"),
]

# Faqat lotin harflari ishlatiladi — kirillchaga o'xshash harflarni almashtirish
_CYRILLIC_TO_LATIN = str.maketrans({
    "А": "A", "В": "B", "С": "C", "Е": "E", "Н": "H", "К": "K",
    "М": "M", "О": "O", "Р": "P", "Т": "T", "Х": "X", "У": "Y",
})


def normalize_uz_plate(raw: str) -> str:
    """Bo'sh joy/chiziqlarni olib tashlaydi, katta harfga o'tkazadi, kirillni lotinga."""
    cleaned = re.sub(r"[\s\-]", "", raw or "")
    return cleaned.upper().translate(_CYRILLIC_TO_LATIN)


def validate_uz_plate(raw: str) -> str:
    """Raqamni normallashtiradi va O'zbekiston formatiga tekshiradi.

    Mos kelmasa ValueError ko'taradi. Mos kelsa normallashgan raqamni qaytaradi.
    """
    plate = normalize_uz_plate(raw)

    if len(plate) < 7 or len(plate) > 9:
        raise ValueError(
            "Avtomobil raqami noto'g'ri. O'zbekiston namunasi: 01A123BC"
        )

    if not any(p.match(plate) for p in _UZ_PLATE_PATTERNS):
        raise ValueError(
            "Avtomobil raqami O'zbekiston formatiga mos emas. "
            "Masalan: 01A123BC, 01123ABC yoki 30BB777AA"
        )

    region = int(plate[:2])
    if not (1 <= region <= 99):
        raise ValueError("Viloyat kodi 01 dan 99 gacha bo'lishi kerak")

    return plate
