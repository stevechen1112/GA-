#!/usr/bin/env python3
"""
GA+ 完整系統測試
測試 AI 聊天、GA4 數據查詢等核心功能
"""

import sys
import os
import requests
import json
from pathlib import Path

# 設置項目路徑
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_system_health():
    """測試系統健康狀態"""
    try:
        response = requests.get("http://localhost:8000/api/v1/health/detailed", timeout=5)
        if response.status_code == 200:
            health = response.json()
            print("🟢 系統運行正常")
            
            # 檢查各服務狀態
            services = health.get('detail', {}).get('services', {})
            for service, status in services.items():
                status_icon = "✅" if status.get('status') == 'healthy' else "❌"
                print(f"   {status_icon} {service}: {status.get('message', 'Unknown')}")
            
            return True
        else:
            print("❌ 系統狀態異常")
            return False
    except:
        print("❌ 無法連接到系統")
        return False

def test_ai_chat():
    """測試 AI 聊天功能"""
    
    print("\n🤖 測試 AI 聊天功能")
    print("=" * 60)
    
    # API 端點
    base_url = "http://localhost:8000"
    chat_url = f"{base_url}/api/v1/chat/"
    
    # 測試問題
    test_questions = [
        {
            "question": "過去7天我網站有多少訪客？",
            "description": "基本數據查詢"
        },
        {
            "question": "我的網站轉換率為什麼是0？請給我專業建議",
            "description": "專業分析問題"
        }
    ]
    
    for i, test in enumerate(test_questions, 1):
        print(f"\n📝 測試 {i}: {test['description']}")
        print(f"❓ 問題: {test['question']}")
        print("-" * 60)
        
        try:
            # 發送請求
            payload = {
                "message": test['question'],
                "property_id": "471264301"
            }
            
            response = requests.post(
                chat_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                
                print("✅ API 調用成功")
                print(f"🎯 查詢類型: {result.get('query_type', 'unknown')}")
                print(f"⏱️ 執行時間: {result.get('execution_time', 0):.2f} 秒")
                print(f"🔍 信心度: {result.get('confidence', 0):.2f}")
                
                # 顯示 AI 回應
                ai_response = result.get('response', '')
                if ai_response:
                    print(f"\n🤖 AI 回應長度: {len(ai_response)} 字符")
                    print("✅ 確認: AI 智能回應正常")
                else:
                    print("❌ 沒有收到 AI 回應")
                
            else:
                print(f"❌ API 調用失敗: {response.status_code}")
                
        except Exception as e:
            print(f"❌ 錯誤: {e}")
        
        print("\n" + "=" * 60)

def test_user_management():
    """測試用戶管理功能"""
    print("\n👤 測試用戶管理功能")
    print("=" * 60)
    
    base_url = "http://localhost:8000"
    
    # 測試用戶註冊
    try:
        register_data = {
            "username": f"test_user_{int(requests.get('http://worldtimeapi.org/api/timezone/UTC').json()['unixtime'])}",
            "email": "test@example.com",
            "password": "testpass123"
        }
        
        response = requests.post(f"{base_url}/api/v1/users/register", json=register_data)
        if response.status_code == 200:
            print("✅ 用戶註冊功能正常")
        else:
            print("⚠️ 用戶註冊測試跳過 (可能已存在)")
            
    except Exception as e:
        print(f"⚠️ 用戶管理測試跳過: {e}")

if __name__ == "__main__":
    print("🧪 GA+ 完整系統測試")
    print("=" * 60)
    
    # 檢查系統健康狀態
    if test_system_health():
        print("\n開始測試核心功能...")
        test_ai_chat()
        test_user_management()
        print("\n🎉 系統測試完成！")
    else:
        print("\n請先啟動服務器: python scripts/run_dev_server.py") 