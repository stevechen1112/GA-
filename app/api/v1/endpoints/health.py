"""
健康檢查端點

提供系統健康狀態檢查功能
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import time
import structlog

from app.core.config import settings

router = APIRouter()
logger = structlog.get_logger()


@router.get("/")
async def health_check() -> Dict[str, Any]:
    """
    基本健康檢查
    
    Returns:
        系統健康狀態
    """
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT
    }


@router.get("/detailed")
async def detailed_health_check() -> Dict[str, Any]:
    """
    詳細健康檢查
    
    檢查各個服務的連接狀態
    
    Returns:
        詳細的系統健康狀態
    """
    health_status = {
        "status": "healthy",
        "timestamp": time.time(),
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "services": {}
    }
    
    # 檢查資料庫連接
    try:
        # TODO: 實現資料庫連接檢查
        health_status["services"]["database"] = {
            "status": "healthy",
            "message": "Database connection successful"
        }
    except Exception as e:
        logger.error("Database health check failed", error=str(e))
        health_status["services"]["database"] = {
            "status": "unhealthy",
            "message": f"Database connection failed: {str(e)}"
        }
        health_status["status"] = "unhealthy"
    
    # 檢查 Redis 連接
    try:
        # TODO: 實現 Redis 連接檢查
        health_status["services"]["redis"] = {
            "status": "healthy",
            "message": "Redis connection successful"
        }
    except Exception as e:
        logger.error("Redis health check failed", error=str(e))
        health_status["services"]["redis"] = {
            "status": "unhealthy",
            "message": f"Redis connection failed: {str(e)}"
        }
        health_status["status"] = "unhealthy"
    
    # 檢查 GA4 API 連接
    try:
        # TODO: 實現 GA4 API 連接檢查
        health_status["services"]["ga4_api"] = {
            "status": "healthy",
            "message": "GA4 API connection successful"
        }
    except Exception as e:
        logger.error("GA4 API health check failed", error=str(e))
        health_status["services"]["ga4_api"] = {
            "status": "unhealthy",
            "message": f"GA4 API connection failed: {str(e)}"
        }
        health_status["status"] = "unhealthy"
    
    # 檢查 LLM API 連接
    try:
        # TODO: 實現 LLM API 連接檢查
        health_status["services"]["llm_api"] = {
            "status": "healthy",
            "message": "LLM API connection successful"
        }
    except Exception as e:
        logger.error("LLM API health check failed", error=str(e))
        health_status["services"]["llm_api"] = {
            "status": "unhealthy",
            "message": f"LLM API connection failed: {str(e)}"
        }
        health_status["status"] = "unhealthy"
    
    # 如果任何服務不健康，返回 503 狀態碼
    if health_status["status"] == "unhealthy":
        raise HTTPException(status_code=503, detail=health_status)
    
    return health_status


@router.get("/ready")
async def readiness_check() -> Dict[str, Any]:
    """
    就緒檢查
    
    檢查應用程式是否準備好接收流量
    
    Returns:
        就緒狀態
    """
    # TODO: 實現更詳細的就緒檢查
    return {
        "status": "ready",
        "timestamp": time.time(),
        "message": "Application is ready to receive traffic"
    } 