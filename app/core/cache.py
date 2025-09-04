"""
Caching utilities using Redis.
"""
import json
import pickle
from datetime import timedelta
from typing import Any, Optional, Union
import redis
from loguru import logger

from app.core.config import settings


class CacheService:
    """Redis-based caching service."""
    
    def __init__(self):
        try:
            self.redis_client = redis.from_url(
                settings.REDIS_URL,
                decode_responses=False,  # We'll handle encoding ourselves
                socket_connect_timeout=5,
                socket_timeout=5
            )
            # Test connection
            self.redis_client.ping()
            logger.info("Redis connection established")
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}. Caching will be disabled.")
            self.redis_client = None
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if not self.redis_client:
            return None
        
        try:
            value = self.redis_client.get(key)
            if value is None:
                return None
            
            # Try to deserialize as JSON first, then pickle
            try:
                return json.loads(value.decode('utf-8'))
            except (json.JSONDecodeError, UnicodeDecodeError):
                return pickle.loads(value)
                
        except Exception as e:
            logger.error(f"Cache get error for key {key}: {e}")
            return None
    
    def set(self, key: str, value: Any, expire: Optional[Union[int, timedelta]] = None) -> bool:
        """Set value in cache with optional expiration."""
        if not self.redis_client:
            return False
        
        try:
            # Try to serialize as JSON first, then pickle
            try:
                serialized_value = json.dumps(value, default=str)
            except (TypeError, ValueError):
                serialized_value = pickle.dumps(value)
            
            if expire:
                if isinstance(expire, timedelta):
                    expire = int(expire.total_seconds())
                return self.redis_client.setex(key, expire, serialized_value)
            else:
                return self.redis_client.set(key, serialized_value)
                
        except Exception as e:
            logger.error(f"Cache set error for key {key}: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete key from cache."""
        if not self.redis_client:
            return False
        
        try:
            return bool(self.redis_client.delete(key))
        except Exception as e:
            logger.error(f"Cache delete error for key {key}: {e}")
            return False
    
    def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        if not self.redis_client:
            return False
        
        try:
            return bool(self.redis_client.exists(key))
        except Exception as e:
            logger.error(f"Cache exists error for key {key}: {e}")
            return False
    
    def clear_pattern(self, pattern: str) -> int:
        """Clear all keys matching pattern."""
        if not self.redis_client:
            return 0
        
        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                return self.redis_client.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Cache clear pattern error for pattern {pattern}: {e}")
            return 0
    
    def get_or_set(self, key: str, func, expire: Optional[Union[int, timedelta]] = None) -> Any:
        """Get value from cache or set it using the provided function."""
        value = self.get(key)
        if value is not None:
            return value
        
        # Generate value using function
        value = func()
        self.set(key, value, expire)
        return value


# Global cache instance
cache = CacheService()


# Cache decorators and utilities
def cache_key(*args, **kwargs) -> str:
    """Generate cache key from arguments."""
    key_parts = []
    
    # Add positional arguments
    for arg in args:
        if isinstance(arg, (str, int, float, bool)):
            key_parts.append(str(arg))
        else:
            key_parts.append(str(hash(str(arg))))
    
    # Add keyword arguments
    for k, v in sorted(kwargs.items()):
        if isinstance(v, (str, int, float, bool)):
            key_parts.append(f"{k}:{v}")
        else:
            key_parts.append(f"{k}:{hash(str(v))}")
    
    return ":".join(key_parts)


def cached(expire: Optional[Union[int, timedelta]] = None, key_prefix: str = ""):
    """Decorator to cache function results."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Generate cache key
            func_key = f"{key_prefix}:{func.__name__}" if key_prefix else func.__name__
            full_key = f"{func_key}:{cache_key(*args, **kwargs)}"
            
            # Try to get from cache
            result = cache.get(full_key)
            if result is not None:
                logger.debug(f"Cache hit for key: {full_key}")
                return result
            
            # Execute function and cache result
            logger.debug(f"Cache miss for key: {full_key}")
            result = func(*args, **kwargs)
            cache.set(full_key, result, expire)
            return result
        
        return wrapper
    return decorator


# Common cache keys and expiration times
CACHE_KEYS = {
    "channel_overview": "channel:overview:{channel_id}",
    "channel_growth": "channel:growth:{channel_id}:{days}",
    "video_performance": "video:performance:{video_id}:{days}",
    "videos_list": "videos:list:{channel_id}:{page}:{limit}",
    "traffic_data": "traffic:data:{days}",
    "analytics_overview": "analytics:overview:{channel_id}"
}

CACHE_EXPIRATION = {
    "short": timedelta(minutes=5),      # For frequently changing data
    "medium": timedelta(minutes=30),    # For moderately changing data
    "long": timedelta(hours=2),         # For slowly changing data
    "daily": timedelta(hours=24)        # For daily aggregated data
}
