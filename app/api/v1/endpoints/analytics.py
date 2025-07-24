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
    ga4_service: GA4Service = Depends()
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
        result = await ga4_service.execute_query(
            metrics=request.metrics,
            dimensions=request.dimensions,
            date_range=request.date_range,
            property_id=request.property_id,
            filters=request.filters
        )
        
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
async def get_properties() -> Dict[str, Any]:
    """
    獲取可用的 GA4 屬性列表
    
    Returns:
        屬性列表
    """
    # TODO: 實現從 GA4 API 獲取屬性列表
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
async def get_available_metrics() -> Dict[str, Any]:
    """
    獲取可用的 GA4 指標列表
    
    Returns:
        指標列表
    """
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
async def get_available_dimensions() -> Dict[str, Any]:
    """
    獲取可用的 GA4 維度列表
    
    Returns:
        維度列表
    """
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