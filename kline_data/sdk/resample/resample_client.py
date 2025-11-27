"""重采样客户端 - 数据重采样"""

import pandas as pd
from typing import Optional, List
from datetime import datetime

from ...config import Config
from ...resampler import KlineResampler
from ...utils.constants import (
    validate_timeframe,
    validate_exchange,
    validate_symbol,
)


class ResampleClient:
    """
    数据重采样客户端
    
    提供K线数据重采样功能，包括：
    1. 单个时间周期重采样
    2. 批量时间周期重采样
    3. 可选择保存结果
    """
    
    def __init__(self, config: Optional[Config] = None):
        """
        初始化重采样客户端
        
        Args:
            config: 配置对象，如果为None使用默认配置
        """
        if config is None:
            from config import load_config
            config = load_config()
        
        self.config = config
        self.resampler = KlineResampler(config)
    
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
        validate_timeframe(source_interval)
        validate_timeframe(target_interval)
        validate_exchange(exchange)
        validate_symbol(symbol)
        
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
        validate_timeframe(source_interval)
        for interval in target_intervals:
            validate_timeframe(interval)
        validate_exchange(exchange)
        validate_symbol(symbol)
        
        return self.resampler.batch_resample(
            exchange, symbol, start_time, end_time,
            source_interval, target_intervals, save
        )
