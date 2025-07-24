"""
日期處理工具

處理日期範圍和時間相關的轉換
"""

from datetime import datetime, timedelta
from typing import Dict, Any, List
import re


def parse_date_range(date_range: str) -> Dict[str, str]:
    """
    解析日期範圍字符串
    
    Args:
        date_range: 日期範圍字符串
        
    Returns:
        包含開始和結束日期的字典
    """
    today = datetime.now()
    
    date_patterns = {
        "today": {"start_date": "today", "end_date": "today"},
        "yesterday": {"start_date": "yesterday", "end_date": "yesterday"},
        "last_7_days": {"start_date": "7daysAgo", "end_date": "today"},
        "last_30_days": {"start_date": "30daysAgo", "end_date": "today"},
        "last_90_days": {"start_date": "90daysAgo", "end_date": "today"},
        "last_month": {
            "start_date": (today.replace(day=1) - timedelta(days=1)).replace(day=1).strftime("%Y-%m-%d"),
            "end_date": (today.replace(day=1) - timedelta(days=1)).strftime("%Y-%m-%d")
        },
        "this_month": {
            "start_date": today.replace(day=1).strftime("%Y-%m-%d"),
            "end_date": "today"
        },
        "last_year": {
            "start_date": f"{today.year - 1}-01-01",
            "end_date": f"{today.year - 1}-12-31"
        },
        "this_year": {
            "start_date": f"{today.year}-01-01",
            "end_date": "today"
        }
    }
    
    return date_patterns.get(date_range, date_patterns["last_30_days"])


def format_date_for_ga4(date_str: str) -> str:
    """
    格式化日期為 GA4 格式
    
    Args:
        date_str: 日期字符串
        
    Returns:
        GA4 格式的日期字符串
    """
    # 處理相對日期
    if date_str in ["today", "yesterday"]:
        return date_str
    
    # 處理相對天數
    if re.match(r"\d+daysAgo", date_str):
        return date_str
    
    # 處理絕對日期
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        return date_obj.strftime("%Y-%m-%d")
    except ValueError:
        return "today"


def get_date_range_days(start_date: str, end_date: str) -> int:
    """
    計算日期範圍的天數
    
    Args:
        start_date: 開始日期
        end_date: 結束日期
        
    Returns:
        天數
    """
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        return (end - start).days + 1
    except ValueError:
        return 30


def is_valid_date_range(start_date: str, end_date: str) -> bool:
    """
    驗證日期範圍是否有效
    
    Args:
        start_date: 開始日期
        end_date: 結束日期
        
    Returns:
        是否有效
    """
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        return start <= end
    except ValueError:
        return False


def get_relative_date_range(days: int) -> Dict[str, str]:
    """
    獲取相對日期範圍
    
    Args:
        days: 天數
        
    Returns:
        日期範圍字典
    """
    return {
        "start_date": f"{days}daysAgo",
        "end_date": "today"
    }


def format_timestamp(timestamp: datetime) -> str:
    """
    格式化時間戳
    
    Args:
        timestamp: 時間戳
        
    Returns:
        格式化的時間字符串
    """
    return timestamp.strftime("%Y-%m-%d %H:%M:%S")


def get_time_period_label(date_range: str) -> str:
    """
    獲取時間週期標籤
    
    Args:
        date_range: 日期範圍
        
    Returns:
        時間週期標籤
    """
    labels = {
        "today": "今天",
        "yesterday": "昨天",
        "last_7_days": "過去7天",
        "last_30_days": "過去30天",
        "last_90_days": "過去90天",
        "last_month": "上個月",
        "this_month": "本月",
        "last_year": "去年",
        "this_year": "今年"
    }
    
    return labels.get(date_range, "自定義時間範圍") 