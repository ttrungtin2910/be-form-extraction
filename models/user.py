"""
User models for authentication
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class User(BaseModel):
    """User model"""

    username: str = Field(..., min_length=3, max_length=50)
    email: Optional[str] = None
    full_name: Optional[str] = None
    disabled: bool = False
    created_at: datetime = Field(default_factory=datetime.now)
    last_login: Optional[datetime] = None
    role: str = "user"  # user, admin, viewer


class UserInDB(User):
    """User model with hashed password"""

    hashed_password: str


class UserLogin(BaseModel):
    """Login request model"""

    username: str
    password: str


class UserCreate(BaseModel):
    """User creation model"""

    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)
    email: Optional[str] = None
    full_name: Optional[str] = None
    role: str = "user"


class Token(BaseModel):
    """Token response model"""

    access_token: str
    token_type: str
    username: str
    full_name: Optional[str] = None
    role: str


class TokenData(BaseModel):
    """Token data model"""

    username: Optional[str] = None
