"""
安全的日誌記錄系統

防止敏感信息洩漏到日誌中
"""

import structlog
from typing import Any, Dict, List, Optional, Set
import re
import json
from functools import wraps
from datetime import datetime
import hashlib

from app.core.config import settings


class SensitiveDataFilter:
    """敏感數據過濾器"""
    
    # 敏感欄位名稱（不區分大小寫）
    SENSITIVE_FIELDS = {
        'password', 'pwd', 'secret', 'token', 'api_key', 'apikey',
        'access_token', 'refresh_token', 'authorization', 'auth',
        'credit_card', 'card_number', 'cvv', 'ssn', 'passport',
        'private_key', 'encryption_key', 'secret_key', 'client_secret',
        'database_url', 'connection_string', 'email', 'phone',
        'ip_address', 'user_id', 'session_id', 'cookie'
    }
    
    # 敏感數據模式
    SENSITIVE_PATTERNS = [
        # API 密鑰格式
        (r'[a-zA-Z0-9_-]{32,}', 'API_KEY'),
        # JWT Token
        (r'eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+', 'JWT_TOKEN'),
        # 信用卡號
        (r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b', 'CREDIT_CARD'),
        # Email（部分遮蔽）
        (r'([a-zA-Z0-9._%+-]+)@([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', 'EMAIL'),
        # IP 地址
        (r'\b(?:\d{1,3}\.){3}\d{1,3}\b', 'IP_ADDRESS'),
        # 電話號碼
        (r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', 'PHONE'),
    ]
    
    def __init__(self, 
                 additional_fields: Optional[Set[str]] = None,
                 mask_char: str = '*',
                 show_length: bool = True):
        """
        初始化過濾器
        
        Args:
            additional_fields: 額外的敏感欄位
            mask_char: 遮蔽字符
            show_length: 是否顯示原始長度
        """
        self.sensitive_fields = self.SENSITIVE_FIELDS.copy()
        if additional_fields:
            self.sensitive_fields.update(additional_fields)
        
        self.mask_char = mask_char
        self.show_length = show_length
    
    def mask_value(self, value: Any, field_name: Optional[str] = None) -> Any:
        """
        遮蔽敏感值
        
        Args:
            value: 要遮蔽的值
            field_name: 欄位名稱
            
        Returns:
            遮蔽後的值
        """
        if value is None:
            return None
        
        # 轉換為字符串處理
        str_value = str(value)
        
        # 根據欄位類型決定遮蔽策略
        if field_name and field_name.lower() in ['email']:
            # Email 特殊處理：保留部分信息
            match = re.match(r'([a-zA-Z0-9._%+-]+)@([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', str_value)
            if match:
                username, domain = match.groups()
                if len(username) > 3:
                    masked_username = username[:2] + self.mask_char * (len(username) - 3) + username[-1]
                else:
                    masked_username = self.mask_char * len(username)
                return f"{masked_username}@{domain}"
        
        # 其他敏感數據完全遮蔽
        if self.show_length:
            return f"{self.mask_char * len(str_value)}[{len(str_value)}]"
        else:
            return self.mask_char * 8
    
    def filter_dict(self, data: Dict[str, Any], path: str = '') -> Dict[str, Any]:
        """
        過濾字典中的敏感數據
        
        Args:
            data: 要過濾的字典
            path: 當前路徑（用於嵌套字典）
            
        Returns:
            過濾後的字典
        """
        filtered = {}
        
        for key, value in data.items():
            current_path = f"{path}.{key}" if path else key
            
            # 檢查欄位名是否敏感
            if self._is_sensitive_field(key):
                filtered[key] = self.mask_value(value, key)
            
            # 遞歸處理嵌套字典
            elif isinstance(value, dict):
                filtered[key] = self.filter_dict(value, current_path)
            
            # 處理列表
            elif isinstance(value, list):
                filtered[key] = self._filter_list(value, current_path)
            
            # 檢查值是否匹配敏感模式
            elif isinstance(value, str) and self._contains_sensitive_pattern(value):
                filtered[key] = self._mask_by_pattern(value)
            
            else:
                filtered[key] = value
        
        return filtered
    
    def _filter_list(self, items: List[Any], path: str) -> List[Any]:
        """過濾列表中的敏感數據"""
        filtered = []
        
        for i, item in enumerate(items):
            current_path = f"{path}[{i}]"
            
            if isinstance(item, dict):
                filtered.append(self.filter_dict(item, current_path))
            elif isinstance(item, list):
                filtered.append(self._filter_list(item, current_path))
            elif isinstance(item, str) and self._contains_sensitive_pattern(item):
                filtered.append(self._mask_by_pattern(item))
            else:
                filtered.append(item)
        
        return filtered
    
    def _is_sensitive_field(self, field_name: str) -> bool:
        """檢查欄位名是否敏感"""
        return field_name.lower() in self.sensitive_fields
    
    def _contains_sensitive_pattern(self, value: str) -> bool:
        """檢查值是否包含敏感模式"""
        for pattern, _ in self.SENSITIVE_PATTERNS:
            if re.search(pattern, value):
                return True
        return False
    
    def _mask_by_pattern(self, value: str) -> str:
        """根據模式遮蔽值"""
        masked_value = value
        
        for pattern, pattern_type in self.SENSITIVE_PATTERNS:
            if pattern_type == 'EMAIL':
                # Email 特殊處理
                masked_value = re.sub(
                    pattern,
                    lambda m: self.mask_value(m.group(0), 'email'),
                    masked_value
                )
            else:
                # 其他模式完全遮蔽
                masked_value = re.sub(
                    pattern,
                    lambda m: self.mask_char * len(m.group(0)),
                    masked_value
                )
        
        return masked_value


class SecureLogger:
    """安全的日誌記錄器"""
    
    def __init__(self, 
                 name: str,
                 filter_sensitive: bool = True,
                 log_level: str = "INFO"):
        """
        初始化安全日誌記錄器
        
        Args:
            name: 記錄器名稱
            filter_sensitive: 是否過濾敏感數據
            log_level: 日誌級別
        """
        self.name = name
        self.filter_sensitive = filter_sensitive
        self.sensitive_filter = SensitiveDataFilter()
        
        # 配置 structlog
        self.logger = structlog.get_logger(name)
    
    def _prepare_log_data(self, event_dict: Dict[str, Any]) -> Dict[str, Any]:
        """準備日誌數據（過濾敏感信息）"""
        if not self.filter_sensitive:
            return event_dict
        
        # 過濾敏感數據
        filtered_dict = self.sensitive_filter.filter_dict(event_dict)
        
        # 添加安全元數據
        filtered_dict['_secure_log'] = True
        filtered_dict['_timestamp'] = datetime.utcnow().isoformat()
        
        return filtered_dict
    
    def info(self, msg: str, **kwargs):
        """記錄 INFO 級別日誌"""
        kwargs = self._prepare_log_data(kwargs)
        self.logger.info(msg, **kwargs)
    
    def warning(self, msg: str, **kwargs):
        """記錄 WARNING 級別日誌"""
        kwargs = self._prepare_log_data(kwargs)
        self.logger.warning(msg, **kwargs)
    
    def error(self, msg: str, **kwargs):
        """記錄 ERROR 級別日誌"""
        kwargs = self._prepare_log_data(kwargs)
        self.logger.error(msg, **kwargs)
    
    def debug(self, msg: str, **kwargs):
        """記錄 DEBUG 級別日誌"""
        # Debug 模式下可以選擇不過濾
        if settings.DEBUG and not self.filter_sensitive:
            self.logger.debug(msg, **kwargs)
        else:
            kwargs = self._prepare_log_data(kwargs)
            self.logger.debug(msg, **kwargs)
    
    def audit_log(self, action: str, user_id: Optional[str] = None, **kwargs):
        """
        審計日誌（用於安全相關操作）
        
        Args:
            action: 操作名稱
            user_id: 用戶 ID
            **kwargs: 其他數據
        """
        # 審計日誌需要保留一些信息但仍要過濾敏感數據
        audit_data = {
            'audit_action': action,
            'audit_timestamp': datetime.utcnow().isoformat(),
            'audit_user_hash': hashlib.sha256(str(user_id).encode()).hexdigest()[:16] if user_id else None,
            **self._prepare_log_data(kwargs)
        }
        
        self.logger.info(f"AUDIT: {action}", **audit_data)


# 創建全局安全日誌記錄器
secure_logger = SecureLogger("ga_plus", filter_sensitive=True)


# 日誌裝飾器
def log_function_call(
    log_args: bool = True,
    log_result: bool = False,
    sensitive_args: Optional[List[str]] = None
):
    """
    函數調用日誌裝飾器
    
    Args:
        log_args: 是否記錄參數
        log_result: 是否記錄結果
        sensitive_args: 敏感參數名稱列表
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # 準備日誌數據
            log_data = {
                'function': func.__name__,
                'module': func.__module__
            }
            
            if log_args:
                # 過濾敏感參數
                filtered_kwargs = {}
                for k, v in kwargs.items():
                    if sensitive_args and k in sensitive_args:
                        filtered_kwargs[k] = "***SENSITIVE***"
                    else:
                        filtered_kwargs[k] = v
                
                log_data['args'] = args
                log_data['kwargs'] = filtered_kwargs
            
            secure_logger.info(f"Calling {func.__name__}", **log_data)
            
            try:
                result = await func(*args, **kwargs)
                
                if log_result:
                    log_data['result'] = result
                    secure_logger.info(f"Completed {func.__name__}", **log_data)
                
                return result
                
            except Exception as e:
                log_data['error'] = str(e)
                log_data['error_type'] = e.__class__.__name__
                secure_logger.error(f"Failed {func.__name__}", **log_data)
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # 同步版本的包裝器
            log_data = {
                'function': func.__name__,
                'module': func.__module__
            }
            
            if log_args:
                filtered_kwargs = {}
                for k, v in kwargs.items():
                    if sensitive_args and k in sensitive_args:
                        filtered_kwargs[k] = "***SENSITIVE***"
                    else:
                        filtered_kwargs[k] = v
                
                log_data['args'] = args
                log_data['kwargs'] = filtered_kwargs
            
            secure_logger.info(f"Calling {func.__name__}", **log_data)
            
            try:
                result = func(*args, **kwargs)
                
                if log_result:
                    log_data['result'] = result
                    secure_logger.info(f"Completed {func.__name__}", **log_data)
                
                return result
                
            except Exception as e:
                log_data['error'] = str(e)
                log_data['error_type'] = e.__class__.__name__
                secure_logger.error(f"Failed {func.__name__}", **log_data)
                raise
        
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


# 設置全局日誌配置
def setup_secure_logging():
    """設置安全的日誌配置"""
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
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )