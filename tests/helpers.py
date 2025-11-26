"""
测试辅助函数和工具

提供测试中常用的辅助函数、装饰器和工具类。
"""

import time
import functools
import warnings
from typing import Any, Callable, Dict, List, Optional, Union, Tuple
from datetime import datetime, timedelta
from contextlib import contextmanager
from unittest.mock import Mock, patch
import pandas as pd
import numpy as np
import psutil
import os
import tempfile
import shutil
import logging

# 禁用测试中的警告
warnings.filterwarnings('ignore', category=DeprecationWarning)
warnings.filterwarnings('ignore', category=PendingDeprecationWarning)


# ============================================================================
# 性能测试装饰器
# ============================================================================

def benchmark(max_duration_ms: Optional[float] = None, max_memory_mb: Optional[float] = None):
    """
    性能基准测试装饰器

    Args:
        max_duration_ms: 最大执行时间（毫秒）
        max_memory_mb: 最大内存使用（MB）
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # 记录开始状态
            start_time = time.perf_counter()
            start_memory = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024

            try:
                # 执行函数
                result = func(*args, **kwargs)

                # 计算性能指标
                duration_ms = (time.perf_counter() - start_time) * 1000
                end_memory = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024
                memory_delta_mb = end_memory - start_memory

                # 验证性能要求
                if max_duration_ms and duration_ms > max_duration_ms:
                    raise AssertionError(
                        f"Performance threshold exceeded: {duration_ms:.2f}ms > {max_duration_ms}ms"
                    )

                if max_memory_mb and memory_delta_mb > max_memory_mb:
                    raise AssertionError(
                        f"Memory threshold exceeded: {memory_delta_mb:.2f}MB > {max_memory_mb}MB"
                    )

                # 添加性能信息到结果
                if isinstance(result, dict):
                    result['_performance'] = {
                        'duration_ms': duration_ms,
                        'memory_delta_mb': memory_delta_mb
                    }

                return result

            except Exception as e:
                # 记录失败时的性能信息
                duration_ms = (time.perf_counter() - start_time) * 1000
                logging.error(f"Function {func.__name__} failed after {duration_ms:.2f}ms")
                raise

        return wrapper
    return decorator


def retry(max_attempts: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """
    重试装饰器，用于测试不稳定的操作

    Args:
        max_attempts: 最大重试次数
        delay: 初始延迟（秒）
        backoff: 延迟倍数
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay

            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logging.warning(f"Function {func.__name__} failed after {max_attempts} attempts")

            raise last_exception
        return wrapper
    return decorator


# ============================================================================
# 数据验证辅助函数
# ============================================================================

def assert_ohlcv_valid(
    df: pd.DataFrame,
    allow_empty: bool = False,
    min_rows: int = 1,
    required_columns: Optional[List[str]] = None
) -> None:
    """
    验证OHLCV DataFrame的有效性

    Args:
        df: 要验证的DataFrame
        allow_empty: 是否允许空DataFrame
        min_rows: 最小行数
        required_columns: 必需的列名列表
    """
    if required_columns is None:
        required_columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']

    # 检查DataFrame是否为空
    if df.empty:
        if not allow_empty:
            raise AssertionError("DataFrame is empty but allow_empty=False")
        return

    # 检查行数
    if len(df) < min_rows:
        raise AssertionError(f"DataFrame has {len(df)} rows, expected at least {min_rows}")

    # 检查必需列
    missing_columns = set(required_columns) - set(df.columns)
    if missing_columns:
        raise AssertionError(f"Missing required columns: {missing_columns}")

    # 检查时间戳列
    if 'timestamp' in df.columns:
        if not pd.api.types.is_datetime64_any_dtype(df['timestamp']):
            raise AssertionError("timestamp column must be datetime type")

        # 检查时间戳是否递增
        if not df['timestamp'].is_monotonic_increasing:
            raise AssertionError("timestamp values must be monotonically increasing")

    # 检查价格列
    price_columns = ['open', 'high', 'low', 'close']
    existing_price_columns = [col for col in price_columns if col in df.columns]

    for col in existing_price_columns:
        # 检查是否为数值类型
        if not pd.api.types.is_numeric_dtype(df[col]):
            raise AssertionError(f"{col} column must be numeric")

        # 检查是否为正数
        if (df[col] <= 0).any():
            raise AssertionError(f"{col} values must be positive")

        # 检查是否有NaN
        if df[col].isna().any():
            raise AssertionError(f"{col} values cannot be NaN")

    # 检查价格逻辑关系
    if all(col in df.columns for col in ['high', 'low', 'open', 'close']):
        if not (df['high'] >= df['low']).all():
            raise AssertionError("high values must be >= low values")

        if not (df['high'] >= df['open']).all():
            raise AssertionError("high values must be >= open values")

        if not (df['high'] >= df['close']).all():
            raise AssertionError("high values must be >= close values")

        if not (df['low'] <= df['open']).all():
            raise AssertionError("low values must be <= open values")

        if not (df['low'] <= df['close']).all():
            raise AssertionError("low values must be <= close values")

    # 检查成交量列
    if 'volume' in df.columns:
        if not pd.api.types.is_numeric_dtype(df['volume']):
            raise AssertionError("volume column must be numeric")

        if (df['volume'] < 0).any():
            raise AssertionError("volume values must be non-negative")

        if df['volume'].isna().any():
            raise AssertionError("volume values cannot be NaN")


def assert_dataframes_equal(
    df1: pd.DataFrame,
    df2: pd.DataFrame,
    check_dtype: bool = True,
    check_index: bool = True,
    check_names: bool = False,
    rtol: float = 1e-5,
    atol: float = 1e-8,
    **kwargs
) -> None:
    """
    比较两个DataFrame是否相等，提供详细的错误信息

    Args:
        df1, df2: 要比较的DataFrame
        check_dtype: 是否检查数据类型
        check_index: 是否检查索引
        check_names: 是否检查列名
        rtol: 相对容差
        atol: 绝对容差
    """
    try:
        pd.testing.assert_frame_equal(
            df1, df2,
            check_dtype=check_dtype,
            check_index=check_index,
            check_names=check_names,
            rtol=rtol,
            atol=atol,
            **kwargs
        )
    except AssertionError as e:
        # 提供更详细的错误信息
        details = []

        if df1.shape != df2.shape:
            details.append(f"Shape mismatch: {df1.shape} vs {df2.shape}")

        if set(df1.columns) != set(df2.columns):
            details.append(f"Columns mismatch: {set(df1.columns)} vs {set(df2.columns)}")

        if not df1.empty and not df2.empty:
            try:
                # 检查数值差异
                numeric_cols = df1.select_dtypes(include=[np.number]).columns.intersection(
                    df2.select_dtypes(include=[np.number]).columns
                )
                for col in numeric_cols:
                    if not np.allclose(df1[col], df2[col], rtol=rtol, atol=atol, equal_nan=True):
                        max_diff = np.abs(df1[col] - df2[col]).max()
                        details.append(f"Column '{col}' max difference: {max_diff}")
            except Exception:
                pass

        error_msg = str(e)
        if details:
            error_msg = f"{error_msg}\nDetails:\n" + "\n".join(f"  - {detail}" for detail in details)

        raise AssertionError(error_msg)


# ============================================================================
# 时间和日期辅助函数
# ============================================================================

def freeze_time(target_time: Union[str, datetime]):
    """
    冻结时间的上下文管理器

    Args:
        target_time: 要冻结到的时间
    """
    try:
        from freezegun import freeze_time as _freeze_time
        return _freeze_time(target_time)
    except ImportError:
        # 如果没有安装freezegun，使用简单的mock
        @contextmanager
        def mock_freeze_time(time):
            original_time = time
            yield
        return mock_freeze_time(target_time)


def create_time_range(
    start: Union[str, datetime],
    end: Union[str, datetime],
    timeframe: str = '1h'
) -> pd.DatetimeIndex:
    """
    创建时间范围

    Args:
        start: 开始时间
        end: 结束时间
        timeframe: 时间间隔

    Returns:
        DatetimeIndex
    """
    if isinstance(start, str):
        start = pd.to_datetime(start)
    if isinstance(end, str):
        end = pd.to_datetime(end)

    freq_map = {
        '1m': '1min',
        '5m': '5min',
        '15m': '15min',
        '1h': '1h',
        '4h': '4h',
        '1d': '1D',
    }

    freq = freq_map.get(timeframe, timeframe)
    return pd.date_range(start=start, end=end, freq=freq)


# ============================================================================
# Mock和Patch辅助函数
# ============================================================================

@contextmanager
def mock_ccxt_exchange(exchange_name: str = 'binance'):
    """
    Mock CCXT交易所的上下文管理器

    Args:
        exchange_name: 交易所名称
    """
    mock_exchange = Mock()
    mock_exchange.name = exchange_name
    mock_exchange.has = {
        'fetchOHLCV': True,
        'fetchTicker': True,
        'fetchTrades': True,
    }
    mock_exchange.rateLimit = 1000
    mock_exchange.timeframes = {
        '1m': '1m', '5m': '5m', '15m': '15m', '1h': '1h', '4h': '4h', '1d': '1d'
    }

    # Mock fetch_ohlcv方法
    def mock_fetch_ohlcv(symbol, timeframe, since=None, limit=None):
        # 生成模拟数据
        now = int(datetime.now().timestamp() * 1000)
        data = []
        base_price = 50000 if 'BTC' in symbol else 3000 if 'ETH' in symbol else 100

        for i in range(min(limit or 100, 100)):
            timestamp = now - (i * 3600000)  # 1小时间隔
            price = base_price * (1 + np.random.normal(0, 0.001))
            data.append([
                timestamp,
                price,  # open
                price * 1.01,  # high
                price * 0.99,  # low
                price * 1.005,  # close
                100000  # volume
            ])

        return data

    mock_exchange.fetch_ohlcv = mock_fetch_ohlcv

    with patch('ccxt.binance', return_value=mock_exchange):
        yield mock_exchange


@contextmanager
def mock_filesystem():
    """
    Mock文件系统的上下文管理器
    """
    temp_dir = tempfile.mkdtemp(prefix="mock_fs_")
    try:
        yield temp_dir
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


@contextmanager
def mock_network_offline():
    """
    Mock网络离线的上下文管理器
    """
    with patch('socket.socket') as mock_socket:
        # 模拟网络连接失败
        mock_socket.side_effect = ConnectionError("Network is offline")
        yield mock_socket


# ============================================================================
# 数据生成辅助函数
# ============================================================================

def generate_realistic_price_series(
    start_price: float = 50000.0,
    periods: int = 100,
    volatility: float = 0.02,
    trend: float = 0.0001,
    timeframe: str = '1h'
) -> pd.Series:
    """
    生成真实的价格序列（几何布朗运动）

    Args:
        start_price: 起始价格
        periods: 周期数
        volatility: 波动率
        trend: 趋势（每期的收益率）
        timeframe: 时间间隔

    Returns:
        价格Series
    """
    # 计算时间步长（以年为单位）
    time_steps = {
        '1m': 1/(365*24*60),
        '5m': 5/(365*24*60),
        '15m': 15/(365*24*60),
        '1h': 1/(365*24),
        '4h': 4/(365*24),
        '1d': 1/365,
    }
    dt = time_steps.get(timeframe, 1/(365*24))

    # 生成随机收益率
    random_shocks = np.random.normal(0, 1, periods)
    returns = (trend - 0.5 * volatility**2) * dt + volatility * np.sqrt(dt) * random_shocks

    # 计算价格
    log_prices = np.log(start_price) + np.cumsum(returns)
    prices = np.exp(log_prices)

    return pd.Series(prices, name='price')


def generate_ohlcv_from_price(
    prices: pd.Series,
    volume_base: float = 100000,
    volume_volatility: float = 0.5
) -> pd.DataFrame:
    """
    从价格序列生成OHLCV数据

    Args:
        prices: 价格序列
        volume_base: 基础成交量
        volume_volatility: 成交量波动性

    Returns:
        OHLCV DataFrame
    """
    timestamps = prices.index if isinstance(prices.index, pd.DatetimeIndex) else pd.date_range(
        start=datetime.now(), periods=len(prices), freq='1h'
    )

    data = []
    for i, price in enumerate(prices):
        # 确定开盘价（第一条数据）
        if i == 0:
            open_price = price
        else:
            open_price = prices.iloc[i-1]

        close_price = price

        # 生成高低价（基于随机游走）
        price_range = abs(close_price - open_price) * random.uniform(0.5, 2.0)
        high = max(open_price, close_price) + price_range * random.uniform(0.3, 1.0)
        low = min(open_price, close_price) - price_range * random.uniform(0.3, 1.0)

        # 确保价格逻辑正确
        high = max(high, open_price, close_price)
        low = min(low, open_price, close_price)

        # 生成成交量（与价格变化相关）
        price_change_pct = abs(close_price - open_price) / open_price
        volume = volume_base * (1 + price_change_pct * 5) * (1 + random.uniform(-volume_volatility, volume_volatility))

        data.append({
            'timestamp': timestamps[i],
            'open': round(open_price, 2),
            'high': round(high, 2),
            'low': round(low, 2),
            'close': round(close_price, 2),
            'volume': int(volume)
        })

    return pd.DataFrame(data)


# ============================================================================
# 测试环境管理
# ============================================================================

class TestEnvironment:
    """测试环境管理器"""

    def __init__(self):
        self.temp_dirs = []
        self.mock_patches = []
        self.env_vars = {}

    def create_temp_dir(self, prefix: str = "test_") -> str:
        """创建临时目录"""
        temp_dir = tempfile.mkdtemp(prefix=prefix)
        self.temp_dirs.append(temp_dir)
        return temp_dir

    def set_env_var(self, key: str, value: str):
        """设置环境变量"""
        original_value = os.environ.get(key)
        os.environ[key] = value
        self.env_vars[key] = original_value

    def add_mock_patch(self, target: str, **kwargs) -> Mock:
        """添加Mock patch"""
        patcher = patch(target, **kwargs)
        mock_obj = patcher.start()
        self.mock_patches.append(patcher)
        return mock_obj

    def cleanup(self):
        """清理测试环境"""
        # 清理临时目录
        for temp_dir in self.temp_dirs:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
        self.temp_dirs.clear()

        # 清理Mock patches
        for patcher in self.mock_patches:
            patcher.stop()
        self.mock_patches.clear()

        # 恢复环境变量
        for key, original_value in self.env_vars.items():
            if original_value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = original_value
        self.env_vars.clear()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()


# ============================================================================
# 断言辅助函数
# ============================================================================

def assert_dict_subset(subset: Dict[str, Any], superset: Dict[str, Any]) -> None:
    """
    断言subset字典中的所有键值对都在superset中

    Args:
        subset: 子集字典
        superset: 超集字典
    """
    for key, value in subset.items():
        if key not in superset:
            raise AssertionError(f"Key '{key}' not found in superset")
        if superset[key] != value:
            raise AssertionError(f"Value mismatch for key '{key}': {value} != {superset[key]}")


def assert_list_contains(list_obj: List[Any], expected_items: List[Any], all_items: bool = True) -> None:
    """
    断言列表包含期望的项目

    Args:
        list_obj: 要检查的列表
        expected_items: 期望包含的项目
        all_items: 是否要求所有项目都存在
    """
    missing_items = [item for item in expected_items if item not in list_obj]

    if all_items and missing_items:
        raise AssertionError(f"List is missing items: {missing_items}")
    elif not all_items and len(expected_items) - len(missing_items) == 0:
        raise AssertionError(f"List contains none of the expected items: {expected_items}")


def assert_file_exists(file_path: str, should_exist: bool = True) -> None:
    """
    断言文件是否存在

    Args:
        file_path: 文件路径
        should_exist: 是否应该存在
    """
    exists = os.path.exists(file_path)
    if should_exist and not exists:
        raise AssertionError(f"File should exist but does not: {file_path}")
    elif not should_exist and exists:
        raise AssertionError(f"File should not exist but does: {file_path}")


# ============================================================================
# 性能监控工具
# ============================================================================

class PerformanceMonitor:
    """性能监控工具"""

    def __init__(self):
        self.metrics = {}
        self.start_time = None
        self.start_memory = None

    def start(self, name: str):
        """开始监控"""
        self.start_time = time.perf_counter()
        self.start_memory = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024
        self.current_name = name

    def stop(self) -> Dict[str, float]:
        """停止监控并返回指标"""
        if self.start_time is None:
            return {}

        duration = time.perf_counter() - self.start_time
        current_memory = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024
        memory_delta = current_memory - self.start_memory

        metrics = {
            'duration_ms': duration * 1000,
            'memory_start_mb': self.start_memory,
            'memory_end_mb': current_memory,
            'memory_delta_mb': memory_delta,
        }

        if hasattr(self, 'current_name'):
            self.metrics[self.current_name] = metrics

        self.start_time = None
        self.start_memory = None
        delattr(self, 'current_name')

        return metrics

    def get_metrics(self, name: str = None) -> Dict[str, Any]:
        """获取指标"""
        if name:
            return self.metrics.get(name, {})
        return self.metrics.copy()

    def reset(self):
        """重置指标"""
        self.metrics.clear()
        self.start_time = None
        self.start_memory = None


# ============================================================================
# 异步测试辅助函数
# ============================================================================

def async_test(func):
    """
    异步测试装饰器
    """
    import asyncio

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(func(*args, **kwargs))
    return wrapper


# ============================================================================
# 使用示例
# ============================================================================

if __name__ == "__main__":
    # 性能测试示例
    @benchmark(max_duration_ms=100, max_memory_mb=10)
    def example_function():
        """示例函数"""
        time.sleep(0.05)  # 模拟计算
        return {"result": "success"}

    # 数据验证示例
    df = pd.DataFrame({
        'timestamp': pd.date_range('2024-01-01', periods=10, freq='1h'),
        'open': [50000 + i for i in range(10)],
        'high': [50050 + i for i in range(10)],
        'low': [49950 + i for i in range(10)],
        'close': [50025 + i for i in range(10)],
        'volume': [100000] * 10
    })

    # 测试辅助函数
    print("=== 性能测试示例 ===")
    result = example_function()
    print(f"结果: {result}")

    print("\n=== 数据验证示例 ===")
    try:
        assert_ohlcv_valid(df)
        print("✓ OHLCV数据验证通过")
    except AssertionError as e:
        print(f"✗ OHLCV数据验证失败: {e}")

    print("\n=== 价格序列生成示例 ===")
    prices = generate_realistic_price_series(periods=50)
    print(f"生成价格序列长度: {len(prices)}")
    print(f"价格范围: {prices.min():.2f} - {prices.max():.2f}")

    print("\n=== 测试环境管理示例 ===")
    with TestEnvironment() as env:
        temp_dir = env.create_temp_dir()
        test_file = os.path.join(temp_dir, "test.txt")
        with open(test_file, 'w') as f:
            f.write("test")
        print(f"创建临时文件: {test_file}")
        print(f"文件存在: {os.path.exists(test_file)}")
    # 环境自动清理