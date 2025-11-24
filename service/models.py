"""
服务层数据模型定义
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime


class KlineResponse(BaseModel):
    """K线数据响应"""
    success: bool = Field(description="请求是否成功")
    data: List[Dict[str, Any]] = Field(description="K线数据列表")
    total: int = Field(description="总记录数")
    exchange: str = Field(description="交易所")
    symbol: str = Field(description="交易对")
    interval: str = Field(description="K线周期")


class IndicatorResponse(BaseModel):
    """指标数据响应"""
    success: bool = Field(description="请求是否成功")
    data: List[Dict[str, Any]] = Field(description="指标数据列表")
    total: int = Field(description="总记录数")
    exchange: str = Field(description="交易所")
    symbol: str = Field(description="交易对")
    interval: str = Field(description="K线周期")
    indicator: str = Field(description="指标名称")


class MetadataResponse(BaseModel):
    """元数据响应"""
    success: bool = Field(description="请求是否成功")
    data: Dict[str, Any] = Field(description="元数据信息")


class SymbolListResponse(BaseModel):
    """交易对列表响应"""
    success: bool = Field(description="请求是否成功")
    data: List[Dict[str, str]] = Field(description="交易对列表")
    total: int = Field(description="总数量")


class ErrorResponse(BaseModel):
    """错误响应"""
    success: bool = Field(default=False, description="请求是否成功")
    error: str = Field(description="错误信息")
    status_code: int = Field(description="HTTP状态码")


class DownloadRequest(BaseModel):
    """下载请求"""
    exchange: str = Field(description="交易所名称")
    symbol: str = Field(description="交易对")
    start_time: Optional[datetime] = Field(None, description="开始时间")
    end_time: Optional[datetime] = Field(None, description="结束时间")


class DownloadResponse(BaseModel):
    """下载响应"""
    success: bool = Field(description="下载是否成功")
    message: str = Field(description="响应消息")
    exchange: str = Field(description="交易所")
    symbol: str = Field(description="交易对")
    result: Dict[str, Any] = Field(description="下载结果详情")
