"""时间周期定义和转换"""

from enum import Enum
from typing import Dict, Optional
from datetime import timedelta


class Timeframe(Enum):
    """时间周期枚举"""
    
    # 秒级
    S1 = '1s'
    S5 = '5s'
    S15 = '15s'
    S30 = '30s'
    
    # 分钟级
    M1 = '1m'
    M3 = '3m'
    M5 = '5m'
    M15 = '15m'
    M30 = '30m'
    
    # 小时级
    H1 = '1h'
    H2 = '2h'
    H4 = '4h'
    H6 = '6h'
    H8 = '8h'
    H12 = '12h'
    
    # 天级
    D1 = '1d'
    
    # 周级
    W1 = '1w'
    
    # 月级
    MO1 = '1M'
    
    @property
    def seconds(self) -> int:
        """获取周期对应的秒数"""
        return TIMEFRAME_SECONDS[self.value]
    
    @property
    def pandas_freq(self) -> str:
        """获取pandas的频率字符串"""
        return TIMEFRAME_TO_PANDAS[self.value]
    
    @classmethod
    def from_string(cls, s: str) -> 'Timeframe':
        """从字符串创建"""
        for tf in cls:
            if tf.value == s:
                return tf
        raise ValueError(f"Invalid timeframe: {s}")
    
    def is_valid_resample_from(self, source: 'Timeframe') -> bool:
        """检查是否可以从source重采样到当前周期"""
        return self.seconds >= source.seconds and self.seconds % source.seconds == 0


# 时间周期到秒数的映射
TIMEFRAME_SECONDS: Dict[str, int] = {
    '1s': 1,
    '5s': 5,
    '15s': 15,
    '30s': 30,
    '1m': 60,
    '3m': 180,
    '5m': 300,
    '15m': 900,
    '30m': 1800,
    '1h': 3600,
    '2h': 7200,
    '4h': 14400,
    '6h': 21600,
    '8h': 28800,
    '12h': 43200,
    '1d': 86400,
    '1w': 604800,
    '1M': 2592000,  # 30天近似
}

# 时间周期到pandas频率的映射
TIMEFRAME_TO_PANDAS: Dict[str, str] = {
    '1s': '1s',
    '5s': '5s',
    '15s': '15s',
    '30s': '30s',
    '1m': '1min',
    '3m': '3min',
    '5m': '5min',
    '15m': '15min',
    '30m': '30min',
    '1h': '1h',
    '2h': '2h',
    '4h': '4h',
    '6h': '6h',
    '8h': '8h',
    '12h': '12h',
    '1d': '1D',
    '1w': '1W',
    '1M': '1M',
}

# pandas频率到时间周期的映射
PANDAS_TO_TIMEFRAME: Dict[str, str] = {v: k for k, v in TIMEFRAME_TO_PANDAS.items()}


def get_timeframe_seconds(timeframe: str) -> int:
    """
    获取时间周期对应的秒数
    
    Args:
        timeframe: 时间周期字符串
        
    Returns:
        int: 秒数
    """
    if timeframe not in TIMEFRAME_SECONDS:
        raise ValueError(f"Unknown timeframe: {timeframe}")
    return TIMEFRAME_SECONDS[timeframe]


def get_pandas_freq(timeframe: str) -> str:
    """
    获取pandas频率字符串
    
    Args:
        timeframe: 时间周期字符串
        
    Returns:
        str: pandas频率
    """
    if timeframe not in TIMEFRAME_TO_PANDAS:
        raise ValueError(f"Unknown timeframe: {timeframe}")
    return TIMEFRAME_TO_PANDAS[timeframe]


def can_resample(source: str, target: str) -> bool:
    """
    检查是否可以从source重采样到target
    
    Args:
        source: 源时间周期
        target: 目标时间周期
        
    Returns:
        bool: 是否可以重采样
    """
    try:
        source_seconds = get_timeframe_seconds(source)
        target_seconds = get_timeframe_seconds(target)
        
        # 目标周期必须大于等于源周期，且是源周期的整数倍
        return (target_seconds >= source_seconds and 
                target_seconds % source_seconds == 0)
    except ValueError:
        return False


def get_timedelta(timeframe: str) -> timedelta:
    """
    获取时间周期对应的timedelta
    
    Args:
        timeframe: 时间周期字符串
        
    Returns:
        timedelta: 时间差
    """
    seconds = get_timeframe_seconds(timeframe)
    return timedelta(seconds=seconds)


def validate_timeframe(timeframe: str) -> None:
    """
    验证时间周期是否有效
    
    Args:
        timeframe: 时间周期字符串
        
    Raises:
        ValueError: 如果时间周期无效
    """
    if timeframe not in TIMEFRAME_SECONDS:
        valid_timeframes = ', '.join(sorted(TIMEFRAME_SECONDS.keys()))
        raise ValueError(
            f"Invalid timeframe: {timeframe}. "
            f"Valid timeframes are: {valid_timeframes}"
        )


class TimeframeConverter:
    """时间周期转换器"""
    
    @staticmethod
    def to_seconds(timeframe: str) -> int:
        """转换为秒数"""
        return get_timeframe_seconds(timeframe)
    
    @staticmethod
    def to_pandas(timeframe: str) -> str:
        """转换为pandas频率"""
        return get_pandas_freq(timeframe)
    
    @staticmethod
    def from_pandas(pandas_freq: str) -> str:
        """从pandas频率转换"""
        if pandas_freq not in PANDAS_TO_TIMEFRAME:
            raise ValueError(f"Unknown pandas frequency: {pandas_freq}")
        return PANDAS_TO_TIMEFRAME[pandas_freq]
    
    @staticmethod
    def normalize(timeframe: str) -> str:
        """
        标准化时间周期字符串
        
        Args:
            timeframe: 时间周期
            
        Returns:
            str: 标准化后的时间周期
        """
        # 移除空格
        timeframe = timeframe.strip()
        
        # 转换为小写
        timeframe = timeframe.lower()
        
        # 标准化格式
        if timeframe in TIMEFRAME_SECONDS:
            return timeframe
        
        # 尝试解析
        if timeframe.endswith('min'):
            # 15min -> 15m
            num = timeframe[:-3]
            return f"{num}m"
        elif timeframe.endswith('hour'):
            # 1hour -> 1h
            num = timeframe[:-4]
            return f"{num}h"
        elif timeframe.endswith('day'):
            # 1day -> 1d
            num = timeframe[:-3]
            return f"{num}d"
        elif timeframe.endswith('week'):
            # 1week -> 1w
            num = timeframe[:-4]
            return f"{num}w"
        
        raise ValueError(f"Cannot normalize timeframe: {timeframe}")
    
    @staticmethod
    def compare(tf1: str, tf2: str) -> int:
        """
        比较两个时间周期
        
        Args:
            tf1: 时间周期1
            tf2: 时间周期2
            
        Returns:
            int: -1 if tf1 < tf2, 0 if tf1 == tf2, 1 if tf1 > tf2
        """
        s1 = get_timeframe_seconds(tf1)
        s2 = get_timeframe_seconds(tf2)
        
        if s1 < s2:
            return -1
        elif s1 > s2:
            return 1
        else:
            return 0
    
    @staticmethod
    def get_smaller(tf1: str, tf2: str) -> str:
        """获取较小的时间周期"""
        return tf1 if TimeframeConverter.compare(tf1, tf2) <= 0 else tf2
    
    @staticmethod
    def get_larger(tf1: str, tf2: str) -> str:
        """获取较大的时间周期"""
        return tf1 if TimeframeConverter.compare(tf1, tf2) >= 0 else tf2
