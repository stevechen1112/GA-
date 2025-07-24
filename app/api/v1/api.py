"""
GA+ API v1 主路由

整合所有 v1 版本的 API 路由
"""

from fastapi import APIRouter

from app.api.v1.endpoints import chat, analytics, users, health

api_router = APIRouter()

# 包含各個端點路由
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
api_router.include_router(users.router, prefix="/users", tags=["users"]) 