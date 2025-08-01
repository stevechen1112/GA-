"""
分析端點

提供 GA4 數據分析功能
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import structlog

from app.core.config import settings
from app.services.ga4_service import GA4Service
from app.core.dependencies import get_ga4_service

router = APIRouter()
logger = structlog.get_logger()


class AnalyticsRequest(BaseModel):
    """分析請求模型"""
    property_id: str
    date_range: str = "last_30_days"
    metrics: List[str]
    dimensions: Optional[List[str]] = None
    filters: Optional[Dict[str, Any]] = None


@router.post("/query")
async def query_analytics(
    request: AnalyticsRequest,
    ga4_service: GA4Service = Depends(get_ga4_service)
) -> Dict[str, Any]:
    """
    執行 GA4 查詢
    
    Args:
        request: 分析請求
        ga4_service: GA4 服務
        
    Returns:
        查詢結果
    """
    try:
        # 構建查詢參數字典
        query_params = {
            "metrics": [{"name": metric} for metric in request.metrics],
            "dimensions": [{"name": dim} for dim in (request.dimensions or [])],
            "date_ranges": [{"start_date": "30daysAgo", "end_date": "today"}],  # 暫時固定
            "limit": 10
        }
        
        if request.filters:
            query_params["filters"] = request.filters
            
        result = await ga4_service.execute_query(query_params, request.property_id)
        
        return {
            "status": "success",
            "data": result,
            "query_info": {
                "metrics": request.metrics,
                "dimensions": request.dimensions,
                "date_range": request.date_range,
                "property_id": request.property_id
            }
        }
    except Exception as e:
        logger.error("Analytics query failed", error=str(e))
        raise HTTPException(
            status_code=500,
            detail={"error": "Failed to execute analytics query", "message": str(e)}
        )


@router.get("/properties")
async def get_properties(
    ga4_service: GA4Service = Depends(get_ga4_service)
) -> Dict[str, Any]:
    """
    獲取可用的 GA4 屬性列表
    
    Returns:
        屬性列表
    """
    try:
        properties = await ga4_service.get_properties()
        return {
            "properties": properties,
            "total": len(properties)
        }
    except Exception as e:
        logger.error("Failed to get properties", error=str(e))
        # 返回模擬數據作為後備
        return {
            "properties": [
                {
                    "id": "123456789",
                    "name": "Example Website",
                    "account_id": "987654321",
                    "account_name": "Example Account"
                }
            ],
            "total": 1
        }


@router.get("/metrics")
async def get_available_metrics(
    ga4_service: GA4Service = Depends(get_ga4_service)
) -> Dict[str, Any]:
    """
    獲取可用的 GA4 指標列表
    
    Returns:
        指標列表
    """
    try:
        metrics = await ga4_service.get_available_metrics()
        return {
            "metrics": metrics,
            "total_categories": len(metrics)
        }
    except Exception as e:
        logger.error("Failed to get metrics", error=str(e))
        # 返回默認指標作為後備
        metrics = {
            "user_metrics": [
                "totalUsers",
                "newUsers",
                "activeUsers",
                "sessionsPerUser"
            ],
            "session_metrics": [
                "sessions",
                "engagedSessions",
                "bounceRate",
                "sessionDuration"
            ],
            "traffic_metrics": [
                "screenPageViews",
                "pageViews",
                "screenPageViewsPerSession"
            ],
            "conversion_metrics": [
                "conversions",
                "conversionRate",
                "totalRevenue",
                "averageSessionDuration"
            ]
        }
        
        return {
            "metrics": metrics,
            "total_categories": len(metrics)
        }


@router.get("/dimensions")
async def get_available_dimensions(
    ga4_service: GA4Service = Depends(get_ga4_service)
) -> Dict[str, Any]:
    """
    獲取可用的 GA4 維度列表
    
    Returns:
        維度列表
    """
    try:
        dimensions = await ga4_service.get_available_dimensions()
        return {
            "dimensions": dimensions,
            "total_categories": len(dimensions)
        }
    except Exception as e:
        logger.error("Failed to get dimensions", error=str(e))
        # 返回默認維度作為後備
        dimensions = {
            "user_dimensions": [
                "userType",
                "userId",
                "userPseudoId"
            ],
            "session_dimensions": [
                "sessionDefaultChannelGrouping",
                "sessionSource",
                "sessionMedium",
                "sessionCampaignName"
            ],
            "page_dimensions": [
                "pageTitle",
                "pagePath",
                "pageLocation",
                "pageReferrer"
            ],
            "event_dimensions": [
                "eventName",
                "eventCategory",
                "eventAction",
                "eventLabel"
            ]
        }
        
        return {
            "dimensions": dimensions,
            "total_categories": len(dimensions)
        } 