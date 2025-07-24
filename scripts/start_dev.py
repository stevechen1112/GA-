#!/usr/bin/env python3
"""
GA+ 開發環境啟動腳本

用於快速啟動開發環境
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path

# 添加專案根目錄到 Python 路徑
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def check_dependencies():
    """檢查依賴項目"""
    print("🔍 檢查依賴項目...")
    
    try:
        import fastapi
        import uvicorn
        import structlog
        print("✅ 核心依賴項目已安裝")
    except ImportError as e:
        print(f"❌ 缺少依賴項目: {e}")
        print("請執行: pip install -r requirements.txt")
        return False
    
    return True


def check_environment():
    """檢查環境變數"""
    print("🔍 檢查環境變數...")
    
    required_vars = [
        "OPENAI_API_KEY",
        "GA4_PROPERTY_ID"
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"⚠️  缺少環境變數: {', '.join(missing_vars)}")
        print("請創建 .env 文件並設置必要的環境變數")
        return False
    
    print("✅ 環境變數檢查完成")
    return True


def create_env_file():
    """創建環境變數範例文件"""
    env_content = """# GA+ 環境變數配置

# 應用程式配置
APP_NAME=GA+
APP_VERSION=0.1.0
DEBUG=true
ENVIRONMENT=development

# 服務器配置
HOST=0.0.0.0
PORT=8000

# 資料庫配置
DATABASE_URL=postgresql://postgres:password@localhost:5432/ga_plus_db
DB_HOST=localhost
DB_PORT=5432
DB_NAME=ga_plus_db
DB_USER=postgres
DB_PASSWORD=password

# Redis 快取配置
REDIS_URL=redis://localhost:6379/0
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# AI/ML 服務配置
OPENAI_API_KEY=your-openai-api-key-here
OPENAI_MODEL=gpt-4o
OPENAI_MAX_TOKENS=4000
OPENAI_TEMPERATURE=0.1

CLAUDE_API_KEY=your-claude-api-key-here
CLAUDE_MODEL=claude-3-5-sonnet-20241022

# Weaviate 向量資料庫
WEAVIATE_URL=http://localhost:8080
WEAVIATE_API_KEY=

# Google Cloud 服務配置
GOOGLE_APPLICATION_CREDENTIALS=path/to/your/service-account-key.json
GA4_PROPERTY_ID=your-ga4-property-id-here

GCP_PROJECT_ID=your-gcp-project-id
BIGQUERY_DATASET_ID=your-bigquery-dataset-id
BIGQUERY_TABLE_PREFIX=ga4_

# 安全配置
SECRET_KEY=your-super-secret-jwt-key-change-this-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

ENCRYPTION_KEY=your-32-character-encryption-key

# CORS 設定
ALLOWED_ORIGINS=["http://localhost:3000", "http://localhost:8080"]
ALLOWED_METHODS=["GET", "POST", "PUT", "DELETE"]
ALLOWED_HEADERS=["*"]
ALLOWED_HOSTS=["*"]

# 第三方服務配置
STRIPE_PUBLISHABLE_KEY=
STRIPE_SECRET_KEY=
STRIPE_WEBHOOK_SECRET=

SENDGRID_API_KEY=
FROM_EMAIL=noreply@gaplus.com

# 監控和日誌配置
LOG_LEVEL=INFO
LOG_FORMAT=json

SENTRY_DSN=

ENABLE_METRICS=true
METRICS_PORT=9090

# 快取和性能配置
CACHE_TTL_SECONDS=3600
MAX_CACHE_SIZE_MB=512

RATE_LIMIT_PER_MINUTE=100
RATE_LIMIT_BURST=20

# 功能開關
ENABLE_BIGQUERY_ROUTING=true
ENABLE_ANOMALY_DETECTION=false
ENABLE_PREDICTIVE_ANALYTICS=false
ENABLE_AUTO_REPORTS=false

# 用戶分層配置
FREE_TIER_QUERY_LIMIT=1000
GROWTH_TIER_QUERY_LIMIT=10000
ENTERPRISE_TIER_QUERY_LIMIT=-1

# 開發和測試配置
TEST_DATABASE_URL=postgresql://test_user:test_pass@localhost:5432/ga_plus_test_db

USE_MOCK_GA4_API=true
USE_MOCK_LLM_API=false
"""
    
    env_file = project_root / ".env"
    if not env_file.exists():
        with open(env_file, "w", encoding="utf-8") as f:
            f.write(env_content)
        print("✅ 已創建 .env 範例文件")
        print("⚠️  請編輯 .env 文件並設置您的 API 金鑰")
    else:
        print("✅ .env 文件已存在")


def start_development_server():
    """啟動開發服務器"""
    print("🚀 啟動開發服務器...")
    
    try:
        # 使用 uvicorn 啟動服務器
        cmd = [
            sys.executable, "-m", "uvicorn",
            "app.main:app",
            "--host", "0.0.0.0",
            "--port", "8000",
            "--reload",
            "--log-level", "info"
        ]
        
        subprocess.run(cmd, cwd=project_root)
        
    except KeyboardInterrupt:
        print("\n👋 開發服務器已停止")
    except Exception as e:
        print(f"❌ 啟動服務器失敗: {e}")


def start_with_docker():
    """使用 Docker 啟動"""
    print("🐳 使用 Docker 啟動...")
    
    try:
        # 檢查 Docker 是否可用
        subprocess.run(["docker", "--version"], check=True, capture_output=True)
        
        # 啟動 Docker Compose
        cmd = ["docker-compose", "up", "--build"]
        subprocess.run(cmd, cwd=project_root)
        
    except subprocess.CalledProcessError:
        print("❌ Docker 不可用，請安裝 Docker 和 Docker Compose")
    except KeyboardInterrupt:
        print("\n👋 Docker 服務已停止")


def main():
    """主函數"""
    parser = argparse.ArgumentParser(description="GA+ 開發環境啟動腳本")
    parser.add_argument(
        "--docker", 
        action="store_true", 
        help="使用 Docker 啟動"
    )
    parser.add_argument(
        "--create-env", 
        action="store_true", 
        help="創建環境變數文件"
    )
    
    args = parser.parse_args()
    
    print("🎯 GA+ 開發環境啟動腳本")
    print("=" * 50)
    
    # 創建環境變數文件
    if args.create_env:
        create_env_file()
        return
    
    # 檢查依賴項目
    if not check_dependencies():
        return
    
    # 檢查環境變數
    if not check_environment():
        create_env_file()
        return
    
    # 啟動服務
    if args.docker:
        start_with_docker()
    else:
        start_development_server()


if __name__ == "__main__":
    main() 