"""Parquet文件写入器"""

import hashlib
from pathlib import Path
from typing import Optional, List
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from datetime import datetime

from ..config import Config
from .models import PartitionInfo
from ..utils.timezone import now_utc, format_datetime


class ParquetWriter:
    """
    Parquet文件写入器
    负责将K线数据写入Parquet文件
    """
    
    # Parquet Schema定义
    KLINE_SCHEMA = pa.schema([
        ('timestamp', pa.timestamp('ms')),
        ('open', pa.float64()),
        ('high', pa.float64()),
        ('low', pa.float64()),
        ('close', pa.float64()),
        ('volume', pa.float64()),
    ])
    
    def __init__(self, config: Config):
        """
        初始化写入器
        
        Args:
            config: 配置对象
        """
        self.config = config
        self.compression = config.storage.compression
        self.root_path = config.storage.get_root_path()
        
    def write(
        self,
        df: pd.DataFrame,
        file_path: Path,
        interval: str = '1s'
    ) -> PartitionInfo:
        """
        写入Parquet文件
        
        Args:
            df: 数据DataFrame
            file_path: 文件路径
            interval: 时间周期
            
        Returns:
            PartitionInfo: 分区信息
        """
        df = self._filter_summary_rows(df, interval)

        # 确保目录存在
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 转换为Arrow Table
        table = pa.Table.from_pandas(df, schema=self.KLINE_SCHEMA)
        
        # 写入文件
        pq.write_table(
            table,
            file_path,
            compression=self.compression,
            row_group_size=100000,
            use_dictionary=True,
            write_statistics=True,
            version='2.6',
        )
        
        # 计算校验和
        checksum = self._calculate_checksum(file_path)
        
        # 获取文件信息
        file_stat = file_path.stat()
        now = format_datetime(now_utc())
        
        # 从路径提取年月
        year, month = self._extract_year_month(file_path)
        
        return PartitionInfo(
            year=year,
            month=month,
            file_path=str(file_path.relative_to(self.root_path)),
            records=len(df),
            size_bytes=file_stat.st_size,
            checksum=checksum,
            created_at=now,
            updated_at=now,
            interval=interval,
        )
    
    def append(
        self,
        df: pd.DataFrame,
        file_path: Path,
        interval: str = '1s'
    ) -> PartitionInfo:
        """
        追加数据到已有文件
        
        Args:
            df: 新数据DataFrame
            file_path: 文件路径
            interval: 时间周期
            
        Returns:
            PartitionInfo: 更新后的分区信息
        """
        if file_path.exists():
            # 读取现有数据
            existing_table = pq.read_table(file_path)
            existing_df = existing_table.to_pandas()
            
            # 确保现有数据的时区为 UTC
            if existing_df['timestamp'].dt.tz is None:
                existing_df['timestamp'] = existing_df['timestamp'].dt.tz_localize('UTC')
            
            # 确保新数据的时区为 UTC
            if not pd.api.types.is_datetime64_any_dtype(df['timestamp']):
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
            elif df['timestamp'].dt.tz is None:
                df['timestamp'] = df['timestamp'].dt.tz_localize('UTC')
            
            # 合并数据
            combined_df = pd.concat([existing_df, df], ignore_index=True)
            
            # 去重并排序
            combined_df = combined_df.drop_duplicates(subset=['timestamp'], keep='last')
            combined_df = combined_df.sort_values('timestamp').reset_index(drop=True)
            combined_df = self._filter_summary_rows(combined_df, interval)
            
            # 写回文件
            return self.write(combined_df, file_path, interval)
        else:
            # 文件不存在，直接写入
            return self.write(df, file_path, interval)
    
    def write_partitioned(
        self,
        df: pd.DataFrame,
        exchange: str,
        symbol: str,
        interval: str = '1s'
    ) -> List[PartitionInfo]:
        """
        按分区写入数据
        
        Args:
            df: 数据DataFrame
            exchange: 交易所
            symbol: 交易对
            interval: 时间周期
            
        Returns:
            List[PartitionInfo]: 分区信息列表
        """
        partition_infos = []
        
        # 确保timestamp是datetime类型且为UTC
        if not pd.api.types.is_datetime64_any_dtype(df['timestamp']):
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
        elif df['timestamp'].dt.tz is None:
            df['timestamp'] = df['timestamp'].dt.tz_localize('UTC')
        
        # 按UTC时区的年月分组
        df['year'] = df['timestamp'].dt.year
        df['month'] = df['timestamp'].dt.month
        
        for (year, month), group_df in df.groupby(['year', 'month']):
            # 移除分组列
            group_df = group_df.drop(columns=['year', 'month'])
            
            # 构造文件路径
            file_path = self._get_partition_path(
                exchange, symbol, interval, year, month
            )
            
            # 如果文件已存在，使用 append 合并数据；否则直接写入
            if file_path.exists():
                partition_info = self.append(group_df, file_path, interval)
            else:
                partition_info = self.write(group_df, file_path, interval)
            partition_infos.append(partition_info)
        
        return partition_infos
    
    def _get_partition_path(
        self,
        exchange: str,
        symbol: str,
        interval: str,
        year: int,
        month: int
    ) -> Path:
        """
        获取分区文件路径
        
        新的统一结构: raw/exchange/symbol/interval/year/month/data.parquet
        
        Args:
            exchange: 交易所
            symbol: 交易对
            interval: 时间周期
            year: 年份
            month: 月份
            
        Returns:
            Path: 文件路径
        """
        symbol_id = symbol.replace('/', '')
        
        # 统一路径结构：所有周期数据都在 raw 目录下，按周期分子目录
        base_path = self.root_path / 'raw' / exchange / symbol_id / interval
        
        return base_path / str(year) / f"{month:02d}" / 'data.parquet'
    
    def _calculate_checksum(self, file_path: Path) -> str:
        """
        计算文件MD5校验和
        
        Args:
            file_path: 文件路径
            
        Returns:
            str: MD5校验和
        """
        md5_hash = hashlib.md5()
        
        with open(file_path, 'rb') as f:
            # 分块读取以处理大文件
            for chunk in iter(lambda: f.read(4096), b''):
                md5_hash.update(chunk)
        
        return md5_hash.hexdigest()
    
    def _extract_year_month(self, file_path: Path) -> tuple:
        """
        从文件路径提取年月
        
        Args:
            file_path: 文件路径
            
        Returns:
            tuple: (年, 月)
        """
        parts = file_path.parts
        try:
            # 路径格式: .../year/month/data.parquet
            year = int(parts[-3])
            month = int(parts[-2])
            return year, month
        except (ValueError, IndexError):
            # 无法提取，返回当前UTC年月
            now = now_utc()
            return now.year, now.month
    
    def _filter_summary_rows(self, df: pd.DataFrame, interval: str) -> pd.DataFrame:
        """
        移除可能混入的月度汇总行（仅对1m数据启用）
        """
        if df is None or df.empty:
            return df
        if interval != '1m':
            return df
        required_cols = {'timestamp', 'volume', 'close'}
        if not required_cols.issubset(df.columns):
            return df

        # 确保时间为UTC，便于排序和对齐
        if not pd.api.types.is_datetime64_any_dtype(df['timestamp']):
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
        elif df['timestamp'].dt.tz is None:
            df['timestamp'] = df['timestamp'].dt.tz_localize('UTC')

        if len(df) < 6:
            return df

        sorted_df = df.sort_values('timestamp').reset_index(drop=True)
        head = sorted_df.head(6)
        vol_avg = head['volume'].iloc[1:6].mean(skipna=True)
        close_avg = head['close'].iloc[1:6].mean(skipna=True)

        # 均值缺失时跳过过滤
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
    
    def verify_integrity(self, file_path: Path, expected_checksum: str) -> bool:
        """
        验证文件完整性
        
        Args:
            file_path: 文件路径
            expected_checksum: 期望的校验和
            
        Returns:
            bool: 文件是否完整
        """
        if not file_path.exists():
            return False
        
        actual_checksum = self._calculate_checksum(file_path)
        return actual_checksum == expected_checksum
    
    def optimize_file(self, file_path: Path) -> None:
        """
        优化Parquet文件
        重新组织行组以提高查询性能
        
        Args:
            file_path: 文件路径
        """
        if not file_path.exists():
            return
        
        # 读取数据
        df = pq.read_table(file_path).to_pandas()
        
        # 重新写入（自动优化）
        self.write(df, file_path)
    
    def delete_time_range(
        self,
        exchange: str,
        symbol: str,
        start_time: datetime,
        end_time: datetime,
        interval: str = '1s'
    ) -> List[str]:
        """
        删除指定时间范围内的数据
        
        Args:
            exchange: 交易所
            symbol: 交易对
            start_time: 开始时间（UTC）
            end_time: 结束时间（UTC）
            interval: 时间周期
            
        Returns:
            List[str]: 被删除/修改的文件路径列表
        """
        from kline_data.utils.timezone import to_utc, datetime_to_timestamp
        from kline_data.reader import ParquetReader
        from rich.console import Console
        console = Console()

        # 确保时间为UTC
        start_time = to_utc(start_time)
        end_time = to_utc(end_time)
        
        start_ts = datetime_to_timestamp(start_time)
        end_ts = datetime_to_timestamp(end_time)
        
        affected_files = []
        reader = ParquetReader(self.config)
        
        # 计算涉及的年月范围
        year_months = set()
        current = start_time.replace(day=1)
        end_month = end_time.replace(day=1)
        
        while current <= end_month:
            year_months.add((current.year, current.month))
            # 移动到下个月
            if current.month == 12:
                current = current.replace(year=current.year + 1, month=1)
            else:
                current = current.replace(month=current.month + 1)
        
        # 处理每个分区文件
        for year, month in year_months:
            file_path = self._get_partition_path(exchange, symbol, interval, year, month)
            
            if not file_path.exists():
                continue
            
            # 读取该分区的数据
            try:
                df = pq.read_table(file_path).to_pandas()
                
                # 确保timestamp是datetime类型且为UTC
                if not pd.api.types.is_datetime64_any_dtype(df['timestamp']):
                    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
                elif df['timestamp'].dt.tz is None:
                    df['timestamp'] = df['timestamp'].dt.tz_localize('UTC')
                
                # 转换为毫秒时间戳进行比较
                df['ts_ms'] = df['timestamp'].astype('int64') / 10**6
                
                # 过滤掉要删除的时间范围
                df_keep = df[(df['ts_ms'] < start_ts) | (df['ts_ms'] > end_ts)].copy()
                df_keep = df_keep.drop(columns=['ts_ms'])
                
                if len(df_keep) == 0:
                    # 该分区所有数据都要删除，直接删除文件
                    file_path.unlink()
                    affected_files.append(str(file_path))
                    console.print(f"Deleted partition file: {file_path}")
                elif len(df_keep) < len(df):
                    # 部分数据被删除，重写文件
                    self.write(df_keep, file_path)
                    affected_files.append(str(file_path))
                    console.print(f"Updated partition file: {file_path} ({len(df) - len(df_keep)} records deleted)")
                # else: 该分区没有数据在要删除的范围内，不做处理
                
            except Exception as e:
                console.print(f"Error processing {file_path}: {e}")
                continue
        
        return affected_files
