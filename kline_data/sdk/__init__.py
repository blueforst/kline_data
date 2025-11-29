"""
SDK层 - 提供统一的Python SDK接口

模块化结构：
- KlineClient: 统一客户端（整合所有功能）
- QueryClient: 查询客户端（数据查询 + 数据流，支持自动下载）
- DownloadClient: 下载客户端（数据下载管理）
- ResampleClient: 重采样客户端（数据重采样）
- IndicatorClient: 指标客户端（技术指标计算）
- MetadataClient: 元数据客户端（元数据查询）

所有客户端都使用统一的底层逻辑和配置。
"""

# 主客户端（推荐使用）
from .sdk_client import KlineClient

# 子客户端（可直接使用）
from .query import QueryClient, ChunkedDataFeed
from .download import DownloadClient
from .resample import ResampleClient
from .indicator import IndicatorClient
from .metadata import MetadataClient

__all__ = [
    # 主客户端
    'KlineClient',
    
    # 子客户端
    'QueryClient',
    'DownloadClient',
    'ResampleClient',
    'IndicatorClient',
    'MetadataClient',
    
    # 数据流
    'ChunkedDataFeed',
]
