import cloudinary
import cloudinary.uploader
from core.config import settings
from loguru import logger

cloudinary.config(
    cloud_name=settings.CLOUDINARY_CLOUD_NAME,
    api_key=settings.CLOUDINARY_API_KEY,
    api_secret=settings.CLOUDINARY_API_SECRET,
    secure=True
)


async def upload_image(file_bytes: bytes, folder: str = "kisansathi", filename: str = None) -> dict:
    """Upload image to Cloudinary and return URL + metadata."""
    try:
        options = {
            "folder": folder,
            "resource_type": "image",
            "quality": "auto:good",
            "fetch_format": "auto",
        }
        if filename:
            options["public_id"] = filename

        result = cloudinary.uploader.upload(file_bytes, **options)
        return {
            "url": result["secure_url"],
            "public_id": result["public_id"],
            "width": result.get("width"),
            "height": result.get("height"),
            "format": result.get("format"),
            "size": result.get("bytes"),
        }
    except Exception as e:
        logger.error(f"Cloudinary upload error: {e}")
        raise Exception(f"Image upload failed: {str(e)}")


async def delete_image(public_id: str) -> bool:
    """Delete image from Cloudinary."""
    try:
        result = cloudinary.uploader.destroy(public_id)
        return result.get("result") == "ok"
    except Exception as e:
        logger.error(f"Cloudinary delete error: {e}")
        return False


def get_optimized_url(public_id: str, width: int = 800, quality: str = "auto") -> str:
    """Get optimized image URL with transformations."""
    return cloudinary.CloudinaryImage(public_id).build_url(
        width=width,
        quality=quality,
        fetch_format="auto",
        crop="fill"
    )
