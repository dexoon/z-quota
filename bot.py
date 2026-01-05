import os
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from dotenv import load_dotenv
from fetch_usage import UsageFetcher

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

bot = Bot(token=TELEGRAM_BOT_TOKEN) if TELEGRAM_BOT_TOKEN else None
dp = Dispatcher()


def format_usage(data):
    model = data["model"]
    tool = data["tool"]
    quota = data["quota"]

    lines = ["<b>📊 Usage Report</b>\n"]

    lines.append("<b>Model Usage:</b>")
    lines.append(f"• Total Calls: {model.total_usage.total_model_call_count}")
    lines.append(f"• Total Tokens: {model.total_usage.total_tokens_usage:,}\n")

    lines.append("<b>Tool Usage:</b>")
    lines.append(f"• Total Search: {tool.total_usage.total_search_mcp_count}")
    for detail in tool.total_usage.tool_details:
        lines.append(f"  - {detail.model_name}: {detail.total_usage_count}")
    lines.append("")

    lines.append("<b>Quota Limits:</b>")
    for limit in quota.limits:
        lines.append(f"• {limit.type}: {limit.percentage}%")
        if limit.current_usage is not None:
            lines.append(f"  - Current: {limit.current_usage}/{limit.total}")

    return "\n".join(lines)


@dp.message(Command("usage"))
async def send_usage_command(message: types.Message):
    fetcher = UsageFetcher()
    try:
        data = await fetcher.fetch_all()
        text = format_usage(data)
        await message.answer(text, parse_mode="HTML")
    except Exception as e:
        await message.answer(f"Error: {e}")


async def send_notification():
    if not bot or not CHAT_ID:
        print("Bot token or Chat ID not configured")
        return

    fetcher = UsageFetcher()
    try:
        data = await fetcher.fetch_all()
        text = format_usage(data)
        await bot.send_message(chat_id=CHAT_ID, text=text, parse_mode="HTML")
        print(f"Notification sent to {CHAT_ID}")
    except Exception as e:
        print(f"Failed to send notification: {e}")


async def main():
    if not TELEGRAM_BOT_TOKEN:
        print("TELEGRAM_BOT_TOKEN not set in .env")
        return

    # If run as a script, we might want to just send a notification or start the bot
    # Let's do both for demonstration: send one notification and then start polling
    await send_notification()
    print("Starting bot polling...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
