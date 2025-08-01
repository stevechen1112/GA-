#!/usr/bin/env python3
"""
GA+ 資料庫初始化腳本

創建資料庫表和初始數據
"""

import sys
from pathlib import Path

# 添加專案根目錄到 Python 路徑
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.core.database import create_tables, drop_tables
from app.core.config import settings
import structlog

logger = structlog.get_logger()

def init_database():
    """初始化資料庫"""
    try:
        logger.info("Starting database initialization...")
        
        # 在開發環境下，先刪除現有表
        if settings.ENVIRONMENT == "development":
            logger.info("Development environment detected, dropping existing tables...")
            drop_tables()
        
        # 創建所有表
        logger.info("Creating database tables...")
        create_tables()
        
        logger.info("Database initialization completed successfully!")
        
    except Exception as e:
        logger.error("Database initialization failed", error=str(e))
        sys.exit(1)

if __name__ == "__main__":
    init_database() 