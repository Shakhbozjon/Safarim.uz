"""Haydovchilik guvohnomasi rasmini tekshirish.

Maqsad: foydalanuvchi har xil/yaroqsiz rasm (selfi, skrinshot, bo'sh rasm,
renomlangan fayl) o'rniga haqiqiy guvohnoma suratini yuklaganini aniqlash.

Ikki qatlam:
  1) Strukturaviy (har doim) — Pillow orqali: haqiqiy rasmmi, o'lcham,
     tomonlar nisbati, bo'sh/bir rangli emasligi.
  2) OCR (ixtiyoriy) — tesseract o'rnatilgan va LICENSE_OCR_ENABLED=True bo'lsa,
     rasmdagi matnda guvohnoma kalit so'zlarini qidiradi. Tesseract topilmasa
     jimgina o'tkazib yuboriladi (dev muhitni buzmaslik uchun).
"""
import io
import logging

from fastapi import UploadFile, HTTPException
from PIL import Image, ImageStat

from app.core.config import settings

logger = logging.getLogger(__name__)

# Minimal o'lcham — kichik ikonka yoki past sifatli rasmni rad etish
_MIN_WIDTH = 400
_MIN_HEIGHT = 250

# Tomonlar nisbati chegarasi — juda cho'zilgan banner/chiziqli rasmni rad etish
_MIN_RATIO = 0.4
_MAX_RATIO = 3.0

# O'rtacha rang og'ishi shu qiymatdan past bo'lsa — rasm bo'sh/bir rangli deb hisoblanadi
_MIN_STDDEV = 10.0

# OCR matnida shu so'zlardan birortasi topilsa — guvohnoma deb qabul qilinadi
_LICENSE_KEYWORDS = (
    "GUVOHNOMA", "HAYDOVCHI", "AVTOMOBIL",
    "DRIVING", "LICENCE", "LICENSE", "PERMIT", "PERMIS",
    "ВОДИТЕЛ", "УДОСТОВЕРЕНИЕ", "UZBEKISTAN", "O'ZBEKISTON", "OZBEKISTON",
)


async def validate_license_image(file: UploadFile) -> None:
    """Guvohnoma rasmini tekshiradi. Yaroqsiz bo'lsa HTTPException(400) ko'taradi.

    Faylni o'qib bo'lgach pointerni boshiga qaytaradi, shunda keyin yuklash
    (storage_service.upload) faylni qayta o'qiy oladi.
    """
    content = await file.read()
    await file.seek(0)

    if not content:
        raise HTTPException(status_code=400, detail="Rasm fayli bo'sh")

    # 1) Haqiqiy rasm ekanini tekshirish (renomlangan/buzilgan fayl emas)
    try:
        with Image.open(io.BytesIO(content)) as probe:
            probe.verify()  # struktura butunligini tekshiradi
        img = Image.open(io.BytesIO(content)).convert("RGB")
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Yuklangan fayl haqiqiy rasm emas. JPEG yoki PNG rasm yuklang",
        )

    width, height = img.size

    # 2) Minimal o'lcham
    if width < _MIN_WIDTH or height < _MIN_HEIGHT:
        raise HTTPException(
            status_code=400,
            detail="Rasm juda kichik. Guvohnomani yaqindan va aniq suratga oling",
        )

    # 3) Tomonlar nisbati
    ratio = width / height
    if ratio < _MIN_RATIO or ratio > _MAX_RATIO:
        raise HTTPException(
            status_code=400,
            detail="Rasm guvohnomaga o'xshamaydi. Hujjatning old tomonini to'liq suratga oling",
        )

    # 4) Bo'sh / bir rangli rasm emasligi (oq fon, bo'sh skrinshot)
    stat = ImageStat.Stat(img)
    avg_stddev = sum(stat.stddev) / len(stat.stddev)
    if avg_stddev < _MIN_STDDEV:
        raise HTTPException(
            status_code=400,
            detail="Rasm bo'sh yoki bir xil rangda. Guvohnoma aniq ko'rinishi kerak",
        )

    # 5) OCR — matn bo'yicha guvohnoma ekanini tasdiqlash (ixtiyoriy)
    if getattr(settings, "LICENSE_OCR_ENABLED", False):
        _verify_license_text(img)


def _verify_license_text(img: Image.Image) -> None:
    """Tesseract OCR orqali rasmda guvohnoma matnini qidiradi.

    Tesseract o'rnatilmagan bo'lsa — jimgina o'tkazib yuboriladi (rad etmaydi).
    """
    try:
        import pytesseract
        text = pytesseract.image_to_string(img).upper()
    except Exception as exc:  # pytesseract yo'q yoki tesseract binari yo'q
        logger.warning("Guvohnoma OCR o'tkazib yuborildi (tesseract topilmadi?): %s", exc)
        return

    if not any(keyword in text for keyword in _LICENSE_KEYWORDS):
        raise HTTPException(
            status_code=400,
            detail="Rasmda haydovchilik guvohnomasi aniqlanmadi. "
                   "To'g'ri hujjatning aniq suratini yuklang",
        )
