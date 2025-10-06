"""
Path sanitization utilities to prevent path traversal attacks.
"""

import re
from pathlib import PurePosixPath
from fastapi import HTTPException


def sanitize_folder_path(folder_path: str) -> str:
    """
    Validate and sanitize folder path to prevent path traversal attacks.

    Args:
        folder_path: User-provided folder path

    Returns:
        str: Sanitized folder path

    Raises:
        HTTPException: If path contains dangerous patterns

    Examples:
        >>> sanitize_folder_path("valid/folder")
        'valid/folder'
        >>> sanitize_folder_path("../../etc/passwd")  # Raises HTTPException
        >>> sanitize_folder_path("/absolute/path")  # Raises HTTPException
    """
    if not folder_path:
        return ""

    # Remove leading/trailing whitespace
    folder_path = folder_path.strip()

    # Allow only alphanumeric, underscore, hyphen, and forward slash
    if not re.match(r"^[\w\-/]+$", folder_path):
        raise HTTPException(
            status_code=400,
            detail="Invalid folder path. Only alphanumeric characters, underscores, hyphens, and forward slashes are allowed.",
        )

    # Normalize path and check for traversal attempts
    normalized = str(PurePosixPath(folder_path))

    # Check for absolute paths
    if normalized.startswith("/"):
        raise HTTPException(status_code=400, detail="Absolute paths are not allowed")

    # Check for parent directory references
    if ".." in normalized:
        raise HTTPException(
            status_code=400, detail="Path traversal attempts are not allowed"
        )

    # Additional check: ensure normalized path doesn't escape the base directory
    if normalized.startswith(".."):
        raise HTTPException(
            status_code=400, detail="Path must not escape base directory"
        )

    return normalized


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to prevent malicious filenames.

    Args:
        filename: User-provided filename

    Returns:
        str: Sanitized filename

    Raises:
        HTTPException: If filename is invalid
    """
    if not filename:
        raise HTTPException(status_code=400, detail="Filename cannot be empty")

    # Remove directory separators
    filename = filename.replace("/", "").replace("\\", "").replace("..", "")

    # Check for null bytes
    if "\x00" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    # Limit length
    if len(filename) > 255:
        raise HTTPException(
            status_code=400, detail="Filename too long (max 255 characters)"
        )

    return filename
