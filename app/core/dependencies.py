"""
GA+ 依賴注入工廠函數

提供 FastAPI 依賴注入所需的工廠函數
"""

from functools import lru_cache
from typing import Generator
from sqlalchemy.orm import Session

from app.core.container import DependencyProvider, container
from app.core.database import get_db


# 使用新的依賴提供者
get_query_parser = DependencyProvider.get_query_parser


get_ga4_service = DependencyProvider.get_ga4_service


get_llm_service = DependencyProvider.get_llm_service


# BigQuery 服務
def get_bigquery_service():
    return container.get("bigquery_service")


get_smart_router = DependencyProvider.get_smart_router


get_cache_service = DependencyProvider.get_cache_service


get_trend_analysis = DependencyProvider.get_trend_analysis


# 資料庫連接依賴
def get_database() -> Generator[Session, None, None]:
    """
    獲取資料庫連接
    
    Yields:
        資料庫會話
    """
    yield from get_db()


# Redis 連接依賴
def get_redis():
    """
    獲取 Redis 連接
    
    Returns:
        Redis 客戶端實例
    """
    cache_service = container.get("cache_service")
    return cache_service.redis_client if hasattr(cache_service, 'redis_client') else None 