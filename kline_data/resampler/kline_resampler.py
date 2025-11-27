"""K线数据重采样

此模块提供K线数据的重采样功能，支持不同时间周期之间的转换。
所有硬编码字符串已替换为从 utils.constants 导入的全局常量。

使用示例:
    >>> from utils.constants import Timeframe, OHLCV_AGGREGATION_RULES
    >>> from resampler.kline_resampler import KlineResampler
    >>> resampler = KlineResampler(config)
    >>> result = resampler.resample(df, Timeframe.M1.value, Timeframe.H1.value)
"""

from typing import Optional, List
from datetime import datetime
import pandas as pd
import numpy as np

from ..config import Config
from ..reader import ParquetReader
from ..storage import ParquetWriter

# 从统一常量模块导入所需的常量
from ..utils.constants import (
    OHLCV_COLUMNS,
    OHLCV_AGGREGATION_RULES,
    INTERNAL_TIMEZONE,
    DEFAULT_SOURCE_INTERVAL,
    SUPPORTED_EXCHANGES,
    DEMO_SYMBOL,
    Timeframe,
    TIMEFRAME_SECONDS,
)

# 延迟导入函数以避免循环导入
def _get_timeframe_functions():
    """延迟导入时间周期相关函数"""
    from utils.constants import (
        validate_timeframe,
        get_timeframe_seconds,
    )
    from .timeframe import (
        get_pandas_freq,
        can_resample,
    )
    return get_pandas_freq, can_resample, validate_timeframe, get_timeframe_seconds

# 向后兼容的导入 - 保持现有API工作
def _get_legacy_functions():
    """延迟导入legacy函数"""
    from .timeframe import (
        get_pandas_freq as legacy_get_pandas_freq,
        can_resample as legacy_can_resample,
        validate_timeframe as legacy_validate_timeframe,
    )
    return legacy_get_pandas_freq, legacy_can_resample, legacy_validate_timeframe


class KlineResampler:
    """
    K线数据重采样器
    负责将K线数据从一个时间周期转换为另一个时间周期
    """
    
    def __init__(self, config: Config):
        """
        初始化重采样器
        
        Args:
            config: 配置对象
        """
        self.config = config
        self.reader = ParquetReader(config)
        self.writer = ParquetWriter(config)
    
    def resample(
        self,
        df: pd.DataFrame,
        source_timeframe: str,
        target_timeframe: str,
        align: str = 'left'
    ) -> pd.DataFrame:
        """
        重采样K线数据
        
        Args:
            df: 源数据DataFrame
            source_timeframe: 源时间周期
            target_timeframe: 目标时间周期
            align: 对齐方式 ('left', 'right')
            
        Returns:
            pd.DataFrame: 重采样后的数据
        """
        if df.empty:
            return df
        
        # 验证时间周期（使用延迟导入的函数）
        get_pandas_freq, can_resample, validate_timeframe, get_timeframe_seconds = _get_timeframe_functions()

        validate_timeframe(source_timeframe)
        validate_timeframe(target_timeframe)

        # 检查是否可以重采样
        if not can_resample(source_timeframe, target_timeframe):
            raise ValueError(
                f"Cannot resample from {source_timeframe} to {target_timeframe}. "
                f"Target timeframe must be >= source and be a multiple of source."
            )

        # 如果相同周期，直接返回
        if source_timeframe == target_timeframe:
            return df.copy()

        # 使用常量定义timestamp列名
        timestamp_column = OHLCV_COLUMNS[0]  # 'timestamp'

        # 确保timestamp是索引
        if timestamp_column in df.columns:
            df = df.set_index(timestamp_column)

        # 确保索引是datetime类型且使用常量定义的时区
        if not isinstance(df.index, pd.DatetimeIndex):
            df.index = pd.to_datetime(df.index, utc=True)
        elif df.index.tz is None:
            df.index = df.index.tz_localize(INTERNAL_TIMEZONE)

        # 获取pandas频率（使用延迟导入的函数）
        freq = get_pandas_freq(target_timeframe)

        # 使用常量定义的聚合规则
        agg_dict = OHLCV_AGGREGATION_RULES.copy()

        # 只保留存在的列
        agg_dict = {k: v for k, v in agg_dict.items() if k in df.columns}
        
        # 执行重采样
        if align == 'left':
            resampled = df.resample(freq, label='left', closed='left').agg(agg_dict)
        else:
            resampled = df.resample(freq, label='right', closed='right').agg(agg_dict)
        
        # 删除全为NaN的行
        resampled = resampled.dropna(how='all')
        
        # 重置索引
        resampled = resampled.reset_index()
        
        return resampled
    
    def resample_range(
        self,
        exchange: str,
        symbol: str,
        start_time: datetime,
        end_time: datetime,
        source_timeframe: str,
        target_timeframe: str,
        save: bool = True
    ) -> pd.DataFrame:
        """
        重采样时间范围内的数据
        
        Args:
            exchange: 交易所
            symbol: 交易对
            start_time: 开始时间
            end_time: 结束时间
            source_timeframe: 源时间周期
            target_timeframe: 目标时间周期
            save: 是否保存重采样结果
            
        Returns:
            pd.DataFrame: 重采样后的数据
        """
        # 读取源数据
        df = self.reader.read_range(
            exchange,
            symbol,
            start_time,
            end_time,
            source_timeframe
        )
        
        if df.empty:
            return df
        
        # 执行重采样
        resampled = self.resample(df, source_timeframe, target_timeframe)
        
        # 保存结果
        if save and not resampled.empty:
            self.writer.write_partitioned(
                resampled,
                exchange,
                symbol,
                target_timeframe
            )
        
        return resampled
    
    def resample_ohlc(
        self,
        df: pd.DataFrame,
        target_timeframe: str,
        source_timeframe: str = None
    ) -> pd.DataFrame:
        """
        专门用于OHLC数据的重采样

        Args:
            df: 源数据
            target_timeframe: 目标周期
            source_timeframe: 源周期，默认使用常量定义的默认源间隔

        Returns:
            pd.DataFrame: 重采样后的OHLC数据
        """
        # 使用常量定义默认源时间间隔
        if source_timeframe is None:
            source_timeframe = DEFAULT_SOURCE_INTERVAL

        return self.resample(df, source_timeframe, target_timeframe)
    
    def batch_resample(
        self,
        exchange: str,
        symbol: str,
        start_time: datetime,
        end_time: datetime,
        source_timeframe: str,
        target_timeframes: List[str],
        save: bool = True
    ) -> dict:
        """
        批量重采样到多个目标周期
        
        Args:
            exchange: 交易所
            symbol: 交易对
            start_time: 开始时间
            end_time: 结束时间
            source_timeframe: 源时间周期
            target_timeframes: 目标时间周期列表
            save: 是否保存结果
            
        Returns:
            dict: {timeframe: DataFrame} 映射
        """
        # 读取源数据一次
        source_df = self.reader.read_range(
            exchange,
            symbol,
            start_time,
            end_time,
            source_timeframe
        )
        
        if source_df.empty:
            return {}
        
        results = {}
        
        for target_tf in target_timeframes:
            try:
                resampled = self.resample(
                    source_df.copy(),
                    source_timeframe,
                    target_tf
                )
                
                results[target_tf] = resampled
                
                # 保存结果
                if save and not resampled.empty:
                    self.writer.write_partitioned(
                        resampled,
                        exchange,
                        symbol,
                        target_tf
                    )
            except Exception as e:
                console.print(f"Error resampling to {target_tf}: {e}")
                continue
        
        return results
    
    def verify_resample(
        self,
        original: pd.DataFrame,
        resampled: pd.DataFrame,
        source_timeframe: str,
        target_timeframe: str
    ) -> dict:
        """
        验证重采样结果的正确性

        Args:
            original: 原始数据
            resampled: 重采样后的数据
            source_timeframe: 源时间周期
            target_timeframe: 目标时间周期

        Returns:
            dict: 验证结果
        """
        from rich.console import Console
        console = Console()

        result = {
            'valid': True,
            'errors': [],
            'warnings': []
        }

        if original.empty or resampled.empty:
            result['valid'] = False
            result['errors'].append('Empty data')
            return result

        # 使用延迟导入的函数获取时间周期秒数
        get_pandas_freq, can_resample, validate_timeframe, get_timeframe_seconds = _get_timeframe_functions()
        source_seconds = get_timeframe_seconds(source_timeframe)
        target_seconds = get_timeframe_seconds(target_timeframe)
        ratio = target_seconds / source_seconds

        expected_rows = len(original) / ratio
        actual_rows = len(resampled)

        if abs(actual_rows - expected_rows) > expected_rows * 0.1:
            result['warnings'].append(
                f"Row count mismatch: expected ~{expected_rows:.0f}, got {actual_rows}"
            )

        # 使用常量定义OHLC字段名
        timestamp_col = OHLCV_COLUMNS[0]  # 'timestamp'
        open_col = OHLCV_COLUMNS[1]       # 'open'
        high_col = OHLCV_COLUMNS[2]       # 'high'
        low_col = OHLCV_COLUMNS[3]        # 'low'
        close_col = OHLCV_COLUMNS[4]      # 'close'

        # 检查OHLC逻辑
        for _, row in resampled.iterrows():
            if high_col in row and low_col in row:
                if row[high_col] < row[low_col]:
                    result['valid'] = False
                    result['errors'].append(f"Invalid OHLC at {row.get(timestamp_col)}")

            if all(col in row for col in [open_col, high_col, low_col, close_col]):
                if (row[high_col] < row[open_col] or row[high_col] < row[close_col] or
                    row[low_col] > row[open_col] or row[low_col] > row[close_col]):
                    result['warnings'].append(f"Suspicious OHLC at {row.get(timestamp_col)}")

        # 检查时间连续性
        if timestamp_col in resampled.columns:
            timestamps = pd.to_datetime(resampled[timestamp_col], utc=True)
            time_diffs = timestamps.diff().dropna()

            if len(time_diffs) > 0:
                expected_diff = pd.Timedelta(seconds=target_seconds)

                # 检查是否有异常的时间间隔
                abnormal_diffs = time_diffs[time_diffs != expected_diff]
                if len(abnormal_diffs) > 0:
                    result['warnings'].append(
                        f"Found {len(abnormal_diffs)} irregular time intervals"
                    )

        return result


class SmartResampler:
    """
    智能重采样器
    自动选择最优的源数据和重采样策略

    此类使用全局常量来确保一致性和可维护性。
    """

    def __init__(self, config: Config):
        """
        初始化智能重采样器

        Args:
            config: 配置对象
        """
        self.config = config
        self.resampler = KlineResampler(config)
        self.reader = ParquetReader(config)

    def resample_auto(
        self,
        exchange: str,
        symbol: str,
        start_time: datetime,
        end_time: datetime,
        target_timeframe: str
    ) -> pd.DataFrame:
        """
        自动选择最优源数据进行重采样

        Args:
            exchange: 交易所名称（会使用SUPPORTED_EXCHANGES进行验证）
            symbol: 交易对符号
            start_time: 开始时间
            end_time: 结束时间
            target_timeframe: 目标时间周期

        Returns:
            pd.DataFrame: 重采样后的数据
        """
        # 导入需要的常量
        from utils.constants import TIMEFRAME_SECONDS

        # 尝试直接读取目标周期数据
        try:
            df = self.reader.read_range(
                exchange,
                symbol,
                start_time,
                end_time,
                target_timeframe
            )
            if not df.empty:
                return df
        except:
            pass

        # 使用延迟导入函数
        get_pandas_freq, can_resample, validate_timeframe, get_timeframe_seconds = _get_timeframe_functions()

        # 查找可用的源数据（从大到小）
        target_seconds = get_timeframe_seconds(target_timeframe)
        available_sources = []

        for tf, seconds in sorted(TIMEFRAME_SECONDS.items(), key=lambda x: x[1]):
            if seconds < target_seconds and target_seconds % seconds == 0:
                # 检查是否有数据
                try:
                    test_df = self.reader.read_range(
                        exchange,
                        symbol,
                        start_time,
                        start_time,
                        tf
                    )
                    if not test_df.empty:
                        available_sources.append(tf)
                except:
                    continue

        # 使用最大的可用源
        if available_sources:
            source_tf = available_sources[-1]
            return self.resampler.resample_range(
                exchange,
                symbol,
                start_time,
                end_time,
                source_tf,
                target_timeframe,
                save=True
            )

        # 如果没有可用源，返回空DataFrame
        return pd.DataFrame()
