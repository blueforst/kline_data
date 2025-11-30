"""重采样层模块

此模块提供K线数据的重采样功能，现在使用统一的全局常量定义。

推荐的导入方式:
    # 新代码推荐从 utils.constants 导入常量和函数
    from kline_data.utils.constants import Timeframe, OHLCV_AGGREGATION_RULES, get_timeframe_seconds

    # 或者从 resampler 模块导入类
    from kline_data.resampler import KlineResampler, SmartResampler

使用示例:
    >>> from kline_data.utils.constants import Timeframe
    >>> from kline_data.resampler import KlineResampler
    >>> resampler = KlineResampler(config)
    >>> result = resampler.resample(df, Timeframe.M1.value, Timeframe.H1.value)
"""

# 导入重采样器类
from .kline_resampler import (
    KlineResampler,
    SmartResampler,
)

# 从常量模块导入核心枚举和函数（推荐使用方式）
from ..utils.constants import (
    Timeframe,
    OHLCV_AGGREGATION_RULES,
    OHLCV_COLUMNS,
    TIMEFRAME_SECONDS,
    TIMEFRAME_TO_PANDAS,
    get_timeframe_seconds,
    validate_timeframe,
)

# 创建辅助函数（这些函数在 constants.py 中没有，我们从 timeframe 模块提供）
def get_pandas_freq(timeframe: str) -> str:
    """获取pandas频率字符串"""
    from .timeframe import get_pandas_freq as tf_get_pandas
    return tf_get_pandas(timeframe)

def can_resample(source: str, target: str) -> bool:
    """检查是否可以重采样"""
    from .timeframe import can_resample as tf_can_resample
    return tf_can_resample(source, target)

# 向后兼容的导入 - 从timeframe模块导入
from .timeframe import (
    TimeframeConverter,
    get_timedelta,
)

# 为了避免循环导入，提供别名函数
def legacy_get_timeframe_seconds(timeframe: str) -> int:
    """向后兼容函数"""
    from .timeframe import get_timeframe_seconds as tf_get_seconds
    return tf_get_seconds(timeframe)

def legacy_get_pandas_freq(timeframe: str) -> str:
    """向后兼容函数"""
    from .timeframe import get_pandas_freq as tf_get_pandas
    return tf_get_pandas(timeframe)

def legacy_can_resample(source: str, target: str) -> bool:
    """向后兼容函数"""
    from .timeframe import can_resample as tf_can_resample
    return tf_can_resample(source, target)

def legacy_validate_timeframe(timeframe: str) -> None:
    """向后兼容函数"""
    from .timeframe import validate_timeframe as tf_validate
    return tf_validate(timeframe)

__all__ = [
    # 核心类
    'KlineResampler',
    'SmartResampler',

    # 推荐的常量和函数（从 utils.constants）
    'Timeframe',
    'get_timeframe_seconds',
    'get_pandas_freq',
    'can_resample',
    'validate_timeframe',
    'OHLCV_AGGREGATION_RULES',
    'OHLCV_COLUMNS',
    'TIMEFRAME_SECONDS',
    'TIMEFRAME_TO_PANDAS',

    # 向后兼容的工具类和函数
    'TimeframeConverter',
    'get_timedelta',

    # 向后兼容的函数（带 legacy_ 前缀）
    'legacy_get_timeframe_seconds',
    'legacy_get_pandas_freq',
    'legacy_can_resample',
    'legacy_validate_timeframe',
]
