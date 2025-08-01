"""
共用工具函數

抽取重複使用的邏輯
"""

from typing import Dict, Any, List, Optional, TypeVar, Callable
from datetime import datetime, timedelta
import hashlib
import json
import re
from functools import wraps
import asyncio
import structlog

logger = structlog.get_logger()

T = TypeVar('T')


# ========================================
# 時間處理工具
# ========================================

class DateRangeHelper:
    """日期範圍處理助手"""
    
    @staticmethod
    def parse_date_range(date_range: str) -> Dict[str, str]:
        """
        解析日期範圍字符串
        
        Args:
            date_range: 日期範圍 (如 "last_7_days", "yesterday")
            
        Returns:
            包含 start_date 和 end_date 的字典
        """
        today = datetime.now().date()
        
        if date_range == "today":
            return {
                "start_date": str(today),
                "end_date": str(today)
            }
        
        elif date_range == "yesterday":
            yesterday = today - timedelta(days=1)
            return {
                "start_date": str(yesterday),
                "end_date": str(yesterday)
            }
        
        elif date_range == "this_week":
            # 本週一到今天
            days_since_monday = today.weekday()
            start_of_week = today - timedelta(days=days_since_monday)
            return {
                "start_date": str(start_of_week),
                "end_date": str(today)
            }
        
        elif date_range == "this_month":
            # 本月第一天到今天
            start_of_month = today.replace(day=1)
            return {
                "start_date": str(start_of_month),
                "end_date": str(today)
            }
        
        elif date_range.startswith("last_") and date_range.endswith("_days"):
            # 解析 last_X_days 格式
            match = re.match(r'last_(\d+)_days', date_range)
            if match:
                days = int(match.group(1))
                start_date = today - timedelta(days=days-1)
                return {
                    "start_date": str(start_date),
                    "end_date": str(today)
                }
        
        # 默認返回最近30天
        return {
            "start_date": str(today - timedelta(days=29)),
            "end_date": str(today)
        }
    
    @staticmethod
    def format_ga4_date(date: datetime) -> str:
        """格式化為 GA4 API 接受的日期格式"""
        return date.strftime("%Y-%m-%d")
    
    @staticmethod
    def days_ago(days: int) -> str:
        """獲取幾天前的日期字符串"""
        date = datetime.now().date() - timedelta(days=days)
        return str(date)


# ========================================
# 雜湊和加密工具
# ========================================

class HashHelper:
    """雜湊處理助手"""
    
    @staticmethod
    def generate_cache_key(data: Dict[str, Any], prefix: str = "") -> str:
        """
        生成穩定的快取鍵
        
        Args:
            data: 要雜湊的數據
            prefix: 鍵前綴
            
        Returns:
            快取鍵
        """
        # 排序並序列化數據以確保穩定性
        sorted_data = json.dumps(data, sort_keys=True, ensure_ascii=False)
        hash_value = hashlib.sha256(sorted_data.encode('utf-8')).hexdigest()[:16]
        
        return f"{prefix}:{hash_value}" if prefix else hash_value
    
    @staticmethod
    def hash_password(password: str) -> str:
        """生成密碼雜湊（簡化示例）"""
        # 實際應用中應使用 bcrypt 或類似的安全雜湊
        return hashlib.sha256(password.encode('utf-8')).hexdigest()


# ========================================
# 數據處理工具
# ========================================

class DataProcessor:
    """數據處理助手"""
    
    @staticmethod
    def flatten_dict(d: Dict[str, Any], parent_key: str = '', sep: str = '.') -> Dict[str, Any]:
        """
        扁平化嵌套字典
        
        Args:
            d: 要扁平化的字典
            parent_key: 父鍵
            sep: 分隔符
            
        Returns:
            扁平化的字典
        """
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(DataProcessor.flatten_dict(v, new_key, sep=sep).items())
            else:
                items.append((new_key, v))
        return dict(items)
    
    @staticmethod
    def safe_get(data: Dict[str, Any], path: str, default: Any = None) -> Any:
        """
        安全獲取嵌套字典值
        
        Args:
            data: 數據字典
            path: 路徑 (如 "user.profile.name")
            default: 默認值
            
        Returns:
            值或默認值
        """
        keys = path.split('.')
        value = data
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        
        return value
    
    @staticmethod
    def chunk_list(lst: List[T], chunk_size: int) -> List[List[T]]:
        """
        將列表分塊
        
        Args:
            lst: 要分塊的列表
            chunk_size: 塊大小
            
        Returns:
            分塊後的列表
        """
        return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]


# ========================================
# 異步工具
# ========================================

class AsyncHelper:
    """異步處理助手"""
    
    @staticmethod
    async def run_with_timeout(
        coro: Callable, 
        timeout: float, 
        default: Any = None
    ) -> Any:
        """
        帶超時的異步執行
        
        Args:
            coro: 協程
            timeout: 超時秒數
            default: 超時時返回的默認值
            
        Returns:
            執行結果或默認值
        """
        try:
            return await asyncio.wait_for(coro, timeout=timeout)
        except asyncio.TimeoutError:
            logger.warning("Async operation timeout", timeout=timeout)
            return default
    
    @staticmethod
    async def gather_with_concurrency(
        coros: List[Callable],
        max_concurrent: int = 5
    ) -> List[Any]:
        """
        限制並發的批量異步執行
        
        Args:
            coros: 協程列表
            max_concurrent: 最大並發數
            
        Returns:
            結果列表
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def run_with_semaphore(coro):
            async with semaphore:
                return await coro
        
        return await asyncio.gather(
            *[run_with_semaphore(coro) for coro in coros],
            return_exceptions=True
        )


# ========================================
# 裝飾器工具
# ========================================

def retry_async(max_attempts: int = 3, delay: float = 1.0):
    """
    異步重試裝飾器
    
    Args:
        max_attempts: 最大重試次數
        delay: 重試延遲（秒）
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        await asyncio.sleep(delay * (2 ** attempt))
                        logger.warning(
                            "Retrying after error",
                            func=func.__name__,
                            attempt=attempt + 1,
                            error=str(e)
                        )
            
            raise last_exception
        
        return wrapper
    return decorator


def measure_time(func):
    """測量執行時間的裝飾器"""
    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        start_time = asyncio.get_event_loop().time()
        try:
            result = await func(*args, **kwargs)
            elapsed = asyncio.get_event_loop().time() - start_time
            logger.info(
                "Function executed",
                func=func.__name__,
                elapsed_time=f"{elapsed:.3f}s"
            )
            return result
        except Exception as e:
            elapsed = asyncio.get_event_loop().time() - start_time
            logger.error(
                "Function failed",
                func=func.__name__,
                elapsed_time=f"{elapsed:.3f}s",
                error=str(e)
            )
            raise
    
    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        import time
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            elapsed = time.time() - start_time
            logger.info(
                "Function executed",
                func=func.__name__,
                elapsed_time=f"{elapsed:.3f}s"
            )
            return result
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(
                "Function failed",
                func=func.__name__,
                elapsed_time=f"{elapsed:.3f}s",
                error=str(e)
            )
            raise
    
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    else:
        return sync_wrapper


# ========================================
# 驗證工具
# ========================================

class ValidationHelper:
    """驗證助手"""
    
    @staticmethod
    def is_valid_email(email: str) -> bool:
        """驗證電子郵件格式"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    @staticmethod
    def is_valid_ga4_property_id(property_id: str) -> bool:
        """驗證 GA4 屬性 ID"""
        return bool(re.match(r'^\d{9,12}$', property_id))
    
    @staticmethod
    def sanitize_string(
        value: str,
        max_length: int = 1000,
        allowed_chars: Optional[str] = None
    ) -> str:
        """
        清理字符串
        
        Args:
            value: 要清理的字符串
            max_length: 最大長度
            allowed_chars: 允許的字符正則表達式
            
        Returns:
            清理後的字符串
        """
        # 移除控制字符
        value = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', value)
        
        # 截斷長度
        if len(value) > max_length:
            value = value[:max_length]
        
        # 如果指定了允許的字符，過濾
        if allowed_chars:
            value = re.sub(f'[^{allowed_chars}]', '', value)
        
        return value.strip()


# ========================================
# 格式化工具
# ========================================

class Formatter:
    """格式化助手"""
    
    @staticmethod
    def format_number(num: float, decimals: int = 2) -> str:
        """格式化數字（帶千位分隔符）"""
        return f"{num:,.{decimals}f}"
    
    @staticmethod
    def format_percentage(value: float, decimals: int = 1) -> str:
        """格式化百分比"""
        return f"{value * 100:.{decimals}f}%"
    
    @staticmethod
    def format_duration(seconds: float) -> str:
        """格式化持續時間"""
        if seconds < 60:
            return f"{seconds:.1f}秒"
        elif seconds < 3600:
            minutes = seconds / 60
            return f"{minutes:.1f}分鐘"
        else:
            hours = seconds / 3600
            return f"{hours:.1f}小時"
    
    @staticmethod
    def format_bytes(bytes_size: int) -> str:
        """格式化字節大小"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_size < 1024.0:
                return f"{bytes_size:.2f} {unit}"
            bytes_size /= 1024.0
        return f"{bytes_size:.2f} PB"