"""K线数据客户端 - 带智能数据源选择"""

import pandas as pd
from typing import Optional, List
from datetime import datetime

from config import Config
from storage import DataFetcher, DownloadManager, MetadataManager
from reader import ParquetReader
from resampler import KlineResampler
from indicators import IndicatorManager
from rich.console import Console

# 导入全局常量
from utils.constants import (
    # 时间周期相关
    Timeframe,
    DEFAULT_QUERY_INTERVAL,
    DEFAULT_DOWNLOAD_INTERVAL,
    API_DEFAULT_INTERVAL,
    TIMEFRAME_SECONDS,

    # 交易所相关
    DEFAULT_EXCHANGE,
    DEFAULT_SYMBOL,

    # OHLCV相关
    OHLCV_COLUMNS,
    OHLCV_AGGREGATION_RULES,

    # 验证和限制
    DEFAULT_QUERY_LIMIT,

    # API相关
    API_SUCCESS_MESSAGE,
    API_METADATA_TAG,

    # 辅助函数
    get_timeframe_seconds,
    validate_timeframe,
    validate_exchange,
    validate_symbol,
)

console = Console()


class KlineClient:
    """
    K线数据客户端
    自动选择最优的数据获取策略
    
    主要特性：
    1. 智能数据源选择（本地/交易所/重采样）
    2. 自动下载缺失数据
    3. 性能优化的数据获取
    4. 完整的指标计算支持
    """
    
    def __init__(self, config: Optional[Config] = None):
        """
        初始化客户端
        
        Args:
            config: 配置对象，如果为None使用默认配置
        """
        if config is None:
            from config import load_config
            config = load_config()
        
        self.config = config
        
        # 初始化组件
        self.fetcher = DataFetcher(config)
        self.download_mgr = DownloadManager(config)
        self.metadata_mgr = MetadataManager(config)
        self.reader = ParquetReader(config)
        self.resampler = KlineResampler(config)
        self.indicator_calc = IndicatorManager()

    # 便于 with 语句使用
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False
    
    # ==================== 核心数据获取 ====================
    
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
        获取K线数据（智能模式）
        
        Args:
            exchange: 交易所
            symbol: 交易对
            start_time: 开始时间
            end_time: 结束时间
            interval: 时间周期（如 '1m', '5m', '1h', '1d', '1w'）
            auto_strategy: 是否自动选择策略（默认True）
            force_strategy: 强制使用策略 ('local', 'ccxt', 'resample')
            with_indicators: 附加计算的指标列表

        Returns:
            pd.DataFrame: K线数据

        Example:
            >>> # 获取币安BTC/USDT的周线数据（自动选择最优策略）
            >>> df = client.get_kline(
            ...     DEFAULT_EXCHANGE, DEFAULT_SYMBOL,
            ...     datetime(2020, 1, 1),
            ...     datetime(2024, 1, 1),
            ...     interval=Timeframe.W1.value
            ... )

            >>> # 强制从交易所直接下载
            >>> df = client.get_kline(
            ...     DEFAULT_EXCHANGE, DEFAULT_SYMBOL,
            ...     datetime(2023, 1, 1),
            ...     datetime(2024, 1, 1),
            ...     interval=Timeframe.W1.value,
            ...     force_strategy='ccxt'
            ... )

            >>> # 获取数据并计算指标
            >>> df = client.get_kline(
            ...     DEFAULT_EXCHANGE, DEFAULT_SYMBOL,
            ...     datetime(2024, 1, 1),
            ...     datetime(2024, 2, 1),
            ...     interval=Timeframe.H1.value,
            ...     with_indicators=['MA_20', 'EMA_12', 'RSI_14']
            ... )
        """
        # 验证输入参数
        validate_timeframe(interval)
        validate_exchange(exchange)
        validate_symbol(symbol)

        # 智能获取数据
        if auto_strategy:
            df = self.fetcher.fetch(
                exchange, symbol, start_time, end_time, interval,
                force_strategy=force_strategy,
                verbose=True
            )
        else:
            # 不使用智能策略，直接读取本地数据
            df = self.reader.read_range(
                exchange, symbol, start_time, end_time, interval
            )

        # 计算指标
        if with_indicators and not df.empty:
            df = self._calculate_indicators(df, with_indicators)

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
        # 验证输入参数
        validate_timeframe(interval)
        validate_exchange(exchange)
        validate_symbol(symbol)

        # 获取数据范围
        data_range = self.metadata_mgr.get_data_range(exchange, symbol)

        if data_range is None:
            console.print(f"No data found for {exchange}/{symbol}")
            return pd.DataFrame()

        # 计算开始时间
        interval_seconds = get_timeframe_seconds(interval)

        end_time = datetime.fromtimestamp(data_range[1] / 1000)
        start_timestamp = data_range[1] - (limit * interval_seconds * 1000)
        start_time = datetime.fromtimestamp(start_timestamp / 1000)

        # 获取数据
        df = self.get_kline(
            exchange, symbol, start_time, end_time, interval,
            with_indicators=with_indicators
        )

        # 限制数量
        if not df.empty and len(df) > limit:
            df = df.tail(limit)

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
        获取指定时间前n条K线数据（使用timezone处理时间）

        Args:
            exchange: 交易所
            symbol: 交易对
            before_time: 截止时间（不包含此时间点的K线）
            interval: 时间周期（如 '1m', '5m', '1h', '1d', '1w'）
            limit: 数量限制（获取多少条K线）
            with_indicators: 附加计算的指标列表

        Returns:
            pd.DataFrame: K线数据，按时间升序排列

        Example:
            >>> from datetime import datetime
            >>> from utils.timezone import to_utc
            >>>
            >>> # 获取2024年1月1日前100条日线数据
            >>> df = client.get_klines_before(
            ...     DEFAULT_EXCHANGE, DEFAULT_SYMBOL,
            ...     datetime(2024, 1, 1),
            ...     interval=Timeframe.D1.value,
            ...     limit=100
            ... )
            >>>
            >>> # 获取指定UTC时间前50条小时线，并计算指标
            >>> before_time = to_utc(datetime(2024, 6, 15, 12, 0, 0))
            >>> df = client.get_klines_before(
            ...     DEFAULT_EXCHANGE, DEFAULT_SYMBOL,
            ...     before_time,
            ...     interval=Timeframe.H1.value,
            ...     limit=50,
            ...     with_indicators=['MA_20', 'RSI_14']
            ... )
        """
        from utils.timezone import to_utc, datetime_to_timestamp, timestamp_to_datetime

        # 验证输入参数
        validate_timeframe(interval)
        validate_exchange(exchange)
        validate_symbol(symbol)

        # 确保时间为UTC
        before_time = to_utc(before_time)

        # 获取周期的秒数
        interval_seconds = get_timeframe_seconds(interval)

        # 计算开始时间（向前推limit个周期，再多取一些以确保足够）
        # 额外多取20%的数据，以防数据不连续
        buffer_multiplier = 1.2
        lookback_seconds = int(limit * interval_seconds * buffer_multiplier)
        start_timestamp = datetime_to_timestamp(before_time) - (lookback_seconds * 1000)
        start_time = timestamp_to_datetime(start_timestamp)

        # 获取数据
        df = self.get_kline(
            exchange, symbol, start_time, before_time, interval,
            with_indicators=None  # 先不计算指标，过滤后再计算
        )

        if df.empty:
            return df

        # 过滤掉大于等于before_time的数据
        before_timestamp = datetime_to_timestamp(before_time)
        df = df[df['timestamp'] < before_timestamp]

        # 取最后limit条数据
        if len(df) > limit:
            df = df.tail(limit)

        # 计算指标
        if with_indicators and not df.empty:
            df = self._calculate_indicators(df, with_indicators)

        return df
    
    # ==================== 数据下载管理 ====================
    
    def download(
        self,
        exchange: str,
        symbol: str,
        start_time: datetime,
        end_time: Optional[datetime] = None,
        interval: str = DEFAULT_DOWNLOAD_INTERVAL,
        force: bool = False,
        progress_callback: Optional[callable] = None
    ) -> dict:
        """
        下载数据

        Args:
            exchange: 交易所
            symbol: 交易对
            start_time: 开始时间
            end_time: 结束时间
            interval: 时间周期
            force: 是否强制重新下载（删除指定时间范围的现有数据）
            progress_callback: 进度回调函数(percentage, downloaded_records, total_records)

        Returns:
            dict: 下载结果摘要
        """
        # 验证输入参数
        validate_timeframe(interval)
        validate_exchange(exchange)
        validate_symbol(symbol)

        task_id = self.download_mgr.download(
            exchange, symbol, start_time, end_time, interval, progress_callback, force
        )

        # 读取元数据汇总
        metadata = self.metadata_mgr.get_symbol_metadata(exchange, symbol)

        result = {
            "task_id": task_id,
            "count": metadata.statistics.total_records if metadata.statistics else 0,
            "start": metadata.data_range.start_date if metadata.data_range else None,
            "end": metadata.data_range.end_date if metadata.data_range else None,
        }
        return result
    
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
            Optional[datetime]: 最早可用时间，如果获取失败返回None
        """
        from storage.downloader import DataDownloader

        # 验证输入参数
        validate_timeframe(interval)
        validate_exchange(exchange)
        validate_symbol(symbol)

        downloader = DataDownloader(exchange, symbol, self.config, interval)
        earliest_timestamp = downloader.get_earliest_timestamp()

        if earliest_timestamp:
            return datetime.fromtimestamp(earliest_timestamp / 1000)

        return None
    
    def update(
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
        # 验证输入参数
        validate_exchange(exchange)
        validate_symbol(symbol)

        task_id = self.download_mgr.update(exchange, symbol)
        if task_id is None:
            return None

        metadata = self.metadata_mgr.get_symbol_metadata(exchange, symbol)
        return {
            "task_id": task_id,
            "updated": True,
            "count": metadata.statistics.total_records if metadata.statistics else 0,
            "latest": metadata.data_range.end_date if metadata.data_range else None,
        }
    
    def get_download_status(self, task_id: str) -> Optional[dict]:
        """
        获取下载任务状态
        
        Args:
            task_id: 任务ID
            
        Returns:
            Optional[dict]: 任务状态
        """
        task = self.download_mgr.get_task_status(task_id)
        
        if task:
            return {
                'task_id': task.task_id,
                'status': task.status,
                'progress': task.progress.percentage if task.progress else 0,
                'downloaded_records': (
                    task.progress.downloaded_records if task.progress else 0
                ),
                'errors': task.errors,
            }
        
        return None
    
    # ==================== 重采样 ====================
    
    def resample(
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
        return self.resampler.resample_range(
            exchange, symbol, start_time, end_time,
            source_interval, target_interval, save
        )
    
    def batch_resample(
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
        return self.resampler.batch_resample(
            exchange, symbol, start_time, end_time,
            source_interval, target_intervals, save
        )
    
    # ==================== 指标计算 ====================
    
    def calculate_indicators(
        self,
        df: pd.DataFrame,
        indicators: List[str]
    ) -> pd.DataFrame:
        """
        计算技术指标

        Args:
            df: K线数据
            indicators: 指标列表（如 ['MA_20', 'EMA_12', 'RSI_14', 'BOLL_20']）

        Returns:
            pd.DataFrame: 带指标的数据
        """
        return self._calculate_indicators(df, indicators)

    def _calculate_indicators(
        self,
        df: pd.DataFrame,
        indicators: List[str]
    ) -> pd.DataFrame:
        """
        内部指标计算方法

        Args:
            df: K线数据
            indicators: 指标列表

        Returns:
            pd.DataFrame: 带指标的数据
        """
        # 验证DataFrame包含必要的OHLCV列
        required_columns = OHLCV_COLUMNS[:5]  # timestamp, open, high, low, close, volume
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise ValueError(f"DataFrame missing required OHLCV columns: {missing_columns}")

        for indicator in indicators:
            try:
                # 解析指标名称和参数
                parts = indicator.split('_')
                indicator_name = parts[0].upper()

                if indicator_name == 'MA':
                    period = int(parts[1]) if len(parts) > 1 else 20
                    df[indicator] = self.indicator_calc.ma(df[OHLCV_COLUMNS[4]], period)  # close

                elif indicator_name == 'EMA':
                    period = int(parts[1]) if len(parts) > 1 else 12
                    df[indicator] = self.indicator_calc.ema(df[OHLCV_COLUMNS[4]], period)  # close

                elif indicator_name == 'RSI':
                    period = int(parts[1]) if len(parts) > 1 else 14
                    df[indicator] = self.indicator_calc.rsi(df[OHLCV_COLUMNS[4]], period)  # close

                elif indicator_name == 'BOLL':
                    period = int(parts[1]) if len(parts) > 1 else 20
                    upper, middle, lower = self.indicator_calc.bollinger_bands(
                        df[OHLCV_COLUMNS[4]], period  # close
                    )
                    df[f'{indicator}_upper'] = upper
                    df[f'{indicator}_middle'] = middle
                    df[f'{indicator}_lower'] = lower

                elif indicator_name == 'MACD':
                    macd, signal, hist = self.indicator_calc.macd(df[OHLCV_COLUMNS[4]])  # close
                    df['MACD'] = macd
                    df['MACD_signal'] = signal
                    df['MACD_hist'] = hist

                else:
                    console.print(f"Unknown indicator: {indicator}")

            except Exception as e:
                console.print(f"Error calculating {indicator}: {e}")

        return df
    
    # ==================== 元数据查询 ====================
    
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
        # 验证输入参数
        validate_exchange(exchange)
        validate_symbol(symbol)

        metadata = self.metadata_mgr.get_symbol_metadata(exchange, symbol)

        if metadata:
            return {
                'exchange': metadata.exchange,
                'symbol': metadata.symbol,
                'intervals': {
                    interval: {
                        'start_time': datetime.fromtimestamp(
                            data.start_timestamp / 1000
                        ),
                        'end_time': datetime.fromtimestamp(
                            data.end_timestamp / 1000
                        ),
                        'records': data.total_records,
                        'completeness': data.completeness,
                    }
                    for interval, data in metadata.intervals.items()
                },
                'last_updated': metadata.last_updated,
                'data_type': API_METADATA_TAG,
            }

        return None
    
    def list_symbols(self, exchange: Optional[str] = None) -> List[str]:
        """
        列出所有交易对

        Args:
            exchange: 可选，过滤交易所

        Returns:
            List[str]: 交易对列表
        """
        # 验证交易所参数（如果提供）
        if exchange is not None:
            validate_exchange(exchange)

        # 这需要元数据管理器支持
        # 简化版实现
        return []
    
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
        # 验证输入参数
        validate_timeframe(interval)
        validate_exchange(exchange)
        validate_symbol(symbol)

        return self.fetcher.explain_strategy(
            exchange, symbol, start_time, end_time, interval
        )
