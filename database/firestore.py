import os
from datetime import datetime
from typing import Optional, List

from google.cloud import firestore
from pydantic import BaseModel

# Set path to Google Cloud service account key
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = (
    "database/crafty-isotope-456021-k2-a99ca9ffcde0.json"
)

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
    FolderPath: str = ""
    Size: float = 0.0


def upsert_image(data, collection_name: str, key_upload: str):
    """
    Create or update an image document in Firestore.

    Args:
        data: Image metadata to be stored (can be ImageData object or dict).
    """
    doc_ref = db.collection(collection_name).document(key_upload)

    # Convert ImageData to dict if needed
    if hasattr(data, "dict"):
        data_dict = data.dict()
    elif isinstance(data, dict):
        data_dict = data
    elif hasattr(data, "__dict__"):
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


# Model and helpers for folder documents


class FolderData(BaseModel):
    """Represents a folder path in Firestore"""

    FolderPath: str
    CreatedAt: str


FOLDER_COLLECTION = "imagefolders"


def _encode_path(path: str) -> str:
    """Encode folder path to a Firestore-safe document id (replace '/' with '__')."""
    return path.replace("/", "__") if path else "root"


def upsert_folder(path: str):
    """Create folder document if not exists"""
    now = datetime.utcnow().isoformat()
    doc_ref = db.collection(FOLDER_COLLECTION).document(_encode_path(path))
    doc_ref.set({"FolderPath": path, "CreatedAt": now}, merge=True)


def list_folders() -> List[str]:
    """Return list of folder paths from folder collection"""
    docs = db.collection(FOLDER_COLLECTION).stream()
    return [doc.to_dict().get("FolderPath", "") for doc in docs]


def delete_folder(path: str):
    """Delete folder document and all image docs within that folder."""
    # Delete folder doc
    db.collection(FOLDER_COLLECTION).document(_encode_path(path)).delete()

    # Delete subfolder docs
    subfolder_docs = (
        db.collection(FOLDER_COLLECTION)
        .where("FolderPath", ">=", path + "/")
        .where("FolderPath", "<=", path + "/\uf8ff")
        .stream()
    )
    batch_sub = db.batch()
    for doc in subfolder_docs:
        batch_sub.delete(doc.reference)
    batch_sub.commit()

    # Collections to purge (images)
    collections_to_clean = ["imagedetail", "forminformation"]

    for col in collections_to_clean:
        imgs = (
            db.collection(col)
            .where("FolderPath", ">=", path)
            .where("FolderPath", "<=", path + "\uf8ff")
            .stream()
        )
        batch = db.batch()
        count = 0
        for img_doc in imgs:
            batch.delete(db.collection(col).document(img_doc.id))
            count += 1
            # Commit in batches of 450 to avoid limits
            if count >= 450:
                batch.commit()
                batch = db.batch()
                count = 0
        if count > 0:
            batch.commit()


def rename_folder(old_path: str, new_path: str):
    """Rename folder: update folder doc and all images whose FolderPath starts with old_path."""
    batch = db.batch()

    # Move folder doc
    old_doc_ref = db.collection(FOLDER_COLLECTION).document(_encode_path(old_path))
    new_doc_ref = db.collection(FOLDER_COLLECTION).document(_encode_path(new_path))
    old_doc = old_doc_ref.get()
    if old_doc.exists:
        batch.set(
            new_doc_ref,
            {
                "FolderPath": new_path,
                "CreatedAt": old_doc.to_dict().get("CreatedAt", ""),
            },
        )
        batch.delete(old_doc_ref)

    # Update image docs
    imgs = db.collection("imagedetail").where("FolderPath", "==", old_path).stream()
    for img_doc in imgs:
        doc_ref = db.collection("imagedetail").document(img_doc.id)
        batch.update(doc_ref, {"FolderPath": new_path})

    batch.commit()
