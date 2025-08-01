"""
用戶管理端點

提供用戶註冊、認證和管理功能
"""

from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, EmailStr
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from datetime import datetime
import structlog

from app.core.config import settings
from app.core.dependencies import get_database
from app.core.security import verify_password, get_password_hash, create_access_token
from app.models.user import User, SubscriptionTier
from app.core.rate_limiter import limiter, RateLimits

router = APIRouter()
logger = structlog.get_logger()


class UserCreate(BaseModel):
    """用戶創建模型"""
    email: EmailStr
    password: str
    name: str
    company: Optional[str] = None


class UserLogin(BaseModel):
    """用戶登入模型"""
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """用戶回應模型"""
    id: str
    email: str
    name: str
    company: Optional[str] = None
    subscription_tier: str
    created_at: str
    last_login: Optional[str] = None


@router.post("/register", response_model=UserResponse)
@limiter.limit(RateLimits.REGISTER)
async def register_user(
    user: UserCreate,
    db: Session = Depends(get_database)
) -> UserResponse:
    """
    用戶註冊
    
    Args:
        user: 用戶創建資訊
        db: 資料庫會話
        
    Returns:
        創建的用戶資訊
    """
    try:
        # 1. 檢查郵箱是否已存在
        existing_user = db.query(User).filter(User.email == user.email).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # 2. 加密密碼
        hashed_password = get_password_hash(user.password)
        
        # 3. 創建用戶記錄
        db_user = User(
            email=user.email,
            name=user.name,
            company=user.company,
            password_hash=hashed_password,
            subscription_tier=SubscriptionTier.FREE,
            query_limit=settings.FREE_TIER_QUERY_LIMIT
        )
        
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        
        logger.info("User registered successfully", email=user.email, user_id=db_user.id)
        
        # 4. 返回用戶資訊（不包含密碼）
        return UserResponse(
            id=str(db_user.id),
            email=db_user.email,
            name=db_user.name,
            company=db_user.company,
            subscription_tier=db_user.subscription_tier.value,
            created_at=db_user.created_at.isoformat(),
            last_login=None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error("User registration failed", email=user.email, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Failed to register user", "message": str(e)}
        )


@router.post("/login")
async def login_user(
    user: UserLogin,
    db: Session = Depends(get_database)
) -> Dict[str, Any]:
    """
    用戶登入
    
    Args:
        user: 用戶登入資訊
        db: 資料庫會話
        
    Returns:
        登入結果和訪問令牌
    """
    try:
        # 1. 查找用戶
        db_user = db.query(User).filter(User.email == user.email).first()
        if not db_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # 2. 驗證密碼
        if not verify_password(user.password, db_user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # 3. 檢查用戶是否啟用
        if not db_user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account is disabled"
            )
        
        # 4. 生成 JWT 令牌
        access_token = create_access_token(
            data={"user_id": db_user.id, "email": db_user.email}
        )
        
        # 5. 更新最後登入時間
        db_user.last_login = datetime.utcnow()
        db.commit()
        
        logger.info("User logged in successfully", email=user.email, user_id=db_user.id)
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "user": {
                "id": str(db_user.id),
                "email": db_user.email,
                "name": db_user.name,
                "subscription_tier": db_user.subscription_tier.value
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("User login failed", email=user.email, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Login failed", "message": str(e)}
        )


@router.get("/profile", response_model=UserResponse)
async def get_user_profile() -> UserResponse:
    """
    獲取用戶個人資料
    
    Returns:
        用戶個人資料
    """
    try:
        # TODO: 實現從 JWT 令牌獲取用戶資訊
        return UserResponse(
            id="user_123",
            email="user@example.com",
            name="Example User",
            company="Example Company",
            subscription_tier="free",
            created_at="2024-01-21T10:00:00Z",
            last_login="2024-01-21T09:30:00Z"
        )
    except Exception as e:
        logger.error("Failed to get user profile", error=str(e))
        raise HTTPException(
            status_code=401,
            detail={"error": "Failed to get user profile", "message": str(e)}
        )


@router.put("/profile")
async def update_user_profile() -> Dict[str, Any]:
    """
    更新用戶個人資料
    
    Returns:
        更新結果
    """
    try:
        # TODO: 實現用戶資料更新邏輯
        return {
            "status": "success",
            "message": "User profile updated successfully"
        }
    except Exception as e:
        logger.error("Failed to update user profile", error=str(e))
        raise HTTPException(
            status_code=400,
            detail={"error": "Failed to update user profile", "message": str(e)}
        )


@router.get("/subscription")
async def get_user_subscription() -> Dict[str, Any]:
    """
    獲取用戶訂閱資訊
    
    Returns:
        訂閱資訊
    """
    try:
        # TODO: 實現訂閱資訊查詢
        return {
            "tier": "free",
            "plan": "Free Plan",
            "query_limit": 1000,
            "queries_used": 150,
            "queries_remaining": 850,
            "billing_cycle": "monthly",
            "next_billing_date": "2024-02-21T00:00:00Z",
            "features": [
                "basic_analytics",
                "natural_language_queries",
                "email_support"
            ]
        }
    except Exception as e:
        logger.error("Failed to get subscription info", error=str(e))
        raise HTTPException(
            status_code=500,
            detail={"error": "Failed to get subscription info", "message": str(e)}
        ) 