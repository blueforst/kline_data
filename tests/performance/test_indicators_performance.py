"""
Technical Indicators Performance Tests

Comprehensive performance testing for technical indicators calculation including
CPU usage monitoring, batch processing efficiency, and computational complexity.
"""

import pytest
import pandas as pd
import numpy as np
import time
import gc
import threading
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from unittest.mock import patch

from kline_data.indicators.manager import IndicatorManager
from kline_data.indicators.base import IndicatorBase


class TestIndicatorsPerformance:
    """Test technical indicators calculation performance"""

    @pytest.fixture
    def indicator_manager(self):
        """Create IndicatorManager instance"""
        return IndicatorManager()

    @pytest.fixture
    def small_dataset(self):
        """Create small dataset for indicator testing"""
        np.random.seed(42)
        periods = 500  # ~2 years of daily data
        timestamps = pd.date_range('2020-01-01', periods=periods, freq='1D')

        # Generate realistic price series
        base_price = 50000.0
        returns = np.random.normal(0.0005, 0.02, periods)
        prices = [base_price]

        for ret in returns:
            prices.append(max(prices[-1] * (1 + ret), 1.0))

        prices = prices[1:]

        data = []
        for i, ts in enumerate(timestamps):
            current_price = prices[i]
            open_price = prices[i-1] if i > 0 else current_price
            close_price = current_price

            high = max(open_price, close_price) * (1 + np.random.uniform(0, 0.02))
            low = min(open_price, close_price) * (1 - np.random.uniform(0, 0.02))
            volume = np.random.randint(1000000, 10000000)

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
    def large_dataset(self):
        """Create large dataset for performance testing"""
        np.random.seed(42)
        periods = 100000  # ~4 years of hourly data
        timestamps = pd.date_range('2020-01-01', periods=periods, freq='1h')

        base_price = 50000.0
        volatility = 0.001  # Hourly volatility

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

            volume = np.random.randint(100000, 1000000)

            data.append({
                'timestamp': ts,
                'open': round(open_price, 2),
                'high': round(high, 2),
                'low': round(low, 2),
                'close': round(close_price, 2),
                'volume': volume
            })

        return pd.DataFrame(data)

    @pytest.mark.benchmark(group="indicators")
    @pytest.mark.parametrize("indicator_name,period", [
        ('SMA', 20),
        ('EMA', 50),
        ('RSI', 14),
        ('MACD', None),
        ('BB', 20),
        ('ATR', 14),
        ('OBV', None),
        ('STOCH', 14),
        ('ADX', 14),
        ('CCI', 20)
    ])
    def test_single_indicator_performance(self, indicator_manager, small_dataset, perf_monitor, indicator_name, period):
        """Test performance of individual indicator calculations"""
        # CPU monitoring during calculation
        cpu_samples = []

        def monitor_cpu():
            for _ in range(20):
                perf_monitor.sample_cpu()
                time.sleep(0.05)

        cpu_thread = threading.Thread(target=monitor_cpu)
        cpu_thread.start()

        # Calculate indicator
        start_time = time.perf_counter()

        if period:
            if indicator_name == 'BB':
                result = indicator_manager.calculate(
                    data=small_dataset,
                    indicator_name=indicator_name,
                    period=period,
                    std_dev=2
                )
            elif indicator_name == 'STOCH':
                result = indicator_manager.calculate(
                    data=small_dataset,
                    indicator_name=indicator_name,
                    k_period=period,
                    d_period=3
                )
            else:
                result = indicator_manager.calculate(
                    data=small_dataset,
                    indicator_name=indicator_name,
                    period=period
                )
        else:
            if indicator_name == 'MACD':
                result = indicator_manager.calculate(
                    data=small_dataset,
                    indicator_name=indicator_name,
                    fast_period=12,
                    slow_period=26,
                    signal_period=9
                )
            else:  # OBV
                result = indicator_manager.calculate(
                    data=small_dataset,
                    indicator_name=indicator_name
                )

        calculation_time = time.perf_counter() - start_time
        cpu_thread.join()
        metrics = perf_monitor.get_metrics()

        # Find indicator columns
        if indicator_name == 'MACD':
            indicator_cols = [col for col in result.columns if 'MACD' in col]
        elif indicator_name == 'BB':
            indicator_cols = [col for col in result.columns if 'BB' in col]
        elif indicator_name == 'STOCH':
            indicator_cols = [col for col in result.columns if any(x in col for x in ['K', 'D'])]
        else:
            indicator_cols = [col for col in result.columns if indicator_name in col]

        # Assertions
        assert not result.empty
        assert len(indicator_cols) > 0, f"No {indicator_name} columns found"

        # Performance assertions
        throughput = len(small_dataset) / calculation_time
        assert throughput > 1000, f"{indicator_name} calculation too slow: {throughput:.0f} records/sec"

        # CPU efficiency check
        avg_cpu = metrics['avg_cpu_percent']
        assert avg_cpu < 80, f"{indicator_name} CPU usage too high: {avg_cpu:.1f}%"

        return {
            'indicator': indicator_name,
            'period': period,
            'calculation_time': calculation_time,
            'throughput': throughput,
            'avg_cpu_percent': avg_cpu,
            'memory_delta_mb': metrics['memory_delta_mb'],
            'indicator_columns': len(indicator_cols)
        }

    @pytest.mark.benchmark(group="indicators")
    @pytest.mark.parametrize("indicator_count", [1, 3, 5, 10, 15])
    def test_multiple_indicators_performance(self, indicator_manager, small_dataset, perf_monitor, indicator_count):
        """Test performance when calculating multiple indicators simultaneously"""
        # Define indicator configurations
        base_indicators = [
            {'name': 'SMA', 'period': 20},
            {'name': 'EMA', 'period': 50},
            {'name': 'RSI', 'period': 14},
            {'name': 'MACD', 'fast_period': 12, 'slow_period': 26, 'signal_period': 9},
            {'name': 'BB', 'period': 20, 'std_dev': 2},
            {'name': 'ATR', 'period': 14},
            {'name': 'OBV'},
            {'name': 'STOCH', 'k_period': 14, 'd_period': 3},
            {'name': 'ADX', 'period': 14},
            {'name': 'CCI', 'period': 20},
            {'name': 'WILLR', 'period': 14},
            {'name': 'MFI', 'period': 14},
            {'name': 'TSI', 'period': 25},
            {'name': 'UO'},
            {'name': 'AO'}
        ]

        indicators = base_indicators[:min(indicator_count, len(base_indicators))]

        # CPU monitoring
        cpu_samples = []
        def monitor_cpu():
            for _ in range(30):
                perf_monitor.sample_cpu()
                time.sleep(0.05)

        cpu_thread = threading.Thread(target=monitor_cpu)
        cpu_thread.start()

        # Calculate indicators
        start_time = time.perf_counter()
        result = indicator_manager.calculate_multiple(
            data=small_dataset,
            indicators=indicators
        )
        calculation_time = time.perf_counter() - start_time

        cpu_thread.join()
        metrics = perf_monitor.get_metrics()

        # Find all indicator columns
        base_cols = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        indicator_cols = [col for col in result.columns if col not in base_cols]

        # Assertions
        assert not result.empty
        assert len(result) == len(small_dataset)

        # Should have indicator columns
        if indicators:
            assert len(indicator_cols) > 0, "No indicator columns calculated"

        # Performance assertions
        throughput = len(small_dataset) / calculation_time
        expected_throughput = 1000 / (1 + indicator_count * 0.1)  # Expect some degradation with more indicators
        assert throughput > expected_throughput, f"Multiple indicators too slow: {throughput:.0f} records/sec"

        # Memory efficiency
        memory_per_indicator = metrics['memory_delta_mb'] / len(indicators) if indicators else 0
        assert memory_per_indicator < 5, f"Memory per indicator too high: {memory_per_indicator:.1f}MB"

        return {
            'indicator_count': len(indicators),
            'calculation_time': calculation_time,
            'throughput': throughput,
            'avg_cpu_percent': metrics['avg_cpu_percent'],
            'memory_delta_mb': metrics['memory_delta_mb'],
            'memory_per_indicator_mb': memory_per_indicator,
            'indicator_columns_count': len(indicator_cols)
        }

    @pytest.mark.benchmark(group="indicators")
    def test_large_dataset_indicator_performance(self, indicator_manager, large_dataset, perf_monitor):
        """Test indicator performance with large datasets"""
        # Select computationally intensive indicators
        indicators = [
            {'name': 'SMA', 'period': 50},
            {'name': 'EMA', 'period': 100},
            {'name': 'RSI', 'period': 14},
            {'name': 'MACD', 'fast_period': 12, 'slow_period': 26, 'signal_period': 9},
            {'name': 'BB', 'period': 20, 'std_dev': 2},
            {'name': 'ATR', 'period': 14}
        ]

        # Monitor CPU and memory
        cpu_samples = []
        memory_samples = []

        def monitor_resources():
            process = psutil.Process()
            for _ in range(50):
                perf_monitor.sample_cpu()
                memory_mb = process.memory_info().rss / 1024 / 1024
                memory_samples.append(memory_mb)
                time.sleep(0.1)

        import psutil
        monitor_thread = threading.Thread(target=monitor_resources)
        monitor_thread.start()

        # Calculate indicators on large dataset
        start_time = time.perf_counter()
        result = indicator_manager.calculate_multiple(
            data=large_dataset,
            indicators=indicators
        )
        calculation_time = time.perf_counter() - start_time

        monitor_thread.join()
        metrics = perf_monitor.get_metrics()

        # Analyze resource usage
        memory_growth = max(memory_samples) - min(memory_samples) if memory_samples else 0

        # Assertions
        assert not result.empty
        assert len(result) == len(large_dataset)

        # Find indicator columns
        base_cols = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        indicator_cols = [col for col in result.columns if col not in base_cols]
        assert len(indicator_cols) > 0, "No indicators calculated for large dataset"

        # Performance assertions
        throughput = len(large_dataset) / calculation_time
        assert throughput > 50000, f"Large dataset throughput too low: {throughput:.0f} records/sec"

        # Memory efficiency for large datasets
        memory_per_record = memory_growth / len(large_dataset) if len(large_dataset) > 0 else 0
        assert memory_per_record < 0.01, f"Memory per record too high: {memory_per_record:.6f}MB"

        # CPU efficiency
        avg_cpu = metrics['avg_cpu_percent']
        assert avg_cpu < 90, f"Large dataset CPU usage too high: {avg_cpu:.1f}%"

        return {
            'dataset_size': len(large_dataset),
            'indicator_count': len(indicators),
            'calculation_time': calculation_time,
            'throughput': throughput,
            'avg_cpu_percent': avg_cpu,
            'memory_growth_mb': memory_growth,
            'memory_per_record_mb': memory_per_record,
            'indicator_columns_count': len(indicator_cols)
        }

    @pytest.mark.benchmark(group="indicators")
    def test_concurrent_indicator_calculation(self, indicator_manager, small_dataset, perf_monitor):
        """Test concurrent calculation of different indicators"""
        # Define separate indicator groups for parallel processing
        indicator_groups = [
            [
                {'name': 'SMA', 'period': 20},
                {'name': 'EMA', 'period': 50}
            ],
            [
                {'name': 'RSI', 'period': 14},
                {'name': 'MACD', 'fast_period': 12, 'slow_period': 26, 'signal_period': 9}
            ],
            [
                {'name': 'BB', 'period': 20, 'std_dev': 2},
                {'name': 'ATR', 'period': 14}
            ]
        ]

        def calculate_indicator_group(group_data, group_id):
            """Calculate a group of indicators"""
            start_time = time.perf_counter()
            result = indicator_manager.calculate_multiple(
                data=group_data.copy(),
                indicators=indicator_groups[group_id]
            )
            calculation_time = time.perf_counter() - start_time

            return {
                'group_id': group_id,
                'result': result,
                'calculation_time': calculation_time,
                'indicator_count': len(indicator_groups[group_id])
            }

        # Sequential calculation baseline
        sequential_start = time.perf_counter()
        sequential_results = []
        for i in range(len(indicator_groups)):
            result = calculate_indicator_group(small_dataset, i)
            sequential_results.append(result)
        sequential_time = time.perf_counter() - sequential_start

        # Concurrent calculation
        concurrent_start = time.perf_counter()
        concurrent_results = []

        with ThreadPoolExecutor(max_workers=3) as executor:
            future_to_group = {
                executor.submit(calculate_indicator_group, small_dataset, i): i
                for i in range(len(indicator_groups))
            }

            for future in future_to_group:
                try:
                    result = future.result()
                    concurrent_results.append(result)
                except Exception as exc:
                    pytest.fail(f"Concurrent indicator calculation failed: {exc}")

        concurrent_time = time.perf_counter() - concurrent_start
        metrics = perf_monitor.get_metrics()

        # Calculate speedup
        speedup = sequential_time / concurrent_time if concurrent_time > 0 else 0

        # Assertions
        assert len(concurrent_results) == len(sequential_results), "Different number of results"
        assert speedup > 1.2, f"Concurrent calculation not efficient: {speedup:.2f}x speedup"

        # Memory should be reasonable during concurrent processing
        assert metrics['memory_delta_mb'] < 50, f"Memory usage too high: {metrics['memory_delta_mb']:.1f}MB"

        # CPU should be utilized efficiently
        assert metrics['avg_cpu_percent'] > 50, f"CPU utilization too low: {metrics['avg_cpu_percent']:.1f}%"

        return {
            'sequential_time': sequential_time,
            'concurrent_time': concurrent_time,
            'speedup': speedup,
            'group_count': len(indicator_groups),
            'memory_delta_mb': metrics['memory_delta_mb'],
            'avg_cpu_percent': metrics['avg_cpu_percent']
        }

    @pytest.mark.benchmark(group="indicators")
    def test_indicator_memory_efficiency(self, indicator_manager, large_dataset, perf_monitor):
        """Test memory efficiency during indicator calculations"""
        # Define memory-intensive indicators
        indicators = [
            {'name': 'SMA', 'period': 20},
            {'name': 'EMA', 'period': 50},
            {'name': 'RSI', 'period': 14},
            {'name': 'MACD', 'fast_period': 12, 'slow_period': 26, 'signal_period': 9},
            {'name': 'BB', 'period': 20, 'std_dev': 2},
            {'name': 'ATR', 'period': 14},
            {'name': 'STOCH', 'k_period': 14, 'd_period': 3},
            {'name': 'ADX', 'period': 14}
        ]

        # Monitor memory usage during calculation
        memory_usage = []
        import psutil
        process = psutil.Process()

        def sample_memory():
            memory_mb = process.memory_info().rss / 1024 / 1024
            memory_usage.append(memory_mb)

        # Sample memory before calculation
        initial_memory = process.memory_info().rss / 1024 / 1024
        sample_memory()

        # Calculate indicators
        start_time = time.perf_counter()
        result = indicator_manager.calculate_multiple(
            data=large_dataset,
            indicators=indicators
        )
        calculation_time = time.perf_counter() - start_time

        # Sample memory after calculation
        final_memory = process.memory_info().rss / 1024 / 1024
        sample_memory()

        # Force cleanup and measure again
        del result
        gc.collect()
        cleanup_memory = process.memory_info().rss / 1024 / 1024

        metrics = perf_monitor.get_metrics()

        # Calculate memory statistics
        peak_memory = max(memory_usage)
        memory_growth = peak_memory - initial_memory
        memory_leak = cleanup_memory - initial_memory

        # Calculate data size for comparison
        data_size_mb = len(large_dataset) * 8 * 6 / 1024 / 1024
        memory_ratio = memory_growth / data_size_mb if data_size_mb > 0 else 0

        # Assertions
        assert memory_growth < 200, f"Memory growth too high: {memory_growth:.1f}MB"
        assert memory_ratio < 2.0, f"Memory ratio too high: {memory_ratio:.1f}x data size"
        assert memory_leak < 20, f"Potential memory leak: {memory_leak:.1f}MB"

        # Performance should remain reasonable
        throughput = len(large_dataset) / calculation_time if calculation_time > 0 else 0
        assert throughput > 10000, f"Throughput too low: {throughput:.0f} records/sec"

        return {
            'indicator_count': len(indicators),
            'dataset_size': len(large_dataset),
            'calculation_time': calculation_time,
            'throughput': throughput,
            'initial_memory_mb': initial_memory,
            'peak_memory_mb': peak_memory,
            'memory_growth_mb': memory_growth,
            'memory_ratio': memory_ratio,
            'memory_leak_mb': memory_leak
        }

    @pytest.mark.benchmark(group="indicators")
    def test_indicator_calculation_complexity(self, indicator_manager, perf_monitor):
        """Test computational complexity scaling with dataset size"""
        # Test with different dataset sizes
        sizes = [1000, 5000, 10000, 50000]
        results = []

        # Use a fixed set of indicators for complexity testing
        indicators = [
            {'name': 'SMA', 'period': 20},
            {'name': 'EMA', 'period': 50},
            {'name': 'RSI', 'period': 14},
            {'name': 'BB', 'period': 20, 'std_dev': 2}
        ]

        for size in sizes:
            # Generate dataset of specified size
            np.random.seed(42)
            data = pd.DataFrame({
                'timestamp': pd.date_range('2020-01-01', periods=size, freq='1h'),
                'open': np.random.uniform(45000, 55000, size),
                'high': np.random.uniform(45000, 55000, size),
                'low': np.random.uniform(45000, 55000, size),
                'close': np.random.uniform(45000, 55000, size),
                'volume': np.random.randint(100000, 1000000, size)
            })

            # Measure calculation time
            start_time = time.perf_counter()
            result = indicator_manager.calculate_multiple(
                data=data,
                indicators=indicators
            )
            calculation_time = time.perf_counter() - start_time

            # Calculate throughput
            throughput = size / calculation_time if calculation_time > 0 else 0

            results.append({
                'dataset_size': size,
                'calculation_time': calculation_time,
                'throughput': throughput
            })

        # Analyze complexity scaling
        throughputs = [r['throughput'] for r in results]
        avg_throughput = np.mean(throughputs)
        throughput_std = np.std(throughputs)

        # Assert reasonable complexity (throughput shouldn't degrade too much with size)
        throughput_degradation = (throughputs[0] - throughputs[-1]) / throughputs[0] if throughputs[0] > 0 else 0
        assert throughput_degradation < 0.5, f"Throughput degradation too high: {throughput_degradation:.2%}"

        # Assert minimum throughput
        assert min(throughputs) > 5000, f"Minimum throughput too low: {min(throughputs):.0f} records/sec"

        return {
            'size_results': results,
            'avg_throughput': avg_throughput,
            'throughput_std': throughput_std,
            'throughput_degradation': throughput_degradation,
            'complexity_factor': results[-1]['calculation_time'] / results[0]['calculation_time'] if results[0]['calculation_time'] > 0 else 0
        }

    @pytest.mark.benchmark(group="indicators")
    def test_custom_indicator_performance(self, perf_monitor):
        """Test performance of custom indicator implementations"""
        from kline_data.indicators.base import IndicatorBase

        # Create a custom indicator for testing
        class CustomMomentumIndicator(IndicatorBase):
            """Custom momentum indicator for performance testing"""

            def calculate(self, data, period=20):
                df = data.copy()
                df['momentum'] = (df['close'] / df['close'].shift(period) - 1) * 100
                df['momentum_signal'] = np.where(df['momentum'] > 0, 1, -1)
                return df

            def validate_params(self, period):
                return period > 0 and period < len(data)

        # Register custom indicator
        indicator_manager = IndicatorManager()
        custom_indicator = CustomMomentumIndicator()

        # Generate test data
        np.random.seed(42)
        test_data = pd.DataFrame({
            'timestamp': pd.date_range('2020-01-01', periods=10000, freq='1h'),
            'open': np.random.uniform(45000, 55000, 10000),
            'high': np.random.uniform(45000, 55000, 10000),
            'low': np.random.uniform(45000, 55000, 10000),
            'close': np.random.uniform(45000, 55000, 10000),
            'volume': np.random.randint(100000, 1000000, 10000)
        })

        # Test custom indicator performance
        start_time = time.perf_counter()
        result = custom_indicator.calculate(test_data, period=20)
        calculation_time = time.perf_counter() - start_time

        metrics = perf_monitor.get_metrics()

        # Assertions
        assert not result.empty
        assert 'momentum' in result.columns
        assert 'momentum_signal' in result.columns
        assert len(result) == len(test_data)

        # Performance assertions
        throughput = len(test_data) / calculation_time
        assert throughput > 50000, f"Custom indicator too slow: {throughput:.0f} records/sec"

        # Memory efficiency
        memory_per_record = metrics['memory_delta_mb'] / len(test_data) if len(test_data) > 0 else 0
        assert memory_per_record < 0.001, f"Custom indicator memory per record too high: {memory_per_record:.6f}MB"

        return {
            'indicator_name': 'CustomMomentum',
            'dataset_size': len(test_data),
            'calculation_time': calculation_time,
            'throughput': throughput,
            'memory_delta_mb': metrics['memory_delta_mb'],
            'memory_per_record_mb': memory_per_record
        }