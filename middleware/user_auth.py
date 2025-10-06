"""
User authentication middleware
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from services.auth_service import get_current_user, verify_token
from models.user import UserInDB

security = HTTPBearer()


async def get_current_active_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> UserInDB:
    """Get current active user from token"""
    token = credentials.credentials
    user = get_current_user(token)
    if user.disabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user"
        )
    return user


async def get_current_admin_user(
    current_user: UserInDB = Depends(get_current_active_user),
) -> UserInDB:
    """Verify current user is admin"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required"
        )
    return current_user
