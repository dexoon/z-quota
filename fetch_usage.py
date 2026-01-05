import os
import sys
import json
import asyncio
import urllib.parse
from datetime import datetime, timedelta
import aiohttp
from dotenv import load_dotenv
from models import ModelUsageResponse, ToolUsageResponse, QuotaLimitResponse

# Load environment variables
load_dotenv()

ANTHROPIC_BASE_URL = os.getenv("ANTHROPIC_BASE_URL", "")
ANTHROPIC_AUTH_TOKEN = os.getenv("ANTHROPIC_AUTH_TOKEN", "")


def get_urls():
    parsed_url = urllib.parse.urlparse(ANTHROPIC_BASE_URL)
    base_domain = f"{parsed_url.scheme}://{parsed_url.netloc}"

    if "api.z.ai" in ANTHROPIC_BASE_URL or "bigmodel.cn" in ANTHROPIC_BASE_URL:
        return {
            "model": f"{base_domain}/api/monitor/usage/model-usage",
            "tool": f"{base_domain}/api/monitor/usage/tool-usage",
            "quota": f"{base_domain}/api/monitor/usage/quota/limit",
            "platform": "ZAI" if "api.z.ai" in ANTHROPIC_BASE_URL else "ZHIPU",
        }
    return None


def process_quota_limit(data):
    if not data or "limits" not in data:
        return data

    new_limits = []
    for item in data["limits"]:
        if item.get("type") == "TOKENS_LIMIT":
            new_limits.append(
                {"type": "Token usage(5 Hour)", "percentage": item.get("percentage")}
            )
        elif item.get("type") == "TIME_LIMIT":
            new_limits.append(
                {
                    "type": "MCP usage(1 Month)",
                    "percentage": item.get("percentage"),
                    "currentUsage": item.get("currentValue"),
                    "totol": item.get("usage"),
                    "usageDetails": item.get("usageDetails"),
                }
            )
        else:
            new_limits.append(item)

    return {"limits": new_limits}


class UsageFetcher:
    def __init__(self, base_url=None, auth_token=None):
        self.base_url = base_url or ANTHROPIC_BASE_URL
        self.auth_token = auth_token or ANTHROPIC_AUTH_TOKEN
        self.urls = get_urls()
        self.headers = {
            "Authorization": self.auth_token,
            "Accept-Language": "en-US,en",
            "Content-Type": "application/json",
        }

    async def fetch_all(self):
        if not self.urls:
            raise ValueError("Unsupported or missing ANTHROPIC_BASE_URL")

        now = datetime.now()
        start_date = (now - timedelta(days=1)).replace(
            minute=0, second=0, microsecond=0
        )
        end_date = now.replace(minute=59, second=59, microsecond=999999)
        fmt = "%Y-%m-%d %H:%M:%S"
        params = {
            "startTime": start_date.strftime(fmt),
            "endTime": end_date.strftime(fmt),
        }

        async with aiohttp.ClientSession(headers=self.headers) as session:

            async def get_json(url, p=None):
                async with session.get(url, params=p) as resp:
                    if resp.status != 200:
                        text = await resp.text()
                        raise Exception(f"HTTP {resp.status}: {text}")
                    return await resp.json()

            model_data = await get_json(self.urls["model"], params)
            tool_data = await get_json(self.urls["tool"], params)
            quota_data = await get_json(self.urls["quota"])

            processed_quota = process_quota_limit(quota_data.get("data", quota_data))

            return {
                "model": ModelUsageResponse.model_validate(
                    model_data.get("data", model_data)
                ),
                "tool": ToolUsageResponse.model_validate(
                    tool_data.get("data", tool_data)
                ),
                "quota": QuotaLimitResponse.model_validate(processed_quota),
            }


async def main():
    fetcher = UsageFetcher()
    try:
        results = await fetcher.fetch_all()
        print("Model Usage:", results["model"].total_usage)
        print("Tool Usage:", results["tool"].total_usage)
        print("Quota Limits:", results["quota"].limits)
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
