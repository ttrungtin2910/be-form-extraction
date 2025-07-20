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

from database.firestore import ImageData, upsert_image, get_image, delete_image, list_images
from database.ggc_storage import upload_image_to_gcs
from utils.file_processing import download_image_from_url, extract_filename_from_url

import logging

# Configure logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Firestore Image Metadata API")

class ExtractFormData(BaseModel):
    title: str
    size: str
    image: str  # URL or base64 string, tùy frontend
    status: str
    createAt: str

class GetFormInfoData(BaseModel):
    title: str


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# GCS config
BUCKET_NAME = "display-form-extract"
UPLOAD_FOLDER = "temp_uploads"

# Firestore collection name
collection_name_image_detail  = "imagedetail"
collection_name_form_extract = "forminformation"

config = Configuration()
bot = TicketChatBot(config)

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.post("/upload-image/")
async def upload_image(
    status: str = Form(...),
    file: UploadFile = File(...)
):
    logger.info("Received request to upload image")
    logger.info(f"Status: {status}")
    logger.info(f"File: {file.filename}, size: {file.size}, content_type: {file.content_type}")
    
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in [".jpg", ".jpeg", ".png", ".bmp", ".webp"]:
        logger.warning(f"Unsupported image format: {ext}")
        raise HTTPException(status_code=400, detail="Unsupported image format.")

    now = datetime.utcnow()
    str_now = now.strftime('%Y%m%d_%H%M%S_%f')
    image_name = f"{str_now}{ext}"
    local_path = os.path.join(UPLOAD_FOLDER, image_name)

    with open(local_path, "wb") as f:
        f.write(await file.read())
    logger.info(f"Saved image locally at {local_path}")

    try:
        upload_image_to_gcs(
            bucket_name=BUCKET_NAME,
            source_file_path=local_path,
            destination_blob_name=image_name
        )
        logger.info(f"Uploaded image to GCS as {image_name}")
    except Exception as e:
        logger.error(f"GCS upload failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"GCS upload failed: {str(e)}")

    image_data = ImageData(
        Status=status,
        ImageName=image_name,
        ImagePath=f"https://storage.googleapis.com/{BUCKET_NAME}/{image_name}",
        CreatedAt=str_now
    )

    try:
        upsert_image(image_data, collection_name_image_detail, image_data.ImageName)
        logger.info(f"Saved image metadata to Firestore: {image_name}")
    except Exception as e:
        logger.error(f"Firestore save failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Firestore save failed: {str(e)}")

    return JSONResponse(content={"message": "Image uploaded and saved successfully."})

@app.post("/images/", response_model=dict)
async def create_or_update_image(data: ImageData):
    """
    Create or update an image record in Firestore.
    """
    upsert_image(data, collection_name_image_detail, data.ImageName)
    return {"message": "Image data saved successfully."}

@app.get("/images/{image_name}", response_model=ImageData)
async def read_image(image_name: str):
    """
    Retrieve an image record by image name.
    """
    image = get_image(image_name, collection_name_image_detail)
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")
    return image

@app.delete("/images/{image_name}", response_model=dict)
async def remove_image(image_name: str):
    """
    Delete an image record from Firestore.
    """
    delete_image(image_name, collection_name_image_detail)
    return {"message": f"Image '{image_name}' deleted successfully."}

@app.get("/images/")
async def get_all_images():
    """
    Retrieve all image records from Firestore.
    """
    data = list_images(collection_name_image_detail)
    return data

@app.post("/ExtractForm")
async def extract_form(data: ExtractFormData):
    logger.info("Received request to analyze image from frontend")

    try:
        filename = extract_filename_from_url(data.image)
        local_path = os.path.join(UPLOAD_FOLDER, filename)
        logger.info(f"Downloading image from {data.image} to {local_path}")

        await download_image_from_url(data.image, local_path)
        logger.info(f"Download successful: {filename}")

        result = await bot.analyze_ticket(local_path, "")
        logger.info(f"Analysis completed for {filename}")

        # Ensure result is a dictionary
        if not isinstance(result, dict):
            logger.error(f"Analysis result is not a dictionary: {type(result)}")
            result = {"error": "Invalid analysis result", "raw_result": str(result)}

        # Convert result dict to proper format for form extraction
        # Only include ImageData fields for the form extraction collection
        form_data = {
            "Status": "Completed",
            "ImageName": filename,
            "ImagePath": data.image,
            "CreatedAt": data.createAt,
            "analysis_result": result  # Store the full analysis result separately
        }
        upsert_image(form_data, collection_name_form_extract, filename)
        logger.info(f"Saved form extract metadata to Firestore: {collection_name_form_extract}")

        # Update image status to Completed in imagedetail collection
        image_data = ImageData(
            Status="Completed",
            ImageName=filename,
            ImagePath=data.image,
            CreatedAt=data.createAt
        )
        upsert_image(image_data, collection_name_image_detail, filename)
        logger.info(f"Updated image status to Completed in Firestore: {filename}")

        os.remove(local_path)
        logger.info(f"Cleaned up local file: {local_path}")

        return {
            "message": "Image processed successfully",
            "analysis_result": result,
            "received": data.dict()
        }

    except Exception as e:
        logger.error(f"Error during extract_form: {str(e)}")
        return {"error": str(e)}
    
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
    logger.info(f"Received request to get form extract information for title: {data.title}")
    
    try:
        # Call helper to fetch image data from Firestore
        result = get_image(image_name=data.title, collection_name=collection_name_form_extract)
        logger.info(f"Firestore query result for {data.title}: {result is not None}")

        # If no document found, raise 404
        if not result:
            logger.warning(f"No form extract data found for title: {data.title}")
            raise HTTPException(status_code=404, detail="Image not found")

        # Return Firestore document as JSON
        logger.info(f"Returning form extract data for {data.title}")
        print(result)
        return result
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error getting form extract information for {data.title}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# ✅ This will run FastAPI when executing this file directly
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)