"""Parquet文件读取器"""

from pathlib import Path
from typing import Optional, List
from datetime import datetime
import pandas as pd
import pyarrow.parquet as pq

from ..config import Config
from .cache import DataCache
from ..utils.timezone import now_utc, to_utc

from rich.console import Console
console = Console()



class ParquetReader:
    """
    Parquet文件读取器
    负责高效读取Parquet文件，支持缓存和查询优化
    """
    
    def __init__(self, config: Config):
        """
        初始化读取器
        
        Args:
            config: 配置对象
        """
        self.config = config
        self.root_path = config.storage.get_root_path()
        
        # 初始化缓存
        if config.memory.cache.enabled:
            self.cache = DataCache(
                config.memory.cache.max_size_mb,
                config.memory.cache.ttl_seconds
            )
        else:
            self.cache = None
    
    def read_range(
        self,
        exchange: str,
        symbol: str,
        start_time: datetime,
        end_time: datetime,
        interval: str = '1s',
        columns: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        读取时间范围内的数据
        
        Args:
            exchange: 交易所
            symbol: 交易对
            start_time: 开始时间（会转换为UTC）
            end_time: 结束时间（会转换为UTC）
            interval: 时间周期
            columns: 指定列（None表示所有列）
            
        Returns:
            pd.DataFrame: 数据（timestamp为UTC时区）
        """
        # 确保时间为UTC
        start_time = to_utc(start_time)
        end_time = to_utc(end_time)
        # 生成缓存键
        cache_key = self._generate_cache_key(
            exchange, symbol, start_time, end_time, interval
        )
        
        # 尝试从缓存获取
        if self.cache:
            cached_data = self.cache.get(cache_key)
            if cached_data is not None:
                if columns:
                    return cached_data[columns]
                return cached_data
        
        # 缓存未命中，从文件读取
        files = self._get_partition_files(
            exchange, symbol, start_time, end_time, interval
        )
        
        if not files:
            return pd.DataFrame()
        
        # 读取所有相关文件
        dfs = []
        for file_path in files:
            df = self._read_parquet_file(
                file_path,
                start_time,
                end_time,
                columns
            )
            if not df.empty:
                dfs.append(df)
        
        # 合并数据
        if not dfs:
            return pd.DataFrame()
        
        result = pd.concat(dfs, ignore_index=True)
        
        # 精确过滤时间范围
        result = result[
            (result['timestamp'] >= start_time) &
            (result['timestamp'] <= end_time)
        ]
        
        # 排序
        result = result.sort_values('timestamp').reset_index(drop=True)
        
        # 存入缓存
        if self.cache and not result.empty:
            self.cache.put(cache_key, result)
        
        return result
    
    def read_file(
        self,
        file_path: Path,
        columns: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        读取单个Parquet文件
        
        Args:
            file_path: 文件路径
            columns: 指定列
            
        Returns:
            pd.DataFrame: 数据
        """
        if not file_path.exists():
            return pd.DataFrame()
        
        try:
            df = pq.read_table(
                file_path,
                columns=columns
            ).to_pandas()
            
            # 确保timestamp是datetime类型且为UTC
            if 'timestamp' in df.columns:
                if not pd.api.types.is_datetime64_any_dtype(df['timestamp']):
                    df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
                elif df['timestamp'].dt.tz is None:
                    df['timestamp'] = df['timestamp'].dt.tz_localize('UTC')
            
            df = self._drop_monthly_summary_row(df, self._infer_interval_from_path(file_path))
            return df
        except Exception as e:
            console.print(f"Error reading {file_path}: {e}")
            return pd.DataFrame()
    
    def _read_parquet_file(
        self,
        file_path: Path,
        start_time: datetime,
        end_time: datetime,
        columns: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        读取单个Parquet文件并过滤时间范围
        
        Args:
            file_path: 文件路径
            start_time: 开始时间
            end_time: 结束时间
            columns: 指定列
            
        Returns:
            pd.DataFrame: 数据
        """
        if not file_path.exists():
            return pd.DataFrame()
        
        try:
            # 使用PyArrow的过滤器优化读取
            # 注意: PyArrow的过滤器对timestamp类型的支持有限
            # 这里先读取全部数据，然后在pandas中过滤
            df = pq.read_table(
                file_path,
                columns=columns
            ).to_pandas()
            
            # 确保timestamp是datetime类型且为UTC
            if 'timestamp' in df.columns:
                if not pd.api.types.is_datetime64_any_dtype(df['timestamp']):
                    df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
                elif df['timestamp'].dt.tz is None:
                    df['timestamp'] = df['timestamp'].dt.tz_localize('UTC')
                
                # 过滤时间范围
                df = df[
                    (df['timestamp'] >= start_time) &
                    (df['timestamp'] <= end_time)
                ]
            
            df = self._drop_monthly_summary_row(df, self._infer_interval_from_path(file_path))
            return df
        except Exception as e:
            console.print(f"Error reading {file_path}: {e}")
            return pd.DataFrame()
    
    def _get_partition_files(
        self,
        exchange: str,
        symbol: str,
        start_time: datetime,
        end_time: datetime,
        interval: str
    ) -> List[Path]:
        """
        获取需要读取的分区文件列表
        
        新的统一结构: raw/exchange/symbol/interval/year/month/data.parquet
        
        Args:
            exchange: 交易所
            symbol: 交易对
            start_time: 开始时间
            end_time: 结束时间
            interval: 时间周期
            
        Returns:
            List[Path]: 文件路径列表
        """
        symbol_id = symbol.replace('/', '')
        
        # 统一路径结构：所有周期数据都在 raw 目录下，按周期分子目录
        base_path = self.root_path / 'raw' / exchange / symbol_id / interval
        
        if not base_path.exists():
            return []
        
        files = []
        
        # 遍历年份
        # 将时间归一到每月第一天零点，避免因为时分秒导致跨月判断错误
        current_date = start_time.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end_date = end_time.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        while current_date <= end_date:
            year_dir = base_path / str(current_date.year)
            
            if year_dir.exists():
                month_dir = year_dir / f"{current_date.month:02d}"
                file_path = month_dir / 'data.parquet'
                
                if file_path.exists():
                    files.append(file_path)
            
            # 移到下一个月
            if current_date.month == 12:
                current_date = current_date.replace(
                    year=current_date.year + 1,
                    month=1
                )
            else:
                current_date = current_date.replace(
                    month=current_date.month + 1
                )
        
        return files
    
    def _infer_interval_from_path(self, file_path: Path) -> Optional[str]:
        """从路径中尝试解析周期，例如 .../symbol/1m/2023/01/data.parquet"""
        parts = file_path.parts
        try:
            raw_idx = parts.index('raw')
            # 结构: .../raw/exchange/symbol/interval/...
            return parts[raw_idx + 3]
        except (ValueError, IndexError):
            return None

    def _drop_monthly_summary_row(self, df: pd.DataFrame, interval: Optional[str]) -> pd.DataFrame:
        """
        过滤掉首行的月度汇总/统计行（仅对1m启用）
        """
        if df is None or df.empty or interval != '1m':
            return df

        required_cols = {'timestamp', 'volume', 'close'}
        if not required_cols.issubset(df.columns):
            return df
        if len(df) < 6:
            return df

        # 保证时间列规范，便于排序和比较
        if not pd.api.types.is_datetime64_any_dtype(df['timestamp']):
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
        elif df['timestamp'].dt.tz is None:
            df['timestamp'] = df['timestamp'].dt.tz_localize('UTC')

        sorted_df = df.sort_values('timestamp').reset_index(drop=True)
        head = sorted_df.head(6)
        vol_avg = head['volume'].iloc[1:6].mean(skipna=True)
        close_avg = head['close'].iloc[1:6].mean(skipna=True)

        if pd.isna(vol_avg) or pd.isna(close_avg):
            return sorted_df

        first = head.iloc[0]
        volume_anomaly = first['volume'] > vol_avg * 100
        price_anomaly = False
        if close_avg != 0:
            price_anomaly = abs(first['close'] - close_avg) / abs(close_avg) > 0.1

        if volume_anomaly or price_anomaly:
            return sorted_df.iloc[1:].reset_index(drop=True)

        return sorted_df
    
    def _generate_cache_key(
        self,
        exchange: str,
        symbol: str,
        start_time: datetime,
        end_time: datetime,
        interval: str
    ) -> str:
        """
        生成缓存键
        
        Args:
            exchange: 交易所
            symbol: 交易对
            start_time: 开始时间
            end_time: 结束时间
            interval: 时间周期
            
        Returns:
            str: 缓存键
        """
        return f"{exchange}:{symbol}:{interval}:{start_time.isoformat()}:{end_time.isoformat()}"
    
    def preload(
        self,
        exchange: str,
        symbol: str,
        interval: str = '1s',
        days: int = 7
    ) -> None:
        """
        预加载最近的数据到缓存
        
        Args:
            exchange: 交易所
            symbol: 交易对
            interval: 时间周期
            days: 预加载天数
        """
        if not self.cache:
            return
        
        end_time = now_utc()
        start_time = end_time - pd.Timedelta(days=days)
        
        # 读取数据（会自动缓存）
        self.read_range(exchange, symbol, start_time, end_time, interval)
    
    def clear_cache(self) -> None:
        """清空缓存"""
        if self.cache:
            self.cache.clear()
    
    def get_cache_stats(self) -> Optional[dict]:
        """
        获取缓存统计信息
        
        Returns:
            Optional[dict]: 统计信息
        """
        if self.cache:
            return self.cache.get_stats()
        return None
    
    def read_latest(
        self,
        exchange: str,
        symbol: str,
        interval: str = '1s',
        limit: int = 1000
    ) -> pd.DataFrame:
        """
        读取最新的N条数据
        
        Args:
            exchange: 交易所
            symbol: 交易对
            interval: 时间周期
            limit: 数量限制
            
        Returns:
            pd.DataFrame: 数据
        """
        # 从当前UTC时间往前读取
        end_time = now_utc()
        start_time = end_time - pd.Timedelta(days=30)  # 往前30天
        
        df = self.read_range(exchange, symbol, start_time, end_time, interval)
        
        if df.empty:
            return df
        
        # 返回最后N条
        return df.tail(limit).reset_index(drop=True)
    
    def read_by_date(
        self,
        exchange: str,
        symbol: str,
        date: datetime,
        interval: str = '1s'
    ) -> pd.DataFrame:
        """
        读取指定日期的数据
        
        Args:
            exchange: 交易所
            symbol: 交易对
            date: 日期
            interval: 时间周期
            
        Returns:
            pd.DataFrame: 数据
        """
        start_time = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_time = start_time + pd.Timedelta(days=1) - pd.Timedelta(microseconds=1)
        
        return self.read_range(exchange, symbol, start_time, end_time, interval)
    
    def get_available_dates(
        self,
        exchange: str,
        symbol: str,
        interval: str = '1s'
    ) -> List[datetime]:
        """
        获取可用的数据日期列表
        
        新的统一结构: raw/exchange/symbol/interval/year/month/data.parquet
        
        Args:
            exchange: 交易所
            symbol: 交易对
            interval: 时间周期
            
        Returns:
            List[datetime]: 日期列表
        """
        symbol_id = symbol.replace('/', '')
        
        # 统一路径结构：所有周期数据都在 raw 目录下，按周期分子目录
        base_path = self.root_path / 'raw' / exchange / symbol_id / interval
        
        if not base_path.exists():
            return []
        
        dates = []
        
        # 遍历年份目录
        for year_dir in sorted(base_path.iterdir()):
            if not year_dir.is_dir():
                continue
            
            try:
                year = int(year_dir.name)
            except ValueError:
                continue
            
            # 遍历月份目录
            for month_dir in sorted(year_dir.iterdir()):
                if not month_dir.is_dir():
                    continue
                
                try:
                    month = int(month_dir.name)
                except ValueError:
                    continue
                
                # 检查是否有数据文件
                data_file = month_dir / 'data.parquet'
                if data_file.exists():
                    dates.append(datetime(year, month, 1))
        
        return dates
