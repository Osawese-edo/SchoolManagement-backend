import os
import uuid
from fastapi import APIRouter, Depends, Request, UploadFile, File, Query
from app.core.exceptions import BadRequestException
from app.core.rate_limit import limiter

from app.core.dependencies import require_permission
from app.models.user import User
from app.services.upload_service import UploadService, validate_magic_bytes, UPLOAD_DIR

router = APIRouter()

EXTENSION_MAP = {
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
    "webp": "image/webp",
}
ALLOWED_TYPES = {"image/jpeg", "image/jpg", "image/png", "image/webp"}
MAX_SIZE = 5 * 1024 * 1024


def _get_ext(filename: str) -> str:
    return filename.rsplit(".", 1)[-1].lower() if "." in filename else "webp"


@router.post("/upload")
@limiter.limit("10/minute")
async def upload_image(
    request: Request,
    file: UploadFile = File(...),
    subdirectory: str = Query("gallery", description="Subdirectory to store the file under"),
    current_user: User = Depends(require_permission("content:manage")),
):
    ext = _get_ext(file.filename or "image.webp")
    content_type = file.content_type or EXTENSION_MAP.get(ext, "application/octet-stream")

    if content_type not in ALLOWED_TYPES:
        raise BadRequestException(detail="Only JPEG, PNG, and WebP images allowed")
    content = await file.read()
    if len(content) > MAX_SIZE:
        raise BadRequestException(detail="File too large (max 5MB)")
    if not validate_magic_bytes(content):
        raise BadRequestException(detail="Invalid image file - magic bytes validation failed")

    safe_subdir = os.path.normpath(subdirectory).lstrip(os.sep)
    if safe_subdir.startswith("..") or os.path.isabs(safe_subdir):
        raise BadRequestException(detail="Invalid subdirectory")
    full_path = os.path.normpath(os.path.join(UPLOAD_DIR, "destined-images", safe_subdir))
    if not full_path.startswith(os.path.normpath(UPLOAD_DIR)):
        raise BadRequestException(detail="Invalid subdirectory")
    filename = f"destined-images/{safe_subdir}/{uuid.uuid4()}.{ext}"

    service = UploadService()
    url, cdn_ok = service.upload(content, filename, content_type)

    storage = "cdn" if cdn_ok else "local"

    result = {"url": url, "storage": storage}
    if service.cdn_configured and not cdn_ok:
        result["warning"] = "Uploaded locally — CDN unavailable, check server logs."
    return result
