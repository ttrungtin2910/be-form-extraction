"""
Authentication service
"""

from datetime import datetime, timedelta
from typing import Optional
import bcrypt
from jose import JWTError, jwt
from fastapi import HTTPException, status
from models.user import UserInDB, TokenData
from properties.config import Configuration

# JWT settings
SECRET_KEY = Configuration.API_SECRET_KEY or "your-secret-key-for-jwt"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


# Mock user database (in production, use real database)
fake_users_db = {
    "tin.trantrung": {
        "username": "tin.trantrung",
        "full_name": "Trần Trung Tín",
        "email": "tin.trantrung@example.com",
        "hashed_password": "$2b$12$pLIHZPZhOn01LXCEmyol5eVjh2GABXbnUmABROn.To9Vl9110flIm",  # secret
        "disabled": False,
        "role": "admin",
        "created_at": datetime.now(),
    },
    "thao.nguyentrang": {
        "username": "thao.nguyentrang",
        "full_name": "Nguyễn Trang Thảo",
        "email": "thao.nguyentrang@example.com",
        "hashed_password": "$2b$12$pLIHZPZhOn01LXCEmyol5eVjh2GABXbnUmABROn.To9Vl9110flIm",  # secret
        "disabled": False,
        "role": "user",
        "created_at": datetime.now(),
    },
    "vin.nguyenthai": {
        "username": "vin.nguyenthai",
        "full_name": "Nguyễn Thái Vĩn",
        "email": "vin.nguyenthai@example.com",
        "hashed_password": "$2b$12$pLIHZPZhOn01LXCEmyol5eVjh2GABXbnUmABROn.To9Vl9110flIm",  # secret
        "disabled": False,
        "role": "user",
        "created_at": datetime.now(),
    },
    "testuser1": {
        "username": "testuser1",
        "full_name": "Test User 1",
        "email": "testuser1@example.com",
        "hashed_password": "$2b$12$pLIHZPZhOn01LXCEmyol5eVjh2GABXbnUmABROn.To9Vl9110flIm",  # secret
        "disabled": False,
        "role": "viewer",
        "created_at": datetime.now(),
    },
    "testuser2": {
        "username": "testuser2",
        "full_name": "Test User 2",
        "email": "testuser2@example.com",
        "hashed_password": "$2b$12$pLIHZPZhOn01LXCEmyol5eVjh2GABXbnUmABROn.To9Vl9110flIm",  # secret
        "disabled": False,
        "role": "viewer",
        "created_at": datetime.now(),
    },
}


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash"""
    # Convert password to bytes, bcrypt handles up to 72 bytes
    password_bytes = plain_password.encode("utf-8")
    hashed_bytes = (
        hashed_password.encode("utf-8")
        if isinstance(hashed_password, str)
        else hashed_password
    )
    return bcrypt.checkpw(password_bytes, hashed_bytes)


def get_password_hash(password: str) -> str:
    """Hash a password"""
    # Convert password to bytes and hash
    password_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode("utf-8")


def get_user(username: str) -> Optional[UserInDB]:
    """Get user from database"""
    if username in fake_users_db:
        user_dict = fake_users_db[username]
        return UserInDB(**user_dict)
    return None


def authenticate_user(username: str, password: str) -> Optional[UserInDB]:
    """Authenticate a user"""
    user = get_user(username)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> TokenData:
    """Verify a JWT token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    return token_data


def get_current_user(token: str) -> UserInDB:
    """Get current user from token"""
    token_data = verify_token(token)
    user = get_user(username=token_data.username)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def update_last_login(username: str):
    """Update user's last login time"""
    if username in fake_users_db:
        fake_users_db[username]["last_login"] = datetime.now()
