#!/usr/bin/env python3
"""
GA+ 開發服務器啟動腳本

使用開發配置啟動服務器，確保模擬模式正確啟用
"""

import sys
import os
from pathlib import Path

# 添加專案根目錄到 Python 路徑
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 設置 GA4 憑證環境變數
credentials_file = project_root / "ga-plus-service-9b792f55ddcc.json"
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(credentials_file)

# 讀取 .env 文件配置
from app.core.config import settings

print("🚀 GA+ 開發服務器啟動")
print("=" * 50)
print("🔧 配置檢查:")
print(f"📊 LLM API: {'真實模式 (OpenAI)' if not settings.USE_MOCK_LLM_API else '模擬模式'}")
print(f"📈 GA4 API: {'真實模式' if not settings.USE_MOCK_GA4_API else '模擬模式'}")
print(f"🗄️  資料庫: SQLite (開發)")
print(f"🔑 API Key: {'已設置' if settings.OPENAI_API_KEY and len(settings.OPENAI_API_KEY) > 10 else '未設置'}")
print("=" * 50)

if __name__ == "__main__":
    import uvicorn
    
    # 初始化資料庫
    try:
        from app.core.database import create_tables
        print("🔧 初始化資料庫...")
        create_tables()
        print("✅ 資料庫初始化完成")
    except Exception as e:
        print(f"⚠️  資料庫初始化警告: {e}")
    
    print("\n🌐 啟動開發服務器...")
    print("📍 URL: http://localhost:8000")
    print("📋 API 文檔: http://localhost:8000/docs")
    print("🔄 自動重新加載已啟用")
    print("\n按 Ctrl+C 停止服務器")
    print("-" * 50)
    
    # 啟動服務器
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=[str(project_root / "app")],
        log_level="info"
    ) 