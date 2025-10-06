"""
Global exception handler for standardized error responses.
"""

from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError, HTTPException
from slowapi.errors import RateLimitExceeded
from pydantic import ValidationError
import logging

logger = logging.getLogger(__name__)


async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTPException with standardized format."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": f"HTTP_{exc.status_code}",
                "message": exc.detail,
                "details": None,
            },
        },
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors with standardized format."""
    errors = {}
    for error in exc.errors():
        field = ".".join(str(x) for x in error["loc"])
        errors[field] = error["msg"]

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "details": errors,
            },
        },
    )


async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    """Handle rate limit exceeded errors."""
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={
            "success": False,
            "error": {
                "code": "RATE_LIMIT_EXCEEDED",
                "message": "Too many requests. Please try again later.",
                "details": {
                    "retry_after": exc.detail if hasattr(exc, "detail") else None
                },
            },
        },
    )


async def generic_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions with standardized format."""
    logger.error(f"Unexpected error: {str(exc)}", exc_info=True)

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
                "details": (
                    {"error": str(exc)} if logger.level == logging.DEBUG else None
                ),
            },
        },
    )
