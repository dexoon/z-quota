import asyncio
import json
from datetime import datetime, timezone, timedelta

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from fetch_usage import UsageFetcher
from db_models import (
    ModelUsage,
    ModelUsageTimeSeries,
    ToolUsage,
    QuotaLimit,
    async_session,
)
from models import ModelUsageResponse


async def save_usage_to_db():
    """Fetch usage data and save to database."""
    fetcher = UsageFetcher()

    async with async_session() as session:
        try:
            data = await fetcher.fetch_all()

            # Save model usage (parent)
            model_response = data["model"]  # This is ModelUsageResponse
            model = ModelUsage(
                total_model_call_count=model_response.total_usage.total_model_call_count,
                total_tokens_usage=model_response.total_usage.total_tokens_usage,
            )
            session.add(model)
            await session.flush()  # Get the ID

            # Save time series data (child records) - using Pydantic's parsed data
            for point in model_response.parsed_time_series:
                time_series = ModelUsageTimeSeries(
                    model_usage_id=model.id,
                    time=point.time,
                    call_count=point.call_count,
                    tokens_usage=point.tokens_usage,
                )
                session.add(time_series)

            # Save tool usage
            tool = ToolUsage(
                total_network_search_count=data["tool"].total_usage.total_network_search_count,
                total_web_read_mcp_count=data["tool"].total_usage.total_web_read_mcp_count,
                total_zread_mcp_count=data["tool"].total_usage.total_zread_mcp_count,
                total_search_mcp_count=data["tool"].total_usage.total_search_mcp_count,
                tool_details_json=json.dumps(
                    [detail.model_dump() for detail in data["tool"].total_usage.tool_details]
                ),
                x_time_json=json.dumps(data["tool"].x_time),
            )
            session.add(tool)

            # Save quota limits
            for limit in data["quota"].limits:
                quota = QuotaLimit(
                    type=limit.type,
                    percentage=float(limit.percentage),
                    current_usage=limit.current_usage,
                    total=limit.total,
                    usage_details_json=json.dumps([ud.model_dump() for ud in limit.usage_details]) if limit.usage_details else None,
                )
                session.add(quota)

            await session.commit()
            print(f"Saved usage data at {model.created_at}")

        except Exception as e:
            await session.rollback()
            print(f"Error saving to database: {e}")
            raise


async def get_latest_usage() -> dict:
    """Get the latest usage data from database."""
    async with async_session() as session:
        # Get latest model usage with time series
        model_result = await session.execute(
            select(ModelUsage)
            .options(selectinload(ModelUsage.time_series))
            .order_by(ModelUsage.created_at.desc())
            .limit(1)
        )
        latest_model = model_result.scalar_one_or_none()

        # Get latest tool usage
        tool_result = await session.execute(
            select(ToolUsage)
            .order_by(ToolUsage.created_at.desc())
            .limit(1)
        )
        latest_tool = tool_result.scalar_one_or_none()

        # Get latest quota limits (group by type and get latest of each)
        from sqlalchemy import func
        subq = (
            select(QuotaLimit.type, func.max(QuotaLimit.id).label("max_id"))
            .group_by(QuotaLimit.type)
            .subquery()
        )
        quota_result = await session.execute(
            select(QuotaLimit).join(
                subq, (QuotaLimit.id == subq.c.max_id) & (QuotaLimit.type == subq.c.type)
            )
        )
        latest_quotas = quota_result.scalars().all()

        return {
            "model": latest_model,
            "tool": latest_tool,
            "quotas": latest_quotas,
        }


if __name__ == "__main__":
    asyncio.run(save_usage_to_db())
