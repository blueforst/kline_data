"""时区处理工具函数

所有内部逻辑使用UTC时区，显示给用户时转换为本地时区
"""

from datetime import datetime, timezone
from typing import Optional, Union


def now_utc() -> datetime:
    """
    获取当前UTC时间（带时区信息）
    
    Returns:
        datetime: 当前UTC时间
    """
    return datetime.now(timezone.utc)


def to_utc(dt: datetime) -> datetime:
    """
    将datetime转换为UTC时区
    
    Args:
        dt: datetime对象（可以是naive或aware）
        
    Returns:
        datetime: UTC时区的datetime
    """
    if dt.tzinfo is None:
        # 假设naive datetime是UTC（内部一致性）
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt


def to_local(dt: datetime) -> datetime:
    """
    将UTC时间转换为本地时区
    
    Args:
        dt: datetime对象（应该是UTC时区）
        
    Returns:
        datetime: 本地时区的datetime
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone()


def format_datetime(dt: datetime, for_display: bool = False) -> str:
    """
    格式化datetime为ISO格式字符串
    
    Args:
        dt: datetime对象
        for_display: 是否用于显示（True=转换为本地时区，False=保持UTC）
        
    Returns:
        str: ISO格式时间字符串（精确到秒）
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    
    if for_display:
        dt = to_local(dt)
    
    # 移除微秒部分，只保留到秒
    dt = dt.replace(microsecond=0)
    
    # 格式化为ISO格式，将T替换为空格，+前添加空格
    iso_str = dt.isoformat()
    iso_str = iso_str.replace('T', ' T').replace('+', ' +')
    return iso_str


def parse_datetime(time_str: str) -> datetime:
    """
    解析ISO格式时间字符串为UTC datetime
    
    Args:
        time_str: ISO格式时间字符串
        
    Returns:
        datetime: UTC时区的datetime
    """
    # 处理 'Z' 后缀（表示UTC）
    if time_str.endswith('Z'):
        time_str = time_str[:-1] + '+00:00'
    
    # 移除display格式中的额外空格 (e.g., '2025-11-23 T14:29:03 +00:00' -> '2025-11-23T14:29:03+00:00')
    time_str = time_str.replace(' T', 'T').replace(' +', '+').replace(' -', '-')
    
    dt = datetime.fromisoformat(time_str)
    return to_utc(dt)


def timestamp_to_datetime(timestamp_ms: int) -> datetime:
    """
    将毫秒时间戳转换为UTC datetime
    
    Args:
        timestamp_ms: 毫秒时间戳
        
    Returns:
        datetime: UTC时区的datetime
    """
    return datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc)


def datetime_to_timestamp(dt: datetime) -> int:
    """
    将datetime转换为毫秒时间戳
    
    Args:
        dt: datetime对象
        
    Returns:
        int: 毫秒时间戳
    """
    dt = to_utc(dt)
    return int(dt.timestamp() * 1000)


def format_time_for_display(time_value: Union[str, datetime, int, None]) -> str:
    """
    统一的时间格式化函数，用于CLI显示
    将各种时间格式转换为用户友好的本地时区字符串

    Args:
        time_value: 时间值，可以是：
            - str: ISO格式时间字符串
            - datetime: datetime对象
            - int: 毫秒时间戳
            - None: 返回 "N/A"

    Returns:
        str: 格式化后的本地时区时间字符串，或 "N/A"
    """
    if time_value is None or time_value == "N/A":
        return "N/A"
    
    try:
        # 处理字符串
        if isinstance(time_value, str):
            if time_value.strip() == "":
                return "N/A"
            dt = parse_datetime(time_value)
            return format_datetime(dt, for_display=True)
        
        # 处理datetime对象
        elif isinstance(time_value, datetime):
            return format_datetime(time_value, for_display=True)
        
        # 处理时间戳（毫秒）
        elif isinstance(time_value, (int, float)):
            dt = timestamp_to_datetime(int(time_value))
            return format_datetime(dt, for_display=True)
        
        else:
            return str(time_value)
            
    except Exception:
        # 转换失败，返回原始值
        return str(time_value) if time_value else "N/A"

