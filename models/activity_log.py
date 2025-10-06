"""
User Activity Log Models
"""

from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class ActivityType(str, Enum):
    """Activity types for user actions"""

    LOGIN = "login"
    LOGOUT = "logout"
    UPLOAD_IMAGE = "upload_image"
    VIEW_IMAGE = "view_image"
    DELETE_IMAGE = "delete_image"
    EXTRACT_DATA = "extract_data"
    VIEW_FOLDER = "view_folder"
    CREATE_FOLDER = "create_folder"
    DELETE_FOLDER = "delete_folder"
    API_CALL = "api_call"
    ERROR = "error"


class ActivityLog(BaseModel):
    """User activity log model"""

    id: Optional[str] = None
    user_id: str = Field(..., description="User who performed the action")
    username: str = Field(..., description="Username for easy reference")
    activity_type: ActivityType = Field(..., description="Type of activity")
    description: str = Field(..., description="Human readable description")
    endpoint: Optional[str] = Field(None, description="API endpoint called")
    method: Optional[str] = Field(None, description="HTTP method")
    status_code: Optional[int] = Field(None, description="HTTP status code")
    ip_address: Optional[str] = Field(None, description="User's IP address")
    user_agent: Optional[str] = Field(None, description="User's browser/device info")
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Additional data"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="When the activity occurred"
    )
    duration_ms: Optional[float] = Field(
        None, description="Request duration in milliseconds"
    )


class ActivityLogCreate(BaseModel):
    """Model for creating activity logs"""

    user_id: str
    username: str
    activity_type: ActivityType
    description: str
    endpoint: Optional[str] = None
    method: Optional[str] = None
    status_code: Optional[int] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    duration_ms: Optional[float] = None


class ActivityLogFilter(BaseModel):
    """Filter for querying activity logs"""

    user_id: Optional[str] = None
    username: Optional[str] = None
    activity_type: Optional[ActivityType] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=50, ge=1, le=1000)


class ActivityLogResponse(BaseModel):
    """Response model for activity logs"""

    logs: list[ActivityLog]
    total: int
    page: int
    limit: int
    total_pages: int
