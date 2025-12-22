"""
Security utilities for authentication and authorization.
Implements API key authentication for admin endpoints.
"""

from fastapi import HTTPException, Security, Depends, Request
from fastapi.security import APIKeyHeader
from typing import Optional
import secrets
import hashlib
import logging

from .config import settings

logger = logging.getLogger(__name__)

# API Key header scheme
api_key_header = APIKeyHeader(name=settings.API_KEY_HEADER, auto_error=False)


def get_client_ip(request: Request) -> str:
    """Extract client IP from request, handling proxies."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def hash_api_key(api_key: str) -> str:
    """Hash an API key for secure comparison."""
    return hashlib.sha256(api_key.encode()).hexdigest()


async def verify_api_key(api_key: str = Security(api_key_header)) -> str:
    """
    Verify API key for protected endpoints.
    Raises HTTPException if invalid.
    """
    if not api_key:
        raise HTTPException(
            status_code=401,
            detail="API key required",
            headers={"WWW-Authenticate": "ApiKey"}
        )
    
    # In production, compare against hashed keys stored in database
    # For this demo, we use the configured admin key
    if not secrets.compare_digest(api_key, settings.ADMIN_API_KEY):
        logger.warning(f"Invalid API key attempt")
        raise HTTPException(
            status_code=403,
            detail="Invalid API key"
        )
    
    return api_key


async def optional_api_key(api_key: str = Security(api_key_header)) -> Optional[str]:
    """
    Optional API key verification - doesn't raise error if missing.
    Used for endpoints that work differently with/without auth.
    """
    if api_key and secrets.compare_digest(api_key, settings.ADMIN_API_KEY):
        return api_key
    return None


class RateLimiter:
    """
    Simple in-memory rate limiter.
    In production, use Redis or similar for distributed rate limiting.
    """
    
    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
        self.requests = {}  # {ip: [timestamps]}
    
    def is_allowed(self, client_ip: str) -> bool:
        """Check if request is allowed under rate limit."""
        import time
        current_time = time.time()
        minute_ago = current_time - 60
        
        if client_ip not in self.requests:
            self.requests[client_ip] = []
        
        # Clean old requests
        self.requests[client_ip] = [
            ts for ts in self.requests[client_ip] 
            if ts > minute_ago
        ]
        
        # Check limit
        if len(self.requests[client_ip]) >= self.requests_per_minute:
            return False
        
        # Record this request
        self.requests[client_ip].append(current_time)
        return True


# Global rate limiter instance
rate_limiter = RateLimiter(requests_per_minute=100)


async def check_rate_limit(request: Request):
    """Dependency to check rate limit."""
    client_ip = get_client_ip(request)
    
    if not rate_limiter.is_allowed(client_ip):
        logger.warning(f"Rate limit exceeded for {client_ip}")
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Please try again later."
        )
