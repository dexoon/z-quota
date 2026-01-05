import pytest
from fetch_usage import process_quota_limit, UsageFetcher
from models import ModelUsageResponse, ToolUsageResponse, QuotaLimitResponse


def test_process_quota_limit():
    raw_data = {
        "limits": [
            {"type": "TOKENS_LIMIT", "percentage": 10},
            {
                "type": "TIME_LIMIT",
                "percentage": 20,
                "currentValue": 5,
                "usage": 100,
                "usageDetails": [],
            },
        ]
    }
    processed = process_quota_limit(raw_data)
    assert len(processed["limits"]) == 2
    assert processed["limits"][0]["type"] == "Token usage(5 Hour)"
    assert processed["limits"][1]["type"] == "MCP usage(1 Month)"
    assert processed["limits"][1]["totol"] == 100


@pytest.mark.asyncio
async def test_usage_fetcher_initialization():
    fetcher = UsageFetcher(
        base_url="https://api.z.ai/api/anthropic", auth_token="test_token"
    )
    assert fetcher.urls["platform"] == "ZAI"
    assert fetcher.auth_token == "test_token"


# More tests could be added here to mock aiohttp and verify fetch_all
