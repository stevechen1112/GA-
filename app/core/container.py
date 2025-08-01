"""
依賴注入容器

使用依賴注入模式管理服務實例
"""

from typing import Dict, Any, Type, Optional, Callable
from functools import lru_cache
import structlog

from app.core.config import settings
from app.services.cache_service_v2 import OptimizedCacheService
from app.services.llm_service_v2 import OptimizedLLMService
from app.services.ga4_service_v2 import OptimizedGA4Service
from app.services.query_parser import QueryParser
from app.services.smart_router import SmartRouter
from app.services.trend_analysis import TrendAnalysisService
from app.services.bigquery_service import BigQueryService

logger = structlog.get_logger()


class ServiceContainer:
    """服務容器 - 管理所有服務實例"""
    
    def __init__(self):
        self._services: Dict[str, Any] = {}
        self._factories: Dict[str, Callable] = {}
        self._singletons: Dict[str, Any] = {}
        
        # 註冊默認服務
        self._register_default_services()
    
    def _register_default_services(self):
        """註冊默認服務"""
        # 註冊單例服務
        self.register_singleton("cache_service", OptimizedCacheService)
        self.register_singleton("llm_service", lambda: OptimizedLLMService(
            max_concurrent_requests=settings.get("LLM_MAX_CONCURRENT", 5)
        ))
        self.register_singleton("ga4_service", OptimizedGA4Service)
        self.register_singleton("bigquery_service", BigQueryService)
        
        # 註冊工廠服務（每次創建新實例）
        self.register_factory("query_parser", QueryParser)
        self.register_factory("trend_analysis", TrendAnalysisService)
        
        # 註冊需要依賴的服務
        self.register_factory("smart_router", self._create_smart_router)
    
    def register_singleton(self, name: str, factory: Callable):
        """
        註冊單例服務
        
        Args:
            name: 服務名稱
            factory: 服務工廠函數
        """
        self._factories[name] = factory
        self._singletons[name] = None
    
    def register_factory(self, name: str, factory: Callable):
        """
        註冊工廠服務（每次調用創建新實例）
        
        Args:
            name: 服務名稱
            factory: 服務工廠函數
        """
        self._factories[name] = factory
    
    def register_instance(self, name: str, instance: Any):
        """
        直接註冊服務實例
        
        Args:
            name: 服務名稱
            instance: 服務實例
        """
        self._services[name] = instance
    
    def get(self, name: str) -> Any:
        """
        獲取服務實例
        
        Args:
            name: 服務名稱
            
        Returns:
            服務實例
            
        Raises:
            KeyError: 服務未註冊
        """
        # 檢查是否有直接註冊的實例
        if name in self._services:
            return self._services[name]
        
        # 檢查是否為單例
        if name in self._singletons:
            if self._singletons[name] is None:
                # 創建單例實例
                factory = self._factories.get(name)
                if factory:
                    self._singletons[name] = factory()
                    logger.info(f"Created singleton service: {name}")
            return self._singletons[name]
        
        # 使用工廠創建新實例
        if name in self._factories:
            return self._factories[name]()
        
        raise KeyError(f"Service '{name}' not registered")
    
    def _create_smart_router(self) -> SmartRouter:
        """創建智能路由器（帶依賴注入）"""
        from app.services.smart_router import SmartRouter
        
        router = SmartRouter()
        # 注入依賴
        router.ga4_service = self.get("ga4_service")
        router.bigquery_service = self.get("bigquery_service")
        router.cache_service = self.get("cache_service")
        router.trend_analysis = self.get("trend_analysis")
        
        return router
    
    def reset(self):
        """重置所有服務（用於測試）"""
        self._services.clear()
        self._singletons.clear()
        for name in self._singletons:
            self._singletons[name] = None


# 創建全局容器實例
container = ServiceContainer()


# 依賴注入裝飾器
def inject(**dependencies):
    """
    依賴注入裝飾器
    
    Usage:
        @inject(cache_service='cache_service', llm_service='llm_service')
        async def my_function(data, cache_service=None, llm_service=None):
            # cache_service 和 llm_service 會自動注入
            pass
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # 注入依賴
            for param_name, service_name in dependencies.items():
                if param_name not in kwargs or kwargs[param_name] is None:
                    kwargs[param_name] = container.get(service_name)
            
            return func(*args, **kwargs)
        
        # 保留原函數的元數據
        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        wrapper.__annotations__ = func.__annotations__
        
        return wrapper
    
    return decorator


# FastAPI 依賴提供者
class DependencyProvider:
    """FastAPI 依賴提供者"""
    
    @staticmethod
    @lru_cache()
    def get_cache_service() -> OptimizedCacheService:
        """獲取快取服務"""
        return container.get("cache_service")
    
    @staticmethod
    @lru_cache()
    def get_llm_service() -> OptimizedLLMService:
        """獲取 LLM 服務"""
        return container.get("llm_service")
    
    @staticmethod
    @lru_cache()
    def get_ga4_service() -> OptimizedGA4Service:
        """獲取 GA4 服務"""
        return container.get("ga4_service")
    
    @staticmethod
    def get_query_parser() -> QueryParser:
        """獲取查詢解析器（每次新實例）"""
        return container.get("query_parser")
    
    @staticmethod
    def get_smart_router() -> SmartRouter:
        """獲取智能路由器"""
        return container.get("smart_router")
    
    @staticmethod
    def get_trend_analysis() -> TrendAnalysisService:
        """獲取趨勢分析服務"""
        return container.get("trend_analysis")


# 服務定位器模式（簡化訪問）
class ServiceLocator:
    """服務定位器 - 提供靜態方法訪問服務"""
    
    @staticmethod
    def cache() -> OptimizedCacheService:
        return container.get("cache_service")
    
    @staticmethod
    def llm() -> OptimizedLLMService:
        return container.get("llm_service")
    
    @staticmethod
    def ga4() -> OptimizedGA4Service:
        return container.get("ga4_service")
    
    @staticmethod
    def query_parser() -> QueryParser:
        return container.get("query_parser")
    
    @staticmethod
    def smart_router() -> SmartRouter:
        return container.get("smart_router")


# 上下文管理器（用於測試）
class ServiceScope:
    """服務作用域 - 用於隔離測試"""
    
    def __init__(self, overrides: Optional[Dict[str, Any]] = None):
        self.overrides = overrides or {}
        self.original_services = {}
    
    def __enter__(self):
        # 保存原始服務
        for name, service in self.overrides.items():
            if name in container._services:
                self.original_services[name] = container._services[name]
            container.register_instance(name, service)
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # 恢復原始服務
        for name in self.overrides:
            if name in self.original_services:
                container.register_instance(name, self.original_services[name])
            elif name in container._services:
                del container._services[name]