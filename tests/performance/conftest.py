"""
Performance testing configuration and fixtures

Provides shared fixtures and configuration for all performance tests
including memory monitoring, resource tracking, and test data generation.
"""

import pytest
import pandas as pd
import numpy as np
import psutil
import os
import tempfile
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch
import time
import gc
from typing import Dict, Any, Generator, Optional

# Performance monitoring utilities
class PerformanceMonitor:
    """Monitor system performance during tests"""

    def __init__(self):
        self.process = psutil.Process(os.getpid())
        self.start_memory = None
        self.start_time = None
        self.peak_memory = None
        self.cpu_samples = []

    def start_monitoring(self):
        """Start performance monitoring"""
        gc.collect()  # Force garbage collection before test
        self.start_memory = self.process.memory_info().rss / 1024 / 1024  # MB
        self.start_time = time.perf_counter()
        self.peak_memory = self.start_memory
        self.cpu_samples = []

    def sample_cpu(self):
        """Sample CPU usage"""
        if self.start_time:
            current_cpu = self.process.cpu_percent()
            self.cpu_samples.append(current_cpu)

    def update_peak_memory(self):
        """Update peak memory usage"""
        current_memory = self.process.memory_info().rss / 1024 / 1024
        self.peak_memory = max(self.peak_memory, current_memory)

    def get_metrics(self) -> Dict[str, Any]:
        """Get performance metrics"""
        self.update_peak_memory()
        duration = time.perf_counter() - self.start_time if self.start_time else 0
        current_memory = self.process.memory_info().rss / 1024 / 1024

        return {
            'duration': duration,
            'start_memory_mb': self.start_memory,
            'current_memory_mb': current_memory,
            'peak_memory_mb': self.peak_memory,
            'memory_delta_mb': current_memory - self.start_memory,
            'avg_cpu_percent': np.mean(self.cpu_samples) if self.cpu_samples else 0,
            'max_cpu_percent': np.max(self.cpu_samples) if self.cpu_samples else 0,
            'cpu_samples_count': len(self.cpu_samples)
        }

@pytest.fixture
def perf_monitor():
    """Performance monitor fixture"""
    monitor = PerformanceMonitor()
    monitor.start_monitoring()
    yield monitor
    # Cleanup after test
    gc.collect()

@pytest.fixture(scope="session")
def temp_dir():
    """Temporary directory for performance tests"""
    temp_path = Path(tempfile.mkdtemp(prefix="kline_perf_test_"))
    yield temp_path
    # Cleanup
    shutil.rmtree(temp_path, ignore_errors=True)

@pytest.fixture
def large_ohlcv_dataset():
    """Generate large OHLCV dataset for performance testing"""
    np.random.seed(42)  # Ensure reproducibility

    # Generate 2 years of hourly data (17520 records)
    periods = 2 * 365 * 24
    timestamps = pd.date_range('2022-01-01', periods=periods, freq='1h')

    # Generate realistic price series
    base_price = 50000.0
    volatility = 0.02  # 2% daily volatility

    # Generate price series with trends
    trend = np.sin(np.linspace(0, 4*np.pi, periods)) * 0.3  # Cyclical trend
    returns = np.random.normal(0, volatility/np.sqrt(24), periods) + trend * 0.001

    prices = [base_price]
    for ret in returns:
        prices.append(max(prices[-1] * (1 + ret), 1.0))
    prices = prices[1:]

    data = []
    for i, ts in enumerate(timestamps):
        current_price = prices[i]
        open_price = prices[i-1] if i > 0 else current_price
        close_price = current_price

        # Generate realistic OHLC
        intrabar_volatility = 0.01  # 1% intrabar volatility
        price_range = current_price * intrabar_volatility

        high = max(open_price, close_price) + price_range * np.random.uniform(0.3, 1.0)
        low = min(open_price, close_price) - price_range * np.random.uniform(0.3, 1.0)
        high = max(high, open_price, close_price)
        low = min(low, open_price, close_price)

        # Volume with some correlation with price movement
        price_change = (close_price - open_price) / open_price
        base_volume = np.random.randint(100000, 500000)
        volume_multiplier = 1 + abs(price_change) * 5  # Higher volume with larger price moves
        volume = int(base_volume * volume_multiplier * np.random.uniform(0.5, 2.0))

        data.append({
            'timestamp': ts,
            'open': round(open_price, 2),
            'high': round(high, 2),
            'low': round(low, 2),
            'close': round(close_price, 2),
            'volume': volume
        })

    return pd.DataFrame(data)

@pytest.fixture
def minute_dataset():
    """Generate 1-minute dataset for resampling tests"""
    np.random.seed(42)

    # Generate 7 days of minute data (10080 records)
    periods = 7 * 24 * 60
    timestamps = pd.date_range('2023-01-01', periods=periods, freq='1min')

    base_price = 45000.0
    volatility = 0.02 / np.sqrt(24*60)  # Convert daily volatility to minute

    prices = [base_price]
    for _ in range(periods):
        change = np.random.normal(0, volatility)
        prices.append(max(prices[-1] * (1 + change), 1.0))
    prices = prices[1:]

    data = []
    for i, ts in enumerate(timestamps):
        current_price = prices[i]
        open_price = prices[i-1] if i > 0 else current_price
        close_price = current_price

        price_range = current_price * 0.005
        high = max(open_price, close_price) + price_range * np.random.uniform(0.2, 0.8)
        low = min(open_price, close_price) - price_range * np.random.uniform(0.2, 0.8)
        high = max(high, open_price, close_price)
        low = min(low, open_price, close_price)

        volume = np.random.randint(1000, 10000)

        data.append({
            'timestamp': ts,
            'open': round(open_price, 2),
            'high': round(high, 2),
            'low': round(low, 2),
            'close': round(close_price, 2),
            'volume': volume
        })

    return pd.DataFrame(data)

@pytest.fixture
def multi_timeframe_datasets(temp_dir, large_ohlcv_dataset):
    """Create multiple timeframe datasets for testing"""
    timeframes = {
        '1m': 1,
        '5m': 5,
        '15m': 15,
        '1h': 60,
        '4h': 240,
        '1d': 1440
    }

    datasets = {}

    for timeframe_name, minutes in timeframes.items():
        # Resample from hourly data
        timeframe_data = large_ohlcv_dataset.copy()
        timeframe_data.set_index('timestamp', inplace=True)

        # Aggregate to target timeframe
        agg_rules = {
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }

        resampled = timeframe_data.resample(f'{minutes}min').agg(agg_rules)
        resampled = resampled.dropna()
        resampled.reset_index(inplace=True)

        # Save to file
        file_path = temp_dir / f"binance_BTC_USDT_{timeframe_name}.parquet"
        resampled.to_parquet(file_path, index=False, compression='snappy')

        datasets[timeframe_name] = {
            'data': resampled,
            'file_path': file_path,
            'record_count': len(resampled)
        }

    return datasets

@pytest.fixture
def mock_ccxt_exchange():
    """Mock CCXT exchange for download performance tests"""
    exchange = Mock()
    exchange.name = 'binance'
    exchange.rateLimit = 100  # 100ms rate limit
    exchange.has = {
        'fetchOHLCV': True,
        'fetchOHLCV': True
    }

    def mock_fetch_ohlcv(symbol, timeframe, since=None, limit=None, params=None):
        # Simulate network latency
        time.sleep(0.01 + np.random.uniform(0, 0.02))  # 10-30ms latency

        # Generate mock data
        now = int(datetime.now().timestamp() * 1000)
        data = []
        base_price = 50000 + np.random.uniform(-5000, 5000)

        limit_count = min(limit or 100, 100)
        timeframe_seconds = {
            '1m': 60,
            '5m': 300,
            '15m': 900,
            '1h': 3600,
            '4h': 14400,
            '1d': 86400
        }.get(timeframe, 3600)

        for i in range(limit_count):
            timestamp = now - (i * timeframe_seconds * 1000)
            price_change = np.random.normal(0, 0.001)
            price = base_price * (1 + price_change)

            data.append([
                timestamp,
                price,  # open
                price * (1 + np.random.uniform(0, 0.002)),  # high
                price * (1 - np.random.uniform(0, 0.002)),  # low
                price * (1 + np.random.uniform(-0.001, 0.001)),  # close
                int(np.random.uniform(100000, 1000000))  # volume
            ])

        return data

    exchange.fetch_ohlcv = mock_fetch_ohlcv
    exchange.load_markets = Mock(return_value={})

    return exchange

@pytest.fixture
def performance_config():
    """Configuration for performance tests"""
    return {
        'performance_thresholds': {
            'query_time_ms': {
                'small': 50,    # < 1000 records
                'medium': 200,  # 1000-10000 records
                'large': 1000   # > 10000 records
            },
            'memory_ratio': {
                'max': 5.0,  # Memory should not exceed 5x data size
                'warning': 3.0
            },
            'throughput_records_per_second': {
                'min_read': 10000,
                'min_write': 5000,
                'min_resample': 50000,
                'min_indicator': 100000
            },
            'concurrent_users': {
                'target': 100,
                'max_response_time_ms': 5000
            }
        },
        'stress_test_params': {
            'max_memory_mb': 1024,
            'max_duration_seconds': 300,
            'concurrent_requests': 50
        }
    }

@pytest.fixture
def benchmark_data_sizes():
    """Different data sizes for benchmarking"""
    return {
        'small': 1000,     # ~1K records
        'medium': 10000,   # ~10K records
        'large': 100000,   # ~100K records
        'xlarge': 1000000  # ~1M records
    }

# Pytest benchmark configuration - group stats moved to avoid hook signature errors

# Performance test markers
# pytest_plugins moved to main conftest.py to avoid deprecation warning

# Add custom markers
def pytest_configure(config):
    config.addinivalue_line(
        "markers", "performance: mark test as performance test"
    )
    config.addinivalue_line(
        "markers", "benchmark: mark test as benchmark test"
    )
    config.addinivalue_line(
        "markers", "stress: mark test as stress test"
    )
    config.addinivalue_line(
        "markers", "memory: mark test as memory usage test"
    )
    config.addinivalue_line(
        "markers", "concurrent: mark test as concurrent test"
    )