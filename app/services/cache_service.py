"""
快取服務

負責 Redis 快取管理和查詢結果快取
"""

from typing import Dict, Any, Optional, List
import structlog
import json
import hashlib
from datetime import datetime, timedelta

from app.core.config import settings

logger = structlog.get_logger()

# 嘗試導入 Redis，如果失敗則使用內存快取
try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None


class CacheService:
    """快取服務類別"""
    
    def __init__(self):
        self.redis_client = None
        self.memory_cache = {}  # 備用內存快取
        self.max_memory_cache_size = 1000
        
        # 快取配置
        self.default_ttl = settings.CACHE_TTL_SECONDS
        self.cache_prefix = "ga_plus:"
        
        # 初始化 Redis 客戶端
        if REDIS_AVAILABLE:
            try:
                self.redis_client = redis.from_url(
                    settings.REDIS_URL,
                    encoding="utf-8",
                    decode_responses=True
                )
                logger.info("Redis client initialized successfully")
            except Exception as e:
                logger.error("Failed to initialize Redis client", error=str(e))
                self.redis_client = None
        else:
            logger.warning("Redis not available, using memory cache")
    
    async def get(self, key: str) -> Optional[Any]:
        """
        獲取快取值
        
        Args:
            key: 快取鍵
            
        Returns:
            快取值或 None
        """
        try:
            full_key = f"{self.cache_prefix}{key}"
            
            if self.redis_client:
                # 使用 Redis
                value = await self.redis_client.get(full_key)
                if value:
                    return json.loads(value)
            else:
                # 使用內存快取
                cache_entry = self.memory_cache.get(full_key)
                if cache_entry:
                    # 檢查是否過期
                    if datetime.now() < cache_entry["expires_at"]:
                        return cache_entry["value"]
                    else:
                        # 清除過期項目
                        del self.memory_cache[full_key]
            
            return None
            
        except Exception as e:
            logger.error("Cache get failed", key=key, error=str(e))
            return None
    
    async def set(
        self, 
        key: str, 
        value: Any, 
        ttl: Optional[int] = None
    ) -> bool:
        """
        設置快取值
        
        Args:
            key: 快取鍵
            value: 快取值
            ttl: 生存時間（秒）
            
        Returns:
            是否成功
        """
        try:
            full_key = f"{self.cache_prefix}{key}"
            ttl = ttl or self.default_ttl
            
            if self.redis_client:
                # 使用 Redis
                serialized_value = json.dumps(value, ensure_ascii=False)
                await self.redis_client.setex(full_key, ttl, serialized_value)
            else:
                # 使用內存快取
                # 如果快取太大，清理一些舊項目
                if len(self.memory_cache) >= self.max_memory_cache_size:
                    self._cleanup_memory_cache()
                
                expires_at = datetime.now() + timedelta(seconds=ttl)
                self.memory_cache[full_key] = {
                    "value": value,
                    "expires_at": expires_at,
                    "created_at": datetime.now()
                }
            
            return True
            
        except Exception as e:
            logger.error("Cache set failed", key=key, error=str(e))
            return False
    
    async def delete(self, key: str) -> bool:
        """
        刪除快取值
        
        Args:
            key: 快取鍵
            
        Returns:
            是否成功
        """
        try:
            full_key = f"{self.cache_prefix}{key}"
            
            if self.redis_client:
                await self.redis_client.delete(full_key)
            else:
                self.memory_cache.pop(full_key, None)
            
            return True
            
        except Exception as e:
            logger.error("Cache delete failed", key=key, error=str(e))
            return False
    
    async def exists(self, key: str) -> bool:
        """
        檢查快取鍵是否存在
        
        Args:
            key: 快取鍵
            
        Returns:
            是否存在
        """
        try:
            full_key = f"{self.cache_prefix}{key}"
            
            if self.redis_client:
                return await self.redis_client.exists(full_key) > 0
            else:
                cache_entry = self.memory_cache.get(full_key)
                if cache_entry:
                    # 檢查是否過期
                    if datetime.now() < cache_entry["expires_at"]:
                        return True
                    else:
                        del self.memory_cache[full_key]
                        return False
                return False
            
        except Exception as e:
            logger.error("Cache exists check failed", key=key, error=str(e))
            return False
    
    async def clear_pattern(self, pattern: str) -> int:
        """
        清除匹配模式的快取
        
        Args:
            pattern: 模式字符串
            
        Returns:
            清除的數量
        """
        try:
            if self.redis_client:
                full_pattern = f"{self.cache_prefix}{pattern}"
                keys = await self.redis_client.keys(full_pattern)
                if keys:
                    return await self.redis_client.delete(*keys)
                return 0
            else:
                # 內存快取模式匹配
                full_pattern = f"{self.cache_prefix}{pattern}"
                keys_to_delete = []
                
                for key in self.memory_cache.keys():
                    if self._match_pattern(key, full_pattern):
                        keys_to_delete.append(key)
                
                for key in keys_to_delete:
                    del self.memory_cache[key]
                
                return len(keys_to_delete)
            
        except Exception as e:
            logger.error("Cache clear pattern failed", pattern=pattern, error=str(e))
            return 0
    
    async def cache_query_result(
        self, 
        query_params: Dict[str, Any], 
        result: Dict[str, Any],
        ttl: Optional[int] = None
    ) -> str:
        """
        快取查詢結果
        
        Args:
            query_params: 查詢參數
            result: 查詢結果
            ttl: 快取時間
            
        Returns:
            快取鍵
        """
        try:
            # 生成查詢快取鍵
            cache_key = self._generate_query_cache_key(query_params)
            
            # 添加快取元數據
            cached_result = {
                "data": result,
                "cached_at": datetime.now().isoformat(),
                "query_params": query_params,
                "ttl": ttl or self.default_ttl
            }
            
            # 設置快取
            await self.set(f"query:{cache_key}", cached_result, ttl)
            
            logger.info("Query result cached", cache_key=cache_key)
            return cache_key
            
        except Exception as e:
            logger.error("Failed to cache query result", error=str(e))
            return ""
    
    async def get_cached_query_result(
        self, 
        query_params: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        獲取快取的查詢結果
        
        Args:
            query_params: 查詢參數
            
        Returns:
            快取的結果或 None
        """
        try:
            cache_key = self._generate_query_cache_key(query_params)
            cached_result = await self.get(f"query:{cache_key}")
            
            if cached_result:
                logger.info("Query result cache hit", cache_key=cache_key)
                return cached_result["data"]
            
            return None
            
        except Exception as e:
            logger.error("Failed to get cached query result", error=str(e))
            return None
    
    async def cache_user_session(
        self, 
        user_id: str, 
        session_data: Dict[str, Any],
        ttl: int = 3600
    ) -> bool:
        """
        快取用戶會話數據
        
        Args:
            user_id: 用戶ID
            session_data: 會話數據
            ttl: 快取時間
            
        Returns:
            是否成功
        """
        try:
            session_key = f"session:{user_id}"
            return await self.set(session_key, session_data, ttl)
            
        except Exception as e:
            logger.error("Failed to cache user session", user_id=user_id, error=str(e))
            return False
    
    async def get_user_session(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        獲取用戶會話數據
        
        Args:
            user_id: 用戶ID
            
        Returns:
            會話數據或 None
        """
        try:
            session_key = f"session:{user_id}"
            return await self.get(session_key)
            
        except Exception as e:
            logger.error("Failed to get user session", user_id=user_id, error=str(e))
            return None
    
    async def increment_counter(
        self, 
        key: str, 
        amount: int = 1,
        ttl: Optional[int] = None
    ) -> int:
        """
        增加計數器
        
        Args:
            key: 計數器鍵
            amount: 增加量
            ttl: 過期時間
            
        Returns:
            新的計數值
        """
        try:
            full_key = f"{self.cache_prefix}counter:{key}"
            
            if self.redis_client:
                count = await self.redis_client.incrby(full_key, amount)
                if ttl:
                    await self.redis_client.expire(full_key, ttl)
                return count
            else:
                # 內存快取實現
                current_value = await self.get(f"counter:{key}") or 0
                new_value = current_value + amount
                await self.set(f"counter:{key}", new_value, ttl)
                return new_value
            
        except Exception as e:
            logger.error("Failed to increment counter", key=key, error=str(e))
            return 0
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """
        獲取快取統計信息
        
        Returns:
            快取統計
        """
        try:
            stats = {
                "redis_available": REDIS_AVAILABLE and self.redis_client is not None,
                "cache_type": "redis" if (REDIS_AVAILABLE and self.redis_client) else "memory",
                "default_ttl": self.default_ttl
            }
            
            if self.redis_client:
                # Redis 統計
                info = await self.redis_client.info()
                stats.update({
                    "redis_memory_used": info.get("used_memory_human", "unknown"),
                    "redis_connected_clients": info.get("connected_clients", 0),
                    "redis_total_commands": info.get("total_commands_processed", 0)
                })
            else:
                # 內存快取統計
                stats.update({
                    "memory_cache_size": len(self.memory_cache),
                    "memory_cache_max_size": self.max_memory_cache_size
                })
            
            return stats
            
        except Exception as e:
            logger.error("Failed to get cache stats", error=str(e))
            return {"error": str(e)}
    
    def _generate_query_cache_key(self, query_params: Dict[str, Any]) -> str:
        """生成查詢快取鍵"""
        
        # 創建標準化的查詢參數字符串
        normalized_params = {
            "metrics": sorted(query_params.get("metrics", [])),
            "dimensions": sorted(query_params.get("dimensions", [])),
            "date_ranges": query_params.get("date_ranges", []),
            "property_id": query_params.get("property_id", ""),
            "limit": query_params.get("limit", 10)
        }
        
        # 生成 MD5 雜湊
        params_str = json.dumps(normalized_params, sort_keys=True, ensure_ascii=False)
        return hashlib.md5(params_str.encode('utf-8')).hexdigest()
    
    def _cleanup_memory_cache(self):
        """清理內存快取"""
        
        try:
            current_time = datetime.now()
            keys_to_delete = []
            
            # 找出過期的項目
            for key, entry in self.memory_cache.items():
                if current_time > entry["expires_at"]:
                    keys_to_delete.append(key)
            
            # 刪除過期項目
            for key in keys_to_delete:
                del self.memory_cache[key]
            
            # 如果還是太多，刪除最舊的項目
            if len(self.memory_cache) >= self.max_memory_cache_size:
                # 按創建時間排序，刪除最舊的 25%
                items = list(self.memory_cache.items())
                items.sort(key=lambda x: x[1]["created_at"])
                
                num_to_delete = len(items) // 4
                for i in range(num_to_delete):
                    del self.memory_cache[items[i][0]]
            
            logger.info("Memory cache cleaned up", 
                       expired_items=len(keys_to_delete),
                       current_size=len(self.memory_cache))
            
        except Exception as e:
            logger.error("Failed to cleanup memory cache", error=str(e))
    
    def _match_pattern(self, key: str, pattern: str) -> bool:
        """簡單的模式匹配（支持 * 通配符）"""
        
        import re
        
        # 將 * 轉換為正則表達式
        regex_pattern = pattern.replace("*", ".*")
        return re.match(regex_pattern, key) is not None
    
    async def health_check(self) -> Dict[str, Any]:
        """
        快取服務健康檢查
        
        Returns:
            健康狀態
        """
        try:
            health_status = {
                "status": "healthy",
                "redis_available": REDIS_AVAILABLE,
                "redis_connected": False
            }
            
            if self.redis_client:
                # 測試 Redis 連接
                await self.redis_client.ping()
                health_status["redis_connected"] = True
                health_status["message"] = "Redis connection successful"
            else:
                health_status["message"] = "Using memory cache (Redis not available)"
            
            return health_status
            
        except Exception as e:
            logger.error("Cache health check failed", error=str(e))
            return {
                "status": "unhealthy",
                "redis_available": REDIS_AVAILABLE,
                "redis_connected": False,
                "error": str(e)
            }
    
    async def close(self):
        """關閉快取連接"""
        
        try:
            if self.redis_client:
                await self.redis_client.close()
                logger.info("Redis connection closed")
        except Exception as e:
            logger.error("Failed to close Redis connection", error=str(e)) 