"""
GA+ 安全認證功能

包含密碼加密、JWT 令牌生成等安全相關功能
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from passlib.context import CryptContext
from jose import JWTError, jwt
import structlog

from app.core.config import settings

logger = structlog.get_logger()

# 密碼加密上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    驗證密碼
    
    Args:
        plain_password: 明文密碼
        hashed_password: 加密後的密碼
        
    Returns:
        bool: 密碼是否正確
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    加密密碼
    
    Args:
        password: 明文密碼
        
    Returns:
        str: 加密後的密碼
    """
    return pwd_context.hash(password)


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    創建 JWT 訪問令牌
    
    Args:
        data: 要編碼的數據
        expires_delta: 過期時間增量
        
    Returns:
        str: JWT 令牌
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    
    try:
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        return encoded_jwt
    except Exception as e:
        logger.error("Failed to create access token", error=str(e))
        raise


def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """
    驗證 JWT 令牌
    
    Args:
        token: JWT 令牌
        
    Returns:
        Optional[Dict[str, Any]]: 解碼後的數據，如果無效則返回 None
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError as e:
        logger.warning("Invalid token", error=str(e))
        return None
    except Exception as e:
        logger.error("Token verification error", error=str(e))
        return None


def get_user_id_from_token(token: str) -> Optional[int]:
    """
    從 JWT 令牌中獲取用戶 ID
    
    Args:
        token: JWT 令牌
        
    Returns:
        Optional[int]: 用戶 ID，如果無效則返回 None
    """
    payload = verify_token(token)
    if payload:
        return payload.get("user_id")
    return None 