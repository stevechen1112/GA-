"""
GA+ 主應用程式入口點

FastAPI 應用程式的主要配置和路由設置
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
import uvicorn
import structlog

from app.core.config import settings
from app.api.v1.api import api_router
from app.core.logging import setup_logging

# 設置結構化日誌
setup_logging()
logger = structlog.get_logger()

def create_application() -> FastAPI:
    """
    創建 FastAPI 應用程式實例
    """
    app = FastAPI(
        title=settings.APP_NAME,
        description=settings.APP_DESCRIPTION,
        version=settings.APP_VERSION,
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
    )

    # 添加中間件
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=settings.ALLOWED_METHODS,
        allow_headers=settings.ALLOWED_HEADERS,
    )

    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["*"] if settings.DEBUG else settings.ALLOWED_HOSTS
    )

    # 包含 API 路由
    app.include_router(api_router, prefix="/api/v1")

    @app.get("/")
    async def root():
        """根路徑 - 返回應用程式資訊"""
        return {
            "app": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "status": "running",
            "description": settings.APP_DESCRIPTION
        }

    @app.get("/health")
    async def health_check():
        """健康檢查端點"""
        try:
            # 這裡可以添加資料庫連接檢查等
            return {
                "status": "healthy",
                "timestamp": "2024-01-21T10:00:00Z",
                "version": settings.APP_VERSION
            }
        except Exception as e:
            logger.error("Health check failed", error=str(e))
            raise HTTPException(status_code=503, detail="Service unhealthy")

    @app.get("/api/v1/status")
    async def api_status():
        """API 狀態檢查"""
        return {
            "api_version": "v1",
            "status": "operational",
            "features": {
                "ga4_integration": "active",
                "llm_integration": "active",
                "query_parser": "active"
            }
        }

    return app

# 創建應用程式實例
app = create_application()

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info"
    ) 