"""
Standardized API response models.
"""

from typing import Generic, TypeVar, Optional, Any
from pydantic import BaseModel

T = TypeVar("T")


class SuccessResponse(BaseModel, Generic[T]):
    """Standard success response format."""

    success: bool = True
    message: str
    data: Optional[T] = None


class ErrorDetail(BaseModel):
    """Error detail structure."""

    code: str
    message: str
    details: Optional[dict[str, Any]] = None


class ErrorResponse(BaseModel):
    """Standard error response format."""

    success: bool = False
    error: ErrorDetail
