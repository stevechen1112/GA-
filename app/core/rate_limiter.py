"""
API 限流配置

使用 slowapi 實現請求速率限制
"""

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from fastapi import Request, HTTPException
from typing import Optional, Callable
import structlog

from app.core.config import settings

logger = structlog.get_logger()


def get_user_id_from_request(request: Request) -> str:
    """
    從請求中獲取用戶標識
    優先使用認證用戶ID，否則使用IP地址
    """
    # 嘗試從認證信息中獲取用戶ID
    if hasattr(request.state, "user_id") and request.state.user_id:
        return f"user:{request.state.user_id}"
    
    # 使用IP地址作為後備
    return get_remote_address(request)


def create_limiter() -> Limiter:
    """
    創建限流器實例
    """
    limiter = Limiter(
        key_func=get_user_id_from_request,
        default_limits=["1000 per hour"],  # 默認限制
        storage_uri=settings.REDIS_URL if settings.REDIS_URL else None,
        enabled=True
    )
    return limiter


# 創建全局限流器實例
limiter = create_limiter()


# 定義不同端點的限流規則
class RateLimits:
    """API 限流規則定義"""
    
    # 聊天對話端點 - 最核心的功能，限制較嚴格
    CHAT = "60 per minute"
    CHAT_BURST = "5 per second"
    
    # 分析端點
    ANALYTICS = "100 per minute"
    
    # 用戶認證端點
    LOGIN = "10 per minute"
    REGISTER = "5 per minute"
    
    # 健康檢查和狀態端點
    HEALTH = "300 per minute"
    
    # 查詢支援端點
    QUERY_SUPPORT = "200 per minute"
    
    # 根據訂閱等級的動態限制
    @staticmethod
    def get_tier_limit(tier: str) -> str:
        """根據用戶訂閱等級返回限流規則"""
        tier_limits = {
            "free": "30 per minute",
            "growth": "100 per minute", 
            "enterprise": "1000 per minute"
        }
        return tier_limits.get(tier, "30 per minute")


def custom_rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    """
    自定義限流超出處理器
    """
    response_content = {
        "error": "Rate limit exceeded",
        "message": f"Too many requests. {exc.detail}",
        "retry_after": request.headers.get("Retry-After", "60")
    }
    
    # 記錄限流事件
    logger.warning(
        "Rate limit exceeded",
        path=request.url.path,
        client=get_remote_address(request),
        limit=exc.detail
    )
    
    raise HTTPException(
        status_code=429,
        detail=response_content,
        headers={"Retry-After": str(request.headers.get("Retry-After", "60"))}
    )


def get_dynamic_limit(request: Request) -> str:
    """
    動態獲取用戶的限流規則
    基於用戶訂閱等級或其他因素
    """
    # 如果是認證用戶，根據訂閱等級設定限制
    if hasattr(request.state, "user") and request.state.user:
        user = request.state.user
        tier = getattr(user, "subscription_tier", "free")
        return RateLimits.get_tier_limit(tier)
    
    # 未認證用戶使用默認限制
    return RateLimits.CHAT