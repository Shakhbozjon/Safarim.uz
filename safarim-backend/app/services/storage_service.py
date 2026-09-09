import io
import logging
import uuid

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from fastapi import UploadFile, HTTPException
from PIL import Image
from app.core.config import settings

logger = logging.getLogger(__name__)


class StorageService:
    """MinIO orqali fayl saqlash."""

    def __init__(self):
        self._client = None
        self._public_client = None

    @property
    def client(self):
        """Ichki klient — yuklash/o'qish uchun (MINIO_ENDPOINT, masalan minio:9000)."""
        if self._client is None:
            self._client = boto3.client(
                "s3",
                endpoint_url=f"{'https' if settings.MINIO_SECURE else 'http'}://{settings.MINIO_ENDPOINT}",
                aws_access_key_id=settings.MINIO_ACCESS_KEY,
                aws_secret_access_key=settings.MINIO_SECRET_KEY,
                config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
                region_name="us-east-1",
            )
        return self._client

    @property
    def public_client(self):
        """Public klient — presigned URL brauzer ko'radigan host uchun imzolanadi.
        MINIO_PUBLIC_ENDPOINT bo'sh bo'lsa ichki klientga teng (lokal dev)."""
        if not settings.MINIO_PUBLIC_ENDPOINT:
            return self.client
        if self._public_client is None:
            self._public_client = boto3.client(
                "s3",
                endpoint_url=f"{'https' if settings.MINIO_PUBLIC_SECURE else 'http'}://{settings.MINIO_PUBLIC_ENDPOINT}",
                aws_access_key_id=settings.MINIO_ACCESS_KEY,
                aws_secret_access_key=settings.MINIO_SECRET_KEY,
                config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
                region_name="us-east-1",
            )
        return self._public_client

    def _ensure_bucket(self, bucket: str) -> None:
        try:
            self.client.head_bucket(Bucket=bucket)
        except ClientError:
            self.client.create_bucket(Bucket=bucket)

    # Faqat shu formatlar; qiymat — (Content-Type, fayl kengaytmasi)
    _FORMATS = {
        "JPEG": ("image/jpeg", "jpg"),
        "PNG": ("image/png", "png"),
        "WEBP": ("image/webp", "webp"),
    }

    async def upload(self, file: UploadFile, bucket: str, folder: str = "") -> str:
        max_size = 5 * 1024 * 1024  # 5 MB
        content = await file.read()
        if len(content) > max_size:
            raise HTTPException(status_code=400, detail="Rasm hajmi 5 MB dan oshmasligi kerak")

        # Fayl turini MIJOZ aytganiga qarab emas, faylning O'ZIGA qarab
        # aniqlaymiz: `content_type` ham, fayl nomi ham foydalanuvchi qo'lida —
        # ilgari ikkalasiga ishonilardi va istalgan bayt "image/png" bo'lib
        # saqlanardi. Kengaytma ham shu yerdan olinadi.
        try:
            with Image.open(io.BytesIO(content)) as probe:
                fmt = (probe.format or "").upper()
                probe.verify()
        except Exception:
            raise HTTPException(status_code=400, detail="Bu fayl rasm emas yoki buzilgan")

        if fmt not in self._FORMATS:
            raise HTTPException(status_code=400, detail="Faqat JPEG, PNG yoki WEBP rasm yuklang")
        content_type, ext = self._FORMATS[fmt]

        key = f"{folder}/{uuid.uuid4()}.{ext}".lstrip("/")

        try:
            self._ensure_bucket(bucket)
            self.client.put_object(
                Bucket=bucket,
                Key=key,
                Body=content,
                ContentType=content_type,
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Fayl yuklashda xato: {str(e)}")

        return key

    def delete_file(self, key: str, bucket: str) -> bool:
        """Faylni o'chiradi. Xato bo'lsa jarayon to'xtamaydi — chaqiruvchi
        amal (masalan hisobni o'chirish) fayl tufayli uzilib qolmasligi kerak.
        """
        if not key:
            return False
        try:
            self.client.delete_object(Bucket=bucket, Key=key)
            return True
        except Exception as exc:
            logger.warning("Fayl o'chirilmadi (%s/%s): %s", bucket, key, exc)
            return False

    def get_url(self, key: str, bucket: str, expires_in: int = 3600) -> str:
        # Presigned URL public klient (brauzer ko'radigan host) bilan imzolanadi
        try:
            return self.public_client.generate_presigned_url(
                "get_object",
                Params={"Bucket": bucket, "Key": key},
                ExpiresIn=expires_in,
            )
        except Exception:
            return ""


storage_service = StorageService()


def photo_url(key: str | None) -> str | None:
    """Rasm kalitini brauzer ocha oladigan to'liq manzilga aylantiradi.

    Bazada faqat MinIO kaliti saqlanadi ("avatars/uuid.jpg"). Uni javobda o'sha
    holicha berish mumkin emas: brauzer uni sayt ildiziga nisbatan hal qilib 404
    oladi va rasm o'rniga singan belgi chiqadi — barcha avatarlar shu sababdan
    ko'rinmasdi.

    Allaqachon to'liq manzil kelsa tegilmaydi — funksiya ikki qatlamda
    (sxema validatori va qo'lda yig'ilgan javoblarda) ishlatiladi.
    """
    if not key:
        return None
    if key.startswith("http://") or key.startswith("https://"):
        return key
    from app.core.config import settings
    return storage_service.get_url(key, settings.MINIO_BUCKET_PHOTOS) or None
