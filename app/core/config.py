from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: str = "postgresql://destined:destined_dev@localhost:5432/destined_school"

    jwt_private_key_path: str = "secrets/private.pem"
    jwt_public_key_path: str = "secrets/public.pem"
    jwt_private_key: Optional[str] = None
    jwt_public_key: Optional[str] = None
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    r2_account_id: Optional[str] = None
    r2_access_key_id: Optional[str] = None
    r2_secret_access_key: Optional[str] = None
    r2_bucket_name: str = "destined-images"
    cdn_base_url: str = "https://cdn.destinedchampions.com"

    whatsapp_number: str = "+2348115742616"

    smtp_host: Optional[str] = None
    smtp_port: int = 587
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_from_email: Optional[str] = None
    smtp_tls: bool = True
    notification_email: Optional[str] = None

    cors_origins: list[str] = [
        "https://destinedchampions.com",
        "https://admin.destinedchampions.com",
        "https://schoolmanagement.osawesedos.workers.dev",
        "https://admin.schoolmanagement.osawesedos.workers.dev",
        "http://localhost:3005",
        "http://localhost:3006",
    ]

    cors_origins_extra: str = ""


settings = Settings()
