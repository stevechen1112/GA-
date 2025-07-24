#!/usr/bin/env python3
"""
GA+ API 測試腳本

用於測試 API 端點的功能
"""

import asyncio
import httpx
import json
from typing import Dict, Any


class APITester:
    """API 測試器"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.client = httpx.AsyncClient()
    
    async def test_health_endpoint(self) -> bool:
        """測試健康檢查端點"""
        print("🔍 測試健康檢查端點...")
        
        try:
            response = await self.client.get(f"{self.base_url}/health")
            if response.status_code == 200:
                data = response.json()
                print(f"✅ 健康檢查成功: {data}")
                return True
            else:
                print(f"❌ 健康檢查失敗: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ 健康檢查錯誤: {e}")
            return False
    
    async def test_api_status(self) -> bool:
        """測試 API 狀態端點"""
        print("🔍 測試 API 狀態端點...")
        
        try:
            response = await self.client.get(f"{self.base_url}/api/v1/status")
            if response.status_code == 200:
                data = response.json()
                print(f"✅ API 狀態檢查成功: {data}")
                return True
            else:
                print(f"❌ API 狀態檢查失敗: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ API 狀態檢查錯誤: {e}")
            return False
    
    async def test_supported_queries(self) -> bool:
        """測試支援的查詢端點"""
        print("🔍 測試支援的查詢端點...")
        
        try:
            response = await self.client.get(f"{self.base_url}/api/v1/chat/supported-queries")
            if response.status_code == 200:
                data = response.json()
                print(f"✅ 支援的查詢獲取成功，共 {data.get('total_types', 0)} 種類型")
                return True
            else:
                print(f"❌ 支援的查詢獲取失敗: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ 支援的查詢獲取錯誤: {e}")
            return False
    
    async def test_chat_endpoint(self) -> bool:
        """測試聊天端點"""
        print("🔍 測試聊天端點...")
        
        test_queries = [
            "昨天有多少訪客？",
            "最熱門的頁面是什麼？",
            "主要流量來源有哪些？"
        ]
        
        success_count = 0
        
        for query in test_queries:
            try:
                payload = {
                    "message": query,
                    "property_id": "test_property",
                    "date_range": "last_30_days"
                }
                
                response = await self.client.post(
                    f"{self.base_url}/api/v1/chat/",
                    json=payload
                )
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"✅ 查詢 '{query}' 成功")
                    print(f"   回應: {data.get('response', '')[:100]}...")
                    print(f"   信心度: {data.get('confidence', 0)}")
                    success_count += 1
                else:
                    print(f"❌ 查詢 '{query}' 失敗: {response.status_code}")
                    print(f"   錯誤: {response.text}")
                    
            except Exception as e:
                print(f"❌ 查詢 '{query}' 錯誤: {e}")
        
        print(f"📊 聊天測試結果: {success_count}/{len(test_queries)} 成功")
        return success_count > 0
    
    async def test_analytics_endpoints(self) -> bool:
        """測試分析端點"""
        print("🔍 測試分析端點...")
        
        endpoints = [
            "/api/v1/analytics/properties",
            "/api/v1/analytics/metrics",
            "/api/v1/analytics/dimensions"
        ]
        
        success_count = 0
        
        for endpoint in endpoints:
            try:
                response = await self.client.get(f"{self.base_url}{endpoint}")
                if response.status_code == 200:
                    data = response.json()
                    print(f"✅ {endpoint} 測試成功")
                    success_count += 1
                else:
                    print(f"❌ {endpoint} 測試失敗: {response.status_code}")
                    
            except Exception as e:
                print(f"❌ {endpoint} 測試錯誤: {e}")
        
        print(f"📊 分析端點測試結果: {success_count}/{len(endpoints)} 成功")
        return success_count > 0
    
    async def test_user_endpoints(self) -> bool:
        """測試用戶端點"""
        print("🔍 測試用戶端點...")
        
        # 測試用戶註冊
        try:
            register_payload = {
                "email": "test@example.com",
                "password": "testpassword123",
                "name": "Test User",
                "company": "Test Company"
            }
            
            response = await self.client.post(
                f"{self.base_url}/api/v1/users/register",
                json=register_payload
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ 用戶註冊測試成功: {data.get('email', '')}")
                return True
            else:
                print(f"❌ 用戶註冊測試失敗: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ 用戶註冊測試錯誤: {e}")
            return False
    
    async def run_all_tests(self) -> Dict[str, bool]:
        """運行所有測試"""
        print("🚀 開始 API 測試")
        print("=" * 50)
        
        tests = [
            ("健康檢查", self.test_health_endpoint),
            ("API 狀態", self.test_api_status),
            ("支援的查詢", self.test_supported_queries),
            ("聊天功能", self.test_chat_endpoint),
            ("分析端點", self.test_analytics_endpoints),
            ("用戶功能", self.test_user_endpoints)
        ]
        
        results = {}
        
        for test_name, test_func in tests:
            print(f"\n📋 測試: {test_name}")
            print("-" * 30)
            results[test_name] = await test_func()
        
        # 總結
        print("\n" + "=" * 50)
        print("📊 測試總結")
        print("=" * 50)
        
        passed = sum(results.values())
        total = len(results)
        
        for test_name, result in results.items():
            status = "✅ 通過" if result else "❌ 失敗"
            print(f"{test_name}: {status}")
        
        print(f"\n總體結果: {passed}/{total} 測試通過")
        
        if passed == total:
            print("🎉 所有測試通過！API 運行正常。")
        else:
            print("⚠️  部分測試失敗，請檢查相關功能。")
        
        return results
    
    async def close(self):
        """關閉客戶端"""
        await self.client.aclose()


async def main():
    """主函數"""
    import argparse
    
    parser = argparse.ArgumentParser(description="GA+ API 測試腳本")
    parser.add_argument(
        "--url", 
        default="http://localhost:8000",
        help="API 基礎 URL"
    )
    
    args = parser.parse_args()
    
    tester = APITester(args.url)
    
    try:
        await tester.run_all_tests()
    finally:
        await tester.close()


if __name__ == "__main__":
    asyncio.run(main()) 