"""数据验证器"""

from typing import List, Tuple
import pandas as pd
import numpy as np
from datetime import timedelta

from .models import MissingRange, DataQuality


class DataValidator:
    """
    数据验证器
    负责验证K线数据的正确性和完整性
    """
    
    @staticmethod
    def validate_kline(df: pd.DataFrame) -> pd.DataFrame:
        """
        验证K线数据
        
        Args:
            df: 原始数据DataFrame
            
        Returns:
            pd.DataFrame: 验证并清洗后的数据
            
        Raises:
            ValueError: 数据格式错误
        """
        # 1. 检查必需列
        required_cols = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            raise ValueError(f"Missing required columns: {missing_cols}")
        
        # 2. 转换数据类型（确保UTC时区）
        if not pd.api.types.is_datetime64_any_dtype(df['timestamp']):
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
        elif df['timestamp'].dt.tz is None:
            df['timestamp'] = df['timestamp'].dt.tz_localize('UTC')
        
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # 3. 删除无效行
        df = df.dropna(subset=['timestamp', 'open', 'high', 'low', 'close'])
        
        # 4. 检查OHLC逻辑
        invalid_high = df['high'] < df['low']
        if invalid_high.any():
            console.print(f"Warning: Found {invalid_high.sum()} rows where high < low, removing...")
            df = df[~invalid_high]
        
        invalid_high_open = df['high'] < df['open']
        if invalid_high_open.any():
            console.print(f"Warning: Found {invalid_high_open.sum()} rows where high < open, correcting...")
            df.loc[invalid_high_open, 'high'] = df.loc[invalid_high_open, 'open']
        
        invalid_high_close = df['high'] < df['close']
        if invalid_high_close.any():
            console.print(f"Warning: Found {invalid_high_close.sum()} rows where high < close, correcting...")
            df.loc[invalid_high_close, 'high'] = df.loc[invalid_high_close, 'close']
        
        invalid_low_open = df['low'] > df['open']
        if invalid_low_open.any():
            console.print(f"Warning: Found {invalid_low_open.sum()} rows where low > open, correcting...")
            df.loc[invalid_low_open, 'low'] = df.loc[invalid_low_open, 'open']
        
        invalid_low_close = df['low'] > df['close']
        if invalid_low_close.any():
            console.print(f"Warning: Found {invalid_low_close.sum()} rows where low > close, correcting...")
            df.loc[invalid_low_close, 'low'] = df.loc[invalid_low_close, 'close']
        
        # 5. 检查负数交易量
        negative_volume = df['volume'] < 0
        if negative_volume.any():
            console.print(f"Warning: Found {negative_volume.sum()} rows with negative volume, setting to 0...")
            df.loc[negative_volume, 'volume'] = 0
        
        # 6. 去重（保留最后一条）
        original_len = len(df)
        df = df.drop_duplicates(subset=['timestamp'], keep='last')
        if len(df) < original_len:
            console.print(f"Removed {original_len - len(df)} duplicate records")
        
        # 7. 排序
        df = df.sort_values('timestamp').reset_index(drop=True)
        
        return df
    
    @staticmethod
    def check_completeness(
        df: pd.DataFrame,
        interval: str = '1s'
    ) -> Tuple[float, List[MissingRange]]:
        """
        检查数据完整性
        
        Args:
            df: 数据DataFrame
            interval: 时间间隔
            
        Returns:
            tuple: (完整性比例, 缺失范围列表)
        """
        if df.empty:
            return 0.0, []
        
        # 确保时间戳排序
        df = df.sort_values('timestamp')
        
        # 解析时间间隔
        expected_diff = DataValidator._parse_interval(interval)
        
        # 计算实际时间差
        time_diffs = df['timestamp'].diff()
        
        # 找出缺失范围
        missing_ranges = []
        for i, diff in enumerate(time_diffs):
            if pd.notna(diff) and diff > expected_diff:
                start_time = df.iloc[i-1]['timestamp']
                end_time = df.iloc[i]['timestamp']
                
                missing_ranges.append(MissingRange(
                    start=start_time.isoformat(),
                    end=end_time.isoformat(),
                    gap=str(diff)
                ))
        
        # 计算完整性
        if len(df) < 2:
            completeness = 1.0
        else:
            total_time = (df['timestamp'].iloc[-1] - df['timestamp'].iloc[0])
            expected_records = int(total_time / expected_diff) + 1
            completeness = len(df) / expected_records if expected_records > 0 else 1.0
        
        return min(completeness, 1.0), missing_ranges
    
    @staticmethod
    def check_data_quality(df: pd.DataFrame, interval: str = '1s') -> DataQuality:
        """
        检查数据质量
        
        Args:
            df: 数据DataFrame
            interval: 时间间隔
            
        Returns:
            DataQuality: 数据质量指标
        """
        if df.empty:
            return DataQuality(completeness=0.0, duplicate_rate=0.0)
        
        # 计算完整性
        completeness, _ = DataValidator.check_completeness(df, interval)
        
        # 计算重复率
        total_records = len(df)
        unique_records = df['timestamp'].nunique()
        duplicate_rate = (total_records - unique_records) / total_records if total_records > 0 else 0.0
        
        return DataQuality(
            completeness=completeness,
            duplicate_rate=duplicate_rate
        )
    
    @staticmethod
    def detect_anomalies(df: pd.DataFrame, threshold: float = 3.0) -> pd.DataFrame:
        """
        检测异常值
        使用Z-score方法检测价格和成交量异常
        
        Args:
            df: 数据DataFrame
            threshold: Z-score阈值
            
        Returns:
            pd.DataFrame: 包含异常标记的DataFrame
        """
        df = df.copy()
        
        # 计算价格变化率
        df['price_change'] = df['close'].pct_change()
        
        # 计算Z-score
        for col in ['price_change', 'volume']:
            if col in df.columns:
                mean = df[col].mean()
                std = df[col].std()
                
                if std > 0:
                    df[f'{col}_zscore'] = (df[col] - mean) / std
                    df[f'{col}_anomaly'] = np.abs(df[f'{col}_zscore']) > threshold
                else:
                    df[f'{col}_zscore'] = 0
                    df[f'{col}_anomaly'] = False
        
        return df
    
    @staticmethod
    def remove_outliers(
        df: pd.DataFrame,
        columns: List[str] = None,
        method: str = 'iqr',
        factor: float = 1.5
    ) -> pd.DataFrame:
        """
        移除异常值
        
        Args:
            df: 数据DataFrame
            columns: 要检查的列，默认为价格列
            method: 方法 ('iqr' 或 'zscore')
            factor: IQR倍数或Z-score阈值
            
        Returns:
            pd.DataFrame: 移除异常值后的数据
        """
        if columns is None:
            columns = ['open', 'high', 'low', 'close', 'volume']
        
        df = df.copy()
        
        if method == 'iqr':
            for col in columns:
                if col in df.columns:
                    Q1 = df[col].quantile(0.25)
                    Q3 = df[col].quantile(0.75)
                    IQR = Q3 - Q1
                    
                    lower_bound = Q1 - factor * IQR
                    upper_bound = Q3 + factor * IQR
                    
                    df = df[(df[col] >= lower_bound) & (df[col] <= upper_bound)]
        
        elif method == 'zscore':
            for col in columns:
                if col in df.columns:
                    mean = df[col].mean()
                    std = df[col].std()
                    
                    if std > 0:
                        z_scores = np.abs((df[col] - mean) / std)
                        df = df[z_scores < factor]
        
        return df.reset_index(drop=True)
    
    @staticmethod
    def _parse_interval(interval: str) -> timedelta:
        """
        解析时间间隔字符串
        
        Args:
            interval: 时间间隔字符串 (如: '1s', '1m', '1h')
            
        Returns:
            timedelta: 时间间隔对象
        """
        interval_map = {
            's': 'seconds',
            'm': 'minutes',
            'h': 'hours',
            'd': 'days',
        }
        
        # 提取数字和单位
        import re
        from rich.console import Console
        console = Console()

        match = re.match(r'(\d+)([smhd])', interval.lower())
        if not match:
            raise ValueError(f"Invalid interval format: {interval}")
        
        value = int(match.group(1))
        unit = match.group(2)
        
        unit_name = interval_map.get(unit)
        if not unit_name:
            raise ValueError(f"Unsupported interval unit: {unit}")
        
        return timedelta(**{unit_name: value})
    
    @staticmethod
    def validate_data_range(
        df: pd.DataFrame,
        start_time: pd.Timestamp,
        end_time: pd.Timestamp
    ) -> bool:
        """
        验证数据是否在指定时间范围内
        
        Args:
            df: 数据DataFrame
            start_time: 开始时间
            end_time: 结束时间
            
        Returns:
            bool: 是否在范围内
        """
        if df.empty:
            return False
        
        df_start = df['timestamp'].min()
        df_end = df['timestamp'].max()
        
        return df_start >= start_time and df_end <= end_time
