"""
聊天對話端點

GA+ 的核心功能：自然語言與 GA4 數據對話
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import time
import structlog

from app.core.config import settings
from app.services.query_parser import QueryParser
from app.services.ga4_service import GA4Service
from app.services.llm_service import LLMService
from app.services.smart_router import SmartRouter
from app.core.logging import log_request, log_response
from app.core.dependencies import get_query_parser, get_ga4_service, get_llm_service, get_smart_router
from app.core.rate_limiter import limiter, RateLimits
from app.api.v1.schemas.validators import StrictChatRequest, sanitize_input

router = APIRouter()
logger = structlog.get_logger()


class ChatResponse(BaseModel):
    """聊天回應模型"""
    response: str
    data: Optional[Dict[str, Any]] = None
    confidence: float
    query_type: str
    execution_time: float
    request_id: str
    suggestions: Optional[List[str]] = None


class QueryIntent(BaseModel):
    """查詢意圖模型"""
    intent: str
    confidence: float
    entities: Dict[str, Any]
    parameters: Dict[str, Any]


@router.post("/", response_model=ChatResponse)
@limiter.limit(RateLimits.CHAT)
async def chat_with_ga4(
    request: StrictChatRequest,  # 使用嚴格驗證
    query_parser: QueryParser = Depends(get_query_parser),
    smart_router: SmartRouter = Depends(get_smart_router),
    llm_service: LLMService = Depends(get_llm_service)
) -> ChatResponse:
    """
    與 GA4 數據進行自然語言對話
    
    Args:
        request: 聊天請求
        query_parser: 查詢解析器
        smart_router: 智能路由器
        llm_service: LLM 服務
        
    Returns:
        聊天回應
    """
    start_time = time.time()
    request_id = f"req_{int(start_time * 1000)}"
    
    try:
        # 記錄請求
        log_request(
            request_id=request_id,
            method="POST",
            url="/api/v1/chat",
            message=request.message,
            property_id=request.property_id
        )
        
        # 1. 解析用戶查詢意圖
        logger.info("Parsing user query", request_id=request_id, message=request.message)
        intent = await query_parser.parse_query(request.message)
        
        # 2. 根據意圖生成 GA4 查詢
        logger.info("Generating GA4 query", request_id=request_id, intent=intent.intent)
        ga4_query = await query_parser.generate_ga4_query(intent, request.property_id)
        
        # 3. 使用智能路由器執行查詢
        logger.info("Executing query via smart router", request_id=request_id, query=ga4_query)
        ga4_data = await smart_router.execute_query(ga4_query, request.property_id)
        
        # 4. 使用 LLM 生成自然語言回應
        logger.info("Generating LLM response", request_id=request_id)
        llm_response = await llm_service.generate_response(
            user_query=request.message,
            ga4_data=ga4_data,
            intent=intent
        )
        
        # 5. 生成建議查詢
        suggestions = await llm_service.generate_suggestions(
            user_query=request.message,
            ga4_data=ga4_data
        )
        
        execution_time = time.time() - start_time
        
        response = ChatResponse(
            response=llm_response["response"],
            data=ga4_data,
            confidence=llm_response["confidence"],
            query_type=intent.intent,
            execution_time=execution_time,
            request_id=request_id,
            suggestions=suggestions
        )
        
        # 記錄回應
        log_response(
            request_id=request_id,
            status_code=200,
            response_time=execution_time,
            query_type=intent.intent
        )
        
        return response
        
    except Exception as e:
        execution_time = time.time() - start_time
        logger.error(
            "Chat request failed",
            request_id=request_id,
            error=str(e),
            execution_time=execution_time
        )
        
        # 記錄錯誤回應
        log_response(
            request_id=request_id,
            status_code=500,
            response_time=execution_time,
            error=str(e)
        )
        
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Failed to process chat request",
                "message": str(e),
                "request_id": request_id
            }
        )


@router.get("/routing-stats")
async def get_routing_stats(
    smart_router: SmartRouter = Depends(get_smart_router)
) -> Dict[str, Any]:
    """
    獲取智能路由統計信息
    
    Args:
        smart_router: 智能路由器
        
    Returns:
        路由統計信息
    """
    try:
        stats = await smart_router.get_routing_stats()
        return {
            "status": "success",
            "data": stats
        }
    except Exception as e:
        logger.error("Failed to get routing stats", error=str(e))
        raise HTTPException(
            status_code=500,
            detail={"error": "Failed to get routing stats", "message": str(e)}
        )


@router.get("/supported-queries")
async def get_supported_queries() -> Dict[str, Any]:
    """
    獲取支援的查詢類型
    
    Returns:
        支援的查詢類型和範例
    """
    supported_queries = {
        "basic_metrics": {
            "description": "基本指標查詢",
            "examples": [
                "昨天有多少訪客？",
                "本月轉換率如何？",
                "今天流量比昨天如何？"
            ]
        },
        "page_analysis": {
            "description": "頁面分析",
            "examples": [
                "最熱門的頁面是什麼？",
                "哪些頁面跳出率最高？",
                "用戶最常訪問的頁面有哪些？"
            ]
        },
        "traffic_sources": {
            "description": "流量來源分析",
            "examples": [
                "主要流量來源有哪些？",
                "哪個渠道轉換率最高？",
                "付費廣告效果如何？"
            ]
        },
        "user_behavior": {
            "description": "用戶行為分析",
            "examples": [
                "用戶平均停留時間是多少？",
                "用戶會話深度如何？",
                "新用戶和老用戶有什麼差異？"
            ]
        },
        "conversion_analysis": {
            "description": "轉換分析",
            "examples": [
                "轉換漏斗表現如何？",
                "哪個步驟流失最多？",
                "轉換率趨勢如何？"
            ]
        }
    }
    
    return {
        "supported_queries": supported_queries,
        "total_types": len(supported_queries),
        "version": settings.APP_VERSION
    }


@router.post("/test-query")
async def test_query(
    request: ChatRequest,
    query_parser: QueryParser = Depends(get_query_parser)
) -> Dict[str, Any]:
    """
    測試查詢解析（開發用）
    
    Args:
        request: 測試請求
        query_parser: 查詢解析器
        
    Returns:
        解析結果
    """
    try:
        intent = await query_parser.parse_query(request.message)
        ga4_query = await query_parser.generate_ga4_query(intent, request.property_id)
        
        return {
            "original_query": request.message,
            "parsed_intent": intent.to_dict(),
            "generated_ga4_query": ga4_query,
            "status": "success"
        }
    except Exception as e:
        logger.error("Test query failed", error=str(e))
        raise HTTPException(
            status_code=400,
            detail={"error": "Failed to parse query", "message": str(e)}
        ) 