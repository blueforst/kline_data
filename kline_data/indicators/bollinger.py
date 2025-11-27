"""布林带指标"""

import pandas as pd
import numpy as np
from typing import Optional, Tuple

from .base import VolatilityBase


class BollingerBands(VolatilityBase):
    """
    布林带 (Bollinger Bands)
    
    布林带由三条线组成:
    - 中轨: n周期移动平均线
    - 上轨: 中轨 + k * 标准差
    - 下轨: 中轨 - k * 标准差
    """
    
    def __init__(self):
        super().__init__('BOLL')
    
    def calculate(
        self,
        df: pd.DataFrame,
        period: int = 20,
        std_dev: float = 2.0,
        column: str = 'close',
        ma_type: str = 'sma'
    ) -> pd.DataFrame:
        """
        计算布林带
        
        Args:
            df: K线数据
            period: 周期
            std_dev: 标准差倍数
            column: 计算列
            ma_type: 移动平均类型 ('sma' or 'ema')
            
        Returns:
            pd.DataFrame: 包含布林带的数据
        """
        self.validate_data(df, [column])
        
        if period <= 0:
            raise ValueError(f"Period must be positive, got {period}")
        
        if std_dev <= 0:
            raise ValueError(f"std_dev must be positive, got {std_dev}")
        
        result = df.copy()
        
        # 计算中轨
        if ma_type.lower() == 'ema':
            middle = result[column].ewm(span=period, adjust=False).mean()
        else:
            middle = result[column].rolling(window=period).mean()
        
        # 计算标准差
        std = result[column].rolling(window=period).std()
        
        # 计算上下轨
        upper = middle + std_dev * std
        lower = middle - std_dev * std
        
        # 添加到结果
        result['boll_middle'] = middle
        result['boll_upper'] = upper
        result['boll_lower'] = lower
        result['boll_width'] = upper - lower
        result['boll_pct_b'] = (result[column] - lower) / (upper - lower)
        
        return result
    
    def get_signals(
        self,
        df: pd.DataFrame,
        period: int = 20,
        std_dev: float = 2.0,
        column: str = 'close'
    ) -> pd.DataFrame:
        """
        生成布林带交易信号
        
        Args:
            df: K线数据
            period: 周期
            std_dev: 标准差倍数
            column: 计算列
            
        Returns:
            pd.DataFrame: 包含信号的数据
        """
        result = self.calculate(df, period, std_dev, column)
        
        # 价格突破上轨
        result['boll_breakout_up'] = result[column] > result['boll_upper']
        
        # 价格突破下轨
        result['boll_breakout_down'] = result[column] < result['boll_lower']
        
        # 价格回归中轨（从上方）
        result['boll_return_from_up'] = (
            (result[column].shift(1) > result['boll_middle'].shift(1)) &
            (result[column] <= result['boll_middle'])
        )
        
        # 价格回归中轨（从下方）
        result['boll_return_from_down'] = (
            (result[column].shift(1) < result['boll_middle'].shift(1)) &
            (result[column] >= result['boll_middle'])
        )
        
        # 布林带收窄（可能突破）
        result['boll_squeeze'] = result['boll_width'] < result['boll_width'].rolling(20).mean() * 0.5
        
        return result


class KeltnerChannel(VolatilityBase):
    """
    肯特纳通道 (Keltner Channel)
    
    类似布林带，但使用ATR而不是标准差
    """
    
    def __init__(self):
        super().__init__('KC')
    
    def calculate(
        self,
        df: pd.DataFrame,
        period: int = 20,
        atr_period: int = 10,
        multiplier: float = 2.0,
        column: str = 'close'
    ) -> pd.DataFrame:
        """
        计算肯特纳通道
        
        Args:
            df: K线数据
            period: EMA周期
            atr_period: ATR周期
            multiplier: ATR倍数
            column: 计算列
            
        Returns:
            pd.DataFrame: 包含肯特纳通道的数据
        """
        self.validate_data(df, [column, 'high', 'low', 'close'])
        
        result = df.copy()
        
        # 计算中轨（EMA）
        middle = result[column].ewm(span=period, adjust=False).mean()
        
        # 计算ATR
        atr = self._calculate_atr(result, atr_period)
        
        # 计算上下轨
        upper = middle + multiplier * atr
        lower = middle - multiplier * atr
        
        result['kc_middle'] = middle
        result['kc_upper'] = upper
        result['kc_lower'] = lower
        result['kc_width'] = upper - lower
        
        return result
    
    def _calculate_atr(self, df: pd.DataFrame, period: int) -> pd.Series:
        """
        计算ATR (Average True Range)
        
        Args:
            df: K线数据
            period: 周期
            
        Returns:
            pd.Series: ATR值
        """
        high = df['high']
        low = df['low']
        close = df['close']
        
        # 计算True Range
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        # 计算ATR
        atr = tr.ewm(span=period, adjust=False).mean()
        
        return atr


class DonchianChannel(VolatilityBase):
    """
    唐奇安通道 (Donchian Channel)
    
    上轨: n周期最高价
    下轨: n周期最低价
    中轨: (上轨 + 下轨) / 2
    """
    
    def __init__(self):
        super().__init__('DC')
    
    def calculate(
        self,
        df: pd.DataFrame,
        period: int = 20
    ) -> pd.DataFrame:
        """
        计算唐奇安通道
        
        Args:
            df: K线数据
            period: 周期
            
        Returns:
            pd.DataFrame: 包含唐奇安通道的数据
        """
        self.validate_data(df, ['high', 'low'])
        
        result = df.copy()
        
        # 计算上下轨
        upper = result['high'].rolling(window=period).max()
        lower = result['low'].rolling(window=period).min()
        
        # 计算中轨
        middle = (upper + lower) / 2
        
        result['dc_upper'] = upper
        result['dc_middle'] = middle
        result['dc_lower'] = lower
        result['dc_width'] = upper - lower
        
        return result


def calculate_bollinger(
    df: pd.DataFrame,
    period: int = 20,
    std_dev: float = 2.0,
    column: str = 'close',
    ma_type: str = 'sma'
) -> pd.DataFrame:
    """
    计算布林带（便捷函数）
    
    Args:
        df: K线数据
        period: 周期
        std_dev: 标准差倍数
        column: 计算列
        ma_type: 移动平均类型
        
    Returns:
        pd.DataFrame: 包含布林带的数据
    """
    boll = BollingerBands()
    return boll.calculate(df, period, std_dev, column, ma_type)


def calculate_keltner(
    df: pd.DataFrame,
    period: int = 20,
    atr_period: int = 10,
    multiplier: float = 2.0,
    column: str = 'close'
) -> pd.DataFrame:
    """
    计算肯特纳通道（便捷函数）
    
    Args:
        df: K线数据
        period: EMA周期
        atr_period: ATR周期
        multiplier: ATR倍数
        column: 计算列
        
    Returns:
        pd.DataFrame: 包含肯特纳通道的数据
    """
    kc = KeltnerChannel()
    return kc.calculate(df, period, atr_period, multiplier, column)


def calculate_donchian(
    df: pd.DataFrame,
    period: int = 20
) -> pd.DataFrame:
    """
    计算唐奇安通道（便捷函数）
    
    Args:
        df: K线数据
        period: 周期
        
    Returns:
        pd.DataFrame: 包含唐奇安通道的数据
    """
    dc = DonchianChannel()
    return dc.calculate(df, period)


def compare_bands(
    df: pd.DataFrame,
    bb_period: int = 20,
    kc_period: int = 20,
    dc_period: int = 20
) -> pd.DataFrame:
    """
    比较不同的通道指标
    
    Args:
        df: K线数据
        bb_period: 布林带周期
        kc_period: 肯特纳通道周期
        dc_period: 唐奇安通道周期
        
    Returns:
        pd.DataFrame: 包含所有通道的数据
    """
    result = df.copy()
    
    # 计算布林带
    result = calculate_bollinger(result, bb_period)
    
    # 计算肯特纳通道
    result = calculate_keltner(result, kc_period)
    
    # 计算唐奇安通道
    result = calculate_donchian(result, dc_period)
    
    return result
