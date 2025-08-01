"""
GA+ 開發環境配置

專門用於開發環境的配置，強制啟用模擬模式
"""

import os
from app.core.config import Settings

class DevSettings(Settings):
    """開發環境設置"""
    
    # 強制啟用模擬模式
    USE_MOCK_GA4_API: bool = True
    USE_MOCK_LLM_API: bool = True
    
    # 開發環境設置
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    
    # 使用 SQLite 資料庫
    DATABASE_URL: str = "sqlite:///./ga_plus_dev.db"
    
    # 模擬的 API Keys
    OPENAI_API_KEY: str = "mock-openai-key-for-development"
    ANTHROPIC_API_KEY: str = "mock-anthropic-key-for-development"
    GA4_PROPERTY_ID: str = "demo_property_123456789"
    
    # JWT 配置
    SECRET_KEY: str = "dev-secret-key-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # 訂閱限制
    FREE_TIER_QUERY_LIMIT: int = 1000
    GROWTH_TIER_QUERY_LIMIT: int = 10000
    ENTERPRISE_TIER_QUERY_LIMIT: int = 100000

# 創建開發設置實例
dev_settings = DevSettings() 