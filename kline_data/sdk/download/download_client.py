"""下载客户端 - 数据下载管理"""

from typing import Optional, Callable
from datetime import datetime

from ...config import Config
from ...storage import DownloadManager, MetadataManager
from ...utils.constants import (
    DEFAULT_DOWNLOAD_INTERVAL,
    validate_timeframe,
    validate_exchange,
    validate_symbol,
)


class DownloadClient:
    """
    数据下载客户端
    
    提供数据下载和更新功能，包括：
    1. 历史数据下载
    2. 增量数据更新
    3. 下载任务管理
    4. 进度跟踪
    """
    
    def __init__(self, config: Optional[Config] = None):
        """
        初始化下载客户端
        
        Args:
            config: 配置对象，如果为None使用默认配置
        """
        if config is None:
            from config import load_config
            config = load_config()
        
        self.config = config
        self.download_mgr = DownloadManager(config)
        self.metadata_mgr = MetadataManager(config)
    
    def download(
        self,
        exchange: str,
        symbol: str,
        start_time: datetime,
        end_time: Optional[datetime] = None,
        interval: str = DEFAULT_DOWNLOAD_INTERVAL,
        force: bool = False,
        progress_callback: Optional[Callable[[float, int, int], None]] = None,
        interrupt_handler: Optional[Callable[[], None]] = None
    ) -> dict:
        """
        下载数据

        Args:
            exchange: 交易所
            symbol: 交易对
            start_time: 开始时间
            end_time: 结束时间
            interval: 时间周期
            force: 是否强制重新下载（删除指定时间范围的现有数据）
            progress_callback: 进度回调函数(percentage, downloaded_records, total_records)
            interrupt_handler: 中断时调用的处理函数

        Returns:
            dict: 下载结果摘要
        """
        validate_timeframe(interval)
        validate_exchange(exchange)
        validate_symbol(symbol)

        task_id = self.download_mgr.download(
            exchange,
            symbol,
            start_time,
            end_time,
            interval,
            progress_callback,
            interrupt_handler,
            force,
        )

        metadata = self.metadata_mgr.get_symbol_metadata(exchange, symbol)

        result = {
            "task_id": task_id,
            "count": metadata.statistics.total_records if metadata.statistics else 0,
            "start": metadata.data_range.start_date if metadata.data_range else None,
            "end": metadata.data_range.end_date if metadata.data_range else None,
        }
        return result
    
    def get_earliest_available_time(
        self,
        exchange: str,
        symbol: str,
        interval: str = DEFAULT_DOWNLOAD_INTERVAL
    ) -> Optional[datetime]:
        """
        获取交易所支持的最早可用数据时间

        Args:
            exchange: 交易所
            symbol: 交易对
            interval: 时间周期

        Returns:
            Optional[datetime]: 最早可用时间，如果获取失败返回None
        """
        from storage.downloader import DataDownloader

        validate_timeframe(interval)
        validate_exchange(exchange)
        validate_symbol(symbol)

        downloader = DataDownloader(exchange, symbol, self.config, interval)
        earliest_timestamp = downloader.get_earliest_timestamp()

        if earliest_timestamp:
            return datetime.fromtimestamp(earliest_timestamp / 1000)

        return None
    
    def update(
        self,
        exchange: str,
        symbol: str
    ) -> Optional[dict]:
        """
        更新数据到最新

        Args:
            exchange: 交易所
            symbol: 交易对

        Returns:
            Optional[dict]: 更新结果摘要
        """
        validate_exchange(exchange)
        validate_symbol(symbol)

        task_id = self.download_mgr.update(exchange, symbol)
        if task_id is None:
            return None

        metadata = self.metadata_mgr.get_symbol_metadata(exchange, symbol)
        return {
            "task_id": task_id,
            "updated": True,
            "count": metadata.statistics.total_records if metadata.statistics else 0,
            "latest": metadata.data_range.end_date if metadata.data_range else None,
        }
    
    def get_task_status(self, task_id: str) -> Optional[dict]:
        """
        获取下载任务状态
        
        Args:
            task_id: 任务ID
            
        Returns:
            Optional[dict]: 任务状态
        """
        task = self.download_mgr.get_task_status(task_id)
        
        if task:
            return {
                'task_id': task.task_id,
                'status': task.status,
                'progress': task.progress.percentage if task.progress else 0,
                'downloaded_records': (
                    task.progress.downloaded_records if task.progress else 0
                ),
                'errors': task.errors,
            }
        
        return None
