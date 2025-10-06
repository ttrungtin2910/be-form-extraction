import uvicorn
import os
import uuid
from datetime import datetime
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from fastapi import (
    FastAPI,
    UploadFile,
    File,
    HTTPException,
    Form,
    Depends,
    Request,
    status,
)
from fastapi.responses import JSONResponse

# from middleware.auth import verify_api_key  # No longer needed - using user authentication
from middleware.rate_limiter import (
    limiter,
    RATE_LIMIT_UPLOAD,
    RATE_LIMIT_AI,
    RATE_LIMIT_GENERAL,
    RATE_LIMIT_STATUS,
)
from middleware.error_handler import (
    http_exception_handler,
    validation_exception_handler,
    generic_exception_handler,
    rate_limit_handler,
)
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from fastapi.exceptions import RequestValidationError
from chain.completions import TicketChatBot
from properties.config import Configuration
from utils.file_validation import validate_upload_file, FileValidationError
from utils.path_sanitizer import sanitize_folder_path
from services.form_extraction_service import FormExtractionService
from services.auth_service import (
    authenticate_user,
    create_access_token,
    update_last_login,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)
from models.user import UserLogin, Token, User
from models.activity_log import ActivityLogResponse
from middleware.user_auth import get_current_active_user, get_current_admin_user
from middleware.activity_logger import ActivityLoggingMiddleware
from datetime import timedelta
from typing import Optional

from database.firestore import (
    db,
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

# Add rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_handler)
app.add_middleware(SlowAPIMiddleware)

# Add activity logging middleware
app.add_middleware(ActivityLoggingMiddleware)

# Add global exception handlers for standardized error responses
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

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


class FolderCreateData(BaseModel):
    """Request model for creating a folder."""

    folderPath: str


class FolderRenameData(BaseModel):
    """Request model for renaming a folder."""

    oldPath: str
    newPath: str


# Configure CORS with restricted origins and headers
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "PUT"],
    allow_headers=["Content-Type", "Authorization", "Accept", "Origin"],
)

# Create upload directory
os.makedirs(config.UPLOAD_FOLDER, exist_ok=True)


# ============================================
# Authentication Endpoints
# ============================================


@app.post("/auth/login", response_model=Token)
@limiter.limit(RATE_LIMIT_GENERAL)
async def login(request: Request, user_login: UserLogin):
    """
    User login endpoint

    Returns JWT access token on successful authentication
    """
    logger.info(f"Login attempt for user: {user_login.username}")

    user = authenticate_user(user_login.username, user_login.password)
    if not user:
        logger.warning(f"Failed login attempt for user: {user_login.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Update last login time
    update_last_login(user.username)

    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )

    logger.info(f"User {user.username} logged in successfully")

    return Token(
        access_token=access_token,
        token_type="bearer",
        username=user.username,
        full_name=user.full_name,
        role=user.role,
    )


@app.get("/auth/me", response_model=User)
async def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    """
    Get current user information

    Requires valid JWT token
    """
    return current_user


@app.post("/auth/logout")
async def logout(current_user: User = Depends(get_current_active_user)):
    """
    Logout endpoint (client should discard token)
    """
    logger.info(f"User {current_user.username} logged out")
    return {"success": True, "message": "Logged out successfully"}


# ============================================
# Image Management Endpoints
# ============================================


@app.post("/upload-image/")
@limiter.limit(RATE_LIMIT_UPLOAD)
async def upload_image(
    request: Request,
    status: str = Form(...),
    folderPath: str = Form(""),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
):
    logger.info("Received request to upload image")
    logger.info(f"Status: {status}")
    logger.info(
        f"File: {file.filename}, size: {file.size}, content_type: {file.content_type}"
    )

    # Sanitize folder path to prevent path traversal
    safe_folder_path = sanitize_folder_path(folderPath) if folderPath else ""

    # Validate file extension
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in config.ALLOWED_EXTENSIONS:
        logger.warning(f"Unsupported image format: {ext}")
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported image format. Allowed: {list(config.ALLOWED_EXTENSIONS)}",
        )

    # Check file size
    if file.size and file.size > config.MAX_FILE_SIZE:
        logger.warning(f"File size {file.size} exceeds maximum {config.MAX_FILE_SIZE}")
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size: {config.MAX_FILE_SIZE} bytes",
        )

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
            local_path, config.MAX_FILE_SIZE, config.ALLOWED_EXTENSIONS
        )
        logger.info(f"File validation successful for {image_name}")

        destination_blob_name = (
            f"{safe_folder_path}/{image_name}" if safe_folder_path else image_name
        )

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
            FolderPath=safe_folder_path,
            Size=size_val,
        )

        # Save metadata to Firestore
        upsert_image(
            image_data, config.COLLECTION_NAME_IMAGE_DETAIL, image_data.ImageName
        )
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
async def create_or_update_image(
    data: ImageData, current_user: User = Depends(get_current_active_user)
):
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
async def remove_image(
    image_name: str, current_user: User = Depends(get_current_active_user)
):
    """
    Delete an image record from Firestore.
    """
    delete_image(image_name, config.COLLECTION_NAME_IMAGE_DETAIL)
    return {"message": f"Image '{image_name}' deleted successfully."}


@app.get("/images/")
async def get_all_images(folderPath: str = "", page: int = 1, limit: int = 20):
    """
    Retrieve image records. If folderPath provided, filter by that path.
    """
    # Sanitize folder path if provided
    safe_folder_path = sanitize_folder_path(folderPath) if folderPath else None

    # Use optimized Firestore query with filtering and pagination at database level
    data, total = list_images(
        config.COLLECTION_NAME_IMAGE_DETAIL,
        folder_path=safe_folder_path,
        page=page,
        limit=limit,
    )

    return {"data": data, "total": total}


# Folder endpoints


# Get folders
@app.get("/folders/")
async def list_folders():
    folders = firestore_list_folders()
    return {"folders": folders}


# Create folder
@app.post("/folders/")
async def create_folder(
    payload: FolderCreateData, current_user: User = Depends(get_current_active_user)
):
    folder_path = payload.folderPath.strip()
    if not folder_path:
        raise HTTPException(status_code=400, detail="folderPath is required")

    # Sanitize folder path
    safe_folder_path = sanitize_folder_path(folder_path)
    upsert_folder(safe_folder_path)
    return {
        "message": "Folder created or already exists",
        "folderPath": safe_folder_path,
    }


# Delete folder
@app.delete("/folders/{folder_path:path}")
async def delete_folder(
    folder_path: str, current_user: User = Depends(get_current_active_user)
):
    # Sanitize folder path
    safe_folder_path = sanitize_folder_path(folder_path)

    # ensure folder exists
    firestore_delete_folder(safe_folder_path)
    delete_blobs_with_prefix(config.BUCKET_NAME, f"{safe_folder_path}/")
    return {"message": "Folder deleted", "folderPath": safe_folder_path}


# Rename folder
@app.post("/folders/rename")
async def rename_folder(
    payload: FolderRenameData, current_user: User = Depends(get_current_active_user)
):
    old_path = payload.oldPath.strip()
    new_path = payload.newPath.strip()
    if not old_path or not new_path:
        raise HTTPException(status_code=400, detail="oldPath and newPath required")

    # Sanitize both paths
    safe_old_path = sanitize_folder_path(old_path)
    safe_new_path = sanitize_folder_path(new_path)

    firestore_rename_folder(safe_old_path, safe_new_path)
    gcs_rename_folder(config.BUCKET_NAME, f"{safe_old_path}/", f"{safe_new_path}/")
    return {
        "message": "Folder renamed",
        "oldPath": safe_old_path,
        "newPath": safe_new_path,
    }


@app.post("/ExtractForm")
@limiter.limit(RATE_LIMIT_AI)
async def extract_form(
    request: Request,
    data: ExtractFormData,
    current_user: User = Depends(get_current_active_user),
):
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
    logger.info(f"Received request to get form extract information for title: {name}")

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
@limiter.limit(RATE_LIMIT_UPLOAD)
async def queue_upload_image(
    request: Request,
    status: str = Form(...),
    folderPath: str = Form(""),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
):
    # Sanitize folder path
    safe_folder_path = sanitize_folder_path(folderPath) if folderPath else ""

    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in [".jpg", ".jpeg", ".png", ".bmp", ".webp"]:
        raise HTTPException(status_code=400, detail="Unsupported image format.")
    os.makedirs(config.UPLOAD_FOLDER, exist_ok=True)
    temp_name = f"enqueue_{uuid.uuid4().hex}{ext}"
    temp_path = os.path.join(config.UPLOAD_FOLDER, temp_name)
    with open(temp_path, "wb") as f:
        f.write(await file.read())
    task = upload_image_task.apply_async(
        args=[temp_path, file.filename, status, safe_folder_path]
    )
    return {"task_id": task.id, "status": "queued"}


@app.post("/queue/extract-form")
@limiter.limit(RATE_LIMIT_AI)
async def queue_extract_form(
    request: Request,
    data: ExtractFormData,
    current_user: User = Depends(get_current_active_user),
):
    existing = get_image(data.ImageName, config.COLLECTION_NAME_IMAGE_DETAIL)
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
        upsert_image(
            processing_meta, config.COLLECTION_NAME_IMAGE_DETAIL, data.ImageName
        )
    except Exception as e:  # non-fatal
        logger.warning(f"Failed to pre-mark Processing for {data.ImageName}: {e}")
    task = extract_form_task.apply_async(
        args=[
            data.ImageName,
            data.ImagePath,
            data.Size,
            data.Status,
            data.CreatedAt,
            data.FolderPath,
        ]
    )
    return {"task_id": task.id, "status": "queued"}


@app.get("/tasks/{task_id}")
@limiter.limit(RATE_LIMIT_STATUS)
async def get_task_status(request: Request, task_id: str):
    result: AsyncResult = celery_app.AsyncResult(task_id)
    resp = {"task_id": task_id, "state": result.state}
    if result.state == "SUCCESS":
        resp["result"] = result.result
    elif result.state == "FAILURE":
        resp["error"] = str(result.result)
    elif result.info and isinstance(result.info, dict):
        resp["meta"] = result.info
    return resp


@app.get("/health")
async def health_check():
    """Basic health check endpoint."""
    return {"success": True, "status": "healthy", "service": "form-extraction-api"}


@app.get("/health/ready")
async def readiness_check():
    """
    Readiness check endpoint - verifies all dependencies are accessible.
    Checks: Firestore, Redis, GCS connectivity.
    """
    health_status = {"success": True, "status": "ready", "checks": {}}

    # Check Firestore
    try:
        # Simple query to test Firestore connectivity
        db.collection(config.COLLECTION_NAME_IMAGE_DETAIL).limit(1).get()
        health_status["checks"]["firestore"] = "healthy"
    except Exception as e:
        health_status["checks"]["firestore"] = f"unhealthy: {str(e)}"
        health_status["success"] = False
        health_status["status"] = "not_ready"

    # Check Redis (Celery broker)
    try:
        import redis

        r = redis.from_url(config.REDIS_URL)
        r.ping()
        health_status["checks"]["redis"] = "healthy"
    except Exception as e:
        health_status["checks"]["redis"] = f"unhealthy: {str(e)}"
        health_status["success"] = False
        health_status["status"] = "not_ready"

    # Check GCS (try to get bucket)
    try:
        from google.cloud import storage

        storage_client = storage.Client()
        bucket = storage_client.bucket(config.BUCKET_NAME)
        bucket.exists()
        health_status["checks"]["gcs"] = "healthy"
    except Exception as e:
        health_status["checks"]["gcs"] = f"unhealthy: {str(e)}"
        health_status["success"] = False
        health_status["status"] = "not_ready"

    status_code = 200 if health_status["success"] else 503
    return JSONResponse(content=health_status, status_code=status_code)


# ==================== DEBUG ENDPOINTS ====================


@app.get("/debug/token")
@limiter.limit(RATE_LIMIT_GENERAL)
async def debug_token(
    request: Request, current_user: User = Depends(get_current_active_user)
):
    """Debug endpoint to check token and user info"""
    return {
        "user_id": current_user.user_id,
        "username": current_user.username,
        "role": current_user.role,
        "headers": dict(request.headers),
        "auth_header": request.headers.get("Authorization"),
    }


# ==================== ACTIVITY LOGGING ENDPOINTS ====================


@app.get("/activity-logs", response_model=ActivityLogResponse)
@limiter.limit(RATE_LIMIT_GENERAL)
async def get_activity_logs(
    request: Request,
    user_id: Optional[str] = None,
    username: Optional[str] = None,
    activity_type: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    page: int = 1,
    limit: int = 50,
    current_user: User = Depends(get_current_admin_user),
):
    """Get activity logs with filtering and pagination (Admin only)"""
    try:
        from models.activity_log import ActivityLogFilter, ActivityType
        from services.datastore_activity_service import datastore_activity_service

        # Convert activity_type string to enum if provided
        activity_type_enum = None
        if activity_type:
            try:
                activity_type_enum = ActivityType(activity_type)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid activity_type: {activity_type}",
                )

        # Create filter
        filters = ActivityLogFilter(
            user_id=user_id,
            username=username,
            activity_type=activity_type_enum,
            start_date=start_date,
            end_date=end_date,
            page=page,
            limit=min(limit, 1000),  # Cap at 1000
        )

        # Get logs
        result = await datastore_activity_service.get_logs(filters)

        return result

    except Exception as e:
        logger.error(f"Failed to get activity logs: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve activity logs",
        )


@app.get("/activity-logs/my-activity")
@limiter.limit(RATE_LIMIT_GENERAL)
async def get_my_activity_logs(
    request: Request,
    page: int = 1,
    limit: int = 50,
    current_user: User = Depends(get_current_active_user),
):
    """Get current user's activity logs"""
    try:
        from models.activity_log import ActivityLogFilter
        from services.datastore_activity_service import datastore_activity_service

        # Create filter for current user only
        filters = ActivityLogFilter(
            user_id=current_user.user_id,
            page=page,
            limit=min(limit, 100),  # Cap at 100 for user's own logs
        )

        # Get logs
        result = await datastore_activity_service.get_logs(filters)

        return result

    except Exception as e:
        logger.error(f"Failed to get user activity logs: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve your activity logs",
        )


@app.get("/activity-logs/summary")
@limiter.limit(RATE_LIMIT_GENERAL)
async def get_activity_summary(
    request: Request,
    user_id: Optional[str] = None,
    days: int = 7,
    current_user: User = Depends(get_current_active_user),
):
    """Get activity summary for a user (Admin can view any user, users can only view themselves)"""
    try:
        from services.datastore_activity_service import datastore_activity_service

        # Determine which user to get summary for
        target_user_id = (
            user_id if current_user.role == "admin" else current_user.user_id
        )

        # Validate days parameter
        if days < 1 or days > 365:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Days must be between 1 and 365",
            )

        # Get summary
        summary = await datastore_activity_service.get_user_activity_summary(
            target_user_id, days
        )

        return summary

    except Exception as e:
        logger.error(f"Failed to get activity summary: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve activity summary",
        )


@app.post("/activity-logs/cleanup")
@limiter.limit(RATE_LIMIT_GENERAL)
async def cleanup_old_activity_logs(
    request: Request,
    days_to_keep: int = 90,
    current_user: User = Depends(get_current_admin_user),
):
    """Clean up old activity logs (Admin only)"""
    try:
        from services.datastore_activity_service import datastore_activity_service

        # Validate days parameter
        if days_to_keep < 30:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Days to keep must be at least 30",
            )

        # Cleanup logs
        deleted_count = await datastore_activity_service.cleanup_old_logs(days_to_keep)

        return {
            "success": True,
            "message": f"Cleaned up {deleted_count} old activity logs",
            "deleted_count": deleted_count,
            "days_kept": days_to_keep,
        }

    except Exception as e:
        logger.error(f"Failed to cleanup activity logs: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cleanup activity logs",
        )


# ✅ This will run FastAPI when executing this file directly
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
