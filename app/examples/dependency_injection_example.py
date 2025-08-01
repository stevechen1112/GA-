"""
依賴注入架構使用範例

展示如何使用新的依賴注入系統
"""

from app.core.container import container, inject, ServiceScope, ServiceLocator


# 範例 1: 使用裝飾器注入依賴
@inject(cache_service='cache_service', llm_service='llm_service')
async def process_data(data: dict, cache_service=None, llm_service=None):
    """
    處理數據的函數，依賴會自動注入
    """
    # 檢查快取
    cached_result = await cache_service.get(data['key'])
    if cached_result:
        return cached_result
    
    # 使用 LLM 處理
    result = await llm_service.generate_completion(data['prompt'])
    
    # 儲存到快取
    await cache_service.set(data['key'], result)
    
    return result


# 範例 2: 使用服務定位器
async def quick_access_example():
    """使用服務定位器快速訪問服務"""
    # 直接訪問服務
    cache = ServiceLocator.cache()
    llm = ServiceLocator.llm()
    ga4 = ServiceLocator.ga4()
    
    # 使用服務
    await cache.set("test_key", "test_value")
    response = await llm.generate_completion("Hello")
    data = await ga4.execute_query({"metrics": [{"name": "sessions"}]})


# 範例 3: 在 FastAPI 路由中使用
from fastapi import APIRouter, Depends
from app.core.dependencies import get_cache_service, get_llm_service

router = APIRouter()

@router.get("/example")
async def example_endpoint(
    cache_service = Depends(get_cache_service),
    llm_service = Depends(get_llm_service)
):
    """FastAPI 端點使用依賴注入"""
    # 服務已自動注入
    cached_data = await cache_service.get("example_key")
    return {"cached": cached_data is not None}


# 範例 4: 測試中使用服務作用域
import pytest

@pytest.mark.asyncio
async def test_with_mock_services():
    """使用模擬服務進行測試"""
    
    # 創建模擬服務
    class MockCacheService:
        async def get(self, key):
            return "mock_value"
        
        async def set(self, key, value):
            return True
    
    class MockLLMService:
        async def generate_completion(self, prompt):
            return "Mock response"
    
    # 使用服務作用域替換真實服務
    with ServiceScope({
        'cache_service': MockCacheService(),
        'llm_service': MockLLMService()
    }):
        # 在此作用域內，服務被替換為模擬版本
        result = await process_data({
            'key': 'test',
            'prompt': 'Test prompt'
        })
        
        assert result == "Mock response"


# 範例 5: 註冊自定義服務
class CustomAnalyticsService:
    """自定義分析服務"""
    
    def __init__(self, config: dict):
        self.config = config
    
    async def analyze(self, data):
        return f"Analyzed: {data}"


# 註冊自定義服務
container.register_singleton(
    "custom_analytics",
    lambda: CustomAnalyticsService({"mode": "advanced"})
)

# 使用自定義服務
@inject(analytics='custom_analytics')
async def use_custom_service(data, analytics=None):
    return await analytics.analyze(data)


# 範例 6: 配置驅動的服務創建
def configure_services(config: dict):
    """根據配置創建服務"""
    
    # 根據配置決定 LLM 服務參數
    if config.get('environment') == 'production':
        container.register_singleton(
            'llm_service',
            lambda: OptimizedLLMService(max_concurrent_requests=10)
        )
    else:
        container.register_singleton(
            'llm_service',
            lambda: OptimizedLLMService(max_concurrent_requests=2)
        )


# 範例 7: 服務生命週期管理
async def application_startup():
    """應用程式啟動時初始化服務"""
    # 預熱服務
    cache = container.get('cache_service')
    await cache.health_check()
    
    llm = container.get('llm_service')
    await llm.health_check()
    
    print("All services initialized successfully")


async def application_shutdown():
    """應用程式關閉時清理服務"""
    # 關閉連接
    cache = container.get('cache_service')
    await cache.close()
    
    print("All services cleaned up")


if __name__ == "__main__":
    import asyncio
    
    # 運行範例
    async def main():
        await application_startup()
        
        # 使用服務
        result = await process_data({
            'key': 'example',
            'prompt': 'What is dependency injection?'
        })
        print(f"Result: {result}")
        
        await application_shutdown()
    
    asyncio.run(main())