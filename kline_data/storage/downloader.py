"""数据下载器"""

import time
import uuid
import signal
from datetime import datetime, timedelta
from typing import Optional, Generator, Callable
import pandas as pd
import ccxt
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)

from ..config import Config
from .models import (
    KlineData,
    DownloadTask,
    DownloadProgress,
    DownloadCheckpoint,
    TaskStatus,
)
from .writer import ParquetWriter
from .validator import DataValidator
from .metadata_manager import MetadataManager
from ..utils.timezone import (
    now_utc,
    format_datetime,
    datetime_to_timestamp,
    timestamp_to_datetime,
    to_utc,
    format_time_for_display
)
from rich.console import Console

console = Console()


class DataDownloader:
    """
    数据下载器
    负责从CCXT获取K线数据
    """
    
    def __init__(
        self,
        exchange: str,
        symbol: str,
        config: Config,
        interval: str = '1s',
        progress_callback: Optional[Callable[[float, int, int], None]] = None,
        interrupt_handler: Optional[Callable[[], None]] = None
    ):
        """
        初始化下载器
        
        Args:
            exchange: 交易所名称
            symbol: 交易对
            config: 配置对象
            interval: 下载的时间周期（默认1s）
            progress_callback: 进度回调函数(percentage, downloaded_records, total_records)
            interrupt_handler: 中断时调用的处理函数，用于立即停止外部进度渲染
        """
        self.exchange_name = exchange
        self.symbol = symbol
        self.config = config
        self.interval = interval
        self.exchange = self._init_exchange()
        self.progress_callback = progress_callback
        self._interrupt_handler = interrupt_handler
        
        # 组件
        self.writer = ParquetWriter(config)
        self.validator = DataValidator()
        self.metadata_mgr = MetadataManager(config)
        
        # 限流参数
        self.rate_limit_enabled = config.ccxt.rate_limit.enabled
        self.requests_per_minute = config.ccxt.rate_limit.requests_per_minute
        self.min_request_interval = 60.0 / self.requests_per_minute if self.rate_limit_enabled else 0
        self.last_request_time = 0
        
        # 中断处理
        self._interrupted = False
        self._interrupt_notified = False
        self._signal_message_printed = False
        self._current_task = None
        self._original_sigint_handler = None
        self._original_sigterm_handler = None
    
    def _notify_interrupt(self):
        """触发中断回调（只执行一次）"""
        if self._interrupt_notified:
            return
        self._interrupt_notified = True
        if self._interrupt_handler:
            try:
                self._interrupt_handler()
            except Exception:
                # 回调仅用于停止外部进度条，失败时忽略以保证下载流程继续清理
                pass
    
    def _signal_handler(self, signum, frame):
        """信号处理器，用于优雅地处理中断"""
        self._interrupted = True
        self._notify_interrupt()
        if not self._signal_message_printed:
            self._signal_message_printed = True
            console.print(f"\n\n[信号] 接收到中断信号 ({signal.Signals(signum).name})，准备停止下载...")
    
    def _setup_signal_handlers(self):
        """设置信号处理器"""
        self._original_sigint_handler = signal.signal(signal.SIGINT, self._signal_handler)
        self._original_sigterm_handler = signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _restore_signal_handlers(self):
        """恢复原始信号处理器"""
        if self._original_sigint_handler is not None:
            signal.signal(signal.SIGINT, self._original_sigint_handler)
        if self._original_sigterm_handler is not None:
            signal.signal(signal.SIGTERM, self._original_sigterm_handler)
    
    def _init_exchange(self) -> ccxt.Exchange:
        """
        初始化交易所连接
        
        Returns:
            ccxt.Exchange: 交易所实例
        """
        # 获取交易所类
        exchange_class = getattr(ccxt, self.exchange_name)
        
        # 配置参数
        params = {
            'enableRateLimit': True,
            'timeout': self.config.ccxt.retry.timeout * 1000,
        }
        
        # 代理配置
        proxy_dict = self.config.ccxt.proxy.to_dict()
        if proxy_dict:
            params['proxies'] = proxy_dict
        
        return exchange_class(params)
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=4, max=60),
        retry=retry_if_exception_type((ccxt.NetworkError, ccxt.ExchangeNotAvailable))
    )
    def _fetch_ohlcv(
        self,
        since: int,
        limit: int = 1000,
        timeframe: Optional[str] = None
    ) -> list:
        """
        获取OHLCV数据（带重试）
        
        Args:
            since: 起始时间戳（毫秒）
            limit: 限制条数
            timeframe: 时间周期（如果为None，使用self.interval）
            
        Returns:
            list: OHLCV数据列表
        """
        # 限流
        if self.rate_limit_enabled:
            elapsed = time.time() - self.last_request_time
            if elapsed < self.min_request_interval:
                time.sleep(self.min_request_interval - elapsed)
        
        # 发起请求
        self.last_request_time = time.time()
        
        if timeframe is None:
            timeframe = self.interval
        
        try:
            return self.exchange.fetch_ohlcv(
                self.symbol,
                timeframe=timeframe,
                since=since,
                limit=limit
            )
        except ccxt.BadSymbol as e:
            # 交易对不支持该周期
            console.print(f"Warning: {self.symbol} doesn't support {timeframe} data")
            raise
        except ccxt.NotSupported as e:
            console.print(f"Warning: {self.exchange_name} doesn't support {timeframe} timeframe")
            raise
    
    def get_earliest_timestamp(self, timeframe: Optional[str] = None) -> Optional[int]:
        """
        获取交易所支持的最早数据时间戳
        
        Args:
            timeframe: 时间周期（如果为None，使用self.interval）
            
        Returns:
            Optional[int]: 最早时间戳（毫秒），如果获取失败返回None
        """
        if timeframe is None:
            timeframe = self.interval
        
        try:
            # 从一个非常早的时间点开始查询（1970-01-01）
            earliest_timestamp = 0
            ohlcv = self._fetch_ohlcv(earliest_timestamp, limit=1, timeframe=timeframe)
            
            if ohlcv and len(ohlcv) > 0:
                return ohlcv[0][0]  # 返回第一条数据的时间戳
            
            return None
        except Exception as e:
            console.print(f"Failed to get earliest timestamp: {e}")
            return None
    
    def download_range(
        self,
        start_time: datetime,
        end_time: datetime,
        checkpoint: Optional[int] = None,
        task_id: Optional[str] = None,
        force: bool = False
    ) -> str:
        """
        下载时间范围内的数据
        
        Args:
            start_time: 开始时间
            end_time: 结束时间
            checkpoint: 断点时间戳
            task_id: 任务ID
            force: 是否强制重新下载（删除现有数据）
            
        Returns:
            str: 任务ID
        """
        # 创建任务
        if task_id is None:
            task_id = str(uuid.uuid4())
        
        # 重置中断状态，确保复用实例时行为正确
        self._interrupted = False
        self._interrupt_notified = False
        self._signal_message_printed = False
    
        # 确保时间为UTC
        start_time = to_utc(start_time)
        end_time = to_utc(end_time)
        
        # 检查该周期是否已有重叠数据
        start_timestamp = datetime_to_timestamp(start_time)
        end_timestamp = datetime_to_timestamp(end_time)
        
        # 如果强制下载，先删除指定时间范围的数据
        if force:
            console.print(f"Force mode enabled, deleting existing data in range [{format_datetime(start_time, for_display=True)} - {format_datetime(end_time, for_display=True)}]...")
            affected_files = self.writer.delete_time_range(
                self.exchange_name,
                self.symbol,
                start_time,
                end_time,
                self.interval
            )
            if affected_files:
                console.print(f"Deleted/updated {len(affected_files)} partition file(s)")
                # 更新元数据
                self.metadata_mgr.delete_time_range_metadata(
                    self.exchange_name,
                    self.symbol,
                    self.interval,
                    start_timestamp,
                    end_timestamp
                )
        
        missing_ranges = self.metadata_mgr.calculate_missing_ranges(
            self.exchange_name,
            self.symbol,
            self.interval,
            start_timestamp,
            end_timestamp
        )
        
        if not missing_ranges:
            console.print(f"All data for {self.interval} in range [{format_datetime(start_time, for_display=True)} - {format_datetime(end_time, for_display=True)}] already exists, skipping download.")
            return task_id
        
        console.print(f"Found {len(missing_ranges)} missing range(s) to download for {self.interval}:")
        for i, (ms, me) in enumerate(missing_ranges, 1):
            console.print(f"  Range {i}: {format_time_for_display(timestamp_to_datetime(ms))} - {format_time_for_display(timestamp_to_datetime(me))}")
        
        task = DownloadTask(
            task_id=task_id,
            exchange=self.exchange_name,
            symbol=self.symbol,
            start_time=format_datetime(start_time),
            end_time=format_datetime(end_time),
            status=TaskStatus.RUNNING,
            progress=None,
            checkpoint=None,
            errors=[],
            created_at=format_datetime(now_utc()),
            updated_at=format_datetime(now_utc()),
        )
        self.metadata_mgr.save_download_task(task)
        
        # 设置信号处理
        self._current_task = task
        self._setup_signal_handlers()
        
        try:
            # 执行下载（分段下载缺失的数据）
            for range_start_ts, range_end_ts in missing_ranges:
                # 检查是否被中断
                if self._interrupted:
                    raise KeyboardInterrupt("Download interrupted by user")
                
                range_start = timestamp_to_datetime(range_start_ts)
                range_end = timestamp_to_datetime(range_end_ts)
                console.print(f"\nDownloading range: {format_datetime(range_start, for_display=True)} - {format_datetime(range_end, for_display=True)}")
                # 每个缺失范围从头开始下载，不使用checkpoint
                self._download_data(range_start, range_end, None, task)
            
            # 更新任务状态
            task.status = TaskStatus.COMPLETED
            task.updated_at = format_datetime(now_utc())
            self.metadata_mgr.save_download_task(task)
            
            # 自动清理已完成的任务文件
            self.metadata_mgr.delete_download_task(task.task_id)
            
        except KeyboardInterrupt:
            # 用户中断（Ctrl+C）
            self._notify_interrupt()
            console.print("\n\n[中断] 检测到用户中断，正在保存进度...")
            task.status = TaskStatus.CANCELLED
            task.errors.append("User interrupted (Ctrl+C)")
            task.updated_at = format_datetime(now_utc())
            self.metadata_mgr.save_download_task(task)
            console.print(f"[保存] 任务已标记为取消状态，可使用 'kline task list' 恢复")
            raise
            
        except Exception as e:
            # 其他错误
            task.status = TaskStatus.FAILED
            task.errors.append(str(e))
            task.updated_at = format_datetime(now_utc())
            self.metadata_mgr.save_download_task(task)
            raise
            
        finally:
            # 恢复信号处理器
            self._restore_signal_handlers()
            self._current_task = None
        
        return task_id
    
    def _download_data(
        self,
        start_time: datetime,
        end_time: datetime,
        checkpoint: Optional[int],
        task: DownloadTask
    ) -> None:
        """
        执行数据下载
        
        Args:
            start_time: 开始时间（UTC）
            end_time: 结束时间（UTC）
            checkpoint: 断点时间戳
            task: 任务对象
        """
        # 确保使用UTC时区
        start_time = to_utc(start_time)
        end_time = to_utc(end_time)
        
        current_time = checkpoint if checkpoint else datetime_to_timestamp(start_time)
        end_timestamp = datetime_to_timestamp(end_time)
        
        chunk_size = self.config.memory.chunk_size
        batch_data = []
        
        total_duration = end_timestamp - (checkpoint if checkpoint else datetime_to_timestamp(start_time))
        downloaded_records = 0
        skip_first_batch_duplicate = checkpoint is not None
        
        # 计算预估总记录数
        from kline_data.resampler.timeframe import get_timeframe_seconds
        interval_seconds = get_timeframe_seconds(self.interval)
        estimated_total_records = int(total_duration / 1000 / interval_seconds) if interval_seconds > 0 else 0
        
        while current_time < end_timestamp:
            # 检查是否被中断
            if self._interrupted:
                raise KeyboardInterrupt("Download interrupted by user")
            
            try:
                # 获取数据
                ohlcv = self._fetch_ohlcv(current_time, limit=1000)
                
                if not ohlcv:
                    console.print(f"No more data available at {timestamp_to_datetime(current_time)}")
                    break
                
                # 转换为KlineData
                for row in ohlcv:
                    # 只有在断点恢复时才跳过首条重复
                    if skip_first_batch_duplicate and row[0] <= current_time:
                        continue  # 跳过已处理的数据
                    
                    if row[0] > end_timestamp:
                        break  # 超出范围
                    
                    kline = KlineData.from_ccxt(row)
                    batch_data.append(kline.to_dict())
                    downloaded_records += 1
                
                # 第一批处理完后，后续批次不再跳过首条
                skip_first_batch_duplicate = False
                
                # 更新时间戳（根据周期移动）
                from kline_data.resampler.timeframe import get_timeframe_seconds
                interval_ms = get_timeframe_seconds(self.interval) * 1000
                last_timestamp = ohlcv[-1][0]
                current_time = last_timestamp + interval_ms
                
                # 达到chunk大小时保存
                if len(batch_data) >= chunk_size:
                    self._save_batch(batch_data)
                    batch_data = []
                
                # 更新进度
                progress = (current_time - datetime_to_timestamp(start_time)) / total_duration * 100
                progress_pct = min(progress, 100.0)
                task.progress = DownloadProgress(
                    current_timestamp=current_time,
                    percentage=progress_pct,
                    downloaded_records=downloaded_records,
                    estimated_completion=self._estimate_completion(
                        progress, task.created_at
                    )
                )
                task.checkpoint = DownloadCheckpoint(
                    last_timestamp=current_time,
                    last_file=''
                )
                task.updated_at = format_datetime(now_utc())
                self.metadata_mgr.save_download_task(task)
                
                # 调用进度回调（仅在未中断时）
                if not self._interrupted:
                    if self.progress_callback:
                        self.progress_callback(progress_pct, downloaded_records, estimated_total_records)
                    else:
                        console.print(f"Progress: {progress_pct:.2f}% ({downloaded_records}/{estimated_total_records} records)")
                
            except Exception as e:
                console.print(f"Error at timestamp {current_time}: {e}")
                task.errors.append(f"{current_time}: {str(e)}")
                
                # 重试前等待
                time.sleep(self.config.ccxt.retry.backoff_factor)
        
        # 保存剩余数据
        if batch_data:
            self._save_batch(batch_data)
    
    def _save_batch(self, batch_data: list) -> None:
        """
        保存批次数据
        
        Args:
            batch_data: 批次数据列表
        """
        if not batch_data:
            return
        
        # 转换为DataFrame
        df = pd.DataFrame(batch_data)
        
        # 验证数据
        df = self.validator.validate_kline(df)
        
        # 分区写入
        partition_infos = self.writer.write_partitioned(
            df,
            self.exchange_name,
            self.symbol,
            interval=self.interval
        )
        
        # 更新元数据
        for partition_info in partition_infos:
            self.metadata_mgr.add_partition(
                self.exchange_name,
                self.symbol,
                partition_info
            )
        
        # 更新数据范围（timestamp已经是UTC aware）
        min_ts = datetime_to_timestamp(df['timestamp'].min())
        max_ts = datetime_to_timestamp(df['timestamp'].max())
        self.metadata_mgr.update_data_range(
            self.exchange_name,
            self.symbol,
            min_ts,
            max_ts
        )

        # 记录该周期的覆盖时间段，合并重叠/相邻区间
        self.metadata_mgr.add_interval_range(
            self.exchange_name,
            self.symbol,
            self.interval,
            min_ts,
            max_ts
        )
        
        # 更新统计信息（只更新总量，不做完整性检查）
        metadata = self.metadata_mgr.get_symbol_metadata(
            self.exchange_name,
            self.symbol
        )

        # 按全部分区聚合，避免多个周期下载时覆盖统计
        total_records = sum(p.records for p in metadata.partitions)
        total_size = sum(p.size_bytes for p in metadata.partitions)
        
        # 使用空列表和默认质量指标，避免混淆单批次与全局统计
        # 完整性检查应该在整个下载任务完成后单独进行
        from .models import DataQuality
        self.metadata_mgr.update_statistics(
            self.exchange_name,
            self.symbol,
            total_records,
            total_size,
            [],  # 不在这里检查缺失范围
            DataQuality(completeness=1.0, duplicate_rate=0.0)  # 使用默认值
        )
    
    def _estimate_completion(
        self,
        progress: float,
        start_time_str: str
    ) -> str:
        """
        估算完成时间
        
        Args:
            progress: 进度百分比
            start_time_str: 开始时间字符串
            
        Returns:
            str: 估算完成时间
        """
        if progress <= 0:
            return "Unknown"
        
        from kline_data.utils.timezone import parse_datetime
        start_time = parse_datetime(start_time_str)
        elapsed = (now_utc() - start_time).total_seconds()
        
        total_time = elapsed / (progress / 100)
        remaining_time = total_time - elapsed
        
        completion_time = now_utc() + timedelta(seconds=remaining_time)
        return format_datetime(completion_time)
    
    def resume_download(self, task_id: str) -> str:
        """
        恢复下载任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            str: 任务ID
        """
        task = self.metadata_mgr.get_download_task(task_id)
        
        if task is None:
            raise ValueError(f"Task {task_id} not found")
        
        if task.status == TaskStatus.COMPLETED:
            console.print(f"Task {task_id} already completed")
            return task_id
        
        # 继续下载（解析为UTC时间）
        from kline_data.utils.timezone import parse_datetime
        start_time = parse_datetime(task.start_time)
        end_time = parse_datetime(task.end_time)
        
        # 不传递checkpoint，让download_range自动检测并填补所有缺失的时间段
        return self.download_range(start_time, end_time, checkpoint=None, task_id=task_id)
    
    def update_to_latest(self) -> Optional[str]:
        """
        更新到最新数据
        
        Returns:
            Optional[str]: 任务ID，如果无需更新返回None
        """
        # 获取现有数据范围
        data_range = self.metadata_mgr.get_data_range(
            self.exchange_name,
            self.symbol
        )
        
        if data_range is None:
            console.print("No existing data, please download first")
            return None
        
        # 从最后时间戳开始下载（UTC）
        start_time = timestamp_to_datetime(data_range[1])
        end_time = now_utc()
        
        # 如果间隔小于1分钟，无需更新
        if (end_time - start_time).total_seconds() < 60:
            console.print("Data is already up to date")
            return None
        
        return self.download_range(start_time, end_time)


class DownloadManager:
    """
    下载管理器
    管理多个下载任务
    """
    
    def __init__(self, config: Config):
        """
        初始化管理器
        
        Args:
            config: 配置对象
        """
        self.config = config
        self.metadata_mgr = MetadataManager(config)
    
    def create_downloader(
        self,
        exchange: str,
        symbol: str,
        interval: str = '1s',
        progress_callback: Optional[Callable[[float, int, int], None]] = None,
        interrupt_handler: Optional[Callable[[], None]] = None
    ) -> DataDownloader:
        """
        创建下载器实例
        
        Args:
            exchange: 交易所
            symbol: 交易对
            interval: 时间周期
            progress_callback: 进度回调函数(percentage, downloaded_records, total_records)
            interrupt_handler: 中断时调用的处理函数，用于停止外部进度显示
            
        Returns:
            DataDownloader: 下载器实例
        """
        return DataDownloader(exchange, symbol, self.config, interval, progress_callback, interrupt_handler)
    
    def download(
        self,
        exchange: str,
        symbol: str,
        start_time: datetime,
        end_time: Optional[datetime] = None,
        interval: str = '1s',
        progress_callback: Optional[Callable[[float, int, int], None]] = None,
        interrupt_handler: Optional[Callable[[], None]] = None,
        force: bool = False
    ) -> str:
        """
        下载数据
        
        Args:
            exchange: 交易所
            symbol: 交易对
            start_time: 开始时间（会转换为UTC）
            end_time: 结束时间（会转换为UTC）
            interval: 时间周期
            progress_callback: 进度回调函数(percentage, downloaded_records, total_records)
            interrupt_handler: 中断时调用的处理函数，用于停止外部进度显示
            force: 是否强制重新下载（删除现有数据）
            
        Returns:
            str: 任务ID
        """
        if end_time is None:
            end_time = now_utc()
        
        downloader = self.create_downloader(exchange, symbol, interval, progress_callback, interrupt_handler)
        return downloader.download_range(start_time, end_time, force=force)
    
    def update(self, exchange: str, symbol: str) -> Optional[str]:
        """
        更新数据到最新
        
        Args:
            exchange: 交易所
            symbol: 交易对
            
        Returns:
            Optional[str]: 任务ID
        """
        downloader = self.create_downloader(exchange, symbol)
        return downloader.update_to_latest()
    
    def resume(self, task_id: str) -> str:
        """
        恢复任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            str: 任务ID
        """
        # 获取任务信息
        task = self.metadata_mgr.get_download_task(task_id)
        
        if task is None:
            raise ValueError(f"Task {task_id} not found")
        
        downloader = self.create_downloader(task.exchange, task.symbol)
        return downloader.resume_download(task_id)
    
    def get_task_status(self, task_id: str) -> Optional[DownloadTask]:
        """
        获取任务状态
        
        Args:
            task_id: 任务ID
            
        Returns:
            Optional[DownloadTask]: 任务对象
        """
        return self.metadata_mgr.get_download_task(task_id)
    
    def list_tasks(
        self,
        status: Optional[TaskStatus] = None
    ) -> list:
        """
        列出任务
        
        Args:
            status: 状态过滤
            
        Returns:
            list: 任务列表
        """
        return self.metadata_mgr.list_download_tasks(status)
