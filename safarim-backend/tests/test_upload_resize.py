"""Rasm saqlashdan OLDIN kichraytiriladi.

Ilgari asl fayl (5MB gacha) o'sha holicha MinIO'ga tushardi va o'sha holicha
yo'lovchining telefoniga ketardi — avatar 80px doirachada ko'rsatilsa ham.
Safarlar ro'yxatida o'nta haydovchi = o'nlab megabayt.
"""
import io

import pytest
from PIL import Image

from app.services.storage_service import (
    AVATAR_MAX_SIDE,
    DOCUMENT_MAX_SIDE,
    StorageService,
)


def _img(w, h, fmt="JPEG", rotate_exif=False) -> bytes:
    img = Image.new("RGB", (w, h))
    px = img.load()
    for x in range(0, w, 4):
        for y in range(0, h, 4):
            px[x, y] = ((x * 7) % 256, (y * 5) % 256, (x + y) % 256)
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    return buf.getvalue()


def _size_of(data: bytes):
    with Image.open(io.BytesIO(data)) as im:
        return im.size


# ─── Kichraytirish ───────────────────────────────────────────────────────────

def test_katta_avatar_kichrayadi():
    big = _img(3000, 2000)
    out = StorageService._shrink(big, "JPEG", AVATAR_MAX_SIDE)

    assert max(_size_of(out)) == AVATAR_MAX_SIDE
    assert len(out) < len(big)


def test_tomonlar_nisbati_saqlanadi():
    out = StorageService._shrink(_img(3000, 1500), "JPEG", AVATAR_MAX_SIDE)
    w, h = _size_of(out)
    assert w == AVATAR_MAX_SIDE
    assert abs(w / h - 2.0) < 0.02       # 2:1 nisbat buzilmasin


def test_kichik_rasm_qayta_kodlanmaydi():
    """Chegaradan kichik bo'lsa originalga TEGILMAYDI — keraksiz qayta
    kodlash sifatni yo'qotadi va hech narsa yutdirmaydi."""
    small = _img(300, 200)
    out = StorageService._shrink(small, "JPEG", AVATAR_MAX_SIDE)
    assert out is small or out == small


def test_hujjat_chegarasi_kengroq():
    """Guvohnomani ADMIN O'QIYDI — yozuv ko'rinishi kerak."""
    assert DOCUMENT_MAX_SIDE > AVATAR_MAX_SIDE
    out = StorageService._shrink(_img(3000, 2000), "JPEG", DOCUMENT_MAX_SIDE)
    assert max(_size_of(out)) == DOCUMENT_MAX_SIDE


def test_png_png_bolib_qoladi():
    """Format o'zgarmasin — shaffoflik yo'qolmasin va kengaytma mos kelsin."""
    out = StorageService._shrink(_img(1200, 900, fmt="PNG"), "PNG", AVATAR_MAX_SIDE)
    with Image.open(io.BytesIO(out)) as im:
        assert im.format == "PNG"


def test_hajm_sezilarli_kamayadi():
    """Asosiy maqsad — trafik. 3000x2000 surat avatar uchun kichrayganda
    hajmi bir necha barobar tushishi kerak."""
    big = _img(3000, 2000)
    out = StorageService._shrink(big, "JPEG", AVATAR_MAX_SIDE)
    assert len(out) * 4 < len(big)


# ─── EXIF burilishi ──────────────────────────────────────────────────────────

def test_exif_burilishi_pikselga_tatbiq_qilinadi():
    """⚠️ Telefon surati EXIF'da «burilgan» deb belgilanadi, pikselda esa
    yonboshlab turadi. Qayta kodlaganda EXIF yo'qoladi — agar burilishni
    pikselga tatbiq qilmasak, kichraytirilgan surat yonboshlab qoladi."""
    img = Image.new("RGB", (2000, 1000), (120, 30, 200))
    exif = img.getexif()
    exif[274] = 6          # Orientation = 90° ga burilgan
    buf = io.BytesIO()
    img.save(buf, format="JPEG", exif=exif)

    out = StorageService._shrink(buf.getvalue(), "JPEG", AVATAR_MAX_SIDE)
    w, h = _size_of(out)
    # Burilish tatbiq qilinsa eni va bo'yi ALMASHADI: 2000x1000 → bo'yi uzun
    assert h > w, "EXIF burilishi tatbiq qilinmagan — surat yonboshlab qoladi"
