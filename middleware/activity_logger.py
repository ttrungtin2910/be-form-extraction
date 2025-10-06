"""
Activity Logging Middleware
"""

import time
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from services.datastore_activity_service import datastore_activity_service
from models.activity_log import ActivityLogCreate, ActivityType
from services.auth_service import get_current_user_from_token
import logging

logger = logging.getLogger(__name__)


class ActivityLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log user activities"""

    def __init__(self, app, exclude_paths: list = None):
        super().__init__(app)
        self.exclude_paths = exclude_paths or [
            "/health",
            "/health/ready",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/favicon.ico",
        ]

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and log activity"""
        start_time = time.time()

        # Skip logging for excluded paths
        if request.url.path in self.exclude_paths:
            return await call_next(request)

        # Get user info from token
        user_info = None
        try:
            auth_header = request.headers.get("Authorization")
            logger.info(f"Authorization header: {auth_header}")
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]
                logger.info(f"Token extracted: {token[:20]}...")
                user_info = get_current_user_from_token(token)
                if user_info:
                    logger.info(f"User info extracted: {user_info}")
                else:
                    logger.warning("No user info found in token")
            else:
                logger.warning("No Authorization header found")
        except Exception as e:
            logger.error(f"Error extracting user info: {str(e)}")
            # If no valid token, we'll log as anonymous
            pass

        # Process request
        response = await call_next(request)

        # Calculate duration
        duration_ms = (time.time() - start_time) * 1000

        # Log the activity
        try:
            await self._log_activity(
                request=request,
                response=response,
                user_info=user_info,
                duration_ms=duration_ms,
            )
        except Exception as e:
            logger.error(f"Failed to log activity: {str(e)}")

        return response

    async def _log_activity(
        self,
        request: Request,
        response: Response,
        user_info: dict = None,
        duration_ms: float = None,
    ):
        """Log the activity"""
        try:
            # Determine activity type based on endpoint
            activity_type = self._get_activity_type(request)

            # Create description
            description = self._create_description(request, response, activity_type)

            # Prepare metadata
            metadata = {
                "request_id": getattr(request.state, "request_id", None),
                "response_size": len(response.body) if hasattr(response, "body") else 0,
                "query_params": (
                    dict(request.query_params) if request.query_params else {}
                ),
            }

            # Create activity log
            log_data = ActivityLogCreate(
                user_id=user_info.get("user_id") if user_info else "anonymous",
                username=user_info.get("username") if user_info else "anonymous",
                activity_type=activity_type,
                description=description,
                endpoint=request.url.path,
                method=request.method,
                status_code=response.status_code,
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
                metadata=metadata,
                duration_ms=duration_ms,
            )

            # Save log
            await datastore_activity_service.create_log(log_data)

        except Exception as e:
            logger.error(f"Error in activity logging: {str(e)}")

    def _get_activity_type(self, request: Request) -> ActivityType:
        """Determine activity type from request"""
        path = request.url.path
        method = request.method

        # Authentication endpoints
        if path.startswith("/auth/"):
            if path == "/auth/login":
                return ActivityType.LOGIN
            elif path == "/auth/logout":
                return ActivityType.LOGOUT
            else:
                return ActivityType.API_CALL

        # Image management endpoints
        elif path.startswith("/images/"):
            if method == "GET":
                return ActivityType.VIEW_IMAGE
            elif method == "DELETE":
                return ActivityType.DELETE_IMAGE
            else:
                return ActivityType.API_CALL

        # Upload endpoints
        elif path.startswith("/queue/upload"):
            return ActivityType.UPLOAD_IMAGE

        # Folder endpoints
        elif path.startswith("/folders/"):
            if method == "GET":
                return ActivityType.VIEW_FOLDER
            elif method == "POST":
                return ActivityType.CREATE_FOLDER
            elif method == "DELETE":
                return ActivityType.DELETE_FOLDER
            else:
                return ActivityType.API_CALL

        # Extraction endpoints
        elif path.startswith("/extract/"):
            return ActivityType.EXTRACT_DATA

        # Default to API call
        else:
            return ActivityType.API_CALL

    def _create_description(
        self, request: Request, response: Response, activity_type: ActivityType
    ) -> str:
        """Create human-readable description for the activity"""
        method = request.method
        path = request.url.path
        status = response.status_code

        # Base description
        if activity_type == ActivityType.LOGIN:
            return f"User logged in successfully"
        elif activity_type == ActivityType.LOGOUT:
            return f"User logged out"
        elif activity_type == ActivityType.UPLOAD_IMAGE:
            return f"Uploaded image to {path}"
        elif activity_type == ActivityType.VIEW_IMAGE:
            return f"Viewed image from {path}"
        elif activity_type == ActivityType.DELETE_IMAGE:
            return f"Deleted image from {path}"
        elif activity_type == ActivityType.VIEW_FOLDER:
            return f"Viewed folder contents from {path}"
        elif activity_type == ActivityType.CREATE_FOLDER:
            return f"Created new folder at {path}"
        elif activity_type == ActivityType.DELETE_FOLDER:
            return f"Deleted folder at {path}"
        elif activity_type == ActivityType.EXTRACT_DATA:
            return f"Extracted data from {path}"
        else:
            return f"{method} {path} - Status: {status}"


# Helper function for manual activity logging
async def log_user_activity(
    user_id: str,
    username: str,
    activity_type: ActivityType,
    description: str,
    endpoint: str = None,
    method: str = None,
    status_code: int = None,
    ip_address: str = None,
    user_agent: str = None,
    metadata: dict = None,
):
    """Helper function to manually log user activities"""
    try:
        log_data = ActivityLogCreate(
            user_id=user_id,
            username=username,
            activity_type=activity_type,
            description=description,
            endpoint=endpoint,
            method=method,
            status_code=status_code,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata=metadata or {},
        )

        await datastore_activity_service.create_log(log_data)

    except Exception as e:
        logger.error(f"Failed to log manual activity: {str(e)}")
