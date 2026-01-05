from datetime import datetime, timezone, timedelta
from typing import List, Optional, Union
from pydantic import BaseModel, Field, ConfigDict, field_validator


# Cached API timezone (detected lazily)
_API_TZ_CACHE: Optional[timezone] = None


async def detect_api_timezone_async() -> timezone:
    """Detect API timezone by finding which timezone has matching hour with latest API time.

    The API returns times where the latest timestamp has the same hour as current time
    in the API's timezone. We test common timezones to find the match.
    """
    # Import here to avoid circular dependency
    from fetch_usage import UsageFetcher

    # Get latest API time hour
    fetcher = UsageFetcher()
    data = await fetcher.fetch_all()
    latest_time_str = data['model'].x_time[-1]
    return detect_timezone_from_latest_hour(latest_time_str)


def detect_timezone_from_latest_hour(latest_time_str: str) -> timezone:
    """Detect timezone from the latest API time string."""
    latest_api_hour = int(latest_time_str.split(' ')[1].split(':')[0])
    now_utc = datetime.now(timezone.utc)

    # Check UTC-11 to UTC+12 for matching hour
    for offset in range(-11, 13):
        tz = timezone(timedelta(hours=offset))
        if now_utc.astimezone(tz).hour == latest_api_hour:
            return tz

    # Fallback to UTC if no match found
    return timezone.utc


def get_api_timezone() -> timezone:
    """Get the API timezone, detecting it once and caching the result.

    This synchronous version will be called during parsing, and if not yet cached,
    it defaults to UTC. The actual detection happens in fetch_usage where we have
    an event loop available.
    """
    global _API_TZ_CACHE
    if _API_TZ_CACHE is None:
        # Default to UTC if not yet detected
        # The actual detection happens in fetch_usage.py
        return timezone.utc
    return _API_TZ_CACHE


def set_api_timezone(tz: timezone) -> None:
    """Set the API timezone cache (called by fetch_usage after detection)."""
    global _API_TZ_CACHE
    _API_TZ_CACHE = tz


def parse_api_time(time_str: str) -> datetime:
    """Parse time string to datetime with detected API timezone.

    The API returns times like "2026-01-05 20:00" in a dynamic timezone
    that matches the current hour. We auto-detect this timezone.
    """
    dt = datetime.strptime(time_str, "%Y-%m-%d %H:%M")
    return dt.replace(tzinfo=get_api_timezone())


class ModelTotalUsage(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    total_model_call_count: int = Field(alias="totalModelCallCount")
    total_tokens_usage: int = Field(alias="totalTokensUsage")


class ModelUsagePoint(BaseModel):
    """Single point in model usage time series."""
    time: datetime
    call_count: Optional[int] = None
    tokens_usage: Optional[int] = None


class ModelUsageResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    x_time: List[str] = Field(alias="x_time")
    model_call_count: List[Optional[int]] = Field(alias="modelCallCount")
    tokens_usage: List[Optional[int]] = Field(alias="tokensUsage")
    total_usage: ModelTotalUsage = Field(alias="totalUsage")

    # Parsed time series data
    time_series: List[ModelUsagePoint] = Field(default_factory=list, exclude=True)

    @field_validator("time_series", mode="before")
    @classmethod
    def parse_time_series(cls, v: List[ModelUsagePoint], info) -> List[ModelUsagePoint]:
        """Parse x_time and model_call_count into time series with API timezone (UTC+3)."""
        if not info.data:
            return []

        x_time = info.data.get("x_time", [])
        model_call_count = info.data.get("model_call_count", [])
        tokens_usage = info.data.get("tokens_usage", [])

        result = []
        for i, time_str in enumerate(x_time):
            result.append(ModelUsagePoint(
                time=parse_api_time(time_str),
                call_count=model_call_count[i] if i < len(model_call_count) else None,
                tokens_usage=tokens_usage[i] if i < len(tokens_usage) else None,
            ))
        return result

    @property
    def parsed_time_series(self) -> List[ModelUsagePoint]:
        """Get parsed time series data."""
        if not self.time_series:
            # Build on demand
            result = []
            for i, time_str in enumerate(self.x_time):
                result.append(ModelUsagePoint(
                    time=parse_api_time(time_str),
                    call_count=self.model_call_count[i] if i < len(self.model_call_count) else None,
                    tokens_usage=self.tokens_usage[i] if i < len(self.tokens_usage) else None,
                ))
            return result
        return self.time_series


class ToolDetail(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    model_name: str = Field(alias="modelName")
    total_usage_count: int = Field(alias="totalUsageCount")


class ToolTotalUsage(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    total_network_search_count: int = Field(alias="totalNetworkSearchCount")
    total_web_read_mcp_count: int = Field(alias="totalWebReadMcpCount")
    total_zread_mcp_count: int = Field(alias="totalZreadMcpCount")
    total_search_mcp_count: int = Field(alias="totalSearchMcpCount")
    tool_details: List[ToolDetail] = Field(alias="toolDetails")


class ToolUsageResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    x_time: List[str] = Field(alias="x_time")
    network_search_count: List[Optional[int]] = Field(alias="networkSearchCount")
    web_read_mcp_count: List[Optional[int]] = Field(alias="webReadMcpCount")
    zread_mcp_count: List[Optional[int]] = Field(alias="zreadMcpCount")
    total_usage: ToolTotalUsage = Field(alias="totalUsage")


class QuotaUsageDetail(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    model_code: str = Field(alias="modelCode")
    usage: int = Field(alias="usage")


class LimitItem(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    type: str
    percentage: Union[int, float]
    current_usage: Optional[int] = Field(None, alias="currentUsage")
    total: Optional[int] = Field(
        None, alias="totol"
    )  # Matches the 'totol' from fetch_usage.py
    usage_details: Optional[List[QuotaUsageDetail]] = Field(None, alias="usageDetails")


class QuotaLimitResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    limits: List[LimitItem]
