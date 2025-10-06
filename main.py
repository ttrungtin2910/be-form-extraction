import uvicorn
import os
import uuid
from datetime import datetime
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.responses import JSONResponse
from chain.completions import TicketChatBot
from properties.config import Configuration
from utils.file_validation import validate_upload_file, FileValidationError
from services.form_extraction_service import FormExtractionService

from database.firestore import (
    ImageData,
    upsert_image,
    get_image,
    delete_image,
    list_images,
    upsert_folder,
    list_folders as firestore_list_folders,
    delete_folder as firestore_delete_folder,
    rename_folder as firestore_rename_folder,
)
from database.ggc_storage import (
    upload_image_to_gcs,
    delete_blobs_with_prefix,
    rename_folder as gcs_rename_folder,
)
from utils.file_processing import download_image_from_url, extract_filename_from_url

import logging
from celery_app import celery_app
from tasks import upload_image_task, extract_form_task
from celery.result import AsyncResult

# Configure logger
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Firestore Image Metadata API")

# Initialize configuration and validate required settings
config = Configuration()
config.validate_required_config()

# Initialize services
bot = TicketChatBot(config)
form_extraction_service = FormExtractionService(config)

class ExtractFormData(BaseModel):
    FolderPath: str = ""
    Status: str
    ImagePath: str  # URL of the image
    Size: float = 0.0
    ImageName: str
    CreatedAt: str


class GetFormInfoData(BaseModel):
    # Accept either 'title' (original spec) or 'ImageName' (frontend usage) for flexibility
    title: str | None = None
    ImageName: str | None = None


# Configure CORS with restricted origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "PUT"],
    allow_headers=["*"],
)

# Create upload directory
os.makedirs(config.UPLOAD_FOLDER, exist_ok=True)


@app.post("/upload-image/")
async def upload_image(
    status: str = Form(...), folderPath: str = Form(""), file: UploadFile = File(...)
):
    logger.info("Received request to upload image")
    logger.info(f"Status: {status}")
    logger.info(
        f"File: {file.filename}, size: {file.size}, content_type: {file.content_type}"
    )

    # Validate file extension
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in config.ALLOWED_EXTENSIONS:
        logger.warning(f"Unsupported image format: {ext}")
        raise HTTPException(status_code=400, detail=f"Unsupported image format. Allowed: {list(config.ALLOWED_EXTENSIONS)}")

    # Check file size
    if file.size and file.size > config.MAX_FILE_SIZE:
        logger.warning(f"File size {file.size} exceeds maximum {config.MAX_FILE_SIZE}")
        raise HTTPException(status_code=400, detail=f"File too large. Maximum size: {config.MAX_FILE_SIZE} bytes")

    now = datetime.utcnow()
    str_now = now.strftime("%Y%m%d_%H%M%S_%f")
    image_name = f"{str_now}{ext}"
    local_path = os.path.join(config.UPLOAD_FOLDER, image_name)

    # Save file temporarily
    with open(local_path, "wb") as f:
        f.write(await file.read())
    logger.info(f"Saved image locally at {local_path}")

    try:
        # Validate the uploaded file
        validate_upload_file(
            local_path, 
            config.MAX_FILE_SIZE, 
            config.ALLOWED_EXTENSIONS
        )
        logger.info(f"File validation successful for {image_name}")
        
        destination_blob_name = f"{folderPath}/{image_name}" if folderPath else image_name

        # Upload to Google Cloud Storage
        upload_image_to_gcs(
            bucket_name=config.BUCKET_NAME,
            source_file_path=local_path,
            destination_blob_name=destination_blob_name,
        )
        logger.info(f"Uploaded image to GCS as {destination_blob_name}")

        gcs_url = f"https://storage.googleapis.com/{config.BUCKET_NAME}/{destination_blob_name}"
        size_val = round((file.size or 0) / (1024 * 1024), 2)
        image_data = ImageData(
            Status=status,
            ImageName=image_name,
            ImagePath=gcs_url,
            CreatedAt=str_now,
            FolderPath=folderPath,
            Size=size_val,
        )

        # Save metadata to Firestore
        upsert_image(image_data, config.COLLECTION_NAME_IMAGE_DETAIL, image_data.ImageName)
        logger.info(f"Saved image metadata to Firestore: {destination_blob_name}")
        
    except FileValidationError as e:
        logger.error(f"File validation failed: {str(e)}")
        # Clean up the temporary file
        if os.path.exists(local_path):
            os.remove(local_path)
        raise HTTPException(status_code=400, detail=f"File validation failed: {str(e)}")
    except Exception as e:
        logger.error(f"Upload failed: {str(e)}")
        # Clean up the temporary file
        if os.path.exists(local_path):
            os.remove(local_path)
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")
    finally:
        # Always clean up temporary file
        if os.path.exists(local_path):
            os.remove(local_path)

    return JSONResponse(content={"message": "Image uploaded and saved successfully."})


@app.post("/images/", response_model=dict)
async def create_or_update_image(data: ImageData):
    """
    Create or update an image record in Firestore.
    """
    upsert_image(data, config.COLLECTION_NAME_IMAGE_DETAIL, data.ImageName)
    return {"message": "Image data saved successfully."}


@app.get("/images/{image_name}", response_model=ImageData)
async def read_image(image_name: str):
    """
    Retrieve an image record by image name.
    """
    image = get_image(image_name, config.COLLECTION_NAME_IMAGE_DETAIL)
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")
    return image


@app.delete("/images/{image_name}", response_model=dict)
async def remove_image(image_name: str):
    """
    Delete an image record from Firestore.
    """
    delete_image(image_name, config.COLLECTION_NAME_IMAGE_DETAIL)
    return {"message": f"Image '{image_name}' deleted successfully."}


@app.get("/images/")
async def get_all_images(folderPath: str = "", page: int = 1, limit: int = 20):
    """
    Retrieve image records. If folderPath provided, filter by that path (prefix match).
    """
    data = list_images(config.COLLECTION_NAME_IMAGE_DETAIL)
    if folderPath:
        data = [d for d in data if d.get("FolderPath", "") == folderPath]

    total = len(data)
    start = (page - 1) * limit
    end = start + limit
    data_page = data[start:end]
    return {"data": data_page, "total": total}


# Folder endpoints


# Get folders
@app.get("/folders/")
async def list_folders():
    folders = firestore_list_folders()
    return {"folders": folders}


# Create folder
@app.post("/folders/")
async def create_folder(payload: dict):
    folder_path = payload.get("folderPath", "").strip()
    if folder_path == "":
        raise HTTPException(status_code=400, detail="folderPath is required")
    upsert_folder(folder_path)
    return {"message": "Folder created or already exists", "folderPath": folder_path}


# Delete folder
@app.delete("/folders/{folder_path:path}")
async def delete_folder(folder_path: str):
    # ensure folder exists
    firestore_delete_folder(folder_path)
    delete_blobs_with_prefix(config.BUCKET_NAME, f"{folder_path}/")
    return {"message": "Folder deleted", "folderPath": folder_path}


# Rename folder
@app.post("/folders/rename")
async def rename_folder(payload: dict):
    old_path = payload.get("oldPath", "").strip()
    new_path = payload.get("newPath", "").strip()
    if not old_path or not new_path:
        raise HTTPException(status_code=400, detail="oldPath and newPath required")
    firestore_rename_folder(old_path, new_path)
    gcs_rename_folder(config.BUCKET_NAME, f"{old_path}/", f"{new_path}/")
    return {"message": "Folder renamed", "oldPath": old_path, "newPath": new_path}


@app.post("/ExtractForm")
async def extract_form(data: ExtractFormData):
    """Extract form data from image using AI analysis."""
    logger.info(f"Received request to analyze image: {data.ImageName}")
    
    try:
        # Convert Pydantic model to dict for service
        data_dict = data.dict()
        
        # Use the form extraction service
        result = await form_extraction_service.process_form_extraction(data_dict)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during extract_form: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/GetFormExtractInformation")
async def get_form_extract_information(data: GetFormInfoData):
    """
    Receive an image title via JSON and fetch corresponding metadata
    from Firestore using the `get_image` helper function.

    Args:
        data (GetFormInfoData): Object containing the image title

    Returns:
        JSON response containing image metadata or 404 if not found.
    """
    name = data.title or data.ImageName
    if not name:
        raise HTTPException(status_code=422, detail="Missing 'title' or 'ImageName'")
    logger.info(
        f"Received request to get form extract information for title: {name}"
    )

    try:
        # Call helper to fetch image data from Firestore
        result = get_image(
            image_name=name, collection_name=config.COLLECTION_NAME_FORM_EXTRACT
        )
        logger.info(f"Firestore query result for {name}: {result is not None}")

        if not result:
            logger.warning(f"No form extract data found for title: {name}")
            raise HTTPException(status_code=404, detail="Image not found")

        logger.info(f"Returning form extract data for {name}")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting form extract information for {name}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.post("/queue/upload-image")
async def queue_upload_image(
    status: str = Form(...), folderPath: str = Form(""), file: UploadFile = File(...)
):
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in [".jpg", ".jpeg", ".png", ".bmp", ".webp"]:
        raise HTTPException(status_code=400, detail="Unsupported image format.")
    os.makedirs(config.UPLOAD_FOLDER, exist_ok=True)
    temp_name = f"enqueue_{uuid.uuid4().hex}{ext}"
    temp_path = os.path.join(config.UPLOAD_FOLDER, temp_name)
    with open(temp_path, "wb") as f:
        f.write(await file.read())
    task = upload_image_task.apply_async(args=[temp_path, file.filename, status, folderPath])
    return {"task_id": task.id, "status": "queued"}


@app.post("/queue/extract-form")
async def queue_extract_form(data: ExtractFormData):
    existing = get_image(data.ImageName, collection_name_image_detail)
    if not existing:
        raise HTTPException(status_code=404, detail="Image not found. Upload first.")
    # Prevent duplicate enqueue if already processing
    if existing.get("Status") == "Processing":
        return {"status": "already_processing"}
    # Mark status as Processing immediately so FE reload sees it
    try:
        processing_meta = ImageData(
            Status="Processing",
            ImageName=data.ImageName,
            ImagePath=data.ImagePath or existing.get("ImagePath", ""),
            CreatedAt=data.CreatedAt or existing.get("CreatedAt", ""),
            FolderPath=data.FolderPath or existing.get("FolderPath", ""),
            Size=data.Size or existing.get("Size", 0.0),
        )
        upsert_image(processing_meta, collection_name_image_detail, data.ImageName)
    except Exception as e:  # non-fatal
        logger.warning(f"Failed to pre-mark Processing for {data.ImageName}: {e}")
    task = extract_form_task.apply_async(args=[
        data.ImageName,
        data.ImagePath,
        data.Size,
        data.Status,
        data.CreatedAt,
        data.FolderPath,
    ])
    return {"task_id": task.id, "status": "queued"}


@app.get("/tasks/{task_id}")
async def get_task_status(task_id: str):
    result: AsyncResult = celery_app.AsyncResult(task_id)
    resp = {"task_id": task_id, "state": result.state}
    if result.state == "SUCCESS":
        resp["result"] = result.result
    elif result.state == "FAILURE":
        resp["error"] = str(result.result)
    elif result.info and isinstance(result.info, dict):
        resp["meta"] = result.info
    return resp




# ✅ This will run FastAPI when executing this file directly
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
