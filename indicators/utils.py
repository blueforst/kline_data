"""
指标工具函数
提供通用的指标计算辅助功能，增强pandas和ta-lib的互操作性
"""
import pandas as pd
import numpy as np
from typing import Union, Optional, Tuple, List
import logging

logger = logging.getLogger(__name__)


def ensure_series(data: Union[pd.Series, np.ndarray, list]) -> pd.Series:
    """
    确保数据为pandas Series格式
    
    Args:
        data: 输入数据
        
    Returns:
        pd.Series: 转换后的Series
    """
    if isinstance(data, pd.Series):
        return data
    elif isinstance(data, np.ndarray):
        return pd.Series(data)
    elif isinstance(data, list):
        return pd.Series(data)
    else:
        raise TypeError(f"不支持的数据类型: {type(data)}")


def ensure_dataframe(data: Union[pd.DataFrame, dict]) -> pd.DataFrame:
    """
    确保数据为pandas DataFrame格式
    
    Args:
        data: 输入数据
        
    Returns:
        pd.DataFrame: 转换后的DataFrame
    """
    if isinstance(data, pd.DataFrame):
        return data
    elif isinstance(data, dict):
        return pd.DataFrame(data)
    else:
        raise TypeError(f"不支持的数据类型: {type(data)}")


def drop_na_rows(df: pd.DataFrame, columns: Optional[List[str]] = None) -> pd.DataFrame:
    """
    删除包含NaN的行
    
    Args:
        df: 输入数据
        columns: 要检查的列，如果为None则检查所有列
        
    Returns:
        pd.DataFrame: 删除NaN后的数据
    """
    if columns is None:
        return df.dropna()
    else:
        return df.dropna(subset=columns)


def fill_na_values(df: pd.DataFrame, method: str = 'ffill', columns: Optional[List[str]] = None) -> pd.DataFrame:
    """
    填充NaN值
    
    Args:
        df: 输入数据
        method: 填充方法 ('ffill', 'bfill', 'zero', 'mean')
        columns: 要填充的列，如果为None则填充所有列
        
    Returns:
        pd.DataFrame: 填充后的数据
    """
    result = df.copy()
    
    if columns is None:
        target = result
    else:
        target = result[columns]
    
    if method == 'ffill':
        filled = target.fillna(method='ffill')
    elif method == 'bfill':
        filled = target.fillna(method='bfill')
    elif method == 'zero':
        filled = target.fillna(0)
    elif method == 'mean':
        filled = target.fillna(target.mean())
    else:
        raise ValueError(f"不支持的填充方法: {method}")
    
    if columns is None:
        result = filled
    else:
        result[columns] = filled
    
    return result


def normalize_ohlcv_columns(df: pd.DataFrame, 
                           mapping: Optional[dict] = None) -> pd.DataFrame:
    """
    标准化OHLCV列名
    
    Args:
        df: 输入数据
        mapping: 列名映射，例如 {'Open': 'open', 'Close': 'close'}
        
    Returns:
        pd.DataFrame: 标准化后的数据
    """
    result = df.copy()
    
    if mapping is None:
        # 默认映射
        mapping = {
            'Open': 'open',
            'High': 'high',
            'Low': 'low',
            'Close': 'close',
            'Volume': 'volume',
            'Adj Close': 'close',
            'Adj_Close': 'close',
        }
    
    # 只重命名存在的列
    rename_dict = {k: v for k, v in mapping.items() if k in result.columns}
    if rename_dict:
        result = result.rename(columns=rename_dict)
    
    return result


def validate_price_data(df: pd.DataFrame, 
                       check_negative: bool = True,
                       check_zero: bool = True,
                       check_consistency: bool = True) -> Tuple[bool, List[str]]:
    """
    验证价格数据的有效性
    
    Args:
        df: 输入数据
        check_negative: 是否检查负数
        check_zero: 是否检查零值
        check_consistency: 是否检查OHLC一致性
        
    Returns:
        Tuple[bool, List[str]]: (是否有效, 错误信息列表)
    """
    errors = []
    
    price_columns = ['open', 'high', 'low', 'close']
    available_columns = [col for col in price_columns if col in df.columns]
    
    if not available_columns:
        errors.append("缺少价格列（open/high/low/close）")
        return False, errors
    
    # 检查负数
    if check_negative:
        for col in available_columns:
            if (df[col] < 0).any():
                errors.append(f"{col}列存在负数")
    
    # 检查零值
    if check_zero:
        for col in available_columns:
            if (df[col] == 0).any():
                errors.append(f"{col}列存在零值")
    
    # 检查OHLC一致性
    if check_consistency and all(col in df.columns for col in ['open', 'high', 'low', 'close']):
        if (df['high'] < df['low']).any():
            errors.append("存在高价低于低价的数据")
        
        if (df['close'] > df['high']).any():
            errors.append("存在收盘价高于最高价的数据")
        
        if (df['close'] < df['low']).any():
            errors.append("存在收盘价低于最低价的数据")
        
        if (df['open'] > df['high']).any():
            errors.append("存在开盘价高于最高价的数据")
        
        if (df['open'] < df['low']).any():
            errors.append("存在开盘价低于最低价的数据")
    
    return len(errors) == 0, errors


def calculate_returns(df: pd.DataFrame, 
                     column: str = 'close',
                     periods: int = 1,
                     method: str = 'simple') -> pd.Series:
    """
    计算收益率
    
    Args:
        df: 输入数据
        column: 计算列
        periods: 周期
        method: 计算方法 ('simple' 或 'log')
        
    Returns:
        pd.Series: 收益率序列
    """
    if column not in df.columns:
        raise ValueError(f"列 {column} 不存在")
    
    prices = df[column]
    
    if method == 'simple':
        returns = prices.pct_change(periods=periods)
    elif method == 'log':
        returns = np.log(prices / prices.shift(periods))
    else:
        raise ValueError(f"不支持的方法: {method}")
    
    return returns


def calculate_rolling_stats(df: pd.DataFrame,
                           column: str,
                           window: int,
                           stats: List[str] = ['mean', 'std', 'min', 'max']) -> pd.DataFrame:
    """
    计算滚动统计量
    
    Args:
        df: 输入数据
        column: 计算列
        window: 窗口大小
        stats: 统计量列表
        
    Returns:
        pd.DataFrame: 包含统计量的数据
    """
    result = df.copy()
    
    if column not in df.columns:
        raise ValueError(f"列 {column} 不存在")
    
    rolling = df[column].rolling(window=window)
    
    for stat in stats:
        if stat == 'mean':
            result[f'{column}_rolling_mean_{window}'] = rolling.mean()
        elif stat == 'std':
            result[f'{column}_rolling_std_{window}'] = rolling.std()
        elif stat == 'min':
            result[f'{column}_rolling_min_{window}'] = rolling.min()
        elif stat == 'max':
            result[f'{column}_rolling_max_{window}'] = rolling.max()
        elif stat == 'median':
            result[f'{column}_rolling_median_{window}'] = rolling.median()
        elif stat == 'sum':
            result[f'{column}_rolling_sum_{window}'] = rolling.sum()
        else:
            logger.warning(f"不支持的统计量: {stat}")
    
    return result


def crossover(series1: pd.Series, series2: pd.Series) -> pd.Series:
    """
    检测上穿（series1从下方穿过series2）
    
    Args:
        series1: 第一个序列
        series2: 第二个序列
        
    Returns:
        pd.Series: 布尔序列，True表示发生上穿
    """
    above = series1 > series2
    shifted = above.shift(1).fillna(False).astype(bool)
    return above & ~shifted


def crossunder(series1: pd.Series, series2: pd.Series) -> pd.Series:
    """
    检测下穿（series1从上方穿过series2）
    
    Args:
        series1: 第一个序列
        series2: 第二个序列
        
    Returns:
        pd.Series: 布尔序列，True表示发生下穿
    """
    below = series1 < series2
    shifted = below.shift(1).fillna(False).astype(bool)
    return below & ~shifted


def peak_detection(series: pd.Series, 
                  order: int = 3,
                  threshold: Optional[float] = None) -> Tuple[np.ndarray, np.ndarray]:
    """
    检测峰值和谷值
    
    Args:
        series: 输入序列
        order: 峰值检测的邻域大小
        threshold: 可选的阈值
        
    Returns:
        Tuple[np.ndarray, np.ndarray]: (峰值索引, 谷值索引)
    """
    from scipy.signal import argrelextrema
    
    # 检测峰值
    peaks = argrelextrema(series.values, np.greater, order=order)[0]
    
    # 检测谷值
    troughs = argrelextrema(series.values, np.less, order=order)[0]
    
    # 应用阈值过滤
    if threshold is not None:
        peak_values = series.iloc[peaks].values
        trough_values = series.iloc[troughs].values
        
        mean_val = series.mean()
        peaks = peaks[peak_values > mean_val + threshold]
        troughs = troughs[trough_values < mean_val - threshold]
    
    return peaks, troughs


def smooth_series(series: pd.Series, 
                 method: str = 'sma',
                 window: int = 5,
                 **kwargs) -> pd.Series:
    """
    平滑时间序列
    
    Args:
        series: 输入序列
        method: 平滑方法 ('sma', 'ema', 'savgol')
        window: 窗口大小
        **kwargs: 额外参数
        
    Returns:
        pd.Series: 平滑后的序列
    """
    if method == 'sma':
        return series.rolling(window=window).mean()
    elif method == 'ema':
        return series.ewm(span=window).mean()
    elif method == 'savgol':
        from scipy.signal import savgol_filter
        polyorder = kwargs.get('polyorder', 2)
        return pd.Series(
            savgol_filter(series.values, window, polyorder),
            index=series.index
        )
    else:
        raise ValueError(f"不支持的平滑方法: {method}")


def resample_ohlcv(df: pd.DataFrame,
                  timeframe: str,
                  timestamp_column: str = 'timestamp') -> pd.DataFrame:
    """
    重采样OHLCV数据
    
    Args:
        df: 输入数据
        timeframe: 目标时间框架（例如：'1H', '4H', '1D'）
        timestamp_column: 时间戳列名
        
    Returns:
        pd.DataFrame: 重采样后的数据
    """
    if timestamp_column not in df.columns:
        raise ValueError(f"列 {timestamp_column} 不存在")
    
    df_copy = df.copy()
    df_copy[timestamp_column] = pd.to_datetime(df_copy[timestamp_column])
    df_copy = df_copy.set_index(timestamp_column)
    
    resampled = pd.DataFrame()
    
    if 'open' in df_copy.columns:
        resampled['open'] = df_copy['open'].resample(timeframe).first()
    if 'high' in df_copy.columns:
        resampled['high'] = df_copy['high'].resample(timeframe).max()
    if 'low' in df_copy.columns:
        resampled['low'] = df_copy['low'].resample(timeframe).min()
    if 'close' in df_copy.columns:
        resampled['close'] = df_copy['close'].resample(timeframe).last()
    if 'volume' in df_copy.columns:
        resampled['volume'] = df_copy['volume'].resample(timeframe).sum()
    
    return resampled.reset_index()
