"""存储层数据模型"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict
from enum import Enum
from ..utils.timezone import timestamp_to_datetime, format_datetime


class TaskStatus(str, Enum):
    """任务状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class KlineData:
    """K线数据模型"""
    timestamp: int          # 毫秒时间戳
    open: float            # 开盘价
    high: float            # 最高价
    low: float             # 最低价
    close: float           # 收盘价
    volume: float          # 成交量
    
    def __post_init__(self):
        """数据验证"""
        if self.high < self.low:
            raise ValueError(f"High price ({self.high}) cannot be less than low price ({self.low})")
        if self.high < self.open or self.high < self.close:
            raise ValueError(f"High price ({self.high}) must be >= open and close")
        if self.low > self.open or self.low > self.close:
            raise ValueError(f"Low price ({self.low}) must be <= open and close")
        if self.volume < 0:
            raise ValueError(f"Volume ({self.volume}) cannot be negative")
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'timestamp': self.timestamp,
            'open': self.open,
            'high': self.high,
            'low': self.low,
            'close': self.close,
            'volume': self.volume,
        }
    
    @classmethod
    def from_ccxt(cls, ohlcv: list) -> 'KlineData':
        """从CCXT数据创建"""
        return cls(
            timestamp=int(ohlcv[0]),
            open=float(ohlcv[1]),
            high=float(ohlcv[2]),
            low=float(ohlcv[3]),
            close=float(ohlcv[4]),
            volume=float(ohlcv[5]),
        )


@dataclass
class DataRange:
    """数据范围"""
    start_timestamp: int
    end_timestamp: int
    start_date: str
    end_date: str
    
    @classmethod
    def from_timestamps(cls, start_ts: int, end_ts: int) -> 'DataRange':
        """从时间戳创建（UTC）"""
        return cls(
            start_timestamp=start_ts,
            end_timestamp=end_ts,
            start_date=format_datetime(timestamp_to_datetime(start_ts)),
            end_date=format_datetime(timestamp_to_datetime(end_ts)),
        )


@dataclass
class MissingRange:
    """缺失数据范围"""
    start: str
    end: str
    gap: str  # 时间差
    
    def to_dict(self) -> dict:
        return {
            'start': self.start,
            'end': self.end,
            'gap': self.gap,
        }


@dataclass
class DataQuality:
    """数据质量指标"""
    completeness: float      # 完整性 (0-1)
    duplicate_rate: float    # 重复率 (0-1)
    
    def to_dict(self) -> dict:
        return {
            'completeness': self.completeness,
            'duplicate_rate': self.duplicate_rate,
        }


@dataclass
class PartitionInfo:
    """分区信息"""
    year: int
    month: int
    file_path: str
    records: int
    size_bytes: int
    checksum: str
    created_at: str
    updated_at: str
    interval: str = '1s'
    
    def to_dict(self) -> dict:
        return {
            'year': self.year,
            'month': self.month,
            'file_path': self.file_path,
            'records': self.records,
            'size_bytes': self.size_bytes,
            'checksum': self.checksum,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'interval': self.interval,
        }


@dataclass
class IntervalRange:
    """单个时间段"""
    start_timestamp: int
    end_timestamp: int

    def to_dict(self) -> dict:
        return {
            'start_timestamp': self.start_timestamp,
            'end_timestamp': self.end_timestamp,
        }


@dataclass
class IntervalData:
    """
    某个周期的元数据

    ranges: 已下载的时间段列表，自动合并重叠/相邻段
    completeness: 覆盖时长 / 总跨度（0-1）
    """
    start_timestamp: int
    end_timestamp: int
    ranges: List[IntervalRange] = field(default_factory=list)
    completeness: float = 1.0

    def to_dict(self) -> dict:
        return {
            'start_timestamp': self.start_timestamp,
            'end_timestamp': self.end_timestamp,
            'ranges': [r.to_dict() for r in self.ranges],
            'completeness': self.completeness,
        }


@dataclass
class Statistics:
    """统计信息"""
    total_records: int
    total_size_bytes: int
    missing_ranges: List[MissingRange]
    data_quality: DataQuality
    
    def to_dict(self) -> dict:
        return {
            'total_records': self.total_records,
            'total_size_bytes': self.total_size_bytes,
            'missing_ranges': [mr.to_dict() for mr in self.missing_ranges],
            'data_quality': self.data_quality.to_dict(),
        }


@dataclass
class SymbolMetadata:
    """交易对元数据"""
    exchange: str
    symbol: str
    symbol_id: str
    base: str
    quote: str
    data_range: Optional[DataRange]
    statistics: Optional[Statistics]
    partitions: List[PartitionInfo]
    schema_version: str
    created_at: str
    last_updated: str
    intervals: Dict[str, IntervalData] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'exchange': self.exchange,
            'symbol': self.symbol,
            'symbol_id': self.symbol_id,
            'base': self.base,
            'quote': self.quote,
            'data_range': {
                'first_timestamp': self.data_range.start_timestamp if self.data_range else None,
                'last_timestamp': self.data_range.end_timestamp if self.data_range else None,
                'first_date': self.data_range.start_date if self.data_range else None,
                'last_date': self.data_range.end_date if self.data_range else None,
            } if self.data_range else {},
            'statistics': self.statistics.to_dict() if self.statistics else {},
            'partitions': [p.to_dict() for p in self.partitions],
            'intervals': {
                k: v.to_dict() for k, v in self.intervals.items()
            },
            'schema_version': self.schema_version,
            'created_at': self.created_at,
            'last_updated': self.last_updated,
        }


@dataclass
class DownloadProgress:
    """下载进度"""
    current_timestamp: int
    percentage: float
    downloaded_records: int
    estimated_completion: str
    
    def to_dict(self) -> dict:
        return {
            'current_timestamp': self.current_timestamp,
            'percentage': self.percentage,
            'downloaded_records': self.downloaded_records,
            'estimated_completion': self.estimated_completion,
        }


@dataclass
class DownloadCheckpoint:
    """下载断点"""
    last_timestamp: int
    last_file: str
    
    def to_dict(self) -> dict:
        return {
            'last_timestamp': self.last_timestamp,
            'last_file': self.last_file,
        }


@dataclass
class DownloadTask:
    """下载任务"""
    task_id: str
    exchange: str
    symbol: str
    start_time: str
    end_time: str
    status: TaskStatus
    progress: Optional[DownloadProgress]
    checkpoint: Optional[DownloadCheckpoint]
    errors: List[str]
    created_at: str
    updated_at: str
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'task_id': self.task_id,
            'exchange': self.exchange,
            'symbol': self.symbol,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'status': self.status.value,
            'progress': self.progress.to_dict() if self.progress else None,
            'checkpoint': self.checkpoint.to_dict() if self.checkpoint else None,
            'errors': self.errors,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
        }
