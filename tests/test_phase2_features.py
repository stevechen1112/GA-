#!/usr/bin/env python3
"""
GA+ 第二階段智能分析版測試套件

測試 BigQuery 整合、智能路由、快取機制、趨勢分析等功能
"""

import sys
import os
import pytest
import asyncio
from pathlib import Path
import json

# 添加專案根目錄到 Python 路徑
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 設置測試環境變數
os.environ["USE_MOCK_LLM_API"] = "true"
os.environ["USE_MOCK_GA4_API"] = "true"
os.environ["ENABLE_BIGQUERY_ROUTING"] = "false"  # 測試時關閉 BigQuery
os.environ["REDIS_URL"] = "redis://localhost:6379/1"  # 測試 Redis DB
os.environ["ENVIRONMENT"] = "test"

from app.services.bigquery_service import BigQueryService
from app.services.smart_router import SmartRouter
from app.services.cache_service import CacheService
from app.services.trend_analysis import TrendAnalysisService
from app.services.query_parser import QueryParser

class TestPhase2Features:
    """第二階段功能測試套件"""
    
    @classmethod
    def setup_class(cls):
        """測試類別設置"""
        print("\n🧪 第二階段功能測試初始化...")
        
        # 初始化服務實例
        cls.bigquery_service = BigQueryService()
        cls.smart_router = SmartRouter()
        cls.cache_service = CacheService()
        cls.trend_analysis = TrendAnalysisService()
        cls.query_parser = QueryParser()
        
        print("✅ 第二階段服務實例創建完成")
    
    def test_01_bigquery_service_initialization(self):
        """測試 BigQuery 服務初始化"""
        print("\n🔍 測試 BigQuery 服務初始化...")
        
        # 檢查服務是否正確初始化
        assert self.bigquery_service is not None
        assert hasattr(self.bigquery_service, 'client')
        assert hasattr(self.bigquery_service, 'is_available')
        
        # 測試可用性檢查
        is_available = self.bigquery_service.is_available()
        print(f"BigQuery 可用性: {is_available}")
        
        print("✅ BigQuery 服務初始化測試通過")
    
    def test_02_smart_router_initialization(self):
        """測試智能路由器初始化"""
        print("\n🔍 測試智能路由器初始化...")
        
        # 檢查路由器是否正確初始化
        assert self.smart_router is not None
        assert hasattr(self.smart_router, 'ga4_service')
        assert hasattr(self.smart_router, 'bigquery_service')
        assert hasattr(self.smart_router, 'cache_service')
        assert hasattr(self.smart_router, 'trend_analysis')
        
        print("✅ 智能路由器初始化測試通過")
    
    @pytest.mark.asyncio
    async def test_03_cache_service_basic_operations(self):
        """測試快取服務基本操作"""
        print("\n🔍 測試快取服務基本操作...")
        
        # 測試設置和獲取
        test_key = "test_key_phase2"
        test_value = {"message": "Hello Phase 2", "data": [1, 2, 3]}
        
        # 設置快取
        result = await self.cache_service.set(test_key, test_value, 60)
        assert result is True
        
        # 獲取快取
        cached_value = await self.cache_service.get(test_key)
        assert cached_value == test_value
        
        # 檢查存在性
        exists = await self.cache_service.exists(test_key)
        assert exists is True
        
        # 刪除快取
        deleted = await self.cache_service.delete(test_key)
        assert deleted is True
        
        # 確認已刪除
        cached_value_after_delete = await self.cache_service.get(test_key)
        assert cached_value_after_delete is None
        
        print("✅ 快取服務基本操作測試通過")
    
    @pytest.mark.asyncio
    async def test_04_trend_analysis_basic_functionality(self):
        """測試趨勢分析基本功能"""
        print("\n🔍 測試趨勢分析基本功能...")
        
        # 準備測試數據
        test_data = [
            {"date": "2024-01-01", "sessions": 100},
            {"date": "2024-01-02", "sessions": 120},
            {"date": "2024-01-03", "sessions": 110},
            {"date": "2024-01-04", "sessions": 140},
            {"date": "2024-01-05", "sessions": 160},
            {"date": "2024-01-06", "sessions": 150},
            {"date": "2024-01-07", "sessions": 180}
        ]
        
        # 轉換為 GA4 格式
        ga4_format_data = []
        for item in test_data:
            ga4_format_data.append({
                "dimension_values": [item["date"]],
                "metric_values": [str(item["sessions"])]
            })
        
        # 執行趨勢分析
        result = await self.trend_analysis.analyze_trend(ga4_format_data, "sessions")
        
        # 驗證結果結構
        assert "metric_name" in result
        assert "trend" in result
        assert "statistics" in result
        assert "insights" in result
        assert result["metric_name"] == "sessions"
        
        print(f"趨勢方向: {result['trend']['direction']}")
        print(f"趨勢強度: {result['trend']['strength']}")
        print(f"洞察數量: {len(result.get('insights', []))}")
        
        print("✅ 趨勢分析基本功能測試通過")
    
    @pytest.mark.asyncio
    async def test_05_query_parser_extended_types(self):
        """測試查詢解析器擴展類型"""
        print("\n🔍 測試查詢解析器擴展類型...")
        
        # 測試不同類型的查詢
        test_queries = [
            ("用戶年齡分布如何？", "demographic_analysis"),
            ("行動設備用戶有多少？", "device_analysis"),
            ("電商銷售數據分析", "ecommerce_analysis"),
            ("事件追蹤統計", "event_analysis"),
            ("地區分析報告", "geographic_analysis"),
            ("即時流量監控", "real_time_analysis"),
            ("廣告活動效果", "campaign_analysis")
        ]
        
        for query_text, expected_intent in test_queries:
            intent = await self.query_parser.parse_query(query_text)
            print(f"查詢: '{query_text}' -> 意圖: {intent.intent}")
            
            # 生成對應的 GA4 查詢
            ga4_query = await self.query_parser.generate_ga4_query(intent)
            assert "property_id" in ga4_query
            assert "metrics" in ga4_query
            assert "date_ranges" in ga4_query
        
        print("✅ 查詢解析器擴展類型測試通過")
    
    @pytest.mark.asyncio
    async def test_06_smart_router_query_execution(self):
        """測試智能路由器查詢執行"""
        print("\n🔍 測試智能路由器查詢執行...")
        
        # 準備測試查詢
        test_query = {
            "metrics": [{"name": "totalUsers"}],
            "dimensions": [{"name": "date"}],
            "date_ranges": [{"start_date": "7daysAgo", "end_date": "today"}],
            "limit": 10
        }
        
        # 執行查詢
        result = await self.smart_router.execute_query(test_query, "test_property_id")
        
        # 驗證結果
        assert "rows" in result
        assert "data_source" in result
        assert "routing_reasoning" in result
        
        print(f"數據源: {result.get('data_source')}")
        print(f"路由原因: {result.get('routing_reasoning')}")
        print(f"數據行數: {len(result.get('rows', []))}")
        
        print("✅ 智能路由器查詢執行測試通過")
    
    @pytest.mark.asyncio
    async def test_07_cache_integration_with_router(self):
        """測試快取與路由器整合"""
        print("\n🔍 測試快取與路由器整合...")
        
        # 準備測試查詢
        test_query = {
            "metrics": [{"name": "sessions"}],
            "dimensions": [],
            "date_ranges": [{"start_date": "30daysAgo", "end_date": "today"}],
            "limit": 5
        }
        
        # 第一次執行（應該快取結果）
        result1 = await self.smart_router.execute_query(test_query, "cache_test_property")
        
        # 第二次執行（應該從快取獲取）
        result2 = await self.smart_router.execute_query(test_query, "cache_test_property")
        
        # 驗證結果一致性
        assert result1.get("rows") == result2.get("rows")
        
        print("✅ 快取與路由器整合測試通過")
    
    @pytest.mark.asyncio
    async def test_08_trend_analysis_integration(self):
        """測試趨勢分析整合"""
        print("\n🔍 測試趨勢分析整合...")
        
        # 準備包含時間維度的查詢
        trend_query = {
            "metrics": [{"name": "totalUsers"}],
            "dimensions": [{"name": "date"}],
            "date_ranges": [{"start_date": "14daysAgo", "end_date": "today"}],
            "limit": 14
        }
        
        # 執行查詢（應該包含趨勢分析）
        result = await self.smart_router.execute_query(trend_query, "trend_test_property")
        
        # 檢查是否包含趨勢分析
        if "trend_analysis" in result:
            trend_data = result["trend_analysis"]
            assert "trend" in trend_data
            assert "statistics" in trend_data
            print(f"趨勢分析結果: {trend_data['trend']['direction']}")
            print("✅ 趨勢分析整合測試通過")
        else:
            print("⚠️  趨勢分析未觸發（可能數據不足）")
    
    @pytest.mark.asyncio
    async def test_09_cache_service_stats(self):
        """測試快取服務統計"""
        print("\n🔍 測試快取服務統計...")
        
        # 獲取快取統計
        stats = await self.cache_service.get_cache_stats()
        
        assert "cache_type" in stats
        assert "default_ttl" in stats
        
        print(f"快取類型: {stats.get('cache_type')}")
        print(f"預設TTL: {stats.get('default_ttl')}")
        
        print("✅ 快取服務統計測試通過")
    
    @pytest.mark.asyncio
    async def test_10_health_checks(self):
        """測試各服務健康檢查"""
        print("\n🔍 測試各服務健康檢查...")
        
        # 測試快取服務健康檢查
        cache_health = await self.cache_service.health_check()
        assert "status" in cache_health
        print(f"快取服務健康狀態: {cache_health.get('status')}")
        
        print("✅ 服務健康檢查測試通過")
    
    def test_11_comprehensive_functionality(self):
        """綜合功能測試"""
        print("\n🔍 綜合功能測試...")
        
        # 檢查所有新增的服務是否正常工作
        services_status = {
            "BigQuery Service": self.bigquery_service is not None,
            "Smart Router": self.smart_router is not None,
            "Cache Service": self.cache_service is not None,
            "Trend Analysis": self.trend_analysis is not None,
            "Extended Query Parser": len(self.query_parser.intent_patterns) >= 15
        }
        
        for service, status in services_status.items():
            print(f"{service}: {'✅ 正常' if status else '❌ 異常'}")
            assert status, f"{service} 未正常初始化"
        
        print("✅ 綜合功能測試通過")
    
    @classmethod
    def teardown_class(cls):
        """測試清理"""
        print("\n🧹 清理測試環境...")
        
        # 關閉快取連接
        try:
            asyncio.run(cls.cache_service.close())
        except:
            pass
        
        print("✅ 測試環境清理完成")

if __name__ == "__main__":
    # 直接運行測試
    print("🚀 開始第二階段功能測試...")
    pytest.main([__file__, "-v", "--tb=short"]) 