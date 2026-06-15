import io
import os
import aiofiles
import logging
from pathlib import Path
from config import settings

logger = logging.getLogger(__name__)
_AUDIO_DIR = Path("storage/audio")
_AUDIO_DIR.mkdir(parents=True, exist_ok=True)

USE_LOCAL_FALLBACK = True
_minio_client = None


def _get_minio_client():
    global _minio_client, USE_LOCAL_FALLBACK
    if _minio_client is None:
        try:
            from minio import Minio
            _minio_client = Minio(
                settings.MINIO_ENDPOINT,
                access_key=settings.MINIO_ACCESS_KEY,
                secret_key=settings.MINIO_SECRET_KEY,
                secure=settings.MINIO_SECURE,
            )
            USE_LOCAL_FALLBACK = False
        except Exception:
            pass
    return _minio_client


_use_local_fallback = USE_LOCAL_FALLBACK


class Storage:
    def upload(self, object_name: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        client = _get_minio_client()
        if client:
            try:
                client.put_object(
                    settings.MINIO_BUCKET, object_name,
                    io.BytesIO(data), len(data),
                    content_type=content_type,
                )
                logger.info("Uploaded to MinIO: %s", object_name)
                return object_name
            except Exception as e:
                logger.warning("MinIO upload failed: %s -- falling back to local", e)
        local_path = Path("storage") / object_name
        local_path.parent.mkdir(parents=True, exist_ok=True)
        local_path.write_bytes(data)
        logger.info("Saved locally: %s", local_path)
        return str(local_path)

    def download(self, object_name: str) -> bytes:
        client = _get_minio_client()
        if client:
            try:
                response = client.get_object(settings.MINIO_BUCKET, object_name)
                data = response.read()
                response.close()
                response.release_conn()
                return data
            except Exception:
                pass
        local_path = Path(object_name)
        if local_path.exists():
            return local_path.read_bytes()
        raise FileNotFoundError(f"Object not found: {object_name}")


storage = Storage()


async def save_audio_locally(audio_bytes: bytes, filename: str) -> str:
    path = _AUDIO_DIR / filename
    async with aiofiles.open(path, "wb") as f:
        await f.write(audio_bytes)
    return str(path)


async def upload_to_cloudinary(audio_bytes: bytes, public_id: str) -> str:
    if settings.STORAGE_BACKEND != "cloudinary":
        return await save_audio_locally(audio_bytes, public_id + ".mp3")

    try:
        import cloudinary
        import cloudinary.uploader
        cloudinary.config(
            cloud_name=settings.CLOUDINARY_CLOUD_NAME,
            api_key=settings.CLOUDINARY_API_KEY,
            api_secret=settings.CLOUDINARY_API_SECRET,
        )
        result = cloudinary.uploader.upload(
            io.BytesIO(audio_bytes),
            resource_type="video",
            public_id=public_id,
            format="mp3",
        )
        return result["secure_url"]
    except Exception as e:
        logger.error("Cloudinary upload failed: %s -- falling back to local", e)
        return await save_audio_locally(audio_bytes, public_id + ".mp3")
