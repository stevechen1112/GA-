#!/usr/bin/env python3
"""
GA4 設置腳本
協助用戶設置 Google Analytics 4 整合
"""

import sys
import os
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def setup_ga4():
    """設置 GA4 整合"""
    
    print("🔧 GA+ GA4 設置向導")
    print("=" * 60)
    
    # 獲取用戶輸入
    property_id = input("請輸入您的 GA4 Property ID: ").strip()
    if not property_id:
        print("❌ 必須提供 GA4 Property ID")
        return False
    
    credentials_path = input("請輸入 Google Cloud 服務帳戶 JSON 文件路徑: ").strip()
    if not credentials_path or not Path(credentials_path).exists():
        print("❌ 憑證文件不存在")
        return False
    
    # 更新 .env 文件
    env_path = project_root / ".env"
    env_content = f"""# GA+ 環境配置文件

# 應用程式基本配置
APP_NAME=GA+
APP_VERSION=0.1.0
DEBUG=true
ENVIRONMENT=development

# 服務器配置
HOST=0.0.0.0
PORT=8000

# 資料庫配置
DATABASE_URL=sqlite:///./ga_plus_dev.db

# AI/ML 服務配置
USE_MOCK_LLM_API=false
OPENAI_API_KEY=your-openai-api-key-here
OPENAI_MODEL=gpt-4o
OPENAI_MAX_TOKENS=4000
OPENAI_TEMPERATURE=0.1

# Google Cloud 服務配置
USE_MOCK_GA4_API=false
GOOGLE_APPLICATION_CREDENTIALS={credentials_path}
GA4_PROPERTY_ID={property_id}

# 安全配置
SECRET_KEY=your-super-secret-jwt-key-change-this-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# CORS 設定
ALLOWED_ORIGINS=["http://localhost:3000","http://localhost:8080"]
ALLOWED_METHODS=["GET","POST","PUT","DELETE"]
ALLOWED_HEADERS=["*"]
"""
    
    try:
        with open(env_path, 'w', encoding='utf-8') as f:
            f.write(env_content)
        
        print("✅ .env 文件已更新")
        print(f"📊 GA4 Property ID: {property_id}")
        print(f"🔑 憑證文件: {credentials_path}")
        
        return True
        
    except Exception as e:
        print(f"❌ 設置失敗: {e}")
        return False

def show_instructions():
    """顯示 GA4 設置說明"""
    
    print("\n📋 GA4 設置說明")
    print("=" * 60)
    print("1. 前往 Google Cloud Console")
    print("2. 創建或選擇項目")
    print("3. 啟用 Google Analytics Data API")
    print("4. 創建服務帳戶")
    print("5. 下載 JSON 憑證文件")
    print("6. 在 GA4 中添加服務帳戶電子郵件為查看者")
    print("7. 運行此腳本完成設置")

if __name__ == "__main__":
    show_instructions()
    
    if input("\n是否開始設置？(y/N): ").lower() == 'y':
        if setup_ga4():
            print("\n🎉 GA4 設置完成！")
            print("現在可以啟動服務器: python scripts/run_dev_server.py")
        else:
            print("\n❌ 設置失敗，請檢查輸入")
    else:
        print("設置已取消") 