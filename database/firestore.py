import os
from datetime import datetime
from typing import Optional, List

from google.cloud import firestore
from pydantic import BaseModel

# Set path to Google Cloud service account key
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "database/crafty-isotope-456021-k2-a99ca9ffcde0.json"

# Initialize Firestore client
db = firestore.Client(database="imageinformation")



class ImageData(BaseModel):
    """
    Pydantic model representing image metadata stored in Firestore.
    """
    Status: str
    ImageName: str
    ImagePath: str
    CreatedAt: str


def upsert_image(data, collection_name: str, key_upload: str):
    """
    Create or update an image document in Firestore.

    Args:
        data: Image metadata to be stored (can be ImageData object or dict).
    """
    doc_ref = db.collection(collection_name).document(key_upload)
    
    # Convert ImageData to dict if needed
    if hasattr(data, 'dict'):
        data_dict = data.dict()
    elif isinstance(data, dict):
        data_dict = data
    elif hasattr(data, '__dict__'):
        data_dict = data.__dict__
    else:
        # Fallback: convert to string representation
        data_dict = {"data": str(data)}
    
    print(f"[Firestore] Upserting data type: {type(data)}")
    print(f"[Firestore] Converted dict: {data_dict}")
    
    doc_ref.set(data_dict)


def get_image(image_name: str, collection_name: str) -> Optional[dict]:
    """
    Retrieve an image document by its name.

    Args:
        image_name (str): The ID (ImageName) of the document.

    Returns:
        dict | None: Document data if exists, else None.
    """
    doc = db.collection(collection_name).document(image_name).get()
    if doc.exists:
        return doc.to_dict()
    return None


def delete_image(image_name: str, collection_name: str):
    """
    Delete an image document from Firestore.

    Args:
        image_name (str): The ID (ImageName) of the document.
    """
    db.collection(collection_name).document(image_name).delete()


def list_images(collection_name: str) -> List[dict]:
    """
    Retrieve all image documents from the Firestore collection.

    Returns:
        List[dict]: A list of image metadata dictionaries.
    """
    docs = db.collection(collection_name).stream()
    return [doc.to_dict() for doc in docs]