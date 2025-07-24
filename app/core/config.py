"""
GA+ 應用程式配置管理

使用 Pydantic Settings 管理環境變數和配置
"""

from typing import List, Optional
from pydantic import BaseSettings, validator
import os


class Settings(BaseSettings):
    """
    應用程式配置類別
    """
    
    # ========================================
    # 應用程式基本配置
    # ========================================
    APP_NAME: str = "GA+"
    APP_VERSION: str = "0.1.0"
    APP_DESCRIPTION: str = "Google Analytics 4 對話式AI分析平台"
    DEBUG: bool = True
    ENVIRONMENT: str = "development"
    
    # 服務器配置
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # ========================================
    # 資料庫配置
    # ========================================
    DATABASE_URL: str = "postgresql://postgres:password@localhost:5432/ga_plus_db"
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "ga_plus_db"
    DB_USER: str = "postgres"
    DB_PASSWORD: str = "password"
    
    # Redis 快取配置
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = None
    
    # ========================================
    # AI/ML 服務配置
    # ========================================
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o"
    OPENAI_MAX_TOKENS: int = 4000
    OPENAI_TEMPERATURE: float = 0.1
    
    CLAUDE_API_KEY: Optional[str] = None
    CLAUDE_MODEL: str = "claude-3-5-sonnet-20241022"
    
    # Weaviate 向量資料庫
    WEAVIATE_URL: str = "http://localhost:8080"
    WEAVIATE_API_KEY: Optional[str] = None
    
    # ========================================
    # Google Cloud 服務配置
    # ========================================
    GOOGLE_APPLICATION_CREDENTIALS: Optional[str] = None
    GA4_PROPERTY_ID: Optional[str] = None
    
    GCP_PROJECT_ID: Optional[str] = None
    BIGQUERY_DATASET_ID: Optional[str] = None
    BIGQUERY_TABLE_PREFIX: str = "ga4_"
    
    # ========================================
    # 安全配置
    # ========================================
    SECRET_KEY: str = "your-super-secret-jwt-key-change-this-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    ENCRYPTION_KEY: str = "your-32-character-encryption-key"
    
    # CORS 設定
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8080"]
    ALLOWED_METHODS: List[str] = ["GET", "POST", "PUT", "DELETE"]
    ALLOWED_HEADERS: List[str] = ["*"]
    ALLOWED_HOSTS: List[str] = ["*"]
    
    # ========================================
    # 第三方服務配置
    # ========================================
    STRIPE_PUBLISHABLE_KEY: Optional[str] = None
    STRIPE_SECRET_KEY: Optional[str] = None
    STRIPE_WEBHOOK_SECRET: Optional[str] = None
    
    SENDGRID_API_KEY: Optional[str] = None
    FROM_EMAIL: str = "noreply@gaplus.com"
    
    # ========================================
    # 監控和日誌配置
    # ========================================
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    
    SENTRY_DSN: Optional[str] = None
    
    ENABLE_METRICS: bool = True
    METRICS_PORT: int = 9090
    
    # ========================================
    # 快取和性能配置
    # ========================================
    CACHE_TTL_SECONDS: int = 3600
    MAX_CACHE_SIZE_MB: int = 512
    
    RATE_LIMIT_PER_MINUTE: int = 100
    RATE_LIMIT_BURST: int = 20
    
    # ========================================
    # 功能開關
    # ========================================
    ENABLE_BIGQUERY_ROUTING: bool = True
    ENABLE_ANOMALY_DETECTION: bool = False
    ENABLE_PREDICTIVE_ANALYTICS: bool = False
    ENABLE_AUTO_REPORTS: bool = False
    
    # 用戶分層配置
    FREE_TIER_QUERY_LIMIT: int = 1000
    GROWTH_TIER_QUERY_LIMIT: int = 10000
    ENTERPRISE_TIER_QUERY_LIMIT: int = -1
    
    # ========================================
    # 開發和測試配置
    # ========================================
    TEST_DATABASE_URL: str = "postgresql://test_user:test_pass@localhost:5432/ga_plus_test_db"
    
    USE_MOCK_GA4_API: bool = False
    USE_MOCK_LLM_API: bool = False
    
    @validator("ALLOWED_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v):
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)
    
    @validator("ALLOWED_METHODS", pre=True)
    def assemble_allowed_methods(cls, v):
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)
    
    @validator("ALLOWED_HEADERS", pre=True)
    def assemble_allowed_headers(cls, v):
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# 創建全局設置實例
settings = Settings() 