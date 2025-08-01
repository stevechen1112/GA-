"""
優化版快取服務

使用 TTLCache 自動管理內存，防止內存洩漏
"""

from typing import Dict, Any, Optional, List
import structlog
import json
import hashlib
from datetime import datetime, timedelta
from cachetools import TTLCache
import asyncio
from functools import wraps

from app.core.config import settings

logger = structlog.get_logger()

# 嘗試導入 Redis
try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None


class OptimizedCacheService:
    """優化的快取服務類別"""
    
    def __init__(self):
        self.redis_client = None
        
        # 使用 TTLCache 自動管理過期和大小
        self.memory_cache = TTLCache(
            maxsize=settings.MAX_CACHE_SIZE_MB * 1024,  # 轉換為 KB
            ttl=settings.CACHE_TTL_SECONDS
        )
        
        # 快取統計
        self.stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0,
            "errors": 0
        }
        
        # 快取配置
        self.cache_prefix = "ga_plus:"
        self.lock = asyncio.Lock()
        
        # 初始化 Redis 客戶端
        if REDIS_AVAILABLE:
            self._init_redis_client()
    
    def _init_redis_client(self):
        """初始化 Redis 客戶端"""
        try:
            self.redis_client = redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
                max_connections=50,
                socket_keepalive=True,
                socket_keepalive_options={
                    1: 1,   # TCP_KEEPIDLE
                    2: 10,  # TCP_KEEPINTVL
                    3: 3,   # TCP_KEEPCNT
                }
            )
            logger.info("Redis client initialized with connection pooling")
        except Exception as e:
            logger.error("Failed to initialize Redis client", error=str(e))
            self.redis_client = None
    
    async def get(self, key: str) -> Optional[Any]:
        """
        獲取快取值（優化版）
        
        Args:
            key: 快取鍵
            
        Returns:
            快取值或 None
        """
        try:
            full_key = f"{self.cache_prefix}{key}"
            
            # 優先從 Redis 獲取
            if self.redis_client:
                try:
                    value = await self.redis_client.get(full_key)
                    if value:
                        self.stats["hits"] += 1
                        return json.loads(value)
                except redis.ConnectionError:
                    logger.warning("Redis connection lost, falling back to memory cache")
                    self.redis_client = None
            
            # 從內存快取獲取
            value = self.memory_cache.get(full_key)
            if value is not None:
                self.stats["hits"] += 1
                return value
            
            self.stats["misses"] += 1
            return None
            
        except Exception as e:
            self.stats["errors"] += 1
            logger.error("Cache get failed", key=key, error=str(e))
            return None
    
    async def set(
        self, 
        key: str, 
        value: Any, 
        ttl: Optional[int] = None
    ) -> bool:
        """
        設置快取值（優化版）
        
        Args:
            key: 快取鍵
            value: 快取值
            ttl: 生存時間（秒）
            
        Returns:
            是否成功
        """
        try:
            full_key = f"{self.cache_prefix}{key}"
            ttl = ttl or settings.CACHE_TTL_SECONDS
            
            # 同時設置到 Redis 和內存快取
            success = True
            
            if self.redis_client:
                try:
                    serialized_value = json.dumps(value, ensure_ascii=False)
                    await self.redis_client.setex(full_key, ttl, serialized_value)
                except redis.ConnectionError:
                    logger.warning("Redis connection lost during set operation")
                    success = False
            
            # 設置到內存快取（TTLCache 會自動處理過期）
            async with self.lock:
                self.memory_cache[full_key] = value
            
            self.stats["sets"] += 1
            return success
            
        except Exception as e:
            self.stats["errors"] += 1
            logger.error("Cache set failed", key=key, error=str(e))
            return False
    
    async def delete(self, key: str) -> bool:
        """
        刪除快取值（優化版）
        
        Args:
            key: 快取鍵
            
        Returns:
            是否成功
        """
        try:
            full_key = f"{self.cache_prefix}{key}"
            
            if self.redis_client:
                try:
                    await self.redis_client.delete(full_key)
                except redis.ConnectionError:
                    logger.warning("Redis connection lost during delete")
            
            # 從內存快取刪除
            async with self.lock:
                self.memory_cache.pop(full_key, None)
            
            self.stats["deletes"] += 1
            return True
            
        except Exception as e:
            self.stats["errors"] += 1
            logger.error("Cache delete failed", key=key, error=str(e))
            return False
    
    async def clear_pattern(self, pattern: str) -> int:
        """
        清除匹配模式的快取（優化版）
        
        Args:
            pattern: 模式字符串
            
        Returns:
            清除的數量
        """
        count = 0
        try:
            if self.redis_client:
                try:
                    full_pattern = f"{self.cache_prefix}{pattern}"
                    # 使用 SCAN 代替 KEYS 以避免阻塞
                    cursor = b'0'
                    while cursor:
                        cursor, keys = await self.redis_client.scan(
                            cursor, match=full_pattern, count=100
                        )
                        if keys:
                            count += len(keys)
                            await self.redis_client.delete(*keys)
                except redis.ConnectionError:
                    logger.warning("Redis connection lost during pattern clear")
            
            # 清除內存快取中的匹配項
            import re
            regex_pattern = pattern.replace("*", ".*")
            regex = re.compile(f"{self.cache_prefix}{regex_pattern}")
            
            async with self.lock:
                keys_to_delete = [k for k in self.memory_cache.keys() if regex.match(k)]
                for key in keys_to_delete:
                    del self.memory_cache[key]
                    count += 1
            
            return count
            
        except Exception as e:
            self.stats["errors"] += 1
            logger.error("Cache clear pattern failed", pattern=pattern, error=str(e))
            return 0
    
    def cache_key_wrapper(self, prefix: str = "func", ttl: int = None):
        """
        函數快取裝飾器
        
        Args:
            prefix: 快取鍵前綴
            ttl: 快取時間
        """
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # 生成快取鍵
                cache_key = f"{prefix}:{func.__name__}:{str(args)}:{str(kwargs)}"
                
                # 嘗試從快取獲取
                cached_value = await self.get(cache_key)
                if cached_value is not None:
                    return cached_value
                
                # 執行函數
                result = await func(*args, **kwargs)
                
                # 快取結果
                await self.set(cache_key, result, ttl)
                
                return result
            return wrapper
        return decorator
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """
        獲取快取統計信息（優化版）
        
        Returns:
            快取統計
        """
        try:
            stats = {
                "cache_type": "hybrid" if self.redis_client else "memory",
                "memory_cache_size": len(self.memory_cache),
                "memory_cache_max_size": self.memory_cache.maxsize,
                "hits": self.stats["hits"],
                "misses": self.stats["misses"],
                "hit_rate": self.stats["hits"] / (self.stats["hits"] + self.stats["misses"]) 
                           if (self.stats["hits"] + self.stats["misses"]) > 0 else 0,
                "sets": self.stats["sets"],
                "deletes": self.stats["deletes"],
                "errors": self.stats["errors"]
            }
            
            if self.redis_client:
                try:
                    info = await self.redis_client.info()
                    stats.update({
                        "redis_connected": True,
                        "redis_memory_used": info.get("used_memory_human", "unknown"),
                        "redis_connected_clients": info.get("connected_clients", 0),
                        "redis_total_commands": info.get("total_commands_processed", 0)
                    })
                except:
                    stats["redis_connected"] = False
            
            return stats
            
        except Exception as e:
            logger.error("Failed to get cache stats", error=str(e))
            return {"error": str(e)}
    
    async def warmup_cache(self, queries: List[Dict[str, Any]]):
        """
        預熱快取
        
        Args:
            queries: 要預熱的查詢列表
        """
        logger.info("Starting cache warmup", query_count=len(queries))
        
        for query in queries:
            try:
                cache_key = self._generate_query_cache_key(query)
                # 這裡應該執行實際的查詢並快取結果
                # 為了示例，我們只是設置一個佔位符
                await self.set(f"query:{cache_key}", {"warmup": True}, ttl=3600)
            except Exception as e:
                logger.error("Cache warmup failed for query", query=query, error=str(e))
        
        logger.info("Cache warmup completed")
    
    def _generate_query_cache_key(self, query_params: Dict[str, Any]) -> str:
        """生成查詢快取鍵（優化版）"""
        # 只包含影響結果的參數
        relevant_params = {
            "metrics": sorted(query_params.get("metrics", [])),
            "dimensions": sorted(query_params.get("dimensions", [])),
            "date_ranges": query_params.get("date_ranges", []),
            "property_id": query_params.get("property_id", ""),
            "filters": query_params.get("filters", {}),
            "limit": query_params.get("limit", 10)
        }
        
        # 生成穩定的雜湊
        params_str = json.dumps(relevant_params, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(params_str.encode('utf-8')).hexdigest()[:16]
    
    async def health_check(self) -> Dict[str, Any]:
        """
        快取服務健康檢查（優化版）
        
        Returns:
            健康狀態
        """
        try:
            health_status = {
                "status": "healthy",
                "redis_available": REDIS_AVAILABLE,
                "redis_connected": False,
                "memory_cache_healthy": True,
                "cache_performance": {
                    "hit_rate": f"{self.stats['hits'] / (self.stats['hits'] + self.stats['misses']) * 100:.1f}%" 
                               if (self.stats['hits'] + self.stats['misses']) > 0 else "0%",
                    "error_rate": f"{self.stats['errors'] / (self.stats['hits'] + self.stats['misses'] + self.stats['sets']) * 100:.1f}%"
                                 if (self.stats['hits'] + self.stats['misses'] + self.stats['sets']) > 0 else "0%"
                }
            }
            
            if self.redis_client:
                try:
                    await self.redis_client.ping()
                    health_status["redis_connected"] = True
                    health_status["message"] = "All cache systems operational"
                except:
                    health_status["message"] = "Redis disconnected, using memory cache only"
            else:
                health_status["message"] = "Memory cache only mode"
            
            return health_status
            
        except Exception as e:
            logger.error("Cache health check failed", error=str(e))
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    async def close(self):
        """關閉快取連接"""
        try:
            if self.redis_client:
                await self.redis_client.close()
                logger.info("Redis connection closed")
            
            # 清理內存快取
            self.memory_cache.clear()
            logger.info("Memory cache cleared")
            
        except Exception as e:
            logger.error("Failed to close cache connections", error=str(e))


# 創建單例實例
cache_service = OptimizedCacheService()