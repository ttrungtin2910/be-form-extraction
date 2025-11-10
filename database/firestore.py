import os
from datetime import datetime
from typing import Optional, List, Tuple, Iterable

from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter
from google.api_core.exceptions import FailedPrecondition, InvalidArgument
from pydantic import BaseModel
from properties.config import Configuration

# Initialize Firestore client
# Credentials should be set via GOOGLE_APPLICATION_CREDENTIALS environment variable
# If FIRESTORE_DATABASE is not set, Firestore will use the default database
if Configuration.FIRESTORE_DATABASE:
    db = firestore.Client(database=Configuration.FIRESTORE_DATABASE)
else:
    # Use default database (no database parameter)
    db = firestore.Client()


ALLOWED_SORT_FIELDS = {"CreatedAt", "ImageName", "Status", "Size"}
DEFAULT_SORT_FIELD = "CreatedAt"


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
    UploadBy: str = ""  # Username who uploaded the image


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

    doc_ref.set(_prepare_image_payload(data_dict))


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


def _normalize_image_dict(data: Optional[dict]) -> dict:
    """Ensure image data contains required fields and normalized types."""
    if not data:
        return {
            "FolderPath": "",
            "Status": "",
            "Size": 0.0,
            "CreatedAt": "",
            "ImageName": "",
        }

    folder_path = data.get("FolderPath")
    data["FolderPath"] = folder_path if folder_path not in (None, "None") else ""

    try:
        data["Size"] = float(data.get("Size", 0.0) or 0.0)
    except (TypeError, ValueError):
        data["Size"] = 0.0

    data["Status"] = data.get("Status") or ""
    data["ImageName"] = data.get("ImageName") or ""
    data["CreatedAt"] = data.get("CreatedAt") or ""
    return data


def _prepare_image_payload(data_dict: dict) -> dict:
    """Prepare payload before saving to Firestore."""
    normalized = _normalize_image_dict(dict(data_dict))
    return normalized


def list_images(
    collection_name: str,
    folder_path: Optional[str] = None,
    page: int = 1,
    limit: int = 20,
    sort_field: str = DEFAULT_SORT_FIELD,
    sort_order: str = "desc",
) -> Tuple[List[dict], int]:
    """
    Retrieve image documents from the Firestore collection with optional filtering and pagination.

    Args:
        collection_name: Name of the Firestore collection
        folder_path: Optional folder path to filter by. Use empty string "" or None for root images.
        page: Page number (1-indexed)
        limit: Number of items per page

    Returns:
        tuple[List[dict], int]: A tuple of (list of image metadata, total count)
    """
    if page < 1:
        page = 1

    # Enforce sane limits
    try:
        max_limit = Configuration.IMAGE_LIST_MAX_LIMIT
    except AttributeError:
        max_limit = 100
    limit = max(1, min(limit, max_limit))

    sort_field = sort_field if sort_field in ALLOWED_SORT_FIELDS else DEFAULT_SORT_FIELD
    sort_direction = (
        firestore.Query.DESCENDING if sort_order.lower() != "asc" else firestore.Query.ASCENDING
    )

    base_query = db.collection(collection_name)

    if folder_path is not None and folder_path != "__all__":
        normalized_folder = folder_path
        base_query = base_query.where(filter=FieldFilter("FolderPath", "==", normalized_folder))

    ordered_query = base_query.order_by(sort_field, direction=sort_direction)

    try:
        count_snapshot = ordered_query.count().get()
        total = 0
        if count_snapshot:
            aggregation_result = count_snapshot[0]
            total_value = getattr(aggregation_result, "value", None)
            if total_value is None:
                try:
                    total_value = aggregation_result[0]
                except (TypeError, IndexError):
                    total_value = 0
            total = int(total_value or 0)

        offset = (page - 1) * limit
        docs_iter = ordered_query.offset(offset).limit(limit).stream()
        data: List[dict] = [_normalize_image_dict(doc.to_dict()) for doc in docs_iter]
        return data, total

    except (FailedPrecondition, InvalidArgument):
        raw_docs = []
        fallback_query = base_query.select(
            ["Status", "ImageName", "ImagePath", "CreatedAt", "FolderPath", "Size"]
        )
        for doc in fallback_query.stream():
            raw_docs.append(_normalize_image_dict(doc.to_dict()))

        total = len(raw_docs)
        reverse = sort_order.lower() != "asc"

        def _sort_key(item: dict):
            value = item.get(sort_field)
            if sort_field == "CreatedAt":
                return value or ""
            if sort_field in {"Size"}:
                try:
                    return float(value or 0.0)
                except (TypeError, ValueError):
                    return 0.0
            return (value or "").lower() if isinstance(value, str) else value

        sorted_docs = sorted(raw_docs, key=_sort_key, reverse=reverse)
        offset = (page - 1) * limit
        paginated_docs = sorted_docs[offset : offset + limit]
        return paginated_docs, total

    except Exception:
        total = sum(1 for _ in base_query.select(["ImageName"]).stream())
        offset = (page - 1) * limit
        docs_iter = ordered_query.offset(offset).limit(limit).stream()
        data: List[dict] = [_normalize_image_dict(doc.to_dict()) for doc in docs_iter]
        return data, total


def stream_images(
    collection_name: str, select_fields: Optional[List[str]] = None
) -> Iterable[dict]:
    """Stream all images from collection with optional field projection."""
    query = db.collection(collection_name)
    if select_fields:
        query = query.select(select_fields)

    for doc in query.stream():
        yield _normalize_image_dict(doc.to_dict())


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


def list_folders(parent_path: Optional[str] = None) -> List[dict]:
    """
    Return list of folders, optionally filtered by parent path.
    
    Args:
        parent_path: If provided, only return direct children of this folder.
                    If None, return all folders.
                    If "", return only root-level folders.
    
    Returns:
        List of folder dicts with FolderPath and metadata
    """
    query = db.collection(FOLDER_COLLECTION)
    
    if parent_path is not None:
        if parent_path == "":
            # Root level folders - no "/" in path
            docs = query.stream()
            folders = []
            for doc in docs:
                folder_data = doc.to_dict()
                folder_path = folder_data.get("FolderPath", "")
                # Only include folders with no "/" (root level)
                if folder_path and "/" not in folder_path:
                    folders.append(folder_data)
            return folders
        else:
            # Direct children of parent_path
            # Example: parent="folder1" -> return "folder1/sub1", "folder1/sub2"
            # but not "folder1/sub1/subsub1"
            docs = query.stream()
            folders = []
            prefix = parent_path + "/"
            for doc in docs:
                folder_data = doc.to_dict()
                folder_path = folder_data.get("FolderPath", "")
                if folder_path.startswith(prefix):
                    # Check if it's a direct child (no additional "/" after prefix)
                    remainder = folder_path[len(prefix):]
                    if remainder and "/" not in remainder:
                        folders.append(folder_data)
            return folders
    
    # Return all folders
    docs = query.stream()
    return [doc.to_dict() for doc in docs]


def count_images_in_folder(collection_name: str, folder_path: str) -> int:
    """
    Count number of images in a specific folder.
    
    Args:
        collection_name: Firestore collection name
        folder_path: Folder path to count images in
    
    Returns:
        Number of images in the folder
    """
    query = db.collection(collection_name)
    
    if folder_path == "":
        # Count root images
        all_docs = list(query.select(["FolderPath"]).stream())
        count = sum(
            1 for doc in all_docs
            if not doc.to_dict().get("FolderPath") or doc.to_dict().get("FolderPath") == ""
        )
        return count
    else:
        # Count images in specific folder
        query = query.where(filter=FieldFilter("FolderPath", "==", folder_path))
        return sum(1 for _ in query.select(["ImageName"]).stream())


def delete_folder(path: str):
    """Delete folder document and all image docs within that folder."""
    # Delete folder doc
    db.collection(FOLDER_COLLECTION).document(_encode_path(path)).delete()

    # Delete subfolder docs
    subfolder_docs = (
        db.collection(FOLDER_COLLECTION)
        .where(filter=FieldFilter("FolderPath", ">=", path + "/"))
        .where(filter=FieldFilter("FolderPath", "<=", path + "/\uf8ff"))
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
            .where(filter=FieldFilter("FolderPath", ">=", path))
            .where(filter=FieldFilter("FolderPath", "<=", path + "\uf8ff"))
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
