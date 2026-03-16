"""
Rate limiter for connection throttling.
"""

import asyncio
import time
from typing import Dict
from collections import deque
import logging

from .config import settings

logger = logging.getLogger(__name__)


class RateLimiter:
    """Token bucket rate limiter per IP"""
    
    def __init__(self):
        self._buckets: Dict[str, deque] = {}
        self._limit = settings.rate_limit_connections
        self._window = 60.0  # 1 minute window
        self._burst = settings.rate_limit_burst
        self._lock = asyncio.Lock()
    
    async def is_allowed(self, ip: str) -> bool:
        """Check if connection from IP is allowed"""
        async with self._lock:
            now = time.monotonic()
            
            if ip not in self._buckets:
                self._buckets[ip] = deque()
            
            bucket = self._buckets[ip]
            
            # Remove old entries outside window
            while bucket and bucket[0] < now - self._window:
                bucket.popleft()
            
            # Check burst limit
            if len(bucket) >= self._burst:
                logger.warning(f"Rate limit exceeded for {ip}")
                return False
            
            # Check rate limit
            if len(bucket) >= self._limit:
                return False
            
            # Add current request
            bucket.append(now)
            return True
    
    async def cleanup(self):
        """Clean up old buckets"""
        async with self._lock:
            now = time.monotonic()
            empty_ips = [
                ip for ip, bucket in self._buckets.items()
                if not bucket or bucket[-1] < now - self._window
            ]
            for ip in empty_ips:
                del self._buckets[ip]