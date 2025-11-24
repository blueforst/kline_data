"""技术指标基类"""

from typing import Optional, Dict, Any, List
from abc import ABC, abstractmethod
import pandas as pd
import numpy as np

from rich.console import Console
console = Console()



class BaseIndicator(ABC):
    """
    技术指标基类
    所有技术指标都应该继承此类
    """
    
    def __init__(self, name: str):
        """
        初始化指标
        
        Args:
            name: 指标名称
        """
        self.name = name
        self._params: Dict[str, Any] = {}
    
    @abstractmethod
    def calculate(self, df: pd.DataFrame, **kwargs) -> pd.DataFrame:
        """
        计算指标
        
        Args:
            df: K线数据
            **kwargs: 指标参数
            
        Returns:
            pd.DataFrame: 包含指标列的数据
        """
        pass
    
    def validate_data(self, df: pd.DataFrame, required_columns: List[str]) -> None:
        """
        验证输入数据
        
        Args:
            df: K线数据
            required_columns: 必需的列
            
        Raises:
            ValueError: 数据验证失败
        """
        if df.empty:
            raise ValueError("Input DataFrame is empty")
        
        missing_columns = set(required_columns) - set(df.columns)
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")
    
    def set_params(self, **kwargs) -> None:
        """设置指标参数"""
        self._params.update(kwargs)
    
    def get_params(self) -> Dict[str, Any]:
        """获取指标参数"""
        return self._params.copy()
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}')"


class MovingAverageBase(BaseIndicator):
    """移动平均指标基类"""
    
    def __init__(self, name: str):
        super().__init__(name)
    
    def _validate_period(self, period: int, data_length: int) -> None:
        """
        验证周期参数
        
        Args:
            period: 周期
            data_length: 数据长度
            
        Raises:
            ValueError: 周期验证失败
        """
        if period <= 0:
            raise ValueError(f"Period must be positive, got {period}")
        
        if period > data_length:
            raise ValueError(
                f"Period ({period}) cannot be greater than data length ({data_length})"
            )


class OscillatorBase(BaseIndicator):
    """震荡指标基类"""
    
    def __init__(self, name: str):
        super().__init__(name)
    
    def _normalize(self, values: pd.Series, min_val: float = 0, max_val: float = 100) -> pd.Series:
        """
        归一化值到指定范围
        
        Args:
            values: 值序列
            min_val: 最小值
            max_val: 最大值
            
        Returns:
            pd.Series: 归一化后的值
        """
        v_min = values.min()
        v_max = values.max()
        
        if v_max == v_min:
            return pd.Series([50.0] * len(values), index=values.index)
        
        normalized = (values - v_min) / (v_max - v_min)
        return normalized * (max_val - min_val) + min_val


class VolatilityBase(BaseIndicator):
    """波动率指标基类"""
    
    def __init__(self, name: str):
        super().__init__(name)
    
    def _calculate_std(self, values: pd.Series, period: int) -> pd.Series:
        """
        计算标准差
        
        Args:
            values: 值序列
            period: 周期
            
        Returns:
            pd.Series: 标准差
        """
        return values.rolling(window=period).std()


class VolumeBase(BaseIndicator):
    """成交量指标基类"""
    
    def __init__(self, name: str):
        super().__init__(name)
    
    def _validate_volume(self, df: pd.DataFrame) -> None:
        """
        验证成交量数据
        
        Args:
            df: K线数据
            
        Raises:
            ValueError: 成交量验证失败
        """
        if 'volume' not in df.columns:
            raise ValueError("Volume column is required")
        
        if (df['volume'] < 0).any():
            raise ValueError("Volume cannot be negative")


class IndicatorPipeline:
    """
    指标计算流水线
    支持批量计算多个指标
    """
    
    def __init__(self):
        """初始化流水线"""
        self.indicators: List[BaseIndicator] = []
    
    def add_indicator(self, indicator: BaseIndicator) -> 'IndicatorPipeline':
        """
        添加指标
        
        Args:
            indicator: 指标实例
            
        Returns:
            IndicatorPipeline: 自身（支持链式调用）
        """
        self.indicators.append(indicator)
        return self
    
    def calculate(self, df: pd.DataFrame, **kwargs) -> pd.DataFrame:
        """
        计算所有指标
        
        Args:
            df: K线数据
            **kwargs: 指标参数
            
        Returns:
            pd.DataFrame: 包含所有指标的数据
        """
        result = df.copy()
        
        for indicator in self.indicators:
            try:
                result = indicator.calculate(result, **kwargs)
            except Exception as e:
                console.print(f"Error calculating {indicator.name}: {e}")
                continue
        
        return result
    
    def clear(self) -> None:
        """清空所有指标"""
        self.indicators.clear()
    
    def __len__(self) -> int:
        return len(self.indicators)
    
    def __repr__(self) -> str:
        indicator_names = [ind.name for ind in self.indicators]
        return f"IndicatorPipeline(indicators={indicator_names})"


def validate_ohlcv(df: pd.DataFrame) -> None:
    """
    验证OHLCV数据完整性
    
    Args:
        df: K线数据
        
    Raises:
        ValueError: 数据验证失败
    """
    required = ['open', 'high', 'low', 'close', 'volume']
    missing = set(required) - set(df.columns)
    
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    
    # 检查OHLC逻辑
    invalid_rows = (
        (df['high'] < df['low']) |
        (df['high'] < df['open']) |
        (df['high'] < df['close']) |
        (df['low'] > df['open']) |
        (df['low'] > df['close'])
    )
    
    if invalid_rows.any():
        raise ValueError(
            f"Invalid OHLC data found in {invalid_rows.sum()} rows"
        )


def validate_series(series: pd.Series, name: str) -> None:
    """
    验证序列数据
    
    Args:
        series: 数据序列
        name: 序列名称
        
    Raises:
        ValueError: 数据验证失败
    """
    if series.empty:
        raise ValueError(f"{name} is empty")
    
    if series.isna().all():
        raise ValueError(f"{name} contains only NaN values")
