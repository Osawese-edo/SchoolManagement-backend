from app.core.config import settings


def get_storage_type(image_url: str) -> str:
    if image_url.startswith("/uploads/"):
        return "local"
    return "cdn"


def enrich_gallery_item(item: dict) -> dict:
    item["before_storage"] = get_storage_type(item.get("before_image_url", ""))
    item["after_storage"] = get_storage_type(item.get("after_image_url", ""))
    return item
