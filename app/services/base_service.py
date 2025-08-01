"""
基礎服務類別

提供共用的服務功能
"""

from typing import Dict, Any, Optional
import structlog
from abc import ABC, abstractmethod

from app.utils.common import HashHelper, measure_time, retry_async

logger = structlog.get_logger()


class BaseService(ABC):
    """所有服務的基礎類別"""
    
    def __init__(self):
        self.logger = structlog.get_logger(self.__class__.__name__)
        self._stats = {
            "requests": 0,
            "errors": 0,
            "total_time": 0.0
        }
    
    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """健康檢查（子類必須實現）"""
        pass
    
    async def get_stats(self) -> Dict[str, Any]:
        """獲取服務統計信息"""
        return {
            "service": self.__class__.__name__,
            "requests": self._stats["requests"],
            "errors": self._stats["errors"],
            "error_rate": self._stats["errors"] / self._stats["requests"] 
                         if self._stats["requests"] > 0 else 0,
            "avg_response_time": self._stats["total_time"] / self._stats["requests"]
                                if self._stats["requests"] > 0 else 0
        }
    
    def _track_request(self, elapsed_time: float, error: bool = False):
        """追蹤請求統計"""
        self._stats["requests"] += 1
        self._stats["total_time"] += elapsed_time
        if error:
            self._stats["errors"] += 1
    
    def _log_operation(self, operation: str, **kwargs):
        """記錄操作日誌"""
        self.logger.info(f"{operation} started", **kwargs)
    
    def _log_error(self, operation: str, error: Exception, **kwargs):
        """記錄錯誤日誌"""
        self.logger.error(
            f"{operation} failed",
            error=str(error),
            error_type=error.__class__.__name__,
            **kwargs
        )


class CacheableService(BaseService):
    """支援快取的服務基類"""
    
    def __init__(self, cache_service=None):
        super().__init__()
        self.cache_service = cache_service
        self.cache_enabled = cache_service is not None
        self.cache_prefix = self.__class__.__name__.lower()
    
    def _generate_cache_key(self, data: Dict[str, Any], prefix: str = "") -> str:
        """生成快取鍵（使用共用工具）"""
        full_prefix = f"{self.cache_prefix}:{prefix}" if prefix else self.cache_prefix
        return HashHelper.generate_cache_key(data, full_prefix)
    
    async def _get_from_cache(self, key: str) -> Optional[Any]:
        """從快取獲取數據"""
        if not self.cache_enabled:
            return None
        
        try:
            return await self.cache_service.get(key)
        except Exception as e:
            self._log_error("Cache get", e, key=key)
            return None
    
    async def _set_to_cache(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """設置快取數據"""
        if not self.cache_enabled:
            return False
        
        try:
            return await self.cache_service.set(key, value, ttl)
        except Exception as e:
            self._log_error("Cache set", e, key=key)
            return False
    
    @measure_time
    @retry_async(max_attempts=3)
    async def execute_with_cache(
        self,
        operation: str,
        params: Dict[str, Any],
        ttl: Optional[int] = None,
        force_refresh: bool = False
    ) -> Any:
        """
        帶快取的執行操作
        
        Args:
            operation: 操作名稱
            params: 參數
            ttl: 快取時間
            force_refresh: 是否強制刷新
            
        Returns:
            操作結果
        """
        # 生成快取鍵
        cache_key = self._generate_cache_key(params, operation)
        
        # 如果不強制刷新，嘗試從快取獲取
        if not force_refresh:
            cached_result = await self._get_from_cache(cache_key)
            if cached_result is not None:
                self._log_operation(f"{operation} cache hit", cache_key=cache_key)
                return cached_result
        
        # 執行實際操作
        try:
            # 子類應該實現 _execute_operation 方法
            result = await self._execute_operation(operation, params)
            
            # 快取結果
            await self._set_to_cache(cache_key, result, ttl)
            
            return result
            
        except Exception as e:
            self._track_request(0, error=True)
            raise
    
    @abstractmethod
    async def _execute_operation(self, operation: str, params: Dict[str, Any]) -> Any:
        """執行實際操作（子類必須實現）"""
        pass


class ConfigurableService(BaseService):
    """可配置的服務基類"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__()
        self.config = config
        self._validate_config()
    
    def _validate_config(self):
        """驗證配置（子類可覆寫）"""
        pass
    
    def get_config_value(self, key: str, default: Any = None) -> Any:
        """獲取配置值"""
        return self.config.get(key, default)
    
    def update_config(self, updates: Dict[str, Any]):
        """更新配置"""
        self.config.update(updates)
        self._validate_config()
        self._log_operation("Config updated", updates=updates)