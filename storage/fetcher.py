"""数据获取器"""

from typing import Optional
from datetime import datetime
import pandas as pd

from config import Config
from .data_source_strategy import DataSourceStrategy, DataSourceDecision
from .downloader import DownloadManager
from reader import ParquetReader
from resampler import KlineResampler
from rich.console import Console

console = Console()


class DataFetcher:
    """
    数据获取器
    根据策略自动选择最优的数据获取方式
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
        self.resampler = KlineResampler(config)
    
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
            force_strategy: 强制使用特定策略 ('local', 'ccxt', 'resample')
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
        elif force_strategy == 'resample':
            # 尝试找到可用的源数据
            can_resample, source_interval = self.strategy._check_resample_possibility(
                exchange, symbol, start_time, end_time, interval
            )
            if can_resample:
                return DataSourceDecision(
                    source='resample',
                    source_interval=source_interval,
                    need_download=False,
                    download_interval=None,
                    reason='Forced to resample from local data'
                )
            else:
                console.print(f"Warning: Cannot resample, falling back to original strategy")
                return decision
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
            # 从交易所下载
            console.print(f"Downloading {interval} data from {exchange}...")
            task_id = self.download_mgr.download(
                exchange, symbol, start_time, end_time, interval
            )
            
            # 等待下载完成（简化版，实际应该有进度监控）
            import time
            while True:
                task = self.download_mgr.get_task_status(task_id)
                if task and task.status in ['COMPLETED', 'FAILED']:
                    break
                time.sleep(1)
            
            # 读取数据
            return self.reader.read_range(
                exchange, symbol, start_time, end_time, interval
            )
        
        elif decision.source == 'resample':
            # 从本地源数据重采样
            console.print(f"Resampling from {decision.source_interval} to {interval}...")
            return self.resampler.resample_range(
                exchange, symbol, start_time, end_time,
                decision.source_interval, interval,
                save=True
            )
        
        elif decision.source == 'hybrid':
            # 先下载，再重采样
            console.print(f"Downloading {decision.download_interval} data from {exchange}...")
            task_id = self.download_mgr.download(
                exchange, symbol, start_time, end_time,
                decision.download_interval
            )
            
            # 等待下载完成
            import time
            while True:
                task = self.download_mgr.get_task_status(task_id)
                if task and task.status in ['COMPLETED', 'FAILED']:
                    break
                time.sleep(1)
            
            # 如果下载的就是目标周期，直接返回
            if decision.download_interval == interval:
                return self.reader.read_range(
                    exchange, symbol, start_time, end_time, interval
                )
            
            # 否则进行重采样
            console.print(f"Resampling from {decision.download_interval} to {interval}...")
            return self.resampler.resample_range(
                exchange, symbol, start_time, end_time,
                decision.download_interval, interval,
                save=True
            )
        
        else:
            raise ValueError(f"Unknown source: {decision.source}")
    
    def fetch_with_fallback(
        self,
        exchange: str,
        symbol: str,
        start_time: datetime,
        end_time: datetime,
        interval: str,
        fallback_intervals: Optional[list] = None
    ) -> pd.DataFrame:
        """
        带降级策略的获取
        如果目标周期无法获取，尝试降级到其他周期
        
        Args:
            exchange: 交易所
            symbol: 交易对
            start_time: 开始时间
            end_time: 结束时间
            interval: 目标周期
            fallback_intervals: 降级周期列表
            
        Returns:
            pd.DataFrame: 数据
        """
        # 首先尝试目标周期
        try:
            df = self.fetch(
                exchange, symbol, start_time, end_time, interval,
                verbose=False
            )
            if not df.empty:
                return df
        except Exception as e:
            console.print(f"Failed to fetch {interval} data: {e}")
        
        # 尝试降级周期
        if fallback_intervals:
            for fallback_interval in fallback_intervals:
                try:
                    console.print(f"Trying fallback interval: {fallback_interval}")
                    df = self.fetch(
                        exchange, symbol, start_time, end_time,
                        fallback_interval, verbose=False
                    )
                    if not df.empty:
                        # 如果降级周期更小，重采样到目标周期
                        from resampler.timeframe import get_timeframe_seconds

                        if (get_timeframe_seconds(fallback_interval) <
                            get_timeframe_seconds(interval)):
                            return self.resampler.resample(
                                df, fallback_interval, interval
                            )
                        return df
                except Exception as e:
                    console.print(f"Failed to fetch {fallback_interval} data: {e}")
                    continue
        
        # 全部失败，返回空DataFrame
        console.print(f"All fetch attempts failed")
        return pd.DataFrame()
    
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
