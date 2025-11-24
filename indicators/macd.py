"""MACD指标"""

import pandas as pd
import numpy as np
from typing import Optional

from .base import BaseIndicator


class MACD(BaseIndicator):
    """
    MACD (Moving Average Convergence Divergence)
    异同移动平均线
    
    MACD = EMA(fast) - EMA(slow)
    Signal = EMA(MACD, signal_period)
    Histogram = MACD - Signal
    """
    
    def __init__(self):
        super().__init__('MACD')
    
    def calculate(
        self,
        df: pd.DataFrame,
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9,
        column: str = 'close'
    ) -> pd.DataFrame:
        """
        计算MACD
        
        Args:
            df: K线数据
            fast_period: 快线周期
            slow_period: 慢线周期
            signal_period: 信号线周期
            column: 计算列
            
        Returns:
            pd.DataFrame: 包含MACD的数据
        """
        self.validate_data(df, [column])
        
        if fast_period >= slow_period:
            raise ValueError("fast_period must be less than slow_period")
        
        result = df.copy()
        
        # 计算快线和慢线EMA
        ema_fast = result[column].ewm(span=fast_period, adjust=False).mean()
        ema_slow = result[column].ewm(span=slow_period, adjust=False).mean()
        
        # 计算MACD线
        macd_line = ema_fast - ema_slow
        
        # 计算信号线
        signal_line = macd_line.ewm(span=signal_period, adjust=False).mean()
        
        # 计算柱状图
        histogram = macd_line - signal_line
        
        # 添加到结果
        result['macd'] = macd_line
        result['macd_signal'] = signal_line
        result['macd_histogram'] = histogram
        
        return result
    
    def get_signals(
        self,
        df: pd.DataFrame,
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9,
        column: str = 'close'
    ) -> pd.DataFrame:
        """
        生成MACD交易信号
        
        Args:
            df: K线数据
            fast_period: 快线周期
            slow_period: 慢线周期
            signal_period: 信号线周期
            column: 计算列
            
        Returns:
            pd.DataFrame: 包含信号的数据
        """
        result = self.calculate(df, fast_period, slow_period, signal_period, column)
        
        # 金叉: MACD上穿信号线
        result['macd_golden_cross'] = (
            (result['macd'].shift(1) <= result['macd_signal'].shift(1)) &
            (result['macd'] > result['macd_signal'])
        )
        
        # 死叉: MACD下穿信号线
        result['macd_death_cross'] = (
            (result['macd'].shift(1) >= result['macd_signal'].shift(1)) &
            (result['macd'] < result['macd_signal'])
        )
        
        # MACD上穿零轴
        result['macd_zero_cross_up'] = (
            (result['macd'].shift(1) <= 0) &
            (result['macd'] > 0)
        )
        
        # MACD下穿零轴
        result['macd_zero_cross_down'] = (
            (result['macd'].shift(1) >= 0) &
            (result['macd'] < 0)
        )
        
        # 柱状图由负转正
        result['macd_hist_positive'] = (
            (result['macd_histogram'].shift(1) <= 0) &
            (result['macd_histogram'] > 0)
        )
        
        # 柱状图由正转负
        result['macd_hist_negative'] = (
            (result['macd_histogram'].shift(1) >= 0) &
            (result['macd_histogram'] < 0)
        )
        
        # 背离检测
        result = self._detect_divergence(result)
        
        return result
    
    def _detect_divergence(self, df: pd.DataFrame, window: int = 14) -> pd.DataFrame:
        """
        检测MACD背离
        
        Args:
            df: 包含MACD的数据
            window: 检测窗口
            
        Returns:
            pd.DataFrame: 包含背离信号的数据
        """
        # 找到价格和MACD的局部高点和低点
        close = df['close']
        macd = df['macd']
        
        # 价格高点
        price_highs = close == close.rolling(window=window, center=True).max()
        # 价格低点
        price_lows = close == close.rolling(window=window, center=True).min()
        
        # MACD高点
        macd_highs = macd == macd.rolling(window=window, center=True).max()
        # MACD低点
        macd_lows = macd == macd.rolling(window=window, center=True).min()
        
        # 顶背离: 价格创新高，MACD未创新高
        df['macd_bearish_divergence'] = False
        
        # 底背离: 价格创新低，MACD未创新低
        df['macd_bullish_divergence'] = False
        
        return df


class PPO(BaseIndicator):
    """
    PPO (Percentage Price Oscillator)
    百分比价格振荡器
    
    类似MACD，但使用百分比而不是绝对值
    PPO = (EMA(fast) - EMA(slow)) / EMA(slow) * 100
    """
    
    def __init__(self):
        super().__init__('PPO')
    
    def calculate(
        self,
        df: pd.DataFrame,
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9,
        column: str = 'close'
    ) -> pd.DataFrame:
        """
        计算PPO
        
        Args:
            df: K线数据
            fast_period: 快线周期
            slow_period: 慢线周期
            signal_period: 信号线周期
            column: 计算列
            
        Returns:
            pd.DataFrame: 包含PPO的数据
        """
        self.validate_data(df, [column])
        
        result = df.copy()
        
        # 计算快线和慢线EMA
        ema_fast = result[column].ewm(span=fast_period, adjust=False).mean()
        ema_slow = result[column].ewm(span=slow_period, adjust=False).mean()
        
        # 计算PPO
        ppo = (ema_fast - ema_slow) / ema_slow * 100
        
        # 计算信号线
        signal = ppo.ewm(span=signal_period, adjust=False).mean()
        
        # 计算柱状图
        histogram = ppo - signal
        
        result['ppo'] = ppo
        result['ppo_signal'] = signal
        result['ppo_histogram'] = histogram
        
        return result


class APO(BaseIndicator):
    """
    APO (Absolute Price Oscillator)
    绝对价格振荡器
    
    实际上就是MACD的另一个名称
    APO = EMA(fast) - EMA(slow)
    """
    
    def __init__(self):
        super().__init__('APO')
    
    def calculate(
        self,
        df: pd.DataFrame,
        fast_period: int = 12,
        slow_period: int = 26,
        column: str = 'close'
    ) -> pd.DataFrame:
        """
        计算APO
        
        Args:
            df: K线数据
            fast_period: 快线周期
            slow_period: 慢线周期
            column: 计算列
            
        Returns:
            pd.DataFrame: 包含APO的数据
        """
        self.validate_data(df, [column])
        
        result = df.copy()
        
        # 计算快线和慢线EMA
        ema_fast = result[column].ewm(span=fast_period, adjust=False).mean()
        ema_slow = result[column].ewm(span=slow_period, adjust=False).mean()
        
        # 计算APO
        result['apo'] = ema_fast - ema_slow
        
        return result


def calculate_macd(
    df: pd.DataFrame,
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9,
    column: str = 'close'
) -> pd.DataFrame:
    """
    计算MACD（便捷函数）
    
    Args:
        df: K线数据
        fast_period: 快线周期
        slow_period: 慢线周期
        signal_period: 信号线周期
        column: 计算列
        
    Returns:
        pd.DataFrame: 包含MACD的数据
    """
    macd = MACD()
    return macd.calculate(df, fast_period, slow_period, signal_period, column)


def calculate_ppo(
    df: pd.DataFrame,
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9,
    column: str = 'close'
) -> pd.DataFrame:
    """
    计算PPO（便捷函数）
    
    Args:
        df: K线数据
        fast_period: 快线周期
        slow_period: 慢线周期
        signal_period: 信号线周期
        column: 计算列
        
    Returns:
        pd.DataFrame: 包含PPO的数据
    """
    ppo = PPO()
    return ppo.calculate(df, fast_period, slow_period, signal_period, column)


def get_macd_signals(
    df: pd.DataFrame,
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9,
    column: str = 'close'
) -> pd.DataFrame:
    """
    获取MACD交易信号（便捷函数）
    
    Args:
        df: K线数据
        fast_period: 快线周期
        slow_period: 慢线周期
        signal_period: 信号线周期
        column: 计算列
        
    Returns:
        pd.DataFrame: 包含信号的数据
    """
    macd = MACD()
    return macd.get_signals(df, fast_period, slow_period, signal_period, column)
