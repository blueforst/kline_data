"""统一客户端 - 整合所有功能的主客户端"""

import pandas as pd
from typing import Optional, List, Callable
from datetime import datetime

from ..config import Config

# 导入各个子客户端
from .query import QueryClient, ChunkedDataFeed
from .download import DownloadClient
from .indicator import IndicatorClient
from .metadata import MetadataClient

from ..utils.constants import (
    DEFAULT_QUERY_INTERVAL,
    DEFAULT_DOWNLOAD_INTERVAL,
    DEFAULT_QUERY_LIMIT,
)


class KlineClient:
    """
    K线数据统一客户端
    
    整合了所有功能模块的主客户端，提供：
    1. 数据查询（QueryClient）
    2. 数据下载（DownloadClient）- 支持多种时间周期
    3. 技术指标（IndicatorClient）
    4. 元数据查询（MetadataClient）
    
    所有周期数据直接从CCXT下载，不再使用重采样。
    
    Example:
        >>> from sdk import KlineClient
        >>> from datetime import datetime
        >>> 
        >>> # 创建客户端
        >>> client = KlineClient()
        >>> 
        >>> # 查询数据（自动下载缺失数据）
        >>> df = client.get_kline(
        ...     'binance', 'BTC/USDT',
        ...     datetime(2024, 1, 1),
        ...     datetime(2024, 1, 2),
        ...     '1h',
        ...     with_indicators=['MA_20', 'RSI_14']
        ... )
        >>> 
        >>> # 下载数据
        >>> result = client.download(
        ...     'binance', 'BTC/USDT',
        ...     datetime(2023, 1, 1),
        ...     datetime(2024, 1, 1),
        ...     '1m'
        ... )
        >>> 
        >>> # 创建数据流（自动下载缺失数据）
        >>> feed = client.create_data_feed(
        ...     'binance', 'BTC/USDT',
        ...     datetime(2020, 1, 1),
        ...     datetime(2024, 1, 1),
        ...     '1h'
        ... )
        >>> for chunk in feed:
        ...     print(f"Processing {len(chunk)} bars")
    """
    
    def __init__(self, config: Optional[Config] = None):
        """
        初始化统一客户端
        
        Args:
            config: 配置对象，如果为None使用默认配置
        """
        if config is None:
            from kline_data.config import load_config
            config = load_config()
        
        self.config = config
        
        # 初始化各个子客户端
        self.query = QueryClient(config)
        self.download = DownloadClient(config)
        self.indicator = IndicatorClient(config)
        self.metadata = MetadataClient(config)
    
    # ==================== 便捷方法 - with 语句支持 ====================
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc, tb):
        return False
    
    # ==================== 查询接口 ====================
    
    def get_kline(
        self,
        exchange: str,
        symbol: str,
        start_time: datetime,
        end_time: datetime,
        interval: str = DEFAULT_QUERY_INTERVAL,
        auto_strategy: bool = True,
        force_strategy: Optional[str] = None,
        with_indicators: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        获取K线数据（智能模式，支持自动下载）
        
        Args:
            exchange: 交易所
            symbol: 交易对
            start_time: 开始时间
            end_time: 结束时间
            interval: 时间周期
            auto_strategy: 是否自动选择策略（包括自动下载）
            force_strategy: 强制使用策略 ('local', 'ccxt')
            with_indicators: 附加计算的指标列表

        Returns:
            pd.DataFrame: K线数据
        """
        df = self.query.get_kline(
            exchange, symbol, start_time, end_time, interval,
            auto_strategy, force_strategy
        )
        
        # 计算指标
        if with_indicators and not df.empty:
            df = self.indicator.calculate(df, with_indicators)
        
        return df
    
    def get_latest(
        self,
        exchange: str,
        symbol: str,
        interval: str = DEFAULT_QUERY_INTERVAL,
        limit: int = DEFAULT_QUERY_LIMIT,
        with_indicators: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        获取最新的N条K线数据

        Args:
            exchange: 交易所
            symbol: 交易对
            interval: 时间周期
            limit: 数量限制
            with_indicators: 附加指标

        Returns:
            pd.DataFrame: K线数据
        """
        df = self.query.get_latest(exchange, symbol, interval, limit)
        
        if with_indicators and not df.empty:
            df = self.indicator.calculate(df, with_indicators)
        
        return df
    
    def get_klines_before(
        self,
        exchange: str,
        symbol: str,
        before_time: datetime,
        interval: str = DEFAULT_QUERY_INTERVAL,
        limit: int = DEFAULT_QUERY_LIMIT,
        with_indicators: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        获取指定时间前n条K线数据

        Args:
            exchange: 交易所
            symbol: 交易对
            before_time: 截止时间
            interval: 时间周期
            limit: 数量限制
            with_indicators: 附加指标

        Returns:
            pd.DataFrame: K线数据
        """
        df = self.query.get_klines_before(
            exchange, symbol, before_time, interval, limit
        )
        
        if with_indicators and not df.empty:
            df = self.indicator.calculate(df, with_indicators)
        
        return df
    
    def explain_strategy(
        self,
        exchange: str,
        symbol: str,
        start_time: datetime,
        end_time: datetime,
        interval: str
    ) -> str:
        """
        解释数据获取策略（不实际获取数据）

        Args:
            exchange: 交易所
            symbol: 交易对
            start_time: 开始时间
            end_time: 结束时间
            interval: 周期

        Returns:
            str: 策略说明
        """
        return self.query.explain_strategy(
            exchange, symbol, start_time, end_time, interval
        )
    
    # ==================== 数据流接口（整合后支持自动下载） ====================
    
    def create_data_feed(
        self,
        exchange: str,
        symbol: str,
        start_time: datetime,
        end_time: datetime,
        interval: str = DEFAULT_QUERY_INTERVAL,
        chunk_size: int = 10000,
        preload_chunks: int = 1
    ) -> ChunkedDataFeed:
        """
        创建数据流（支持自动下载缺失数据）
        
        Args:
            exchange: 交易所
            symbol: 交易对
            start_time: 开始时间
            end_time: 结束时间
            interval: 时间周期
            chunk_size: 块大小
            preload_chunks: 预加载块数
            
        Returns:
            ChunkedDataFeed: 数据流对象
        """
        return ChunkedDataFeed(
            exchange=exchange,
            symbol=symbol,
            start_time=start_time,
            end_time=end_time,
            interval=interval,
            chunk_size=chunk_size,
            config=self.config
        )
    
    # ==================== 下载接口 ====================
    
    def download_kline(
        self,
        exchange: str,
        symbol: str,
        start_time: datetime,
        end_time: Optional[datetime] = None,
        interval: str = DEFAULT_DOWNLOAD_INTERVAL,
        force: bool = False,
        progress_callback: Optional[Callable[[float, int, int], None]] = None,
        interrupt_handler: Optional[Callable[[], None]] = None
    ) -> dict:
        """
        下载数据

        Args:
            exchange: 交易所
            symbol: 交易对
            start_time: 开始时间
            end_time: 结束时间
            interval: 时间周期
            force: 是否强制重新下载
            progress_callback: 进度回调函数
            interrupt_handler: 中断处理函数

        Returns:
            dict: 下载结果摘要
        """
        return self.download.download(
            exchange, symbol, start_time, end_time, interval,
            force, progress_callback, interrupt_handler
        )
    
    def update_kline(
        self,
        exchange: str,
        symbol: str
    ) -> Optional[dict]:
        """
        更新数据到最新

        Args:
            exchange: 交易所
            symbol: 交易对

        Returns:
            Optional[dict]: 更新结果摘要
        """
        return self.download.update(exchange, symbol)
    
    def get_earliest_available_time(
        self,
        exchange: str,
        symbol: str,
        interval: str = DEFAULT_DOWNLOAD_INTERVAL
    ) -> Optional[datetime]:
        """
        获取交易所支持的最早可用数据时间

        Args:
            exchange: 交易所
            symbol: 交易对
            interval: 时间周期

        Returns:
            Optional[datetime]: 最早可用时间
        """
        return self.download.get_earliest_available_time(
            exchange, symbol, interval
        )
    
    def get_download_status(self, task_id: str) -> Optional[dict]:
        """
        获取下载任务状态
        
        Args:
            task_id: 任务ID
            
        Returns:
            Optional[dict]: 任务状态
        """
        return self.download.get_task_status(task_id)
    
    # ==================== 重采样接口 ====================
    
    def resample_kline(
        self,
        exchange: str,
        symbol: str,
        start_time: datetime,
        end_time: datetime,
        source_interval: str,
        target_interval: str,
        save: bool = True
    ) -> pd.DataFrame:
        """
        重采样数据
        
        Args:
            exchange: 交易所
            symbol: 交易对
            start_time: 开始时间
            end_time: 结束时间
            source_interval: 源周期
            target_interval: 目标周期
            save: 是否保存结果
            
        Returns:
            pd.DataFrame: 重采样后的数据
        """
        return self.resample.resample(
            exchange, symbol, start_time, end_time,
            source_interval, target_interval, save
        )
    
    def batch_resample_kline(
        self,
        exchange: str,
        symbol: str,
        start_time: datetime,
        end_time: datetime,
        source_interval: str,
        target_intervals: List[str],
        save: bool = True
    ) -> dict:
        """
        批量重采样
        
        Args:
            exchange: 交易所
            symbol: 交易对
            start_time: 开始时间
            end_time: 结束时间
            source_interval: 源周期
            target_intervals: 目标周期列表
            save: 是否保存结果
            
        Returns:
            dict: {interval: DataFrame}
        """
        return self.resample.batch_resample(
            exchange, symbol, start_time, end_time,
            source_interval, target_intervals, save
        )
    
    # ==================== 指标计算接口 ====================
    
    def calculate_indicators(
        self,
        df: pd.DataFrame,
        indicators: List[str]
    ) -> pd.DataFrame:
        """
        计算技术指标

        Args:
            df: K线数据
            indicators: 指标列表

        Returns:
            pd.DataFrame: 带指标的数据
        """
        return self.indicator.calculate(df, indicators)
    
    # ==================== 元数据查询接口 ====================
    
    def get_metadata(
        self,
        exchange: str,
        symbol: str
    ) -> Optional[dict]:
        """
        获取元数据

        Args:
            exchange: 交易所
            symbol: 交易对

        Returns:
            Optional[dict]: 元数据
        """
        return self.metadata.get_metadata(exchange, symbol)
    
    def list_symbols(self, exchange: Optional[str] = None) -> List[str]:
        """
        列出所有交易对

        Args:
            exchange: 可选，过滤交易所

        Returns:
            List[str]: 交易对列表
        """
        return self.metadata.list_symbols(exchange)
