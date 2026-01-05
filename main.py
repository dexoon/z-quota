import asyncio
import json
import os
import sys

import sqlalchemy as sa
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from dotenv import load_dotenv
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from db_models import ModelUsage, ToolUsage, QuotaLimit, ModelUsageTimeSeries, async_session
from db_usage import save_usage_to_db

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

bot = Bot(token=TELEGRAM_BOT_TOKEN) if TELEGRAM_BOT_TOKEN else None
dp = Dispatcher()


def format_usage_from_db(model, tool, quotas):
    """Format usage data from database models."""
    lines = ["<b>📊 Usage Report (from database)</b>\n"]

    if model:
        lines.append("<b>Model Usage:</b>")
        lines.append(f"• Total Calls: {model.total_model_call_count}")
        lines.append(f"• Total Tokens: {model.total_tokens_usage:,}")

        # Show time series data (last 5 entries from relationship)
        if model.time_series:
            lines.append(f"\n<b>Recent Activity:</b>")
            # Sort by time and get last 5
            sorted_series = sorted(model.time_series, key=lambda x: x.time, reverse=True)[:5]
            for ts in sorted_series:
                # Format datetime: "2026-01-05 20:00"
                time_str = ts.time.strftime("%m-%d %H:%M")
                call_count = ts.call_count if ts.call_count is not None else "N/A"
                lines.append(f"  • {time_str}: {call_count} calls")
        lines.append("")

    if tool:
        lines.append("<b>Tool Usage:</b>")
        lines.append(f"• Total Search: {tool.total_search_mcp_count}")
        tool_details = json.loads(tool.tool_details_json) if tool.tool_details_json else []
        for detail in tool_details:
            lines.append(f"  - {detail.get('modelName', 'N/A')}: {detail.get('totalUsageCount', 0)}")
        lines.append("")

    if quotas:
        lines.append("<b>Quota Limits:</b>")
        for quota in quotas:
            lines.append(f"• {quota.type}: {quota.percentage}%")
            if quota.current_usage is not None:
                lines.append(f"  - Current: {quota.current_usage}/{quota.total}")

    return "\n".join(lines)


async def get_latest_usage_from_db():
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

        return latest_model, latest_tool, latest_quotas


@dp.message(Command("usage"))
async def send_usage_command(message: types.Message):
    try:
        model, tool, quotas = await get_latest_usage_from_db()

        if not model and not tool and not quotas:
            await message.answer("No usage data available in database yet.")
            return

        text = format_usage_from_db(model, tool, quotas)
        await message.answer(text, parse_mode="HTML")
    except Exception as e:
        await message.answer(f"Error: {e}")


async def send_periodic_report():
    """Fetch usage data, save to database, and send report to CHAT_ID."""
    if not bot or not CHAT_ID:
        print("Bot token or Chat ID not configured")
        return

    try:
        # Fetch and save usage data to database
        await save_usage_to_db()

        # Get latest data and send report
        model, tool, quotas = await get_latest_usage_from_db()

        if not model and not tool and not quotas:
            print("No usage data available")
            return

        text = format_usage_from_db(model, tool, quotas)
        await bot.send_message(chat_id=CHAT_ID, text=text, parse_mode="HTML")
        print(f"Periodic report sent to {CHAT_ID}")
    except Exception as e:
        print(f"Failed to send periodic report: {e}")


async def scheduler_task(interval_seconds: int = 60):
    """Background task that runs the periodic report every interval."""
    while True:
        try:
            await send_periodic_report()
        except Exception as e:
            print(f"Scheduler error: {e}")

        # Wait for the next interval
        await asyncio.sleep(interval_seconds)


async def main():
    if not TELEGRAM_BOT_TOKEN:
        print("TELEGRAM_BOT_TOKEN not set in .env")
        return

    # Start the scheduler in the background
    scheduler = asyncio.create_task(scheduler_task(60))
    print("Scheduler started: sending reports every 60 seconds")

    # Start bot polling (this blocks)
    print("Starting bot polling...")
    try:
        await dp.start_polling(bot)
    finally:
        # Cancel scheduler when bot stops
        scheduler.cancel()
        try:
            await scheduler
        except asyncio.CancelledError:
            pass


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutting down...")
        sys.exit(0)
