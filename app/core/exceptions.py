"""
GA+ 自定義異常類型

定義應用程式中使用的具體異常類型
"""

from typing import Optional, Dict, Any
from fastapi import HTTPException, status


class GA4PlusException(Exception):
    """GA+ 基礎異常類別"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


# ========================================
# 認證和授權異常
# ========================================

class AuthenticationError(GA4PlusException):
    """認證失敗異常"""
    pass


class AuthorizationError(GA4PlusException):
    """授權失敗異常"""
    pass


class TokenExpiredError(AuthenticationError):
    """Token 過期異常"""
    pass


class InvalidCredentialsError(AuthenticationError):
    """無效憑證異常"""
    pass


# ========================================
# 數據和驗證異常
# ========================================

class ValidationError(GA4PlusException):
    """數據驗證失敗異常"""
    pass


class DataNotFoundError(GA4PlusException):
    """數據未找到異常"""
    pass


class DuplicateDataError(GA4PlusException):
    """數據重複異常"""
    pass


# ========================================
# 外部服務異常
# ========================================

class ExternalServiceError(GA4PlusException):
    """外部服務異常基類"""
    pass


class GA4APIError(ExternalServiceError):
    """GA4 API 異常"""
    pass


class BigQueryError(ExternalServiceError):
    """BigQuery 異常"""
    pass


class LLMServiceError(ExternalServiceError):
    """LLM 服務異常"""
    pass


class RedisConnectionError(ExternalServiceError):
    """Redis 連接異常"""
    pass


# ========================================
# 業務邏輯異常
# ========================================

class BusinessLogicError(GA4PlusException):
    """業務邏輯異常"""
    pass


class QuotaExceededError(BusinessLogicError):
    """配額超出異常"""
    pass


class SubscriptionError(BusinessLogicError):
    """訂閱相關異常"""
    pass


class PaymentError(BusinessLogicError):
    """支付相關異常"""
    pass


# ========================================
# 系統異常
# ========================================

class SystemError(GA4PlusException):
    """系統異常"""
    pass


class ConfigurationError(SystemError):
    """配置錯誤異常"""
    pass


class DatabaseError(SystemError):
    """資料庫異常"""
    pass


class CacheError(SystemError):
    """快取異常"""
    pass


# ========================================
# HTTP 異常工廠函數
# ========================================

def create_http_exception(
    error: GA4PlusException,
    status_code: Optional[int] = None
) -> HTTPException:
    """
    將自定義異常轉換為 HTTP 異常
    
    Args:
        error: 自定義異常
        status_code: HTTP 狀態碼（可選）
        
    Returns:
        HTTPException
    """
    # 根據異常類型映射狀態碼
    status_mapping = {
        AuthenticationError: status.HTTP_401_UNAUTHORIZED,
        AuthorizationError: status.HTTP_403_FORBIDDEN,
        ValidationError: status.HTTP_400_BAD_REQUEST,
        DataNotFoundError: status.HTTP_404_NOT_FOUND,
        DuplicateDataError: status.HTTP_409_CONFLICT,
        QuotaExceededError: status.HTTP_429_TOO_MANY_REQUESTS,
        ExternalServiceError: status.HTTP_503_SERVICE_UNAVAILABLE,
        SystemError: status.HTTP_500_INTERNAL_SERVER_ERROR,
    }
    
    # 獲取對應的狀態碼
    if status_code is None:
        for exc_type, code in status_mapping.items():
            if isinstance(error, exc_type):
                status_code = code
                break
        else:
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    
    # 構建錯誤詳情
    detail = {
        "error": error.__class__.__name__,
        "message": error.message,
        "details": error.details
    }
    
    return HTTPException(status_code=status_code, detail=detail)


# ========================================
# 異常處理裝飾器
# ========================================

def handle_exceptions(func):
    """
    異常處理裝飾器
    
    自動捕獲和轉換異常
    """
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except GA4PlusException as e:
            raise create_http_exception(e)
        except Exception as e:
            # 未預期的異常
            error = SystemError(
                message="An unexpected error occurred",
                details={"original_error": str(e)}
            )
            raise create_http_exception(error)
    
    return wrapper