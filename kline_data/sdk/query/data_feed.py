"""分块数据流 - 用于回测引擎（如backtrader）

这个模块提供了高效的分块数据读取功能，特别适合大规模回测场景。
主要特性：
1. 内存高效的分块迭代
2. 支持多种时间周期
3. 兼容backtrader数据格式
4. 可配置的块大小
5. 自动处理数据边界
"""

import pandas as pd
from typing import Optional, Iterator, Tuple
from datetime import datetime, timedelta
import logging

from ...config import Config
from ...utils.constants import (
    Timeframe,
    DEFAULT_QUERY_INTERVAL,
    OHLCV_COLUMNS,
    validate_timeframe,
    validate_exchange,
    validate_symbol,
)
from ...utils.timezone import to_utc
from .query_client import QueryClient

logger = logging.getLogger(__name__)


class ChunkedDataFeed:
    """
    分块数据流
    
    提供内存高效的K线数据迭代器，适合回测和实时数据处理。
    数据按时间顺序分块加载，避免一次性加载大量数据到内存。
    
    Example:
        >>> from datetime import datetime
        >>> from sdk import ChunkedDataFeed
        >>> 
        >>> # 创建数据流
        >>> feed = ChunkedDataFeed(
        ...     exchange='binance',
        ...     symbol='BTC/USDT',
        ...     start_time=datetime(2020, 1, 1),
        ...     end_time=datetime(2024, 1, 1),
        ...     interval='1h',
        ...     chunk_size=10000  # 每次加载10000条数据
        ... )
        >>> 
        >>> # 迭代数据块
        >>> for chunk_df in feed:
        ...     # 处理数据块
        ...     print(f"Loaded {len(chunk_df)} bars")
        ...     # 进行回测逻辑
        >>> 
        >>> # 或使用行级迭代（更适合backtrader）
        >>> for row in feed.iter_rows():
        ...     timestamp, open_price, high, low, close, volume = row
        ...     # 处理单根K线
    """
    
    def __init__(
        self,
        exchange: str,
        symbol: str,
        start_time: datetime,
        end_time: datetime,
        interval: str = DEFAULT_QUERY_INTERVAL,
        chunk_size: int = 10000,
        config: Optional[Config] = None,
        preload_chunks: int = 1,
    ):
        """
        初始化分块数据流
        
        Args:
            exchange: 交易所名称（如 'binance', 'okx'）
            symbol: 交易对（如 'BTC/USDT'）
            start_time: 开始时间
            end_time: 结束时间
            interval: 时间周期（'1m', '5m', '15m', '1h', '4h', '1d', '1w'）
            chunk_size: 每个数据块的大小（行数）
            config: 配置对象（None则使用默认配置）
            preload_chunks: 预加载的块数（用于优化性能）
        """
        # 验证输入参数
        validate_timeframe(interval)
        validate_exchange(exchange)
        validate_symbol(symbol)
        
        self.exchange = exchange
        self.symbol = symbol
        self.start_time = to_utc(start_time)
        self.end_time = to_utc(end_time)
        self.interval = interval
        self.chunk_size = chunk_size
        self.preload_chunks = preload_chunks
        
        # 初始化配置和读取器
        if config is None:
            from config import load_config
            config = load_config()
        
        self.config = config
        self.query_client = QueryClient(config)
        
        # 状态管理
        self._current_chunk: Optional[pd.DataFrame] = None
        self._chunk_index = 0
        self._row_index = 0
        self._total_rows_loaded = 0
        self._is_exhausted = False
        
        # 预加载第一块数据
        self._preload_initial_data()
    
    def _preload_initial_data(self) -> None:
        """预加载初始数据"""
        try:
            # 读取第一批数据
            self._current_chunk = self._load_next_chunk()
            if self._current_chunk is not None and not self._current_chunk.empty:
                logger.info(
                    f"Preloaded {len(self._current_chunk)} rows for "
                    f"{self.exchange}/{self.symbol} {self.interval}"
                )
            else:
                logger.warning(
                    f"No data available for {self.exchange}/{self.symbol} "
                    f"{self.interval} from {self.start_time} to {self.end_time}"
                )
                self._is_exhausted = True
        except Exception as e:
            logger.error(f"Failed to preload initial data: {e}")
            self._is_exhausted = True
    
    def _load_next_chunk(self) -> Optional[pd.DataFrame]:
        """
        加载下一个数据块
        
        Returns:
            Optional[pd.DataFrame]: 数据块，如果没有更多数据则返回None
        """
        if self._is_exhausted:
            return None
        
        try:
            # 计算当前块的时间范围
            # 使用已加载的行数来估算下一个时间点
            if self._total_rows_loaded == 0:
                chunk_start = self.start_time
            else:
                # 基于已加载的数据，计算下一个起始时间
                # 这里使用简单的时间推进，实际可能需要更精确的方法
                from utils.constants import get_timeframe_seconds
                interval_seconds = get_timeframe_seconds(self.interval)
                offset_seconds = self._total_rows_loaded * interval_seconds
                chunk_start = self.start_time + timedelta(seconds=offset_seconds)
            
            # 如果已经超过结束时间，返回None
            if chunk_start >= self.end_time:
                self._is_exhausted = True
                return None
            
            # 计算块的结束时间（估算）
            from utils.constants import get_timeframe_seconds
            interval_seconds = get_timeframe_seconds(self.interval)
            chunk_duration = self.chunk_size * interval_seconds
            chunk_end = min(
                chunk_start + timedelta(seconds=chunk_duration),
                self.end_time
            )
            
            # 使用QueryClient获取数据（支持自动下载）
            df = self.query_client.get_kline(
                exchange=self.exchange,
                symbol=self.symbol,
                start_time=chunk_start,
                end_time=chunk_end,
                interval=self.interval,
                auto_strategy=True  # 自动下载缺失数据
            )
            
            if df.empty:
                # 尝试读取更大的时间范围
                # 可能数据稀疏或有间隙
                chunk_end = min(
                    chunk_start + timedelta(days=30),  # 扩展到30天
                    self.end_time
                )
                df = self.query_client.get_kline(
                    exchange=self.exchange,
                    symbol=self.symbol,
                    start_time=chunk_start,
                    end_time=chunk_end,
                    interval=self.interval,
                    auto_strategy=True
                )
                
                if df.empty:
                    self._is_exhausted = True
                    return None
            
            # 限制块大小
            if len(df) > self.chunk_size:
                df = df.head(self.chunk_size)
            
            # 更新统计
            self._total_rows_loaded += len(df)
            self._chunk_index += 1
            
            logger.debug(
                f"Loaded chunk {self._chunk_index}: {len(df)} rows "
                f"(total: {self._total_rows_loaded})"
            )
            
            return df
            
        except Exception as e:
            logger.error(f"Error loading chunk: {e}")
            self._is_exhausted = True
            return None
    
    def __iter__(self) -> Iterator[pd.DataFrame]:
        """
        迭代数据块
        
        Yields:
            pd.DataFrame: 数据块
        """
        while not self._is_exhausted:
            if self._current_chunk is not None and not self._current_chunk.empty:
                yield self._current_chunk
                self._current_chunk = self._load_next_chunk()
            else:
                break
    
    def iter_rows(self) -> Iterator[Tuple]:
        """
        逐行迭代数据（适合backtrader等逐笔处理）
        
        Yields:
            Tuple: (timestamp, open, high, low, close, volume)
        
        Example:
            >>> for timestamp, o, h, l, c, v in feed.iter_rows():
            ...     # 处理每一根K线
            ...     strategy.next(o, h, l, c, v)
        """
        for chunk in self:
            for _, row in chunk.iterrows():
                yield (
                    row['timestamp'],
                    row['open'],
                    row['high'],
                    row['low'],
                    row['close'],
                    row['volume']
                )
    
    def iter_dicts(self) -> Iterator[dict]:
        """
        以字典格式迭代数据
        
        Yields:
            dict: K线数据字典
        
        Example:
            >>> for bar in feed.iter_dicts():
            ...     print(f"Time: {bar['timestamp']}, Close: {bar['close']}")
        """
        for chunk in self:
            for record in chunk.to_dict('records'):
                yield record
    
    def to_dataframe(self, max_rows: Optional[int] = None) -> pd.DataFrame:
        """
        将所有数据加载为单个DataFrame
        
        警告: 对于大数据集可能消耗大量内存
        
        Args:
            max_rows: 最大行数限制（None表示无限制）
        
        Returns:
            pd.DataFrame: 完整数据
        """
        chunks = []
        total_rows = 0
        
        for chunk in self:
            chunks.append(chunk)
            total_rows += len(chunk)
            
            if max_rows and total_rows >= max_rows:
                break
        
        if not chunks:
            return pd.DataFrame()
        
        df = pd.concat(chunks, ignore_index=True)
        
        if max_rows:
            df = df.head(max_rows)
        
        return df
    
    def reset(self) -> None:
        """重置迭代器到起始位置"""
        self._current_chunk = None
        self._chunk_index = 0
        self._row_index = 0
        self._total_rows_loaded = 0
        self._is_exhausted = False
        self._preload_initial_data()
    
    def get_stats(self) -> dict:
        """
        获取数据流统计信息
        
        Returns:
            dict: 统计信息
        """
        return {
            'exchange': self.exchange,
            'symbol': self.symbol,
            'interval': self.interval,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat(),
            'chunk_size': self.chunk_size,
            'chunks_loaded': self._chunk_index,
            'total_rows_loaded': self._total_rows_loaded,
            'is_exhausted': self._is_exhausted,
        }
    
    def __repr__(self) -> str:
        return (
            f"ChunkedDataFeed("
            f"exchange='{self.exchange}', "
            f"symbol='{self.symbol}', "
            f"interval='{self.interval}', "
            f"chunk_size={self.chunk_size}, "
            f"loaded={self._total_rows_loaded})"
        )


class BacktraderDataFeed(ChunkedDataFeed):
    """
    Backtrader兼容的数据流
    
    提供与backtrader.feeds.PandasData兼容的接口
    可以直接用于backtrader策略回测
    
    Example:
        >>> import backtrader as bt
        >>> from sdk import BacktraderDataFeed
        >>> 
        >>> # 创建Cerebro实例
        >>> cerebro = bt.Cerebro()
        >>> 
        >>> # 添加数据流
        >>> data_feed = BacktraderDataFeed(
        ...     exchange='binance',
        ...     symbol='BTC/USDT',
        ...     start_time=datetime(2023, 1, 1),
        ...     end_time=datetime(2024, 1, 1),
        ...     interval='1h'
        ... )
        >>> 
        >>> # 转换为backtrader可用的格式
        >>> bt_data = bt.feeds.PandasData(
        ...     dataname=data_feed.to_dataframe(),
        ...     datetime='timestamp',
        ...     open='open',
        ...     high='high',
        ...     low='low',
        ...     close='close',
        ...     volume='volume',
        ...     openinterest=-1
        ... )
        >>> 
        >>> cerebro.adddata(bt_data)
        >>> # 添加策略并运行
        >>> # cerebro.addstrategy(MyStrategy)
        >>> # cerebro.run()
    """
    
    def to_backtrader_format(self, max_rows: Optional[int] = None) -> pd.DataFrame:
        """
        转换为backtrader标准格式
        
        Args:
            max_rows: 最大行数
        
        Returns:
            pd.DataFrame: backtrader格式的数据
        """
        df = self.to_dataframe(max_rows=max_rows)
        
        if df.empty:
            return df
        
        # 确保timestamp是datetime索引
        if 'timestamp' in df.columns:
            df = df.set_index('timestamp')
        
        # 确保列名符合backtrader标准
        # backtrader需要: open, high, low, close, volume, openinterest
        if 'openinterest' not in df.columns:
            df['openinterest'] = 0
        
        # 确保列顺序
        columns = ['open', 'high', 'low', 'close', 'volume', 'openinterest']
        df = df[[col for col in columns if col in df.columns]]
        
        return df
    
    def get_backtrader_params(self) -> dict:
        """
        获取backtrader PandasData的参数配置
        
        Returns:
            dict: 参数字典
        """
        return {
            'datetime': None,  # 使用索引作为datetime
            'open': 'open',
            'high': 'high',
            'low': 'low',
            'close': 'close',
            'volume': 'volume',
            'openinterest': 'openinterest',
        }


class StreamingDataFeed(ChunkedDataFeed):
    """
    流式数据源（实时模拟）
    
    模拟实时数据流，适合进行实时策略测试
    可以控制数据推送速度，模拟真实交易环境
    
    Example:
        >>> from sdk import StreamingDataFeed
        >>> import time
        >>> 
        >>> feed = StreamingDataFeed(
        ...     exchange='binance',
        ...     symbol='BTC/USDT',
        ...     start_time=datetime(2024, 1, 1),
        ...     end_time=datetime(2024, 1, 2),
        ...     interval='1m',
        ...     playback_speed=100  # 100倍速播放
        ... )
        >>> 
        >>> # 实时处理数据
        >>> for bar in feed.stream():
        ...     print(f"New bar: {bar['close']}")
        ...     # 执行交易逻辑
        ...     time.sleep(feed.get_sleep_time())  # 模拟实时延迟
    """
    
    def __init__(
        self,
        exchange: str,
        symbol: str,
        start_time: datetime,
        end_time: datetime,
        interval: str = DEFAULT_QUERY_INTERVAL,
        chunk_size: int = 1000,
        config: Optional[Config] = None,
        playback_speed: float = 1.0,
    ):
        """
        初始化流式数据源
        
        Args:
            exchange: 交易所
            symbol: 交易对
            start_time: 开始时间
            end_time: 结束时间
            interval: 时间周期
            chunk_size: 块大小
            config: 配置
            playback_speed: 播放速度（1.0=实时，10.0=10倍速）
        """
        super().__init__(
            exchange=exchange,
            symbol=symbol,
            start_time=start_time,
            end_time=end_time,
            interval=interval,
            chunk_size=chunk_size,
            config=config,
        )
        self.playback_speed = playback_speed
    
    def stream(self) -> Iterator[dict]:
        """
        流式推送数据
        
        Yields:
            dict: K线数据
        """
        import time
        
        for bar in self.iter_dicts():
            yield bar
            # 计算延迟时间
            sleep_time = self.get_sleep_time()
            if sleep_time > 0:
                time.sleep(sleep_time)
    
    def get_sleep_time(self) -> float:
        """
        计算每根K线之间的延迟时间
        
        Returns:
            float: 延迟时间（秒）
        """
        from utils.constants import get_timeframe_seconds
        interval_seconds = get_timeframe_seconds(self.interval)
        return interval_seconds / self.playback_speed if self.playback_speed > 0 else 0
