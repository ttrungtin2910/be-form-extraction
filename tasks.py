import os
import time
import logging
from typing import Dict, Any

from celery import states

from celery_app import celery_app

from database.firestore import ImageData, upsert_image, get_image
from database.ggc_storage import upload_image_to_gcs
from utils.file_processing import download_image_from_url_sync
from chain.completions import TicketChatBot
from properties.config import Configuration

# Configure logger
logger = logging.getLogger(__name__)

# Initialize configuration
_config = Configuration()
_bot = TicketChatBot(_config)

# Create upload directory
os.makedirs(_config.UPLOAD_FOLDER, exist_ok=True)


def _timestamp_name(ext: str) -> str:
    return time.strftime("%Y%m%d_%H%M%S") + f"_{int(time.time()*1000)%1000:03d}{ext}"


@celery_app.task(bind=True, name="tasks.upload_image")
def upload_image_task(self, temp_local_path: str, original_filename: str, status: str, folder_path: str) -> Dict[str, Any]:
    """Upload image (stored temporarily) to GCS & Firestore.

    Args:
        temp_local_path: Path to file saved by API endpoint.
        original_filename: Original name from client (for extension extraction only).
        status: Initial status (e.g., 'Uploaded').
        folder_path: Optional logical folder path.
    Returns metadata similar to synchronous endpoint.
    """
    try:
        ext = os.path.splitext(original_filename or "")[1].lower() or ".jpg"
        image_name = _timestamp_name(ext)
        destination_blob_name = f"{folder_path}/{image_name}" if folder_path else image_name

        upload_image_to_gcs(
            bucket_name=_config.BUCKET_NAME,
            source_file_path=temp_local_path,
            destination_blob_name=destination_blob_name,
        )

        gcs_url = f"https://storage.googleapis.com/{_config.BUCKET_NAME}/{destination_blob_name}"
        file_size_mb = round(os.path.getsize(temp_local_path) / (1024 * 1024), 2)
        meta = ImageData(
            Status=status,
            ImageName=image_name,
            ImagePath=gcs_url,
            CreatedAt=image_name.split(ext)[0],  # reuse timestamp portion
            FolderPath=folder_path,
            Size=file_size_mb,
        )
        upsert_image(meta, _config.COLLECTION_NAME_IMAGE_DETAIL, meta.ImageName)
        try:
            os.remove(temp_local_path)
        except OSError:
            pass
        return {"image_name": image_name, "url": gcs_url, "status": status}
    except Exception as e:  # pragma: no cover
        raise


@celery_app.task(bind=True, name="tasks.extract_form")
def extract_form_task(
    self,
    image_name: str,
    image_url: str,
    size: float,
    status: str,
    created_at: str,
    folder_path: str,
) -> Dict[str, Any]:
    """Perform form extraction (OpenAI + Firestore updates)."""
    local_path = os.path.join(_config.UPLOAD_FOLDER, image_name)
    try:
        logger.info(f"Starting form extraction for {image_name}")
        
        # Mark image status as Processing immediately (avoid duplicate clicks client-side)
        try:
            existing = get_image(image_name, _config.COLLECTION_NAME_IMAGE_DETAIL) or {}
            processing_meta = ImageData(
                Status="Processing",
                ImageName=image_name,
                ImagePath=image_url,
                CreatedAt=created_at or existing.get("CreatedAt", ""),
                FolderPath=folder_path or existing.get("FolderPath", ""),
                Size=size or existing.get("Size", 0.0),
            )
            upsert_image(processing_meta, _config.COLLECTION_NAME_IMAGE_DETAIL, image_name)
            logger.info(f"Marked {image_name} as Processing")
        except Exception as e:
            # Non-fatal – continue extraction even if we cannot pre-mark
            logger.warning(f"Could not mark image as Processing: {e}")
        
        # Download image using synchronous method (avoid asyncio.run conflicts)
        logger.info(f"Downloading image from {image_url}")
        download_image_from_url_sync(image_url, local_path)
        logger.info(f"Download completed for {image_name}")

        # Analyze (synchronous wrapper)
        logger.info(f"Starting AI analysis for {image_name}")
        result = _bot.analyze_ticket_sync(local_path, "")
        if not isinstance(result, dict):
            result = {"raw": str(result)}
        logger.info(f"AI analysis completed for {image_name}")

        # Determine size fallback (reuse previously fetched existing if available)
        if not size:
            if 'existing' not in locals():
                existing = get_image(image_name, _config.COLLECTION_NAME_IMAGE_DETAIL) or {}
            size = existing.get("Size", 0.0)

        # Save extraction result to forminformation collection
        form_doc = {
            "Status": "Completed",
            "ImageName": image_name,
            "ImagePath": image_url,
            "CreatedAt": created_at,
            "FolderPath": folder_path,
            "Size": size,
            "analysis_result": result,
        }
        upsert_image(form_doc, _config.COLLECTION_NAME_FORM_EXTRACT, image_name)
        logger.info(f"Saved form extraction result for {image_name}")

        # Update status in imagedetail
        meta = ImageData(
            Status="Completed",
            ImageName=image_name,
            ImagePath=image_url,
            CreatedAt=created_at,
            FolderPath=folder_path,
            Size=size,
        )
        upsert_image(meta, _config.COLLECTION_NAME_IMAGE_DETAIL, image_name)
        logger.info(f"Updated image status to Completed for {image_name}")

        # Clean up temporary file
        try:
            os.remove(local_path)
            logger.info(f"Cleaned up temporary file: {local_path}")
        except OSError as e:
            logger.warning(f"Could not remove temporary file {local_path}: {e}")
        
        logger.info(f"Form extraction completed successfully for {image_name}")
        return {"image_name": image_name, "analysis_result": result}
    except Exception as e:
        logger.error(f"Form extraction failed for {image_name}: {str(e)}")
        # Clean up temporary file on error
        try:
            if os.path.exists(local_path):
                os.remove(local_path)
        except OSError:
            pass
        raise
