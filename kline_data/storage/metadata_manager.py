"""元数据管理器"""

import json
from pathlib import Path
from typing import Optional, List, Tuple
from datetime import datetime

from ..config import Config
from .models import (
    SymbolMetadata,
    DataRange,
    Statistics,
    DataQuality,
    MissingRange,
    PartitionInfo,
    IntervalData,
    IntervalRange,
    DownloadTask,
    TaskStatus,
)
from ..utils.timezone import (
    now_utc,
    format_datetime,
    timestamp_to_datetime,
)


class MetadataManager:
    """
    元数据管理器
    负责管理交易对的元数据
    """
    
    def __init__(self, config: Config):
        """
        初始化元数据管理器
        
        Args:
            config: 配置对象
        """
        self.config = config
        self.root_path = config.storage.get_root_path()
        self.metadata_dir = self.root_path / 'metadata'
        self.index_dir = self.metadata_dir / 'index'
        
        # 确保目录存在
        self.metadata_dir.mkdir(parents=True, exist_ok=True)
        self.index_dir.mkdir(parents=True, exist_ok=True)
    
    def get_symbol_metadata(
        self,
        exchange: str,
        symbol: str
    ) -> SymbolMetadata:
        """
        获取交易对元数据
        
        Args:
            exchange: 交易所
            symbol: 交易对
            
        Returns:
            SymbolMetadata: 元数据对象
        """
        file_path = self._get_metadata_path(exchange, symbol)
        
        if file_path.exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return self._dict_to_metadata(data)
        else:
            return self._create_empty_metadata(exchange, symbol)
    
    def save_symbol_metadata(
        self,
        metadata: SymbolMetadata
    ) -> None:
        """
        保存交易对元数据
        
        Args:
            metadata: 元数据对象
        """
        file_path = self._get_metadata_path(metadata.exchange, metadata.symbol)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 更新最后修改时间（UTC）
        metadata.last_updated = format_datetime(now_utc())
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(metadata.to_dict(), f, indent=2, ensure_ascii=False)
    
    def update_metadata(
        self,
        exchange: str,
        symbol: str,
        **updates
    ) -> SymbolMetadata:
        """
        更新元数据
        
        Args:
            exchange: 交易所
            symbol: 交易对
            **updates: 要更新的字段
            
        Returns:
            SymbolMetadata: 更新后的元数据
        """
        metadata = self.get_symbol_metadata(exchange, symbol)
        
        # 更新字段
        for key, value in updates.items():
            if hasattr(metadata, key):
                setattr(metadata, key, value)
        
        # 保存
        self.save_symbol_metadata(metadata)
        
        return metadata
    
    def add_partition(
        self,
        exchange: str,
        symbol: str,
        partition_info: PartitionInfo
    ) -> None:
        """
        添加分区信息
        
        Args:
            exchange: 交易所
            symbol: 交易对
            partition_info: 分区信息
        """
        metadata = self.get_symbol_metadata(exchange, symbol)
        
        # 检查是否已存在（通过 year, month 和 interval 匹配）
        existing_idx = None
        for i, p in enumerate(metadata.partitions):
            if (p.year == partition_info.year and 
                p.month == partition_info.month and 
                p.interval == partition_info.interval):
                existing_idx = i
                break
        
        if existing_idx is not None:
            # 更新现有分区
            metadata.partitions[existing_idx] = partition_info
        else:
            # 添加新分区
            metadata.partitions.append(partition_info)
        
        # 保存
        self.save_symbol_metadata(metadata)
    
    def add_interval_range(
        self,
        exchange: str,
        symbol: str,
        interval: str,
        start_timestamp: int,
        end_timestamp: int
    ) -> IntervalData:
        """
        记录某个周期的已下载时间段，并自动合并重叠/相邻区间
        
        Args:
            exchange: 交易所
            symbol: 交易对
            interval: 周期字符串（如 '1s', '1m'）
            start_timestamp: 时间段起始（毫秒）
            end_timestamp: 时间段结束（毫秒）
        
        Returns:
            IntervalData: 更新后的周期元数据
        """
        from kline_data.resampler.timeframe import get_timeframe_seconds
        from rich.console import Console
        console = Console()

        metadata = self.get_symbol_metadata(exchange, symbol)

        # 现有区间
        existing = metadata.intervals.get(interval)
        ranges = list(existing.ranges) if existing else []

        # 追加新段
        ranges.append(IntervalRange(
            start_timestamp=start_timestamp,
            end_timestamp=end_timestamp
        ))

        # 按步长合并，允许相邻（<=1个步长）
        step_ms = get_timeframe_seconds(interval) * 1000
        merged = self._merge_ranges(ranges, step_ms)

        # 计算完整性：已覆盖时长 / 总跨度
        total_span = merged[-1].end_timestamp - merged[0].start_timestamp + step_ms
        covered = sum(
            r.end_timestamp - r.start_timestamp + step_ms
            for r in merged
        )
        completeness = covered / total_span if total_span > 0 else 1.0

        interval_data = IntervalData(
            start_timestamp=merged[0].start_timestamp,
            end_timestamp=merged[-1].end_timestamp,
            ranges=merged,
            completeness=min(completeness, 1.0)
        )

        metadata.intervals[interval] = interval_data
        self.save_symbol_metadata(metadata)
        return interval_data
    
    def update_data_range(
        self,
        exchange: str,
        symbol: str,
        start_timestamp: int,
        end_timestamp: int
    ) -> None:
        """
        更新数据范围
        
        Args:
            exchange: 交易所
            symbol: 交易对
            start_timestamp: 开始时间戳
            end_timestamp: 结束时间戳
        """
        metadata = self.get_symbol_metadata(exchange, symbol)
        
        # 更新或创建数据范围
        if metadata.data_range is None:
            metadata.data_range = DataRange.from_timestamps(
                start_timestamp, end_timestamp
            )
        else:
            # 扩展范围
            if start_timestamp < metadata.data_range.start_timestamp:
                metadata.data_range.start_timestamp = start_timestamp
                metadata.data_range.start_date = format_datetime(
                    timestamp_to_datetime(start_timestamp)
                )
            
            if end_timestamp > metadata.data_range.end_timestamp:
                metadata.data_range.end_timestamp = end_timestamp
                metadata.data_range.end_date = format_datetime(
                    timestamp_to_datetime(end_timestamp)
                )
        
        # 保存
        self.save_symbol_metadata(metadata)
    
    def update_statistics(
        self,
        exchange: str,
        symbol: str,
        total_records: int,
        total_size_bytes: int,
        missing_ranges: List[MissingRange],
        data_quality: DataQuality
    ) -> None:
        """
        更新统计信息
        
        Args:
            exchange: 交易所
            symbol: 交易对
            total_records: 总记录数
            total_size_bytes: 总大小（字节）
            missing_ranges: 缺失范围列表
            data_quality: 数据质量
        """
        metadata = self.get_symbol_metadata(exchange, symbol)
        
        metadata.statistics = Statistics(
            total_records=total_records,
            total_size_bytes=total_size_bytes,
            missing_ranges=missing_ranges,
            data_quality=data_quality
        )
        
        self.save_symbol_metadata(metadata)
    
    def get_data_range(
        self,
        exchange: str,
        symbol: str
    ) -> Optional[Tuple[int, int]]:
        """
        获取数据时间范围
        
        Args:
            exchange: 交易所
            symbol: 交易对
            
        Returns:
            Optional[Tuple[int, int]]: (开始时间戳, 结束时间戳)
        """
        metadata = self.get_symbol_metadata(exchange, symbol)
        
        if metadata.data_range:
            return (
                metadata.data_range.start_timestamp,
                metadata.data_range.end_timestamp
            )
        
        return None
    
    def get_interval_ranges(
        self,
        exchange: str,
        symbol: str,
        interval: str
    ) -> List[IntervalRange]:
        """
        获取指定周期的已下载时间段列表
        
        Args:
            exchange: 交易所
            symbol: 交易对
            interval: 周期字符串（如 '1s', '1m'）
            
        Returns:
            List[IntervalRange]: 已下载的时间段列表（已排序）
        """
        metadata = self.get_symbol_metadata(exchange, symbol)
        interval_data = metadata.intervals.get(interval)
        
        if interval_data and interval_data.ranges:
            return sorted(interval_data.ranges, key=lambda r: r.start_timestamp)
        
        return []
    
    def calculate_missing_ranges(
        self,
        exchange: str,
        symbol: str,
        interval: str,
        request_start: int,
        request_end: int
    ) -> List[Tuple[int, int]]:
        """
        计算需要下载的时间段（排除已有数据）
        
        注意：时间戳范围是闭区间 [start, end]，已有数据的边界点不需要重复下载
        
        Args:
            exchange: 交易所
            symbol: 交易对
            interval: 周期字符串（如 '1s', '1m'）
            request_start: 请求起始时间戳（毫秒）
            request_end: 请求结束时间戳（毫秒）
            
        Returns:
            List[Tuple[int, int]]: 需要下载的时间段列表 [(start1, end1), (start2, end2), ...]
        """
        existing_ranges = self.get_interval_ranges(exchange, symbol, interval)
        
        if not existing_ranges:
            # 没有已下载数据，返回完整区间
            return [(request_start, request_end)]
        
        missing = []
        current_start = request_start
        
        for existing in existing_ranges:
            # 如果已有数据在请求范围之后，退出循环
            if existing.start_timestamp > request_end:
                break
            
            # 如果已有数据在请求范围之前，跳过
            if existing.end_timestamp < request_start:
                continue
            
            # 如果当前起点在已有数据之前，有缺失段
            # 缺失段结束于已有数据的起点前一个时间戳
            if current_start < existing.start_timestamp:
                missing.append((current_start, existing.start_timestamp - 1))
            
            # 更新当前起点到已有数据的结束点之后
            # 已有数据的结束点已经包含在内，所以下一段从 end_timestamp + 1 开始
            current_start = max(current_start, existing.end_timestamp + 1)
        
        # 如果还有剩余时间段
        if current_start <= request_end:
            missing.append((current_start, request_end))
        
        return missing
    
    def list_exchanges(self) -> List[str]:
        """
        列出所有交易所
        
        Returns:
            List[str]: 交易所列表
        """
        exchanges = []
        
        if self.index_dir.exists():
            for path in self.index_dir.iterdir():
                if path.is_dir():
                    exchanges.append(path.name)
        
        return sorted(exchanges)
    
    def list_symbols(self, exchange: str) -> List[str]:
        """
        列出交易所的所有交易对
        
        Args:
            exchange: 交易所名称
            
        Returns:
            List[str]: 交易对列表
        """
        symbols = []
        exchange_dir = self.index_dir / exchange
        
        if exchange_dir.exists():
            for path in exchange_dir.iterdir():
                if path.is_file() and path.suffix == '.json':
                    try:
                        # 读取元数据获取symbol
                        with open(path, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        symbols.append(data.get('symbol'))
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        # 跳过无效的JSON文件
                        continue
        
        return sorted(symbols)
    
    def delete_symbol_metadata(
        self,
        exchange: str,
        symbol: str
    ) -> bool:
        """
        删除交易对元数据
        
        Args:
            exchange: 交易所
            symbol: 交易对
            
        Returns:
            bool: 是否删除成功
        """
        file_path = self._get_metadata_path(exchange, symbol)
        
        if file_path.exists():
            file_path.unlink()
            return True
        
        return False
    
    # 下载任务管理
    
    def save_download_task(self, task: DownloadTask) -> None:
        """
        保存下载任务
        
        Args:
            task: 下载任务对象
        """
        tasks_dir = self.metadata_dir / 'tasks'
        tasks_dir.mkdir(exist_ok=True)
        
        file_path = tasks_dir / f"{task.task_id}.json"
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(task.to_dict(), f, indent=2, ensure_ascii=False)
    
    def get_download_task(self, task_id: str) -> Optional[DownloadTask]:
        """
        获取下载任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            Optional[DownloadTask]: 任务对象
        """
        tasks_dir = self.metadata_dir / 'tasks'
        file_path = tasks_dir / f"{task_id}.json"
        
        if not file_path.exists():
            return None
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return self._dict_to_task(data)
    
    def list_download_tasks(
        self,
        status: Optional[TaskStatus] = None
    ) -> List[DownloadTask]:
        """
        列出下载任务
        
        Args:
            status: 任务状态过滤
            
        Returns:
            List[DownloadTask]: 任务列表
        """
        tasks_dir = self.metadata_dir / 'tasks'
        
        if not tasks_dir.exists():
            return []
        
        tasks = []
        for file_path in tasks_dir.glob('*.json'):
            # 跳过隐藏文件和系统文件（如macOS的._文件）
            if file_path.name.startswith('.') or file_path.name.startswith('._'):
                continue
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                task = self._dict_to_task(data)
                
                if status is None or task.status == status:
                    tasks.append(task)
            except (json.JSONDecodeError, UnicodeDecodeError, KeyError) as e:
                # 跳过损坏或格式错误的任务文件
                console.print(f"Warning: Failed to read task file {file_path.name}: {e}")
                continue
        
        return sorted(tasks, key=lambda t: t.created_at, reverse=True)
    
    def delete_download_task(self, task_id: str) -> bool:
        """
        删除下载任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            bool: 是否删除成功
        """
        tasks_dir = self.metadata_dir / 'tasks'
        file_path = tasks_dir / f"{task_id}.json"
        
        if file_path.exists():
            file_path.unlink()
            return True
        
        return False
    
    def _get_metadata_path(self, exchange: str, symbol: str) -> Path:
        """
        获取元数据文件路径
        
        Args:
            exchange: 交易所
            symbol: 交易对
            
        Returns:
            Path: 文件路径
        """
        symbol_id = symbol.replace('/', '')
        return self.index_dir / exchange / f"{symbol_id}.json"
    
    def _create_empty_metadata(
        self,
        exchange: str,
        symbol: str
    ) -> SymbolMetadata:
        """
        创建空元数据
        
        Args:
            exchange: 交易所
            symbol: 交易对
            
        Returns:
            SymbolMetadata: 元数据对象
        """
        # 解析交易对
        parts = symbol.split('/')
        base = parts[0] if len(parts) > 0 else ''
        quote = parts[1] if len(parts) > 1 else ''
        
        return SymbolMetadata(
            exchange=exchange,
            symbol=symbol,
            symbol_id=symbol.replace('/', ''),
            base=base,
            quote=quote,
            data_range=None,
            statistics=None,
            partitions=[],
            intervals={},
            schema_version='1.0',
            created_at=format_datetime(now_utc()),
            last_updated=format_datetime(now_utc()),
        )
    
    def _dict_to_metadata(self, data: dict) -> SymbolMetadata:
        """
        将字典转换为元数据对象
        
        Args:
            data: 字典数据
            
        Returns:
            SymbolMetadata: 元数据对象
        """
        # 转换data_range
        data_range = None
        if data.get('data_range') and data['data_range'].get('first_timestamp'):
            data_range = DataRange(
                start_timestamp=data['data_range']['first_timestamp'],
                end_timestamp=data['data_range']['last_timestamp'],
                start_date=data['data_range']['first_date'],
                end_date=data['data_range']['last_date'],
            )
        
        # 转换statistics
        statistics = None
        if data.get('statistics') and data['statistics'].get('total_records') is not None:
            missing_ranges = [
                MissingRange(**mr) for mr in data['statistics'].get('missing_ranges', [])
            ]
            data_quality = DataQuality(**data['statistics'].get('data_quality', {}))
            
            statistics = Statistics(
                total_records=data['statistics']['total_records'],
                total_size_bytes=data['statistics']['total_size_bytes'],
                missing_ranges=missing_ranges,
                data_quality=data_quality,
            )
        
        # 转换partitions（兼容旧格式，如果没有 interval 字段则默认为 '1s'）
        partitions = []
        for p in data.get('partitions', []):
            if 'interval' not in p:
                p['interval'] = '1s'
            partitions.append(PartitionInfo(**p))

        # 转换intervals
        intervals = {}
        for interval, info in data.get('intervals', {}).items():
            start_ts = info.get('start_timestamp')
            end_ts = info.get('end_timestamp')
            if start_ts is None or end_ts is None:
                continue

            ranges = []
            for r in info.get('ranges', []):
                r_start = r.get('start_timestamp')
                r_end = r.get('end_timestamp')
                if r_start is None or r_end is None:
                    continue
                ranges.append(IntervalRange(
                    start_timestamp=r_start,
                    end_timestamp=r_end
                ))

            intervals[interval] = IntervalData(
                start_timestamp=start_ts,
                end_timestamp=end_ts,
                ranges=ranges,
                completeness=info.get('completeness', 1.0)
            )
        
        return SymbolMetadata(
            exchange=data['exchange'],
            symbol=data['symbol'],
            symbol_id=data['symbol_id'],
            base=data.get('base', ''),
            quote=data.get('quote', ''),
            data_range=data_range,
            statistics=statistics,
            partitions=partitions,
            intervals=intervals,
            schema_version=data.get('schema_version', '1.0'),
            created_at=data.get('created_at', format_datetime(now_utc())),
            last_updated=data.get('last_updated', format_datetime(now_utc())),
        )
    
    def _dict_to_task(self, data: dict) -> DownloadTask:
        """
        将字典转换为下载任务对象
        
        Args:
            data: 字典数据
            
        Returns:
            DownloadTask: 任务对象
        """
        from .models import DownloadProgress, DownloadCheckpoint

        
        progress = None
        if data.get('progress'):
            progress = DownloadProgress(**data['progress'])
        
        checkpoint = None
        if data.get('checkpoint'):
            checkpoint = DownloadCheckpoint(**data['checkpoint'])
        
        return DownloadTask(
            task_id=data['task_id'],
            exchange=data['exchange'],
            symbol=data['symbol'],
            start_time=data['start_time'],
            end_time=data['end_time'],
            status=TaskStatus(data['status']),
            progress=progress,
            checkpoint=checkpoint,
            errors=data.get('errors', []),
            created_at=data['created_at'],
            updated_at=data['updated_at'],
        )

    @staticmethod
    def _merge_ranges(
        ranges: List[IntervalRange],
        step_ms: int
    ) -> List[IntervalRange]:
        """
        合并重叠或相邻的时间段

        Args:
            ranges: 时间段列表
            step_ms: 周期对应的毫秒步长

        Returns:
            List[IntervalRange]: 合并后的时间段
        """
        if not ranges:
            return []

        sorted_ranges = sorted(
            ranges, key=lambda r: r.start_timestamp
        )

        merged: List[IntervalRange] = []
        for r in sorted_ranges:
            if not merged:
                merged.append(r)
                continue

            last = merged[-1]
            if r.start_timestamp <= last.end_timestamp + step_ms:
                # 合并
                last.end_timestamp = max(last.end_timestamp, r.end_timestamp)
            else:
                merged.append(r)

        return merged
    
    def delete_time_range_metadata(
        self,
        exchange: str,
        symbol: str,
        interval: str,
        start_timestamp: int,
        end_timestamp: int
    ) -> None:
        """
        删除元数据中指定时间范围的信息
        
        Args:
            exchange: 交易所
            symbol: 交易对
            interval: 时间周期
            start_timestamp: 开始时间戳（毫秒）
            end_timestamp: 结束时间戳（毫秒）
        """
        metadata = self.get_symbol_metadata(exchange, symbol)
        if not metadata:
            return
        
        # 更新 interval ranges - 从现有范围中剔除被删除的时间段
        if interval in metadata.intervals:
            interval_data = metadata.intervals[interval]
            updated_ranges = []
            
            for range_obj in interval_data.ranges:
                # 完全在删除范围之前
                if range_obj.end_timestamp < start_timestamp:
                    updated_ranges.append(range_obj)
                # 完全在删除范围之后
                elif range_obj.start_timestamp > end_timestamp:
                    updated_ranges.append(range_obj)
                # 部分重叠 - 需要切分
                else:
                    # 保留删除范围之前的部分
                    if range_obj.start_timestamp < start_timestamp:
                        updated_ranges.append(IntervalRange(
                            start_timestamp=range_obj.start_timestamp,
                            end_timestamp=start_timestamp - 1
                        ))
                    # 保留删除范围之后的部分
                    if range_obj.end_timestamp > end_timestamp:
                        updated_ranges.append(IntervalRange(
                            start_timestamp=end_timestamp + 1,
                            end_timestamp=range_obj.end_timestamp
                        ))
            
            # 更新ranges
            interval_data.ranges = updated_ranges
            
            # 如果该周期没有数据了，移除该周期
            if not updated_ranges:
                del metadata.intervals[interval]
            else:
                # 更新该周期的整体范围
                interval_data.start_timestamp = min(r.start_timestamp for r in updated_ranges)
                interval_data.end_timestamp = max(r.end_timestamp for r in updated_ranges)
        
        # 重新计算总体数据范围（从所有 interval 中取并集）
        if metadata.intervals:
            all_starts = [iv.start_timestamp for iv in metadata.intervals.values()]
            all_ends = [iv.end_timestamp for iv in metadata.intervals.values()]
            
            if all_starts and all_ends:
                global_start = min(all_starts)
                global_end = max(all_ends)
                
                if metadata.data_range:
                    metadata.data_range.start_timestamp = global_start
                    metadata.data_range.end_timestamp = global_end
                    metadata.data_range.start_date = format_datetime(timestamp_to_datetime(global_start))
                    metadata.data_range.end_date = format_datetime(timestamp_to_datetime(global_end))
                else:
                    metadata.data_range = DataRange.from_timestamps(global_start, global_end)
        else:
            # 如果没有任何 interval 数据了，清空 data_range
            metadata.data_range = None
        
        self.save_symbol_metadata(metadata)
