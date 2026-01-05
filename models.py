from typing import List, Optional, Union
from pydantic import BaseModel, Field, ConfigDict


class ModelTotalUsage(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    total_model_call_count: int = Field(alias="totalModelCallCount")
    total_tokens_usage: int = Field(alias="totalTokensUsage")


class ModelUsageResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    x_time: List[str] = Field(alias="x_time")
    model_call_count: List[Optional[int]] = Field(alias="modelCallCount")
    tokens_usage: List[Optional[int]] = Field(alias="tokensUsage")
    total_usage: ModelTotalUsage = Field(alias="totalUsage")


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
