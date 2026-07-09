import io
import logging
import os
import time
from PIL import Image
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from typing import Optional
from app.core.config import settings


logger = logging.getLogger(__name__)


def validate_magic_bytes(content: bytes, allowed_types: list[str] = None) -> bool:
    if allowed_types is None:
        allowed_types = ["image/jpeg", "image/png", "image/gif", "image/webp", "application/pdf"]

    MAGIC_BYTES = {
        b'\xff\xd8\xff': "image/jpeg",
        b'\x89PNG\r\n\x1a\n': "image/png",
        b'GIF87a': "image/gif",
        b'GIF89a': "image/gif",
        b'RIFF': "image/webp",
        b'%PDF': "application/pdf",
    }

    for magic, mime in MAGIC_BYTES.items():
        if content.startswith(magic):
            return mime in (allowed_types if allowed_types else ["image/jpeg", "image/png", "image/gif", "image/webp", "application/pdf"])

    return False

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads")
MAX_RETRIES = 3
RETRY_DELAY = 1


def optimize_image(content: bytes, max_width: int = 1920, max_height: int = 1080, quality: int = 85) -> bytes:
    try:
        img = Image.open(io.BytesIO(content))
        if img.width > max_width or img.height > max_height:
            img.thumbnail((max_width, max_height), Image.LANCZOS)
        output = io.BytesIO()
        img.save(output, format=img.format or "JPEG", quality=quality, optimize=True)
        return output.getvalue()
    except Exception:
        return content


class UploadService:
    def __init__(self):
        self.client = None
        self.cdn_configured = bool(settings.r2_account_id) and bool(settings.r2_access_key_id) and bool(settings.r2_secret_access_key)
        if self.cdn_configured:
            self.client = boto3.client(
                "s3",
                endpoint_url=f"https://{settings.r2_account_id}.r2.cloudflarestorage.com",
                aws_access_key_id=settings.r2_access_key_id,
                aws_secret_access_key=settings.r2_secret_access_key,
                config=Config(signature_version="s3v4", retries={"max_attempts": 0}),
            )

    def _save_local(self, file_bytes: bytes, filename: str) -> str:
        full_path = os.path.join(UPLOAD_DIR, filename)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "wb") as f:
            f.write(file_bytes)
        return f"/uploads/{filename}"

    def upload(self, file_bytes: bytes, filename: str, content_type: str) -> tuple[str, bool]:
        if content_type and content_type.startswith("image/"):
            file_bytes = optimize_image(file_bytes)
        if not self.cdn_configured:
            logger.info("CDN not configured, saving locally: %s", filename)
            return self._save_local(file_bytes, filename), False

        last_error = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                self.client.put_object(
                    Bucket=settings.r2_bucket_name,
                    Key=filename,
                    Body=file_bytes,
                    ContentType=content_type,
                )
                url = f"{settings.cdn_base_url}/{filename}"
                logger.info("Uploaded to CDN: %s (attempt %d/%d)", url, attempt, MAX_RETRIES)
                return url, True
            except ClientError as e:
                last_error = e
                error_code = e.response.get("Error", {}).get("Code", "Unknown")
                logger.warning("CDN upload attempt %d/%d failed: [%s] %s", attempt, MAX_RETRIES, error_code, e)
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_DELAY * attempt)

        logger.error("CDN upload failed after %d attempts, falling back to local: %s", MAX_RETRIES, last_error)
        return self._save_local(file_bytes, filename), False
