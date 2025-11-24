"""波动率指标"""

import pandas as pd
import numpy as np
from typing import Optional

from .base import VolatilityBase


class ATR(VolatilityBase):
    """
    ATR (Average True Range)
    平均真实波幅
    
    TR = max(High - Low, |High - Close_prev|, |Low - Close_prev|)
    ATR = EMA(TR, period)
    """
    
    def __init__(self):
        super().__init__('ATR')
    
    def calculate(
        self,
        df: pd.DataFrame,
        period: int = 14
    ) -> pd.DataFrame:
        """
        计算ATR
        
        Args:
            df: K线数据
            period: 周期
            
        Returns:
            pd.DataFrame: 包含ATR的数据
        """
        self.validate_data(df, ['high', 'low', 'close'])
        
        result = df.copy()
        
        # 计算True Range
        high = result['high']
        low = result['low']
        close_prev = result['close'].shift(1)
        
        tr1 = high - low
        tr2 = abs(high - close_prev)
        tr3 = abs(low - close_prev)
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        # 计算ATR
        atr = tr.ewm(span=period, adjust=False).mean()
        
        result[f'atr_{period}'] = atr
        result['tr'] = tr
        
        return result


class NormalizedATR(VolatilityBase):
    """
    归一化ATR (NATR)
    NATR = ATR / Close * 100
    """
    
    def __init__(self):
        super().__init__('NATR')
    
    def calculate(
        self,
        df: pd.DataFrame,
        period: int = 14
    ) -> pd.DataFrame:
        """
        计算归一化ATR
        
        Args:
            df: K线数据
            period: 周期
            
        Returns:
            pd.DataFrame: 包含NATR的数据
        """
        # 先计算ATR
        atr_indicator = ATR()
        result = atr_indicator.calculate(df, period)
        
        # 归一化
        atr_col = f'atr_{period}'
        result[f'natr_{period}'] = result[atr_col] / result['close'] * 100
        
        return result


class StandardDeviation(VolatilityBase):
    """
    标准差 (Standard Deviation)
    """
    
    def __init__(self):
        super().__init__('StdDev')
    
    def calculate(
        self,
        df: pd.DataFrame,
        period: int = 20,
        column: str = 'close'
    ) -> pd.DataFrame:
        """
        计算标准差
        
        Args:
            df: K线数据
            period: 周期
            column: 计算列
            
        Returns:
            pd.DataFrame: 包含标准差的数据
        """
        self.validate_data(df, [column])
        
        result = df.copy()
        
        # 计算标准差
        std = result[column].rolling(window=period).std()
        
        result[f'std_{period}'] = std
        
        return result


class HistoricalVolatility(VolatilityBase):
    """
    历史波动率 (Historical Volatility)
    HV = std(log_returns) * sqrt(252) * 100
    """
    
    def __init__(self):
        super().__init__('HV')
    
    def calculate(
        self,
        df: pd.DataFrame,
        period: int = 20,
        column: str = 'close',
        annualize: bool = True,
        trading_days: int = 252
    ) -> pd.DataFrame:
        """
        计算历史波动率
        
        Args:
            df: K线数据
            period: 周期
            column: 计算列
            annualize: 是否年化
            trading_days: 年交易日数
            
        Returns:
            pd.DataFrame: 包含历史波动率的数据
        """
        self.validate_data(df, [column])
        
        result = df.copy()
        
        # 计算对数收益率
        log_returns = np.log(result[column] / result[column].shift(1))
        
        # 计算标准差
        volatility = log_returns.rolling(window=period).std()
        
        # 年化
        if annualize:
            volatility = volatility * np.sqrt(trading_days)
        
        # 转换为百分比
        volatility = volatility * 100
        
        result[f'hv_{period}'] = volatility
        
        return result


class UlcerIndex(VolatilityBase):
    """
    溃疡指数 (Ulcer Index)
    衡量下行波动率
    
    UI = sqrt(sum((Close - Max_close)^2) / period)
    """
    
    def __init__(self):
        super().__init__('UI')
    
    def calculate(
        self,
        df: pd.DataFrame,
        period: int = 14,
        column: str = 'close'
    ) -> pd.DataFrame:
        """
        计算溃疡指数
        
        Args:
            df: K线数据
            period: 周期
            column: 计算列
            
        Returns:
            pd.DataFrame: 包含溃疡指数的数据
        """
        self.validate_data(df, [column])
        
        result = df.copy()
        
        # 计算周期内最高价
        max_close = result[column].rolling(window=period).max()
        
        # 计算回撤百分比
        drawdown_pct = ((result[column] - max_close) / max_close) * 100
        
        # 计算溃疡指数
        ui = np.sqrt((drawdown_pct ** 2).rolling(window=period).mean())
        
        result[f'ui_{period}'] = ui
        
        return result


class AverageTrueRangePercent(VolatilityBase):
    """
    ATR百分比 (ATR%)
    ATRP = ATR / Close * 100
    """
    
    def __init__(self):
        super().__init__('ATRP')
    
    def calculate(
        self,
        df: pd.DataFrame,
        period: int = 14
    ) -> pd.DataFrame:
        """
        计算ATR百分比
        
        Args:
            df: K线数据
            period: 周期
            
        Returns:
            pd.DataFrame: 包含ATR%的数据
        """
        # 先计算ATR
        atr_indicator = ATR()
        result = atr_indicator.calculate(df, period)
        
        # 计算百分比
        atr_col = f'atr_{period}'
        result[f'atrp_{period}'] = result[atr_col] / result['close'] * 100
        
        return result


class MassIndex(VolatilityBase):
    """
    质量指数 (Mass Index)
    用于识别趋势反转
    
    MI = sum(EMA(High-Low, 9) / EMA(EMA(High-Low, 9), 9), 25)
    """
    
    def __init__(self):
        super().__init__('MI')
    
    def calculate(
        self,
        df: pd.DataFrame,
        fast_period: int = 9,
        slow_period: int = 25
    ) -> pd.DataFrame:
        """
        计算质量指数
        
        Args:
            df: K线数据
            fast_period: 快速EMA周期
            slow_period: 慢速周期
            
        Returns:
            pd.DataFrame: 包含质量指数的数据
        """
        self.validate_data(df, ['high', 'low'])
        
        result = df.copy()
        
        # 计算价格范围
        price_range = result['high'] - result['low']
        
        # 计算单次EMA
        ema1 = price_range.ewm(span=fast_period, adjust=False).mean()
        
        # 计算双重EMA
        ema2 = ema1.ewm(span=fast_period, adjust=False).mean()
        
        # 计算比率
        ratio = ema1 / ema2
        
        # 计算质量指数
        mi = ratio.rolling(window=slow_period).sum()
        
        result['mass_index'] = mi
        
        return result


class ChoppinessIndex(VolatilityBase):
    """
    震荡指数 (Choppiness Index)
    衡量市场是震荡还是趋势
    
    CI = 100 * log10(sum(ATR) / (Max_high - Min_low)) / log10(period)
    """
    
    def __init__(self):
        super().__init__('CI')
    
    def calculate(
        self,
        df: pd.DataFrame,
        period: int = 14
    ) -> pd.DataFrame:
        """
        计算震荡指数
        
        Args:
            df: K线数据
            period: 周期
            
        Returns:
            pd.DataFrame: 包含震荡指数的数据
        """
        self.validate_data(df, ['high', 'low', 'close'])
        
        result = df.copy()
        
        # 计算ATR
        atr_indicator = ATR()
        temp = atr_indicator.calculate(df, 1)
        atr = temp['atr_1']
        
        # 计算ATR总和
        atr_sum = atr.rolling(window=period).sum()
        
        # 计算最高和最低
        max_high = result['high'].rolling(window=period).max()
        min_low = result['low'].rolling(window=period).min()
        
        # 计算震荡指数
        ci = 100 * np.log10(atr_sum / (max_high - min_low)) / np.log10(period)
        
        result[f'ci_{period}'] = ci
        
        return result


# 便捷函数

def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """计算ATR"""
    atr = ATR()
    return atr.calculate(df, period)


def calculate_natr(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """计算归一化ATR"""
    natr = NormalizedATR()
    return natr.calculate(df, period)


def calculate_std(df: pd.DataFrame, period: int = 20, column: str = 'close') -> pd.DataFrame:
    """计算标准差"""
    std = StandardDeviation()
    return std.calculate(df, period, column)


def calculate_hv(
    df: pd.DataFrame,
    period: int = 20,
    column: str = 'close',
    annualize: bool = True
) -> pd.DataFrame:
    """计算历史波动率"""
    hv = HistoricalVolatility()
    return hv.calculate(df, period, column, annualize)


def calculate_ulcer_index(df: pd.DataFrame, period: int = 14, column: str = 'close') -> pd.DataFrame:
    """计算溃疡指数"""
    ui = UlcerIndex()
    return ui.calculate(df, period, column)
