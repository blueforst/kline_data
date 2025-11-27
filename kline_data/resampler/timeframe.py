"""时间周期定义和转换

注意：本模块保留用于向后兼容。新代码应使用 utils.constants 模块中的定义。

推荐导入方式：
    from utils.constants import Timeframe, TIMEFRAME_SECONDS, TIMEFRAME_TO_PANDAS
"""

from enum import Enum
from typing import Dict, Optional
from datetime import timedelta

# 从统一常量模块导入
from ..utils.constants import (
    Timeframe,
    TIMEFRAME_SECONDS,
    TIMEFRAME_TO_PANDAS,
    PANDAS_TO_TIMEFRAME,
    get_timeframe_seconds as _get_timeframe_seconds,
    validate_timeframe as _validate_timeframe,
)


def get_timeframe_seconds(timeframe: str) -> int:
    """
    获取时间周期对应的秒数

    注意：此函数为向后兼容性保留，新代码请使用 utils.constants.get_timeframe_seconds

    Args:
        timeframe: 时间周期字符串

    Returns:
        int: 秒数
    """
    return _get_timeframe_seconds(timeframe)


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

    注意：此函数为向后兼容性保留，新代码请使用 utils.constants.validate_timeframe

    Args:
        timeframe: 时间周期字符串

    Raises:
        ValueError: 如果时间周期无效
    """
    _validate_timeframe(timeframe)


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
