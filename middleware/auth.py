"""
Authentication middleware for API endpoints.
Supports API Key authentication via Bearer token.
"""

from fastapi import Security, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from properties.config import Configuration

config = Configuration()
security = HTTPBearer()


async def verify_api_key(
    credentials: HTTPAuthorizationCredentials = Security(security),
):
    """
    Verify API key from Authorization header.

    Args:
        credentials: HTTPAuthorizationCredentials from Bearer token

    Returns:
        str: The validated token

    Raises:
        HTTPException: If authentication fails
    """
    token = credentials.credentials

    # Validate API key
    if not config.API_SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="API authentication not configured",
        )

    if token != config.API_SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return token
