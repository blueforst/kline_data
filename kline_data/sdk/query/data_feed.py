"""分块数据流 - 用于回测引擎（如backtrader）

这个模块提供了高效的分块数据读取功能，特别适合大规模回测场景。
主要特性：
1. 内存高效的分块迭代（直接读取Parquet文件）
2. 支持多种时间周期
3. 兼容backtrader数据格式
4. 可配置的块大小
"""

import pandas as pd
from typing import Optional, Iterator, Tuple, List
from datetime import datetime, timedelta
import logging
import pyarrow.parquet as pq
import gc

from ...config import Config
from ...utils.constants import (
    DEFAULT_QUERY_INTERVAL,
    validate_timeframe,
    validate_exchange,
    validate_symbol,
)
from ...utils.timezone import to_utc
from ...reader import ParquetReader

logger = logging.getLogger(__name__)


class ChunkedDataFeed:
    """
    分块数据流 (内存优化版)
    
    直接从Parquet文件读取数据，避免一次性加载所有数据到内存。
    按文件（通常是按月）迭代读取，并支持流式输出。
    
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
        ...     chunk_size=50000
        ... )
        >>> 
        >>> # 迭代数据块
        >>> for chunk_df in feed:
        ...     # 处理数据块
        ...     print(f"Loaded {len(chunk_df)} bars")
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
        columns: Optional[List[str]] = None,
    ):
        """
        初始化分块数据流
        
        Args:
            exchange: 交易所名称
            symbol: 交易对
            start_time: 开始时间
            end_time: 结束时间
            interval: 时间周期
            chunk_size: 每个数据块的大小（行数）
            config: 配置对象
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
        # 限定列可以显著降低内存占用；None 时读取所有列（向后兼容）
        self.columns = columns

        if config is None:
            from ...config import load_config
            config = load_config()
        
        self.config = config
        self.reader = ParquetReader(config)
        
        # 获取文件列表
        # 使用ParquetReader的内部方法获取文件列表
        self._files = self.reader._get_partition_files(
            exchange, symbol, self.start_time, self.end_time, interval
        )
        
        self._current_file_index = 0
        self._current_parquet_file = None
        self._current_batch_iter = None
        self._current_batch_df = None
        self._current_batch_row = 0
        
        # 状态管理
        self._current_chunk: Optional[pd.DataFrame] = None
        self._chunk_index = 0
        self._total_rows_loaded = 0
        self._is_exhausted = False
        
        logger.info(f"Found {len(self._files)} partition files for {exchange}/{symbol}")
        
        # 预加载第一块
        self._preload_initial_data()

    def _preload_initial_data(self) -> None:
        """预加载初始数据"""
        try:
            self._current_chunk = self._load_next_chunk()
            if self._current_chunk is None or self._current_chunk.empty:
                if not self._files:
                    logger.warning(
                        f"No data files found for {self.exchange}/{self.symbol} "
                        f"{self.interval} from {self.start_time} to {self.end_time}"
                    )
                self._is_exhausted = True
        except Exception as e:
            logger.error(f"Failed to preload initial data: {e}")
            self._is_exhausted = True

    def _load_next_chunk(self) -> Optional[pd.DataFrame]:
        """加载下一个数据块"""
        if self._is_exhausted:
            return None

        chunk_rows = []
        rows_needed = self.chunk_size

        while rows_needed > 0:
            # 如果当前batch未加载或已读完，加载下一个batch
            if self._current_batch_df is None or self._current_batch_row >= len(self._current_batch_df):
                
                # 如果当前文件未打开或batch迭代器已耗尽，打开下一个文件或获取下一个batch
                if self._current_batch_iter is None:
                    # 需要打开新文件
                    if self._current_file_index >= len(self._files):
                        # 没有更多文件了
                        if not chunk_rows:
                            self._is_exhausted = True
                            return None
                        break # 返回已有的数据
                    
                    file_path = self._files[self._current_file_index]
                    self._current_file_index += 1
                    
                    try:
                        logger.debug(f"Opening parquet file: {file_path}")
                        self._current_parquet_file = pq.ParquetFile(file_path)
                        # 使用iter_batches分批读取，batch_size设为chunk_size以优化内存
                        self._current_batch_iter = self._current_parquet_file.iter_batches(
                            batch_size=self.chunk_size,
                            columns=self.columns
                        )
                    except Exception as e:
                        logger.error(f"Error opening file {file_path}: {e}")
                        continue
                
                # 获取下一个batch
                try:
                    batch = next(self._current_batch_iter)
                    df = batch.to_pandas()
                    
                    # 过滤时间范围
                    if 'timestamp' in df.columns:
                        # 确保timestamp是datetime类型且为UTC
                        if not pd.api.types.is_datetime64_any_dtype(df['timestamp']):
                            df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
                        elif df['timestamp'].dt.tz is None:
                            df['timestamp'] = df['timestamp'].dt.tz_localize('UTC')
                        
                        # 过滤
                        df = df[
                            (df['timestamp'] >= self.start_time) &
                            (df['timestamp'] <= self.end_time)
                        ]
                    
                    if df.empty:
                        continue
                        
                    self._current_batch_df = df
                    self._current_batch_row = 0
                    
                except StopIteration:
                    # 当前文件读完
                    self._current_parquet_file = None
                    self._current_batch_iter = None
                    self._current_batch_df = None
                    gc.collect()
                    continue
                except Exception as e:
                    logger.error(f"Error reading batch: {e}")
                    self._current_parquet_file = None
                    self._current_batch_iter = None
                    self._current_batch_df = None
                    gc.collect()
                    continue

            # 从当前batch获取数据
            remaining_in_batch = len(self._current_batch_df) - self._current_batch_row
            take_rows = min(rows_needed, remaining_in_batch)
            
            chunk = self._current_batch_df.iloc[self._current_batch_row : self._current_batch_row + take_rows]
            chunk_rows.append(chunk)
            
            self._current_batch_row += take_rows
            rows_needed -= take_rows

        if not chunk_rows:
            self._is_exhausted = True
            return None

        # 合并块
        if len(chunk_rows) == 1:
            result_df = chunk_rows[0]
        else:
            result_df = pd.concat(chunk_rows, ignore_index=True)

        # 当前batch数据已耗尽，释放引用以便GC及时回收
        if self._current_batch_df is not None and self._current_batch_row >= len(self._current_batch_df):
            self._current_batch_df = None
            self._current_batch_row = 0
            gc.collect()

        # 清理临时列表
        chunk_rows.clear()
        del chunk_rows

        self._total_rows_loaded += len(result_df)
        self._chunk_index += 1
        
        logger.debug(
            f"Loaded chunk {self._chunk_index}: {len(result_df)} rows "
            f"(total: {self._total_rows_loaded})"
        )
        
        return result_df
    
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
        逐行迭代数据
        
        Yields:
            Tuple: (timestamp, open, high, low, close, volume)
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
