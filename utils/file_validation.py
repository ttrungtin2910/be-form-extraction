"""
File validation utilities for secure file upload handling.
"""

import os
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# Try to import magic, fallback to basic validation if not available
try:
    import magic

    MAGIC_AVAILABLE = True
except ImportError:
    MAGIC_AVAILABLE = False
    logger.warning("python-magic not available, using basic file validation only")


class FileValidationError(Exception):
    """Custom exception for file validation errors."""

    pass


def validate_image_file(file_path: str, allowed_extensions: set = None) -> bool:
    """
    Validate image file using both extension and MIME type checking.

    Args:
        file_path: Path to the file to validate
        allowed_extensions: Set of allowed file extensions

    Returns:
        bool: True if file is valid, False otherwise

    Raises:
        FileValidationError: If validation fails
    """
    if allowed_extensions is None:
        allowed_extensions = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

    try:
        # Check if file exists
        if not os.path.exists(file_path):
            raise FileValidationError("File does not exist")

        # Check file extension
        _, ext = os.path.splitext(file_path.lower())
        if ext not in allowed_extensions:
            raise FileValidationError(
                f"File extension {ext} not allowed. Allowed: {allowed_extensions}"
            )

        # Check MIME type using python-magic if available
        if MAGIC_AVAILABLE:
            try:
                mime_type = magic.from_file(file_path, mime=True)
                if not mime_type.startswith("image/"):
                    raise FileValidationError(
                        f"File is not an image. Detected MIME type: {mime_type}"
                    )

                # Additional validation for specific image types
                allowed_mime_types = {
                    "image/jpeg",
                    "image/jpg",
                    "image/png",
                    "image/bmp",
                    "image/webp",
                }

                if mime_type not in allowed_mime_types:
                    raise FileValidationError(f"MIME type {mime_type} not allowed")

                logger.info(f"MIME type validation successful: {mime_type}")

            except Exception as e:
                logger.warning(f"Could not validate MIME type for {file_path}: {e}")
                # Fallback to extension-only validation if magic fails
                logger.info(f"Using extension-only validation for {file_path}")
        else:
            logger.info(
                f"Using extension-only validation for {file_path} (magic not available)"
            )

        return True

    except FileValidationError:
        raise
    except Exception as e:
        raise FileValidationError(f"Unexpected error during file validation: {str(e)}")


def validate_file_size(file_path: str, max_size_bytes: int = 10485760) -> bool:
    """
    Validate file size.

    Args:
        file_path: Path to the file
        max_size_bytes: Maximum allowed file size in bytes (default: 10MB)

    Returns:
        bool: True if file size is valid

    Raises:
        FileValidationError: If file is too large
    """
    try:
        file_size = os.path.getsize(file_path)
        if file_size > max_size_bytes:
            raise FileValidationError(
                f"File size {file_size} bytes exceeds maximum allowed size {max_size_bytes} bytes"
            )
        return True
    except Exception as e:
        raise FileValidationError(f"Error checking file size: {str(e)}")


def validate_upload_file(
    file_path: str, max_size_bytes: int = 10485760, allowed_extensions: set = None
) -> bool:
    """
    Comprehensive file validation for uploads.

    Args:
        file_path: Path to the uploaded file
        max_size_bytes: Maximum allowed file size
        allowed_extensions: Set of allowed file extensions

    Returns:
        bool: True if file passes all validations

    Raises:
        FileValidationError: If any validation fails
    """
    # Validate file size
    validate_file_size(file_path, max_size_bytes)

    # Validate file type and content
    validate_image_file(file_path, allowed_extensions)

    logger.info(f"File validation successful for {file_path}")
    return True
