"""
GA+ 資料庫連接管理

使用 SQLAlchemy 管理 PostgreSQL 連接
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator
import structlog

from app.core.config import settings

logger = structlog.get_logger()

# 創建資料庫引擎
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=300,
    echo=settings.DEBUG
)

# 創建會話工廠
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 創建基礎模型類
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    獲取資料庫會話
    
    Yields:
        Session: SQLAlchemy 會話
    """
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error("Database session error", error=str(e))
        db.rollback()
        raise
    finally:
        db.close()


def create_tables():
    """
    創建所有資料庫表
    """
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error("Failed to create database tables", error=str(e))
        raise


def drop_tables():
    """
    刪除所有資料庫表（僅用於開發）
    """
    if settings.ENVIRONMENT == "development":
        Base.metadata.drop_all(bind=engine)
        logger.info("Database tables dropped")
    else:
        logger.warning("Cannot drop tables in non-development environment") 