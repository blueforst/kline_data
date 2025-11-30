"""数据获取器"""

from typing import Optional
from datetime import datetime
import pandas as pd

from ..config import Config
from .data_source_strategy import DataSourceStrategy, DataSourceDecision
from .downloader import DownloadManager
from ..reader import ParquetReader
from rich.console import Console

console = Console()


class DataFetcher:
    """
    数据获取器
    根据策略自动选择最优的数据获取方式（直接从交易所下载，不使用重采样）
    """
    
    def __init__(self, config: Config):
        """
        初始化数据获取器
        
        Args:
            config: 配置对象
        """
        self.config = config
        self.strategy = DataSourceStrategy(config)
        self.download_mgr = DownloadManager(config)
        self.reader = ParquetReader(config)
    
    def fetch(
        self,
        exchange: str,
        symbol: str,
        start_time: datetime,
        end_time: datetime,
        interval: str,
        force_strategy: Optional[str] = None,
        verbose: bool = True
    ) -> pd.DataFrame:
        """
        获取数据
        
        Args:
            exchange: 交易所
            symbol: 交易对
            start_time: 开始时间
            end_time: 结束时间
            interval: 目标周期
            force_strategy: 强制使用特定策略 ('local', 'ccxt')
            verbose: 是否打印决策信息
            
        Returns:
            pd.DataFrame: K线数据
        """
        # 决策数据源
        decision = self.strategy.decide_data_source(
            exchange, symbol, start_time, end_time, interval
        )
        
        if verbose:
            console.print(self.strategy.explain_decision(decision))
        
        # 强制策略
        if force_strategy:
            decision = self._override_decision(
                decision, force_strategy, exchange, symbol,
                start_time, end_time, interval
            )
            if verbose:
                console.print(f"\n[Overridden] Using forced strategy: {force_strategy}")
        
        # 根据决策执行
        return self._execute_decision(
            decision, exchange, symbol, start_time, end_time, interval
        )
    
    def _override_decision(
        self,
        decision: DataSourceDecision,
        force_strategy: str,
        exchange: str,
        symbol: str,
        start_time: datetime,
        end_time: datetime,
        interval: str
    ) -> DataSourceDecision:
        """
        覆盖决策
        
        Args:
            decision: 原决策
            force_strategy: 强制策略
            exchange: 交易所
            symbol: 交易对
            start_time: 开始时间
            end_time: 结束时间
            interval: 周期
            
        Returns:
            DataSourceDecision: 新决策
        """
        if force_strategy == 'local':
            return DataSourceDecision(
                source='local',
                source_interval=None,
                need_download=False,
                download_interval=None,
                reason='Forced to use local data'
            )
        elif force_strategy == 'ccxt':
            return DataSourceDecision(
                source='ccxt',
                source_interval=None,
                need_download=True,
                download_interval=interval,
                reason='Forced to download from exchange'
            )
        else:
            return decision
    
    def _execute_decision(
        self,
        decision: DataSourceDecision,
        exchange: str,
        symbol: str,
        start_time: datetime,
        end_time: datetime,
        interval: str
    ) -> pd.DataFrame:
        """
        执行决策
        
        Args:
            decision: 决策结果
            exchange: 交易所
            symbol: 交易对
            start_time: 开始时间
            end_time: 结束时间
            interval: 周期
            
        Returns:
            pd.DataFrame: 数据
        """
        if decision.source == 'local':
            # 直接从本地读取
            return self.reader.read_range(
                exchange, symbol, start_time, end_time, interval
            )
        
        elif decision.source == 'ccxt':
            # 从交易所下载目标周期数据（download方法是同步的，会阻塞直到完成）
            console.print(f"Downloading {interval} data from {exchange}...")
            task_id = self.download_mgr.download(
                exchange, symbol, start_time, end_time, interval
            )
            
            # download方法已经同步完成，直接读取数据
            return self.reader.read_range(
                exchange, symbol, start_time, end_time, interval
            )
        
        else:
            raise ValueError(f"Unknown source: {decision.source}")
    
    def explain_strategy(
        self,
        exchange: str,
        symbol: str,
        start_time: datetime,
        end_time: datetime,
        interval: str
    ) -> str:
        """
        解释策略（不实际获取数据）
        
        Args:
            exchange: 交易所
            symbol: 交易对
            start_time: 开始时间
            end_time: 结束时间
            interval: 周期
            
        Returns:
            str: 策略说明
        """
        decision = self.strategy.decide_data_source(
            exchange, symbol, start_time, end_time, interval
        )
        return self.strategy.explain_decision(decision)
