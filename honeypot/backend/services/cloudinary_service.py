"""
Cloudinary Service — single point of contact for all cloud file storage.
Every other service MUST go through this module; none should import cloudinary directly.
"""

import io
import logging
from typing import Optional

import cloudinary
import cloudinary.uploader

from config import settings

logger = logging.getLogger("cloudinary_service")

# ── SDK configuration (runs once at import time) ──────────────
cloudinary.config(
    cloud_name=getattr(settings, "CLOUDINARY_CLOUD_NAME", ""),
    api_key=getattr(settings, "CLOUDINARY_API_KEY", ""),
    api_secret=getattr(settings, "CLOUDINARY_API_SECRET", ""),
    secure=True,
)

_configured = bool(
    getattr(settings, "CLOUDINARY_CLOUD_NAME", "")
    and getattr(settings, "CLOUDINARY_API_KEY", "")
    and getattr(settings, "CLOUDINARY_API_SECRET", "")
)

if _configured:
    logger.info("✅ Cloudinary service configured")
else:
    logger.warning("⚠️ Cloudinary credentials missing — uploads will fail")


# ── Folder constants ──────────────────────────────────────────
FOLDER_AUDIO_CHUNKS = "honeybadger/audio/chunks"
FOLDER_AUDIO_SYNTHESIZED = "honeybadger/audio/synthesized"
FOLDER_VOICES = "honeybadger/voices"
FOLDER_REPORTS = "honeybadger/reports"


class CloudinaryService:
    """Reusable helpers for uploading / deleting raw files on Cloudinary."""

    # ── upload helpers ────────────────────────────────────────

    def upload_audio(
        self,
        file_bytes: bytes,
        filename: str,
        folder: str = FOLDER_AUDIO_CHUNKS,
    ) -> str:
        """
        Upload an audio blob (WAV / MP3 / WebM etc.) and return the secure URL.

        Args:
            file_bytes: Raw audio bytes
            filename:   Desired filename (without folder prefix)
            folder:     Cloudinary folder path

        Returns:
            Cloudinary secure_url string.

        Raises:
            RuntimeError on upload failure.
        """
        return self._upload(file_bytes, filename, folder)

    def upload_voice_sample(self, file_bytes: bytes, filename: str) -> str:
        """Upload a voice-clone sample to honeybadger/voices/."""
        return self._upload(file_bytes, filename, FOLDER_VOICES)

    def upload_report(self, file_bytes: bytes, filename: str) -> str:
        """Upload a report file (PDF / JSON / CSV) to honeybadger/reports/."""
        return self._upload(file_bytes, filename, FOLDER_REPORTS)

    # ── deletion ──────────────────────────────────────────────

    def delete_file(self, public_id: str) -> bool:
        """
        Delete a file on Cloudinary by its public_id.

        Returns True on success, False otherwise.
        """
        try:
            result = cloudinary.uploader.destroy(
                public_id, resource_type="raw"
            )
            ok = result.get("result") == "ok"
            if ok:
                logger.info(f"🗑️ Deleted from Cloudinary: {public_id}")
            else:
                logger.warning(f"Cloudinary delete returned: {result}")
            return ok
        except Exception as e:
            logger.error(f"Cloudinary delete error ({public_id}): {e}")
            return False

    # ── utility ───────────────────────────────────────────────

    @staticmethod
    def get_public_id(cloudinary_url: str) -> Optional[str]:
        """
        Extract the public_id from a Cloudinary secure URL.

        Example URL:
            https://res.cloudinary.com/<cloud>/raw/upload/v123/honeybadger/audio/chunks/foo.wav
        Returns:
            honeybadger/audio/chunks/foo  (no extension)
        """
        if not cloudinary_url:
            return None
        try:
            # Everything after "/upload/vXXX/" is <public_id>.<ext>
            parts = cloudinary_url.split("/upload/")
            if len(parts) < 2:
                return None
            after = parts[1]  # e.g. "v123/honeybadger/audio/chunks/foo.wav"
            # Strip the version prefix
            after_parts = after.split("/", 1)
            if len(after_parts) < 2:
                return None
            path_with_ext = after_parts[1]  # "honeybadger/audio/chunks/foo.wav"
            # Strip file extension
            dot_idx = path_with_ext.rfind(".")
            if dot_idx != -1:
                return path_with_ext[:dot_idx]
            return path_with_ext
        except Exception:
            return None

    # ── internal ──────────────────────────────────────────────

    def _upload(self, file_bytes: bytes, filename: str, folder: str) -> str:
        """Upload raw bytes to Cloudinary. Raises on failure."""
        try:
            result = cloudinary.uploader.upload(
                io.BytesIO(file_bytes),
                resource_type="raw",
                folder=folder,
                public_id=filename.rsplit(".", 1)[0],  # strip extension from id
                overwrite=True,
                # Preserve the original extension so the URL ends with it
                format=filename.rsplit(".", 1)[-1] if "." in filename else None,
            )
            url = result.get("secure_url")
            if not url:
                raise RuntimeError(f"Cloudinary returned no URL: {result}")
            logger.info(f"☁️ Uploaded to Cloudinary: {url}")
            return url
        except Exception as e:
            logger.error(f"Cloudinary upload failed ({folder}/{filename}): {e}", exc_info=True)
            raise RuntimeError(f"Cloudinary upload failed: {e}") from e


# Singleton
cloudinary_service = CloudinaryService()
