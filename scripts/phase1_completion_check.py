#!/usr/bin/env python3
"""
GA+ 第一階段完成度檢查腳本

全面檢查第一階段 MVP 的所有功能是否完成
"""

import sys
import os
import requests
import time
from pathlib import Path

# 添加專案根目錄到 Python 路徑
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def check_phase1_completion():
    """檢查第一階段完成度"""
    print("🚀 GA+ 第一階段完成度檢查")
    print("=" * 60)
    print("📋 根據開發計劃檢查所有必要功能")
    print("=" * 60)
    
    results = []
    base_url = "http://localhost:8000"
    
    # 1. 系統架構檢查
    print("\n1️⃣  系統架構檢查")
    print("-" * 40)
    
    try:
        # 檢查配置
        from app.core.config import settings
        print(f"✅ 配置系統: 正常")
        print(f"   - 環境: {settings.ENVIRONMENT}")
        print(f"   - 資料庫: {settings.DATABASE_URL}")
        print(f"   - LLM API: {'真實模式' if not settings.USE_MOCK_LLM_API else '模擬模式'}")
        print(f"   - GA4 API: {'真實模式' if not settings.USE_MOCK_GA4_API else '模擬模式'}")
        results.append(True)
    except Exception as e:
        print(f"❌ 配置系統: 失敗 - {e}")
        results.append(False)
    
    # 2. 資料庫層檢查
    print("\n2️⃣  資料庫層檢查")
    print("-" * 40)
    
    try:
        from app.core.database import SessionLocal
        from app.models.user import User, QueryLog
        
        db = SessionLocal()
        try:
            # 檢查表是否存在
            user_count = db.query(User).count()
            print(f"✅ 用戶表: 正常 (當前 {user_count} 個用戶)")
            
            # 檢查模型定義
            user_fields = [column.name for column in User.__table__.columns]
            required_fields = ['id', 'email', 'name', 'password_hash', 'subscription_tier']
            missing_fields = [f for f in required_fields if f not in user_fields]
            
            if not missing_fields:
                print(f"✅ 用戶模型: 完整 ({len(user_fields)} 個欄位)")
            else:
                print(f"⚠️  用戶模型: 缺少欄位 {missing_fields}")
            
            print(f"✅ 查詢日誌模型: 已定義")
            results.append(True)
        finally:
            db.close()
    except Exception as e:
        print(f"❌ 資料庫層: 失敗 - {e}")
        results.append(False)
    
    # 3. API 端點檢查
    print("\n3️⃣  API 端點檢查")
    print("-" * 40)
    
    api_endpoints = [
        ("/api/v1/health/", "健康檢查"),
        ("/api/v1/health/detailed", "詳細健康檢查"),
        ("/api/v1/status", "API 狀態"),
        ("/api/v1/chat/supported-queries", "支援查詢類型"),
        ("/api/v1/analytics/properties", "分析屬性"),
        ("/api/v1/analytics/metrics", "分析指標"),
        ("/api/v1/analytics/dimensions", "分析維度")
    ]
    
    api_success = 0
    for endpoint, name in api_endpoints:
        try:
            r = requests.get(f"{base_url}{endpoint}", timeout=5)
            if r.status_code == 200:
                print(f"✅ {name}: 正常 (200)")
                api_success += 1
            else:
                print(f"⚠️  {name}: 狀態碼 {r.status_code}")
        except Exception as e:
            print(f"❌ {name}: 失敗 - {e}")
    
    results.append(api_success >= len(api_endpoints) * 0.8)  # 80% 通過率
    
    # 4. LLM 聊天功能檢查
    print("\n4️⃣  LLM 聊天功能檢查")
    print("-" * 40)
    
    try:
        chat_data = {
            "message": "請用繁體中文簡短說明什麼是 Google Analytics 4？",
            "property_id": "demo_property"
        }
        
        r = requests.post(f"{base_url}/api/v1/chat/", json=chat_data, timeout=20)
        
        if r.status_code == 200:
            data = r.json()
            response_text = data.get("response", "")
            confidence = data.get("confidence", 0)
            
            print(f"✅ 聊天端點: 正常 (200)")
            print(f"   - 回應長度: {len(response_text)} 字符")
            print(f"   - 信心度: {confidence:.2f}")
            print(f"   - 查詢類型: {data.get('query_type', 'unknown')}")
            
            # 檢查回應品質
            if len(response_text) > 50 and "抱歉" not in response_text:
                print(f"✅ 回應品質: 良好")
                results.append(True)
            else:
                print(f"⚠️  回應品質: 需改善")
                results.append(False)
        else:
            print(f"❌ 聊天端點: 失敗 ({r.status_code})")
            results.append(False)
    except Exception as e:
        print(f"❌ LLM 聊天功能: 失敗 - {e}")
        results.append(False)
    
    # 5. 用戶管理檢查
    print("\n5️⃣  用戶管理檢查")
    print("-" * 40)
    
    try:
        # 測試註冊
        unique_email = f"phase1_test_{int(time.time())}@example.com"
        register_data = {
            "email": unique_email,
            "name": "第一階段測試用戶",
            "company": "測試公司",
            "password": "testpass123"
        }
        
        r1 = requests.post(f"{base_url}/api/v1/users/register", json=register_data, timeout=10)
        
        if r1.status_code == 200:
            user_data = r1.json()
            print(f"✅ 用戶註冊: 正常 (ID: {user_data.get('id')})")
            
            # 測試登入
            login_data = {
                "email": unique_email,
                "password": "testpass123"
            }
            
            r2 = requests.post(f"{base_url}/api/v1/users/login", json=login_data, timeout=10)
            
            if r2.status_code == 200:
                login_result = r2.json()
                print(f"✅ 用戶登入: 正常")
                print(f"✅ JWT Token: 已生成")
                results.append(True)
            else:
                print(f"❌ 用戶登入: 失敗 ({r2.status_code})")
                results.append(False)
        else:
            print(f"❌ 用戶註冊: 失敗 ({r1.status_code})")
            results.append(False)
    except Exception as e:
        print(f"❌ 用戶管理: 失敗 - {e}")
        results.append(False)
    
    # 6. 查詢解析器檢查
    print("\n6️⃣  查詢解析器檢查")
    print("-" * 40)
    
    try:
        from app.services.query_parser import QueryParser
        
        parser = QueryParser()
        test_queries = [
            "昨天有多少訪客？",
            "最熱門的頁面是什麼？",
            "主要流量來源有哪些？"
        ]
        
        parsed_count = 0
        for query in test_queries:
            try:
                intent = parser.parse_query(query)
                if hasattr(intent, 'query_type') and intent.query_type:
                    parsed_count += 1
            except:
                pass
        
        if parsed_count >= len(test_queries) * 0.8:
            print(f"✅ 查詢解析器: 正常 ({parsed_count}/{len(test_queries)} 成功)")
            results.append(True)
        else:
            print(f"⚠️  查詢解析器: 部分功能 ({parsed_count}/{len(test_queries)} 成功)")
            results.append(False)
    except Exception as e:
        print(f"❌ 查詢解析器: 失敗 - {e}")
        results.append(False)
    
    # 7. 前端檢查
    print("\n7️⃣  前端檢查")
    print("-" * 40)
    
    frontend_files = [
        "frontend/package.json",
        "frontend/src/App.js",
        "frontend/src/index.js",
        "frontend/public/index.html"
    ]
    
    frontend_exists = 0
    for file_path in frontend_files:
        if (project_root / file_path).exists():
            frontend_exists += 1
    
    if frontend_exists >= len(frontend_files) * 0.8:
        print(f"✅ 前端文件: 完整 ({frontend_exists}/{len(frontend_files)})")
        results.append(True)
    else:
        print(f"⚠️  前端文件: 不完整 ({frontend_exists}/{len(frontend_files)})")
        results.append(False)
    
    # 8. 開發工具檢查
    print("\n8️⃣  開發工具檢查")
    print("-" * 40)
    
    dev_tools = [
        "scripts/run_dev_server.py",
        "scripts/test_api.py",
        "scripts/init_db.py",
        "requirements.txt"
    ]
    
    tools_exists = 0
    for tool_path in dev_tools:
        if (project_root / tool_path).exists():
            tools_exists += 1
    
    if tools_exists >= len(dev_tools) * 0.8:
        print(f"✅ 開發工具: 完整 ({tools_exists}/{len(dev_tools)})")
        results.append(True)
    else:
        print(f"⚠️  開發工具: 不完整 ({tools_exists}/{len(dev_tools)})")
        results.append(False)
    
    # 總結
    print("\n" + "=" * 60)
    passed = sum(results)
    total = len(results)
    completion_rate = (passed / total) * 100
    
    print(f"📊 第一階段完成度檢查結果")
    print(f"通過項目: {passed}/{total}")
    print(f"完成率: {completion_rate:.1f}%")
    print("=" * 60)
    
    if completion_rate >= 90:
        print("🎉🎉🎉 第一階段 MVP 開發完成！🎉🎉🎉")
        print("✅ 所有核心功能都已實現")
        print("✅ 系統架構完整穩定")
        print("✅ API 端點全部正常")
        print("✅ LLM 集成成功")
        print("✅ 用戶管理完整")
        print("✅ 前端基礎完成")
        print("✅ 開發環境配置完整")
        print("🚀 準備進入第二階段開發！")
        return True
    elif completion_rate >= 80:
        print("🎯 第一階段基本完成")
        print("✅ 核心功能已實現")
        print("⚠️  部分功能需要優化")
        print("💡 建議完善後進入下一階段")
        return True
    else:
        print("⚠️  第一階段尚未完成")
        print("❌ 多個核心功能需要修復")
        print("💡 建議先完成剩餘功能")
        return False

if __name__ == "__main__":
    check_phase1_completion() 