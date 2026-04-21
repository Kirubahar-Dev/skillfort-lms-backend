from functools import lru_cache
from pydantic import BaseModel, field_validator
from dotenv import load_dotenv
import os

load_dotenv()


class Settings(BaseModel):
    app_name: str = "Skillfort LMS API"
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./skillfort_prod.db")

    @field_validator("database_url")
    @classmethod
    def fix_postgres_url(cls, v: str) -> str:
        # Supabase / Render provide postgres:// but SQLAlchemy needs postgresql://
        if v.startswith("postgres://"):
            return v.replace("postgres://", "postgresql://", 1)
        return v
    secret_key: str = os.getenv("SECRET_KEY", "change-me")
    algorithm: str = os.getenv("ALGORITHM", "HS256")
    access_token_expire_minutes: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))
    refresh_token_expire_days: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

    frontend_url: str = os.getenv("FRONTEND_URL", "http://localhost:5173")
    allowed_origins: str = os.getenv("ALLOWED_ORIGINS", "http://127.0.0.1:5173,http://localhost:5173")

    judge0_api_url: str = os.getenv("JUDGE0_API_URL", "https://judge0-ce.p.rapidapi.com")
    judge0_api_key: str = os.getenv("JUDGE0_API_KEY", "")

    razorpay_key_id: str = os.getenv("RAZORPAY_KEY_ID", "")
    razorpay_key_secret: str = os.getenv("RAZORPAY_KEY_SECRET", "")

    smtp_host: str = os.getenv("SMTP_HOST", "")
    smtp_port: int = int(os.getenv("SMTP_PORT", "587"))
    smtp_user: str = os.getenv("SMTP_USER", "")
    smtp_password: str = os.getenv("SMTP_PASSWORD", "")
    brevo_api_key: str = os.getenv("BREVO_API_KEY", "")

    file_storage_dir: str = os.getenv("FILE_STORAGE_DIR", "./storage")

    supabase_url: str = os.getenv("SUPABASE_URL", "")
    supabase_service_key: str = os.getenv("SUPABASE_SERVICE_KEY", "")
    supabase_storage_bucket: str = os.getenv("SUPABASE_STORAGE_BUCKET", "course-videos")

    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")


@lru_cache
def get_settings() -> Settings:
    return Settings()
