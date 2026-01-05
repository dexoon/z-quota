import os
from datetime import datetime, timezone, timedelta
from typing import Optional, List
from enum import Enum

import sqlmodel as sqlm
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy import ForeignKey, DateTime
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# Convert postgresql:// to postgresql+asyncpg:// for async connection
if DATABASE_URL and DATABASE_URL.startswith("postgresql://"):
    ASYNC_DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
else:
    ASYNC_DATABASE_URL = DATABASE_URL


engine = create_async_engine(ASYNC_DATABASE_URL, echo=False)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


# Beijing timezone (UTC+8)
BEIJING_TZ = timezone(timedelta(hours=8))


class ModelUsage(sqlm.SQLModel, table=True):
    """Model usage statistics snapshot (parent)."""

    __tablename__ = "model_usage"

    id: Optional[int] = sqlm.Field(default=None, primary_key=True)
    created_at: datetime = sqlm.Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_type=DateTime(timezone=True)
    )

    total_model_call_count: int = sqlm.Field(index=True)
    total_tokens_usage: int = sqlm.Field(index=True)

    # Relationship to child time series records
    time_series: List["ModelUsageTimeSeries"] = sqlm.Relationship(back_populates="model_usage")


class ModelUsageTimeSeries(sqlm.SQLModel, table=True):
    """Individual time series data point for model usage (child)."""

    __tablename__ = "model_usage_time_series"

    id: Optional[int] = sqlm.Field(default=None, primary_key=True)
    created_at: datetime = sqlm.Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_type=DateTime(timezone=True)
    )

    # Foreign key to parent
    model_usage_id: int = sqlm.Field(foreign_key="model_usage.id")
    model_usage: ModelUsage = sqlm.Relationship(back_populates="time_series")

    # Time series data - Beijing timezone (converted from API string like "2026-01-05 20:00")
    time: datetime = sqlm.Field(sa_type=DateTime(timezone=True))
    call_count: Optional[int] = None
    tokens_usage: Optional[int] = None


class ToolUsage(sqlm.SQLModel, table=True):
    """Tool usage statistics snapshot."""

    __tablename__ = "tool_usage"

    id: Optional[int] = sqlm.Field(default=None, primary_key=True)
    created_at: datetime = sqlm.Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_type=DateTime(timezone=True)
    )

    total_network_search_count: int
    total_web_read_mcp_count: int
    total_zread_mcp_count: int
    total_search_mcp_count: int

    tool_details_json: str = sqlm.Field()  # JSON list of ToolDetail
    x_time_json: str = sqlm.Field()  # JSON list of timestamps


class QuotaLimit(sqlm.SQLModel, table=True):
    """Quota limit snapshot."""

    __tablename__ = "quota_limit"

    id: Optional[int] = sqlm.Field(default=None, primary_key=True)
    created_at: datetime = sqlm.Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_type=DateTime(timezone=True)
    )

    type: str = sqlm.Field(index=True)
    percentage: float = sqlm.Field(index=True)
    current_usage: Optional[int] = None
    total: Optional[int] = None

    usage_details_json: Optional[str] = None  # JSON list of QuotaUsageDetail


async def get_session() -> AsyncSession:
    async with async_session() as session:
        yield session


async def init_db():
    """Initialize database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(sqlm.SQLModel.metadata.create_all)
