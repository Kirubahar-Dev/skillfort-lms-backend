import os
import uuid
from app.utils.config import get_settings


def upload_video(file_bytes: bytes, filename: str, content_type: str = "video/mp4") -> str:
    """Upload video to Supabase Storage and return public URL. Falls back to local if not configured."""
    settings = get_settings()

    if settings.supabase_url and settings.supabase_service_key:
        try:
            from supabase import create_client
            client = create_client(settings.supabase_url, settings.supabase_service_key)
            ext = filename.rsplit(".", 1)[-1] if "." in filename else "mp4"
            unique_name = f"{uuid.uuid4().hex}.{ext}"
            bucket = settings.supabase_storage_bucket
            client.storage.from_(bucket).upload(
                unique_name,
                file_bytes,
                file_options={"content-type": content_type, "upsert": "true"}
            )
            public_url = client.storage.from_(bucket).get_public_url(unique_name)
            return public_url
        except Exception as e:
            raise RuntimeError(f"Supabase upload failed: {e}")
    else:
        # Local fallback
        storage_dir = os.path.join(settings.file_storage_dir, "videos")
        os.makedirs(storage_dir, exist_ok=True)
        ext = filename.rsplit(".", 1)[-1] if "." in filename else "mp4"
        unique_name = f"{uuid.uuid4().hex}.{ext}"
        path = os.path.join(storage_dir, unique_name)
        with open(path, "wb") as f:
            f.write(file_bytes)
        return f"/storage/videos/{unique_name}"
