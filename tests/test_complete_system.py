#!/usr/bin/env python3
"""
GA+ 完整系統測試套件

驗證第一階段MVP的所有功能
"""

import sys
import os
import pytest
import asyncio
from pathlib import Path
from fastapi.testclient import TestClient
import json

# 添加專案根目錄到 Python 路徑
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 強制設置測試環境變數
os.environ["USE_MOCK_LLM_API"] = "true"
os.environ["USE_MOCK_GA4_API"] = "true"
os.environ["DATABASE_URL"] = "sqlite:///./test_ga_plus.db"
os.environ["ENVIRONMENT"] = "test"

from app.main import app
from app.core.database import create_tables, drop_tables

class TestGA_Plus_MVP:
    """GA+ MVP 完整測試套件"""
    
    @classmethod
    def setup_class(cls):
        """測試類別設置"""
        print("\n🧪 初始化測試環境...")
        
        # 初始化測試資料庫
        try:
            drop_tables()
            create_tables()
            print("✅ 測試資料庫初始化完成")
        except Exception as e:
            print(f"⚠️  資料庫初始化警告: {e}")
        
        # 創建測試客戶端
        cls.client = TestClient(app)
        print("✅ 測試客戶端創建完成")
    
    def test_01_health_check(self):
        """測試健康檢查端點"""
        print("\n📋 測試 1: 健康檢查")
        
        response = self.client.get("/api/v1/health/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "version" in data
        
        print("✅ 健康檢查通過")
    
    def test_02_detailed_health_check(self):
        """測試詳細健康檢查"""
        print("\n📋 測試 2: 詳細健康檢查")
        
        response = self.client.get("/api/v1/health/detailed")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["healthy", "degraded"]
        assert "services" in data
        assert "database" in data["services"]
        assert "ga4_api" in data["services"]
        assert "llm_api" in data["services"]
        
        print("✅ 詳細健康檢查通過")
    
    def test_03_api_status(self):
        """測試API狀態端點"""
        print("\n📋 測試 3: API 狀態")
        
        response = self.client.get("/api/v1/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data["api_version"] == "v1"
        assert data["status"] == "operational"
        assert "features" in data
        
        print("✅ API 狀態檢查通過")
    
    def test_04_supported_queries(self):
        """測試支援的查詢類型"""
        print("\n📋 測試 4: 支援的查詢類型")
        
        response = self.client.get("/api/v1/chat/supported-queries")
        
        assert response.status_code == 200
        data = response.json()
        assert "query_types" in data
        assert len(data["query_types"]) >= 5
        
        # 檢查必要的查詢類型
        query_types = [qt["type"] for qt in data["query_types"]]
        required_types = ["basic_metrics", "page_analysis", "traffic_sources"]
        for req_type in required_types:
            assert req_type in query_types
        
        print("✅ 支援的查詢類型檢查通過")
    
    def test_05_chat_basic_metrics(self):
        """測試基本指標聊天功能"""
        print("\n📋 測試 5: 基本指標聊天")
        
        request_data = {
            "message": "昨天有多少訪客？",
            "property_id": "demo_property",
            "date_range": "last_30_days"
        }
        
        response = self.client.post("/api/v1/chat/", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        # 檢查回應結構
        assert "response" in data
        assert "confidence" in data
        assert "query_type" in data
        assert "execution_time" in data
        assert "suggestions" in data
        
        # 檢查回應內容不是錯誤訊息
        assert "抱歉" not in data["response"] or "訪客" in data["response"]
        assert data["confidence"] > 0.5
        
        print(f"✅ 基本指標聊天通過 (信心度: {data['confidence']:.2f})")
    
    def test_06_chat_page_analysis(self):
        """測試頁面分析聊天功能"""
        print("\n📋 測試 6: 頁面分析聊天")
        
        request_data = {
            "message": "最熱門的頁面是什麼？",
            "property_id": "demo_property",
            "date_range": "last_30_days"
        }
        
        response = self.client.post("/api/v1/chat/", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "response" in data
        assert data["confidence"] > 0.5
        assert "頁面" in data["response"] or "page" in data["response"].lower()
        
        print(f"✅ 頁面分析聊天通過 (信心度: {data['confidence']:.2f})")
    
    def test_07_chat_traffic_sources(self):
        """測試流量來源聊天功能"""
        print("\n📋 測試 7: 流量來源聊天")
        
        request_data = {
            "message": "主要流量來源有哪些？",
            "property_id": "demo_property",
            "date_range": "last_30_days"
        }
        
        response = self.client.post("/api/v1/chat/", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "response" in data
        assert data["confidence"] > 0.5
        assert any(keyword in data["response"] for keyword in ["流量", "來源", "source", "traffic"])
        
        print(f"✅ 流量來源聊天通過 (信心度: {data['confidence']:.2f})")
    
    def test_08_analytics_properties(self):
        """測試分析屬性端點"""
        print("\n📋 測試 8: 分析屬性")
        
        response = self.client.get("/api/v1/analytics/properties")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "properties" in data
        assert "total" in data
        assert len(data["properties"]) > 0
        
        # 檢查屬性結構
        prop = data["properties"][0]
        assert "id" in prop
        assert "name" in prop
        
        print("✅ 分析屬性檢查通過")
    
    def test_09_analytics_metrics(self):
        """測試分析指標端點"""
        print("\n📋 測試 9: 分析指標")
        
        response = self.client.get("/api/v1/analytics/metrics")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "metrics" in data
        assert "total_categories" in data
        
        # 檢查指標分類
        metrics = data["metrics"]
        assert "user_metrics" in metrics
        assert "session_metrics" in metrics
        assert len(metrics["user_metrics"]) > 0
        
        print("✅ 分析指標檢查通過")
    
    def test_10_analytics_dimensions(self):
        """測試分析維度端點"""
        print("\n📋 測試 10: 分析維度")
        
        response = self.client.get("/api/v1/analytics/dimensions")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "dimensions" in data
        assert "total_categories" in data
        
        # 檢查維度分類
        dimensions = data["dimensions"]
        assert "user_dimensions" in dimensions
        assert "page_dimensions" in dimensions
        
        print("✅ 分析維度檢查通過")
    
    def test_11_user_registration(self):
        """測試用戶註冊"""
        print("\n📋 測試 11: 用戶註冊")
        
        user_data = {
            "email": "test@example.com",
            "name": "測試用戶",
            "company": "測試公司",
            "password": "testpassword123"
        }
        
        response = self.client.post("/api/v1/users/register", json=user_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "id" in data
        assert data["email"] == user_data["email"]
        assert data["name"] == user_data["name"]
        assert data["subscription_tier"] == "free"
        assert "password" not in data  # 密碼不應該返回
        
        print("✅ 用戶註冊通過")
    
    def test_12_user_login(self):
        """測試用戶登入"""
        print("\n📋 測試 12: 用戶登入")
        
        login_data = {
            "email": "test@example.com",
            "password": "testpassword123"
        }
        
        response = self.client.post("/api/v1/users/login", json=login_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "access_token" in data
        assert "token_type" in data
        assert data["token_type"] == "bearer"
        assert "user" in data
        assert data["user"]["email"] == login_data["email"]
        
        print("✅ 用戶登入通過")
    
    def test_13_query_parser_test(self):
        """測試查詢解析器"""
        print("\n📋 測試 13: 查詢解析器")
        
        test_data = {
            "message": "昨天有多少新用戶？"
        }
        
        response = self.client.post("/api/v1/chat/test-query", json=test_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "original_query" in data
        assert "parsed_intent" in data
        assert "generated_ga4_query" in data
        assert data["status"] == "success"
        
        print("✅ 查詢解析器測試通過")
    
    def test_14_error_handling(self):
        """測試錯誤處理"""
        print("\n📋 測試 14: 錯誤處理")
        
        # 測試無效的聊天請求
        invalid_request = {
            "message": "",  # 空訊息
            "property_id": "invalid_property"
        }
        
        response = self.client.post("/api/v1/chat/", json=invalid_request)
        
        # 應該返回錯誤或默認回應
        assert response.status_code in [200, 400, 422]
        
        print("✅ 錯誤處理測試通過")
    
    @classmethod
    def teardown_class(cls):
        """測試類別清理"""
        print("\n🧹 清理測試環境...")
        try:
            # 清理測試資料庫
            if os.path.exists("test_ga_plus.db"):
                os.remove("test_ga_plus.db")
            print("✅ 測試環境清理完成")
        except Exception as e:
            print(f"⚠️  清理警告: {e}")


def run_complete_test():
    """運行完整測試套件"""
    print("🚀 GA+ MVP 完整測試套件")
    print("=" * 60)
    print("🎯 第一階段功能驗證")
    print("🔧 模擬模式測試")
    print("📊 涵蓋所有核心功能")
    print("=" * 60)
    
    # 運行測試
    pytest_args = [
        __file__,
        "-v",  # 詳細輸出
        "-s",  # 不捕獲 print 輸出
        "--tb=short"  # 簡短的錯誤追蹤
    ]
    
    exit_code = pytest.main(pytest_args)
    
    print("\n" + "=" * 60)
    if exit_code == 0:
        print("🎉 所有測試通過！GA+ MVP 第一階段開發完成！")
        print("✅ 健康檢查功能正常")
        print("✅ 聊天功能正常")
        print("✅ 分析端點正常") 
        print("✅ 用戶管理正常")
        print("✅ 查詢解析正常")
        print("✅ 錯誤處理正常")
    else:
        print("❌ 部分測試失敗，請檢查相關功能")
    
    print("=" * 60)
    return exit_code


if __name__ == "__main__":
    run_complete_test() 