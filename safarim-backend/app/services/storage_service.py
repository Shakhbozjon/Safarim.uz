import uuid
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from fastapi import UploadFile, HTTPException
from app.core.config import settings


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
                config=Config(signature_version="s3v4"),
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
                config=Config(signature_version="s3v4"),
                region_name="us-east-1",
            )
        return self._public_client

    def _ensure_bucket(self, bucket: str) -> None:
        try:
            self.client.head_bucket(Bucket=bucket)
        except ClientError:
            self.client.create_bucket(Bucket=bucket)

    async def upload(self, file: UploadFile, bucket: str, folder: str = "") -> str:
        allowed_types = {"image/jpeg", "image/png", "image/jpg", "image/webp"}
        if file.content_type not in allowed_types:
            raise HTTPException(status_code=400, detail="Faqat JPEG/PNG formatidagi rasm yuklang")

        max_size = 5 * 1024 * 1024  # 5 MB
        content = await file.read()
        if len(content) > max_size:
            raise HTTPException(status_code=400, detail="Rasm hajmi 5 MB dan oshmasligi kerak")

        ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else "jpg"
        key = f"{folder}/{uuid.uuid4()}.{ext}".lstrip("/")

        try:
            self._ensure_bucket(bucket)
            self.client.put_object(
                Bucket=bucket,
                Key=key,
                Body=content,
                ContentType=file.content_type,
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Fayl yuklashda xato: {str(e)}")

        return key

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
