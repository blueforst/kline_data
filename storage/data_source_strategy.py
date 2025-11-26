"""数据源选择策略"""

from typing import Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass

from config import Config
from .metadata_manager import MetadataManager
from utils.timezone import timestamp_to_datetime, to_utc
from rich.console import Console

console = Console()


@dataclass
class DataSourceDecision:
    """数据源决策结果"""
    source: str  # 'local', 'ccxt', 'resample', 'hybrid'
    source_interval: Optional[str]  # 如果需要重采样，源数据周期
    need_download: bool  # 是否需要下载
    download_interval: Optional[str]  # 下载时使用的周期
    reason: str  # 决策理由


class DataSourceStrategy:
    """
    数据源选择策略
    智能决策数据应该从哪里获取
    """
    
    # 交易所支持的原生周期（大多数交易所支持）
    COMMON_NATIVE_TIMEFRAMES = [
        '1m', '3m', '5m', '15m', '30m',
        '1h', '2h', '4h', '6h', '8h', '12h',
        '1d', '3d', '1w', '1M'
    ]
    
    # 重采样阈值：如果需要的数据量小于此值，使用重采样；否则直接下载
    RESAMPLE_THRESHOLD_RECORDS = 10000  # 1万条记录
    
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
        决定数据源（优先级：本地完整数据 > 交易所下载 > 本地重采样）
        
        Args:
            exchange: 交易所
            symbol: 交易对
            start_time: 开始时间
            end_time: 结束时间
            target_interval: 目标周期
            
        Returns:
            DataSourceDecision: 数据源决策
        """
        # 1. 检查本地是否有目标周期的完整数据（最高优先级）
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
        
        # 2. 优先从交易所获取（比本地重采样更高效）
        # 2.1 检查交易所是否原生支持目标周期
        if self._is_native_timeframe(target_interval):
            return DataSourceDecision(
                source='ccxt',
                source_interval=None,
                need_download=True,
                download_interval=target_interval,
                reason=f'Download {target_interval} directly from exchange '
                       f'(native support, more efficient than resampling)'
            )
        
        # 2.2 找到交易所支持的、可以重采样的最大周期
        best_source = self._find_best_download_interval(target_interval)
        
        if best_source:
            return DataSourceDecision(
                source='hybrid',
                source_interval=best_source,
                need_download=True,
                download_interval=best_source,
                reason=f'Download {best_source} from exchange and resample to {target_interval} '
                       f'(more efficient than local resample)'
            )
        
        # 3. 回退：检查本地是否可以重采样（仅当交易所无法获取时）
        can_resample, source_interval = self._check_resample_possibility(
            exchange, symbol, start_time, end_time, target_interval
        )
        
        if can_resample:
            # 计算重采样的数据量和效率
            estimated_records = self._estimate_records(
                start_time, end_time, source_interval
            )
            
            # 只有在数据量适中时才使用本地重采样
            if estimated_records < self.RESAMPLE_THRESHOLD_RECORDS:
                return DataSourceDecision(
                    source='resample',
                    source_interval=source_interval,
                    need_download=False,
                    download_interval=None,
                    reason=f'Fallback: Resample from local {source_interval} data '
                           f'({estimated_records} records, exchange unavailable)'
                )
        
        # 4. 最后的选择：下载1s数据后重采样（通常不会到这一步）
        return DataSourceDecision(
            source='hybrid',
            source_interval='1s',
            need_download=True,
            download_interval='1s',
            reason=f'Last resort: Download 1s data and resample to {target_interval} '
                   f'(no better option available)'
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
    
    def _check_resample_possibility(
        self,
        exchange: str,
        symbol: str,
        start_time: datetime,
        end_time: datetime,
        target_interval: str
    ) -> Tuple[bool, Optional[str]]:
        """
        检查是否可以从本地数据重采样
        
        Args:
            exchange: 交易所
            symbol: 交易对
            start_time: 开始时间
            end_time: 结束时间
            target_interval: 目标周期
            
        Returns:
            Tuple[bool, Optional[str]]: (是否可以, 源周期)
        """
        from resampler.timeframe import (
            can_resample,
            get_timeframe_seconds,
            TIMEFRAME_SECONDS
        )
        
        try:
            metadata = self.metadata_mgr.get_symbol_metadata(exchange, symbol)
            
            if not metadata or not metadata.intervals:
                return False, None
            
            target_seconds = get_timeframe_seconds(target_interval)
            
            # 找到所有可以重采样的源周期（从大到小）
            candidates = []
            
            for interval, interval_data in metadata.intervals.items():
                try:
                    interval_seconds = get_timeframe_seconds(interval)
                    
                    # 必须小于目标周期，且可以重采样
                    if (interval_seconds < target_seconds and 
                        can_resample(interval, target_interval)):
                        
                        # 检查时间范围（UTC）
                        data_start = timestamp_to_datetime(
                            interval_data.start_timestamp
                        )
                        data_end = timestamp_to_datetime(
                            interval_data.end_timestamp
                        )
                        
                        # 确保所有时间都是UTC aware
                        start_time_utc = to_utc(start_time)
                        end_time_utc = to_utc(end_time)
                        
                        if data_start <= start_time_utc and data_end >= end_time_utc:
                            candidates.append((interval, interval_seconds))
                
                except:
                    continue
            
            # 选择最大的可用周期（减少数据量）
            if candidates:
                best_interval = max(candidates, key=lambda x: x[1])[0]
                return True, best_interval
            
            return False, None
            
        except Exception as e:
            console.print(f"Error checking resample possibility: {e}")
            return False, None
    
    def _is_native_timeframe(self, interval: str) -> bool:
        """
        检查是否为交易所原生支持的周期
        
        Args:
            interval: 周期
            
        Returns:
            bool: 是否原生支持
        """
        return interval in self.COMMON_NATIVE_TIMEFRAMES
    
    def _find_best_download_interval(
        self,
        target_interval: str
    ) -> Optional[str]:
        """
        找到最适合下载的周期
        
        Args:
            target_interval: 目标周期
            
        Returns:
            Optional[str]: 最佳下载周期
        """
        from resampler.timeframe import (
            can_resample,
            get_timeframe_seconds,
        )
        
        target_seconds = get_timeframe_seconds(target_interval)
        
        # 在原生支持的周期中找到最接近的、小于目标的周期
        candidates = []
        
        for interval in self.COMMON_NATIVE_TIMEFRAMES:
            try:
                interval_seconds = get_timeframe_seconds(interval)
                
                if (interval_seconds < target_seconds and
                    can_resample(interval, target_interval)):
                    candidates.append((interval, interval_seconds))
            except:
                continue
        
        # 返回最大的候选周期
        if candidates:
            return max(candidates, key=lambda x: x[1])[0]
        
        return None
    
    def _estimate_records(
        self,
        start_time: datetime,
        end_time: datetime,
        interval: str
    ) -> int:
        """
        估算记录数量
        
        Args:
            start_time: 开始时间
            end_time: 结束时间
            interval: 周期
            
        Returns:
            int: 估算的记录数
        """
        from resampler.timeframe import get_timeframe_seconds

        
        duration_seconds = (end_time - start_time).total_seconds()
        interval_seconds = get_timeframe_seconds(interval)
        
        return int(duration_seconds / interval_seconds)
    
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
