"""
增強的數據驗證模型

使用 Pydantic 實現嚴格的輸入驗證
"""

from pydantic import BaseModel, Field, validator, EmailStr
from typing import Dict, Any, List, Optional
from datetime import datetime
import re


class StrictChatRequest(BaseModel):
    """嚴格的聊天請求驗證模型"""
    
    message: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="用戶查詢消息"
    )
    property_id: Optional[str] = Field(
        None,
        regex=r"^\d{9,12}$",
        description="GA4 屬性 ID"
    )
    date_range: str = Field(
        "last_30_days",
        regex=r"^(today|yesterday|last_\d+_days|this_week|this_month|custom)$",
        description="日期範圍"
    )
    user_id: Optional[str] = Field(
        None,
        min_length=1,
        max_length=100
    )
    session_id: Optional[str] = Field(
        None,
        min_length=1,
        max_length=100
    )
    
    @validator('message')
    def validate_message(cls, v):
        """驗證消息內容"""
        # 清理空白
        v = v.strip()
        
        if not v:
            raise ValueError('Message cannot be empty')
        
        # 檢查是否包含危險字符
        dangerous_patterns = [
            r'<script',
            r'javascript:',
            r'onclick=',
            r'onerror=',
            r'DROP\s+TABLE',
            r'DELETE\s+FROM',
            r'INSERT\s+INTO'
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, v, re.IGNORECASE):
                raise ValueError('Message contains potentially dangerous content')
        
        return v
    
    @validator('date_range')
    def validate_date_range(cls, v):
        """驗證日期範圍"""
        valid_ranges = [
            "today", "yesterday", "this_week", "this_month", "custom"
        ]
        
        # 檢查預定義範圍
        if v in valid_ranges:
            return v
        
        # 檢查 last_X_days 格式
        match = re.match(r'^last_(\d+)_days$', v)
        if match:
            days = int(match.group(1))
            if 1 <= days <= 365:
                return v
            else:
                raise ValueError('Days must be between 1 and 365')
        
        raise ValueError(f'Invalid date range: {v}')
    
    class Config:
        schema_extra = {
            "example": {
                "message": "昨天有多少訪客？",
                "property_id": "123456789",
                "date_range": "yesterday"
            }
        }


class StrictUserCreate(BaseModel):
    """嚴格的用戶創建驗證模型"""
    
    email: EmailStr = Field(
        ...,
        description="用戶電子郵件"
    )
    password: str = Field(
        ...,
        min_length=8,
        max_length=100,
        description="用戶密碼"
    )
    name: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="用戶姓名"
    )
    company: Optional[str] = Field(
        None,
        max_length=200,
        description="公司名稱"
    )
    
    @validator('password')
    def validate_password(cls, v):
        """驗證密碼強度"""
        # 至少包含一個大寫字母
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        
        # 至少包含一個小寫字母
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        
        # 至少包含一個數字
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one digit')
        
        # 至少包含一個特殊字符
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError('Password must contain at least one special character')
        
        return v
    
    @validator('name')
    def validate_name(cls, v):
        """驗證姓名"""
        v = v.strip()
        
        # 只允許字母、空格和某些標點
        if not re.match(r'^[\w\s\-\.\']+$', v, re.UNICODE):
            raise ValueError('Name contains invalid characters')
        
        return v
    
    @validator('email')
    def validate_email_domain(cls, v):
        """額外的郵件驗證"""
        # 檢查是否為臨時郵箱域名
        temp_email_domains = [
            'tempmail.com', 'throwaway.email', 'guerrillamail.com',
            '10minutemail.com', 'mailinator.com'
        ]
        
        domain = v.split('@')[1].lower()
        if domain in temp_email_domains:
            raise ValueError('Temporary email addresses are not allowed')
        
        return v.lower()


class GA4QueryParams(BaseModel):
    """GA4 查詢參數驗證模型"""
    
    metrics: List[Dict[str, str]] = Field(
        ...,
        min_items=1,
        max_items=10,
        description="查詢指標"
    )
    dimensions: Optional[List[Dict[str, str]]] = Field(
        None,
        max_items=7,
        description="查詢維度"
    )
    date_ranges: List[Dict[str, str]] = Field(
        ...,
        min_items=1,
        max_items=2,
        description="日期範圍"
    )
    filters: Optional[Dict[str, Any]] = Field(
        None,
        description="過濾條件"
    )
    order_by: Optional[List[Dict[str, str]]] = Field(
        None,
        max_items=5,
        description="排序規則"
    )
    limit: int = Field(
        10,
        ge=1,
        le=10000,
        description="結果數量限制"
    )
    offset: int = Field(
        0,
        ge=0,
        description="結果偏移量"
    )
    
    @validator('metrics', each_item=True)
    def validate_metric(cls, v):
        """驗證單個指標"""
        if not isinstance(v, dict) or 'name' not in v:
            raise ValueError('Each metric must have a name')
        
        # 驗證指標名稱格式
        if not re.match(r'^[a-zA-Z][a-zA-Z0-9_]*$', v['name']):
            raise ValueError(f'Invalid metric name: {v["name"]}')
        
        return v
    
    @validator('dimensions', each_item=True)
    def validate_dimension(cls, v):
        """驗證單個維度"""
        if v is None:
            return v
            
        if not isinstance(v, dict) or 'name' not in v:
            raise ValueError('Each dimension must have a name')
        
        # 驗證維度名稱格式
        if not re.match(r'^[a-zA-Z][a-zA-Z0-9_]*$', v['name']):
            raise ValueError(f'Invalid dimension name: {v["name"]}')
        
        return v
    
    @validator('date_ranges', each_item=True)
    def validate_date_range_item(cls, v):
        """驗證日期範圍項目"""
        if not isinstance(v, dict):
            raise ValueError('Date range must be a dictionary')
        
        if 'start_date' not in v or 'end_date' not in v:
            raise ValueError('Date range must have start_date and end_date')
        
        # 驗證日期格式 (YYYY-MM-DD 或特殊值)
        date_pattern = r'^\d{4}-\d{2}-\d{2}$|^today$|^yesterday$|^\d+daysAgo$'
        
        for date_field in ['start_date', 'end_date']:
            if not re.match(date_pattern, v[date_field]):
                raise ValueError(f'Invalid date format: {v[date_field]}')
        
        return v


class PaginationParams(BaseModel):
    """分頁參數驗證模型"""
    
    page: int = Field(1, ge=1, le=1000)
    per_page: int = Field(20, ge=1, le=100)
    
    @property
    def offset(self) -> int:
        return (self.page - 1) * self.per_page
    
    @property
    def limit(self) -> int:
        return self.per_page


class SearchParams(BaseModel):
    """搜尋參數驗證模型"""
    
    query: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="搜尋查詢"
    )
    filters: Optional[Dict[str, Any]] = None
    sort_by: Optional[str] = Field(
        None,
        regex=r'^[a-zA-Z_]+$'
    )
    sort_order: str = Field(
        "desc",
        regex=r'^(asc|desc)$'
    )
    
    @validator('query')
    def sanitize_query(cls, v):
        """清理搜尋查詢"""
        # 移除特殊字符
        v = re.sub(r'[^\w\s\-\u4e00-\u9fff]', ' ', v)
        # 移除多餘空白
        v = ' '.join(v.split())
        return v


def sanitize_input(value: Any, max_length: int = 1000) -> str:
    """
    通用輸入清理函數
    
    Args:
        value: 輸入值
        max_length: 最大長度
        
    Returns:
        清理後的字符串
    """
    if value is None:
        return ""
    
    # 轉換為字符串
    value = str(value)
    
    # 截斷長度
    if len(value) > max_length:
        value = value[:max_length]
    
    # 移除控制字符
    value = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', value)
    
    # 清理多餘空白
    value = ' '.join(value.split())
    
    return value


def validate_date_string(date_str: str) -> bool:
    """
    驗證日期字符串格式
    
    Args:
        date_str: 日期字符串
        
    Returns:
        是否有效
    """
    try:
        # 嘗試解析標準格式
        datetime.strptime(date_str, '%Y-%m-%d')
        return True
    except ValueError:
        # 檢查特殊格式
        special_formats = ['today', 'yesterday']
        days_ago_pattern = r'^\d+daysAgo$'
        
        return date_str in special_formats or bool(re.match(days_ago_pattern, date_str))


def validate_property_id(property_id: str) -> bool:
    """
    驗證 GA4 屬性 ID
    
    Args:
        property_id: 屬性 ID
        
    Returns:
        是否有效
    """
    # GA4 屬性 ID 通常是 9-12 位數字
    return bool(re.match(r'^\d{9,12}$', property_id))