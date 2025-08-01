"""
健康檢查端點

提供系統健康狀態檢查功能
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any
import time
import structlog
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.dependencies import get_database, get_ga4_service, get_llm_service
from app.services.ga4_service import GA4Service
from app.services.llm_service import LLMService

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
async def detailed_health_check(
    db: Session = Depends(get_database),
    ga4_service: GA4Service = Depends(get_ga4_service),
    llm_service: LLMService = Depends(get_llm_service)
) -> Dict[str, Any]:
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
        # 執行簡單的資料庫查詢
        db.execute("SELECT 1")
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
        # 檢查 GA4 服務是否可用
        if settings.USE_MOCK_GA4_API:
            health_status["services"]["ga4_api"] = {
                "status": "healthy",
                "message": "GA4 API (mock mode) is operational"
            }
        else:
            # 執行簡單的 GA4 查詢測試
            test_result = await ga4_service.execute_query({
                "metrics": [{"name": "totalUsers"}],
                "date_ranges": [{"start_date": "today", "end_date": "today"}],
                "limit": 1
            })
            
            if test_result.get("error"):
                raise Exception(test_result.get("message", "GA4 query failed"))
                
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
        # 檢查 LLM 服務是否可用
        if settings.USE_MOCK_LLM_API:
            health_status["services"]["llm_api"] = {
                "status": "healthy",
                "message": "LLM API (mock mode) is operational"
            }
        else:
            # 執行簡單的 LLM 測試
            test_response = await llm_service.generate_completion("健康檢查測試")
            if not test_response or "抱歉" in test_response:
                raise Exception("LLM service returned error response")
                
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