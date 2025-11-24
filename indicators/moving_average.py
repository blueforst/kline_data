"""移动平均指标"""

import pandas as pd
import numpy as np
from typing import Optional, Union

from .base import MovingAverageBase

from rich.console import Console
console = Console()



class SMA(MovingAverageBase):
    """
    简单移动平均 (Simple Moving Average)
    """
    
    def __init__(self):
        super().__init__('SMA')
    
    def calculate(
        self,
        df: pd.DataFrame,
        period: int = 20,
        column: str = 'close',
        name: Optional[str] = None
    ) -> pd.DataFrame:
        """
        计算SMA
        
        Args:
            df: K线数据
            period: 周期
            column: 计算列
            name: 输出列名
            
        Returns:
            pd.DataFrame: 包含SMA的数据
        """
        self.validate_data(df, [column])
        self._validate_period(period, len(df))
        
        result = df.copy()
        col_name = name or f'sma_{period}'
        
        result[col_name] = result[column].rolling(window=period).mean()
        
        return result


class EMA(MovingAverageBase):
    """
    指数移动平均 (Exponential Moving Average)
    """
    
    def __init__(self):
        super().__init__('EMA')
    
    def calculate(
        self,
        df: pd.DataFrame,
        period: int = 20,
        column: str = 'close',
        name: Optional[str] = None
    ) -> pd.DataFrame:
        """
        计算EMA
        
        Args:
            df: K线数据
            period: 周期
            column: 计算列
            name: 输出列名
            
        Returns:
            pd.DataFrame: 包含EMA的数据
        """
        self.validate_data(df, [column])
        self._validate_period(period, len(df))
        
        result = df.copy()
        col_name = name or f'ema_{period}'
        
        result[col_name] = result[column].ewm(span=period, adjust=False).mean()
        
        return result


class WMA(MovingAverageBase):
    """
    加权移动平均 (Weighted Moving Average)
    """
    
    def __init__(self):
        super().__init__('WMA')
    
    def calculate(
        self,
        df: pd.DataFrame,
        period: int = 20,
        column: str = 'close',
        name: Optional[str] = None
    ) -> pd.DataFrame:
        """
        计算WMA
        
        Args:
            df: K线数据
            period: 周期
            column: 计算列
            name: 输出列名
            
        Returns:
            pd.DataFrame: 包含WMA的数据
        """
        self.validate_data(df, [column])
        self._validate_period(period, len(df))
        
        result = df.copy()
        col_name = name or f'wma_{period}'
        
        # 计算权重
        weights = np.arange(1, period + 1)
        
        def wma_func(x):
            if len(x) < period:
                return np.nan
            return np.dot(x[-period:], weights) / weights.sum()
        
        result[col_name] = result[column].rolling(window=period).apply(wma_func, raw=True)
        
        return result


class DEMA(MovingAverageBase):
    """
    双重指数移动平均 (Double Exponential Moving Average)
    DEMA = 2 * EMA - EMA(EMA)
    """
    
    def __init__(self):
        super().__init__('DEMA')
    
    def calculate(
        self,
        df: pd.DataFrame,
        period: int = 20,
        column: str = 'close',
        name: Optional[str] = None
    ) -> pd.DataFrame:
        """
        计算DEMA
        
        Args:
            df: K线数据
            period: 周期
            column: 计算列
            name: 输出列名
            
        Returns:
            pd.DataFrame: 包含DEMA的数据
        """
        self.validate_data(df, [column])
        self._validate_period(period, len(df))
        
        result = df.copy()
        col_name = name or f'dema_{period}'
        
        # 计算EMA
        ema = result[column].ewm(span=period, adjust=False).mean()
        # 计算EMA的EMA
        ema_ema = ema.ewm(span=period, adjust=False).mean()
        
        result[col_name] = 2 * ema - ema_ema
        
        return result


class TEMA(MovingAverageBase):
    """
    三重指数移动平均 (Triple Exponential Moving Average)
    TEMA = 3 * EMA - 3 * EMA(EMA) + EMA(EMA(EMA))
    """
    
    def __init__(self):
        super().__init__('TEMA')
    
    def calculate(
        self,
        df: pd.DataFrame,
        period: int = 20,
        column: str = 'close',
        name: Optional[str] = None
    ) -> pd.DataFrame:
        """
        计算TEMA
        
        Args:
            df: K线数据
            period: 周期
            column: 计算列
            name: 输出列名
            
        Returns:
            pd.DataFrame: 包含TEMA的数据
        """
        self.validate_data(df, [column])
        self._validate_period(period, len(df))
        
        result = df.copy()
        col_name = name or f'tema_{period}'
        
        # 计算EMA
        ema1 = result[column].ewm(span=period, adjust=False).mean()
        # 计算EMA的EMA
        ema2 = ema1.ewm(span=period, adjust=False).mean()
        # 计算EMA(EMA(EMA))
        ema3 = ema2.ewm(span=period, adjust=False).mean()
        
        result[col_name] = 3 * ema1 - 3 * ema2 + ema3
        
        return result


class VWMA(MovingAverageBase):
    """
    成交量加权移动平均 (Volume Weighted Moving Average)
    """
    
    def __init__(self):
        super().__init__('VWMA')
    
    def calculate(
        self,
        df: pd.DataFrame,
        period: int = 20,
        column: str = 'close',
        name: Optional[str] = None
    ) -> pd.DataFrame:
        """
        计算VWMA
        
        Args:
            df: K线数据
            period: 周期
            column: 计算列（价格）
            name: 输出列名
            
        Returns:
            pd.DataFrame: 包含VWMA的数据
        """
        self.validate_data(df, [column, 'volume'])
        self._validate_period(period, len(df))
        
        result = df.copy()
        col_name = name or f'vwma_{period}'
        
        # VWMA = sum(price * volume) / sum(volume)
        pv = result[column] * result['volume']
        result[col_name] = (
            pv.rolling(window=period).sum() / 
            result['volume'].rolling(window=period).sum()
        )
        
        return result


class HMA(MovingAverageBase):
    """
    赫尔移动平均 (Hull Moving Average)
    HMA = WMA(2 * WMA(n/2) - WMA(n), sqrt(n))
    """
    
    def __init__(self):
        super().__init__('HMA')
    
    def calculate(
        self,
        df: pd.DataFrame,
        period: int = 20,
        column: str = 'close',
        name: Optional[str] = None
    ) -> pd.DataFrame:
        """
        计算HMA
        
        Args:
            df: K线数据
            period: 周期
            column: 计算列
            name: 输出列名
            
        Returns:
            pd.DataFrame: 包含HMA的数据
        """
        self.validate_data(df, [column])
        self._validate_period(period, len(df))
        
        result = df.copy()
        col_name = name or f'hma_{period}'
        
        # 计算WMA(n/2)
        half_period = period // 2
        wma_half = self._wma(result[column], half_period)
        
        # 计算WMA(n)
        wma_full = self._wma(result[column], period)
        
        # 计算2 * WMA(n/2) - WMA(n)
        diff = 2 * wma_half - wma_full
        
        # 计算WMA(sqrt(n))
        sqrt_period = int(np.sqrt(period))
        result[col_name] = self._wma(diff, sqrt_period)
        
        return result
    
    def _wma(self, series: pd.Series, period: int) -> pd.Series:
        """
        计算WMA
        
        Args:
            series: 数据序列
            period: 周期
            
        Returns:
            pd.Series: WMA
        """
        weights = np.arange(1, period + 1)
        
        def wma_func(x):
            if len(x) < period:
                return np.nan
            return np.dot(x[-period:], weights) / weights.sum()
        
        return series.rolling(window=period).apply(wma_func, raw=True)


def calculate_ma(
    df: pd.DataFrame,
    period: int = 20,
    ma_type: str = 'sma',
    column: str = 'close',
    name: Optional[str] = None
) -> pd.DataFrame:
    """
    通用移动平均计算函数
    
    Args:
        df: K线数据
        period: 周期
        ma_type: MA类型 ('sma', 'ema', 'wma', 'dema', 'tema', 'vwma', 'hma')
        column: 计算列
        name: 输出列名
        
    Returns:
        pd.DataFrame: 包含MA的数据
    """
    ma_classes = {
        'sma': SMA,
        'ema': EMA,
        'wma': WMA,
        'dema': DEMA,
        'tema': TEMA,
        'vwma': VWMA,
        'hma': HMA,
    }
    
    ma_type = ma_type.lower()
    if ma_type not in ma_classes:
        raise ValueError(
            f"Invalid ma_type: {ma_type}. "
            f"Must be one of: {list(ma_classes.keys())}"
        )
    
    ma = ma_classes[ma_type]()
    return ma.calculate(df, period=period, column=column, name=name)


def calculate_multiple_ma(
    df: pd.DataFrame,
    periods: list = [5, 10, 20, 50, 200],
    ma_type: str = 'sma',
    column: str = 'close'
) -> pd.DataFrame:
    """
    批量计算多个周期的移动平均
    
    Args:
        df: K线数据
        periods: 周期列表
        ma_type: MA类型
        column: 计算列
        
    Returns:
        pd.DataFrame: 包含所有MA的数据
    """
    result = df.copy()
    
    for period in periods:
        try:
            result = calculate_ma(
                result,
                period=period,
                ma_type=ma_type,
                column=column
            )
        except Exception as e:
            console.print(f"Error calculating {ma_type}_{period}: {e}")
            continue
    
    return result
