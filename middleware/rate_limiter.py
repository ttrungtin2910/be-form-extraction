"""
Rate limiting middleware to prevent API abuse.
Uses slowapi library with Redis backend.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address
from properties.config import Configuration

config = Configuration()

# Initialize rate limiter
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=config.REDIS_URL,
    strategy="fixed-window",
)


# Rate limit decorators for different endpoint types
# General API endpoints: 100 requests per minute
RATE_LIMIT_GENERAL = "100/minute"

# Upload endpoints: 20 requests per minute (resource intensive)
RATE_LIMIT_UPLOAD = "20/minute"

# Extract/AI endpoints: 10 requests per minute (expensive API calls)
RATE_LIMIT_AI = "10/minute"

# Queue status check: 200 requests per minute
RATE_LIMIT_STATUS = "200/minute"
