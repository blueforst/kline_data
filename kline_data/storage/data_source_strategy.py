"""数据源选择策略"""

from typing import Optional, Tuple
from datetime import datetime
from dataclasses import dataclass

from ..config import Config
from .metadata_manager import MetadataManager
from ..utils.timezone import timestamp_to_datetime, to_utc
from rich.console import Console

console = Console()


@dataclass
class DataSourceDecision:
    """数据源决策结果"""
    source: str  # 'local' 或 'ccxt'
    source_interval: Optional[str]  # 兼容字段，始终为None（保留供未来扩展）
    need_download: bool  # 是否需要下载
    download_interval: Optional[str]  # 下载时使用的周期
    reason: str  # 决策理由


class DataSourceStrategy:
    """
    数据源选择策略
    智能决策数据应该从哪里获取
    """
    
    def __init__(self, config: Config):
        """
        初始化策略
        
        Args:
            config: 配置对象
        """
        self.config = config
        self.metadata_mgr = MetadataManager(config)
    
    def decide_data_source(
        self,
        exchange: str,
        symbol: str,
        start_time: datetime,
        end_time: datetime,
        target_interval: str
    ) -> DataSourceDecision:
        """
        决定数据源（优先级：本地完整数据 > 交易所下载）
        
        所有周期的数据直接从CCXT下载，不再使用重采样。
        
        Args:
            exchange: 交易所
            symbol: 交易对
            start_time: 开始时间
            end_time: 结束时间
            target_interval: 目标周期
            
        Returns:
            DataSourceDecision: 数据源决策
        """
        # 1. 检查本地是否有目标周期的完整数据
        local_complete = self._check_local_data(
            exchange, symbol, start_time, end_time, target_interval
        )
        
        if local_complete:
            return DataSourceDecision(
                source='local',
                source_interval=None,
                need_download=False,
                download_interval=None,
                reason=f'Local has complete {target_interval} data'
            )
        
        # 2. 直接从交易所下载目标周期数据
        return DataSourceDecision(
            source='ccxt',
            source_interval=None,
            need_download=True,
            download_interval=target_interval,
            reason=f'Download {target_interval} directly from exchange'
        )
    
    def _check_local_data(
        self,
        exchange: str,
        symbol: str,
        start_time: datetime,
        end_time: datetime,
        interval: str
    ) -> bool:
        """
        检查本地是否有完整数据
        
        Args:
            exchange: 交易所
            symbol: 交易对
            start_time: 开始时间
            end_time: 结束时间
            interval: 周期
            
        Returns:
            bool: 是否有完整数据
        """
        try:
            metadata = self.metadata_mgr.get_symbol_metadata(exchange, symbol)
            
            if not metadata:
                return False
            
            # 检查是否有该周期的数据
            interval_data = metadata.intervals.get(interval)
            if not interval_data:
                return False
            
            # 检查时间范围（UTC）
            data_start = timestamp_to_datetime(interval_data.start_timestamp)
            data_end = timestamp_to_datetime(interval_data.end_timestamp)
            
            # 确保所有时间都是UTC aware
            start_time_utc = to_utc(start_time)
            end_time_utc = to_utc(end_time)
            
            if data_start <= start_time_utc and data_end >= end_time_utc:
                # 检查数据完整性
                if interval_data.completeness >= 0.95:  # 95%以上完整
                    return True
            
            return False
            
        except Exception as e:
            console.print(f"Error checking local data: {e}")
            return False
    
    def explain_decision(
        self,
        decision: DataSourceDecision
    ) -> str:
        """
        解释决策
        
        Args:
            decision: 决策结果
            
        Returns:
            str: 决策说明
        """
        lines = [
            "=== Data Source Decision ===",
            f"Source: {decision.source}",
            f"Reason: {decision.reason}",
        ]
        
        if decision.source_interval:
            lines.append(f"Source Interval: {decision.source_interval}")
        
        if decision.need_download:
            lines.append(f"Need Download: Yes ({decision.download_interval})")
        else:
            lines.append("Need Download: No (use local data)")
        
        lines.append("=" * 30)
        
        return "\n".join(lines)
