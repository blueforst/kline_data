"""查询客户端 - 统一的数据查询接口"""

import pandas as pd
from typing import Optional, List
from datetime import datetime

from ...config import Config
from ...storage import DataFetcher, MetadataManager
from ...reader import ParquetReader
from rich.console import Console

from ...utils.constants import (
    Timeframe,
    DEFAULT_QUERY_INTERVAL,
    DEFAULT_QUERY_LIMIT,
    OHLCV_COLUMNS,
    get_timeframe_seconds,
    validate_timeframe,
    validate_exchange,
    validate_symbol,
)

console = Console()


class QueryClient:
    """
    数据查询客户端
    
    提供统一的K线数据查询接口，支持：
    1. 智能数据源选择（本地/交易所/重采样）
    2. 自动下载缺失数据
    3. 时间范围查询
    4. 最新数据查询
    5. 指定时间点之前的数据查询
    """
    
    def __init__(self, config: Optional[Config] = None):
        """
        初始化查询客户端
        
        Args:
            config: 配置对象，如果为None使用默认配置
        """
        if config is None:
            from kline_data.config import load_config
            config = load_config()
        
        self.config = config
        self.fetcher = DataFetcher(config)
        self.metadata_mgr = MetadataManager(config)
        self.reader = ParquetReader(config)
    
    def get_kline(
        self,
        exchange: str,
        symbol: str,
        start_time: datetime,
        end_time: datetime,
        interval: str = DEFAULT_QUERY_INTERVAL,
        auto_strategy: bool = True,
        force_strategy: Optional[str] = None
    ) -> pd.DataFrame:
        """
        获取K线数据（智能模式）
        
        智能策略优先级（auto_strategy=True时）：
        1. 本地有完整数据 -> 直接读取本地（最快）
        2. 否则直接从交易所下载目标周期（所有周期均由CCXT提供）
        
        Args:
            exchange: 交易所
            symbol: 交易对
            start_time: 开始时间
            end_time: 结束时间
            interval: 时间周期（如 '1m', '5m', '1h', '1d', '1w'）
            auto_strategy: 是否自动选择策略（默认True）
            force_strategy: 强制使用策略 ('local', 'ccxt')

        Returns:
            pd.DataFrame: K线数据
        """
        validate_timeframe(interval)
        validate_exchange(exchange)
        validate_symbol(symbol)

        if auto_strategy:
            df = self.fetcher.fetch(
                exchange, symbol, start_time, end_time, interval,
                force_strategy=force_strategy,
                verbose=True
            )
        else:
            df = self.reader.read_range(
                exchange, symbol, start_time, end_time, interval
            )

        return df
    
    def get_latest(
        self,
        exchange: str,
        symbol: str,
        interval: str = DEFAULT_QUERY_INTERVAL,
        limit: int = DEFAULT_QUERY_LIMIT
    ) -> pd.DataFrame:
        """
        获取最新的N条K线数据

        Args:
            exchange: 交易所
            symbol: 交易对
            interval: 时间周期
            limit: 数量限制

        Returns:
            pd.DataFrame: K线数据
        """
        validate_timeframe(interval)
        validate_exchange(exchange)
        validate_symbol(symbol)

        data_range = self.metadata_mgr.get_data_range(exchange, symbol)

        if data_range is None:
            console.print(f"No data found for {exchange}/{symbol}")
            return pd.DataFrame()

        interval_seconds = get_timeframe_seconds(interval)

        end_time = datetime.fromtimestamp(data_range[1] / 1000)
        start_timestamp = data_range[1] - (limit * interval_seconds * 1000)
        start_time = datetime.fromtimestamp(start_timestamp / 1000)

        df = self.get_kline(
            exchange, symbol, start_time, end_time, interval
        )

        if not df.empty and len(df) > limit:
            df = df.tail(limit)

        return df
    
    def get_klines_before(
        self,
        exchange: str,
        symbol: str,
        before_time: datetime,
        interval: str = DEFAULT_QUERY_INTERVAL,
        limit: int = DEFAULT_QUERY_LIMIT
    ) -> pd.DataFrame:
        """
        获取指定时间前n条K线数据

        Args:
            exchange: 交易所
            symbol: 交易对
            before_time: 截止时间（不包含此时间点的K线）
            interval: 时间周期
            limit: 数量限制

        Returns:
            pd.DataFrame: K线数据，按时间升序排列
        """
        from kline_data.utils.timezone import to_utc, datetime_to_timestamp, timestamp_to_datetime

        validate_timeframe(interval)
        validate_exchange(exchange)
        validate_symbol(symbol)

        before_time = to_utc(before_time)

        interval_seconds = get_timeframe_seconds(interval)

        buffer_multiplier = 1.2
        lookback_seconds = int(limit * interval_seconds * buffer_multiplier)
        start_timestamp = datetime_to_timestamp(before_time) - (lookback_seconds * 1000)
        start_time = timestamp_to_datetime(start_timestamp)

        df = self.get_kline(
            exchange, symbol, start_time, before_time, interval
        )

        if df.empty:
            return df

        # 记录原始timestamp类型，用于在需要时恢复
        # 注意：由于底层数据源可能已经返回datetime类型，我们需要强制转换回整数（毫秒）
        # 以保持向后兼容性
        original_timestamp_numeric = pd.api.types.is_numeric_dtype(df['timestamp'])
        
        # 如果已经是datetime类型，标记为需要转换回整数
        need_convert_back = not original_timestamp_numeric or pd.api.types.is_datetime64_any_dtype(df['timestamp'])

        # 确保timestamp列为UTC datetime，避免与int类型比较导致报错
        if not pd.api.types.is_datetime64_any_dtype(df['timestamp']):
            if pd.api.types.is_numeric_dtype(df['timestamp']):
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
            else:
                df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
        elif df['timestamp'].dt.tz is None:
            df['timestamp'] = df['timestamp'].dt.tz_localize('UTC')

        # 按时间排序后再做过滤/截断，确保返回结果有序且取到最新的limit条
        df = df.sort_values('timestamp').copy()

        if interval_seconds > 0:
            close_times = df['timestamp'] + pd.to_timedelta(interval_seconds, unit='s')
            df = df[close_times <= before_time].copy()
        else:
            df = df[df['timestamp'] < before_time].copy()

        if len(df) > limit:
            df = df.tail(limit).copy()

        # 如果原始数据的timestamp是datetime类型，在过滤后转换为ms整数，保持对外接口一致
        if need_convert_back and not df.empty:
            # 根据精度选择转换方式
            # datetime64[ms] -> 直接astype('int64')得到毫秒
            # datetime64[ns] -> astype('int64')后除以1_000_000得到毫秒
            if 'ms' in str(df['timestamp'].dtype):
                timestamp_ms = df['timestamp'].astype('int64')
            else:  # ns或其他纳秒精度
                timestamp_ms = df['timestamp'].astype('int64') // 1_000_000
            # 创建新列避免dtype不兼容警告
            df = df.copy()
            df['timestamp'] = timestamp_ms

        df = df.reset_index(drop=True)

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
        validate_timeframe(interval)
        validate_exchange(exchange)
        validate_symbol(symbol)

        return self.fetcher.explain_strategy(
            exchange, symbol, start_time, end_time, interval
        )
