"""
GA+ 結構化日誌配置

使用 structlog 設置結構化日誌系統
"""

import sys
import structlog
from typing import Any, Dict
from app.core.config import settings


def setup_logging() -> None:
    """
    設置結構化日誌系統
    """
    # 配置 structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer() if settings.LOG_FORMAT == "json" else structlog.dev.ConsoleRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def get_logger(name: str = None) -> structlog.BoundLogger:
    """
    獲取結構化日誌記錄器
    
    Args:
        name: 日誌記錄器名稱
        
    Returns:
        結構化日誌記錄器實例
    """
    return structlog.get_logger(name)


def log_request(request_id: str, method: str, url: str, **kwargs) -> None:
    """
    記錄 HTTP 請求日誌
    
    Args:
        request_id: 請求ID
        method: HTTP 方法
        url: 請求URL
        **kwargs: 其他參數
    """
    logger = get_logger("http.request")
    logger.info(
        "HTTP request",
        request_id=request_id,
        method=method,
        url=url,
        **kwargs
    )


def log_response(request_id: str, status_code: int, response_time: float, **kwargs) -> None:
    """
    記錄 HTTP 回應日誌
    
    Args:
        request_id: 請求ID
        status_code: HTTP 狀態碼
        response_time: 回應時間（秒）
        **kwargs: 其他參數
    """
    logger = get_logger("http.response")
    logger.info(
        "HTTP response",
        request_id=request_id,
        status_code=status_code,
        response_time=response_time,
        **kwargs
    )


def log_ga4_query(query: str, property_id: str, **kwargs) -> None:
    """
    記錄 GA4 查詢日誌
    
    Args:
        query: 查詢內容
        property_id: GA4 屬性ID
        **kwargs: 其他參數
    """
    logger = get_logger("ga4.query")
    logger.info(
        "GA4 query executed",
        query=query,
        property_id=property_id,
        **kwargs
    )


def log_llm_request(prompt: str, model: str, **kwargs) -> None:
    """
    記錄 LLM 請求日誌
    
    Args:
        prompt: 提示詞
        model: 模型名稱
        **kwargs: 其他參數
    """
    logger = get_logger("llm.request")
    logger.info(
        "LLM request",
        prompt_length=len(prompt),
        model=model,
        **kwargs
    )


def log_error(error: Exception, context: Dict[str, Any] = None) -> None:
    """
    記錄錯誤日誌
    
    Args:
        error: 錯誤實例
        context: 錯誤上下文
    """
    logger = get_logger("error")
    logger.error(
        "Application error",
        error_type=type(error).__name__,
        error_message=str(error),
        context=context or {}
    ) 