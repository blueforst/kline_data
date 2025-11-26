"""技术指标基类 - 支持TA-Lib和Pandas实现"""

from typing import Optional, Dict, Any, List
from abc import ABC, abstractmethod
import pandas as pd
import numpy as np
from rich.console import Console

from .talib_adapter import talib_adapter

console = Console()

class BaseIndicator(ABC):
    """
    技术指标基类 - 支持TA-Lib和Pandas实现
    所有技术指标都应该继承此类
    """

    def __init__(self, name: str, use_talib: bool = True):
        """
        初始化指标

        Args:
            name: 指标名称
            use_talib: 是否使用TA-Lib（如果可用）
        """
        self.name = name
        self.use_talib = use_talib and talib_adapter.is_available()
        self._params: Dict[str, Any] = {}

    @abstractmethod
    def calculate(self, df: pd.DataFrame, **kwargs) -> pd.DataFrame:
        """
        计算指标值

        Args:
            df: K线数据
            **kwargs: 计算参数

        Returns:
            包含指标值的DataFrame
        """
        pass

    def validate_data(self, df: pd.DataFrame, required_columns: List[str]) -> None:
        """验证输入数据"""
        if df.empty:
            raise ValueError("输入数据不能为空")

        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise ValueError(f"缺少必需列: {missing_columns}")

    def _validate_period(self, period: int, data_length: int) -> None:
        """验证周期参数"""
        if period <= 0:
            raise ValueError("周期必须大于0")

        if period >= data_length:
            raise ValueError(f"周期({period})不能大于等于数据长度({data_length})")

    def get_required_length(self, **kwargs) -> int:
        """
        获取计算所需的最小数据长度

        Args:
            **kwargs: 计算参数

        Returns:
            最小数据长度
        """
        # 子类应该重写此方法
        return 1

    def set_params(self, **params) -> None:
        """设置指标参数"""
        self._params.update(params)

    def get_params(self) -> Dict[str, Any]:
        """获取指标参数"""
        return self._params.copy()

    def __repr__(self) -> str:
        """字符串表示"""
        return f"{self.__class__.__name__}(name='{self.name}', use_talib={self.use_talib})"


class MovingAverageBase(BaseIndicator):
    """移动平均基类"""

    def __init__(self, name: str, use_talib: bool = True):
        super().__init__(name, use_talib)

    def validate_data(self, df: pd.DataFrame, required_columns: List[str]) -> None:
        """验证输入数据"""
        super().validate_data(df, required_columns)

        # 检查数据类型
        for col in required_columns:
            if not pd.api.types.is_numeric_dtype(df[col]):
                raise ValueError(f"列 '{col}' 必须是数值类型")

        # 检查NaN值
        nan_count = df[required_columns].isnull().sum().sum()
        if nan_count > 0:
            console.print(f"警告: 发现 {nan_count} 个NaN值，可能会影响指标计算", style="yellow")

    def _get_data_array(self, df: pd.DataFrame, column: str) -> np.ndarray:
        """获取指定列的numpy数组"""
        data = df[column].dropna()
        if len(data) < 2:
            raise ValueError(f"列 '{column}' 的有效数据不足")
        return data.values


class OscillatorBase(BaseIndicator):
    """震荡指标基类"""

    def __init__(self, name: str, use_talib: bool = True):
        super().__init__(name, use_talib)

    def validate_oscillator_output(self, values: np.ndarray) -> None:
        """验证震荡指标输出值"""
        if np.isnan(values).all():
            raise ValueError("指标计算结果全部为NaN")

        # 检查是否有明显的异常值
        finite_values = values[np.isfinite(values)]
        if len(finite_values) > 0:
            q1, q3 = np.percentile(finite_values, [25, 75])
            iqr = q3 - q1
            lower_bound = q1 - 3 * iqr
            upper_bound = q3 + 3 * iqr

            outliers = finite_values[(finite_values < lower_bound) | (finite_values > upper_bound)]
            if len(outliers) > 0:
                console.print(f"警告: 发现 {len(outliers)} 个可能的异常值", style="yellow")


class TrendIndicatorBase(BaseIndicator):
    """趋势指标基类"""

    def __init__(self, name: str, use_talib: bool = True):
        super().__init__(name, use_talib)

    def calculate_trend_strength(self, values: np.ndarray) -> float:
        """
        计算趋势强度

        Args:
            values: 指标值序列

        Returns:
            趋势强度 (0-1之间，1表示强趋势)
        """
        if len(values) < 10:
            return 0.0

        # 使用线性回归斜率作为趋势强度
        x = np.arange(len(values))
        finite_mask = np.isfinite(values)

        if finite_mask.sum() < 5:
            return 0.0

        x_finite = x[finite_mask]
        y_finite = values[finite_mask]

        if len(x_finite) < 2:
            return 0.0

        # 计算线性相关系数
        correlation = np.corrcoef(x_finite, y_finite)[0, 1]

        if np.isnan(correlation):
            return 0.0

        return abs(correlation)


class VolatilityBase(BaseIndicator):
    """波动率指标基类"""

    def __init__(self, name: str, use_talib: bool = True):
        super().__init__(name, use_talib)

    def validate_high_low_data(self, df: pd.DataFrame) -> None:
        """验证高低价数据"""
        required_columns = ['high', 'low', 'close']
        missing = [col for col in required_columns if col not in df.columns]
        if missing:
            raise ValueError(f"缺少必需列: {missing}")

        # 验证高低价的合理性
        if (df['high'] < df['low']).any():
            raise ValueError("存在高价低于低价的数据")

        if (df['close'] > df['high']).any() or (df['close'] < df['low']).any():
            console.print("警告: 存在收盘价超出高低价范围的数据", style="yellow")


class VolumeBase(BaseIndicator):
    """成交量指标基类"""

    def __init__(self, name: str, use_talib: bool = True):
        super().__init__(name, use_talib)

    def validate_volume_data(self, df: pd.DataFrame, volume_column: str = 'volume') -> None:
        """验证成交量数据"""
        if volume_column not in df.columns:
            raise ValueError(f"缺少成交量列: {volume_column}")

        volume_data = df[volume_column]
        if (volume_data < 0).any():
            raise ValueError("成交量不能为负数")

        zero_volume_ratio = (volume_data == 0).sum() / len(volume_data)
        if zero_volume_ratio > 0.1:
            console.print(f"警告: {zero_volume_ratio:.1%} 的成交量为0", style="yellow")


class IndicatorPipeline:
    """指标计算流水线"""

    def __init__(self):
        self.indicators: List[BaseIndicator] = []

    def add_indicator(self, indicator: BaseIndicator) -> 'IndicatorPipeline':
        """添加指标到流水线"""
        self.indicators.append(indicator)
        return self

    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """执行流水线计算"""
        result = df.copy()
        for indicator in self.indicators:
            result = indicator.calculate(result)
        return result


def validate_ohlcv(df: pd.DataFrame, require_volume: bool = False) -> None:
    """验证OHLCV数据格式"""
    required = ['open', 'high', 'low', 'close']
    if require_volume:
        required.append('volume')

    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"缺少必需列: {missing}")

    if df.empty:
        raise ValueError("数据不能为空")

    # 验证价格数据合理性
    if (df['high'] < df['low']).any():
        raise ValueError("存在高价低于低价的数据")

    if (df['close'] > df['high']).any() or (df['close'] < df['low']).any():
        console.print("警告: 存在收盘价超出高低价范围的数据", style="yellow")