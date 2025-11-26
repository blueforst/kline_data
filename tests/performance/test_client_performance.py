"""
KlineClient Performance Tests

Comprehensive performance testing for KlineClient data acquisition with different
data volumes, time ranges, and configurations.
"""

import pytest
import pandas as pd
import numpy as np
import time
import gc
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from pathlib import Path

from sdk.client import KlineClient
from storage.data_source_strategy import DataSourceStrategy
from storage.metadata_manager import MetadataManager


class TestKlineClientPerformance:
    """Test KlineClient data acquisition performance"""

    @pytest.fixture
    def client(self, temp_dir):
        """Create KlineClient instance for testing"""
        # Create mock config
        config = Mock()
        config.storage.data_dir = str(temp_dir)
        config.download.enabled = True
        config.download.rate_limit = 100
        config.resample.enabled = True
        config.cache.enabled = True
        config.cache.max_size_mb = 100

        return KlineClient(config)

    @pytest.fixture
    def populated_storage(self, temp_dir, large_ohlcv_dataset):
        """Create populated storage with test data"""
        # Create test data file
        file_path = temp_dir / "binance_BTC_USDT_1h.parquet"
        large_ohlcv_dataset.to_parquet(file_path, index=False, compression='snappy')

        # Create metadata
        metadata = {
            'exchange': 'binance',
            'symbol': 'BTC/USDT',
            'timeframe': '1h',
            'first_timestamp': large_ohlcv_dataset['timestamp'].min(),
            'last_timestamp': large_ohlcv_dataset['timestamp'].max(),
            'total_records': len(large_ohlcv_dataset),
            'file_size_bytes': file_path.stat().st_size,
            'compression': 'snappy',
            'created_at': datetime.now()
        }

        metadata_file = temp_dir / "binance_BTC_USDT_1h_metadata.json"
        import json
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, default=str)

        return {
            'data_file': file_path,
            'metadata': metadata
        }

    @pytest.mark.benchmark(group="client")
    @pytest.mark.parametrize("data_size", [
        ('small', 24),      # 1 day
        ('medium', 168),    # 1 week
        ('large', 720),     # 1 month
        ('xlarge', 8760)    # 1 year
    ])
    def test_get_kline_performance_by_size(self, client, populated_storage, perf_monitor, data_size):
        """Test KlineClient.get_kline performance with different data sizes"""
        size_name, hours = data_size

        start_time = datetime(2022, 1, 1)
        end_time = start_time + timedelta(hours=hours)

        # Periodically monitor CPU during large operations
        if hours > 168:  # For larger datasets
            import threading
            def monitor_cpu():
                for _ in range(10):
                    perf_monitor.sample_cpu()
                    time.sleep(0.1)
            cpu_thread = threading.Thread(target=monitor_cpu)
            cpu_thread.start()

        # Execute the query
        result = client.get_kline(
            exchange='binance',
            symbol='BTC/USDT',
            start_time=start_time,
            end_time=end_time,
            interval='1h',
            auto_strategy=False,
            force_strategy='local'
        )

        # Wait for CPU monitoring to finish
        if hours > 168:
            cpu_thread.join()

        # Get performance metrics
        metrics = perf_monitor.get_metrics()

        # Assertions
        assert not result.empty
        assert len(result) == hours

        # Calculate data size for performance validation
        data_size_mb = len(result) * 8 * 6 / 1024 / 1024  # Estimate
        memory_ratio = metrics['memory_delta_mb'] / data_size_mb if data_size_mb > 0 else 0

        # Performance assertions based on data size
        if size_name == 'small':
            assert metrics['duration'] < 0.1, f"Small query too slow: {metrics['duration']*1000:.1f}ms"
            assert memory_ratio < 3.0, f"Small query memory ratio too high: {memory_ratio:.1f}"
        elif size_name == 'medium':
            assert metrics['duration'] < 0.5, f"Medium query too slow: {metrics['duration']*1000:.1f}ms"
            assert memory_ratio < 4.0, f"Medium query memory ratio too high: {memory_ratio:.1f}"
        elif size_name == 'large':
            assert metrics['duration'] < 2.0, f"Large query too slow: {metrics['duration']*1000:.1f}ms"
            assert memory_ratio < 5.0, f"Large query memory ratio too high: {memory_ratio:.1f}"

        return {
            'result_size': len(result),
            'duration': metrics['duration'],
            'memory_delta_mb': metrics['memory_delta_mb'],
            'memory_ratio': memory_ratio
        }

    @pytest.mark.benchmark(group="client")
    @pytest.mark.parametrize("indicator_count", [1, 5, 10, 20])
    def test_get_kline_with_indicators_performance(self, client, populated_storage, perf_monitor, indicator_count):
        """Test performance when calculating multiple indicators"""
        # Generate indicator configurations
        indicators = []
        base_indicators = ['SMA', 'EMA', 'RSI', 'MACD', 'BB', 'ATR', 'OBV', 'STOCH', 'ADX', 'CCI']

        for i in range(min(indicator_count, len(base_indicators))):
            indicators.append(base_indicators[i])

        start_time = datetime(2022, 1, 1)
        end_time = datetime(2022, 1, 31)  # 1 month

        # Execute query with indicators
        result = client.get_kline(
            exchange='binance',
            symbol='BTC/USDT',
            start_time=start_time,
            end_time=end_time,
            interval='1h',
            auto_strategy=False,
            force_strategy='local',
            with_indicators=indicators
        )

        metrics = perf_monitor.get_metrics()

        # Assertions
        assert not result.empty
        expected_records = 31 * 24  # 31 days * 24 hours
        assert len(result) == expected_records

        # Check indicator columns
        indicator_cols = [col for col in result.columns
                         if any(ind in col for ind in indicators)]
        assert len(indicator_cols) > 0 if indicators else True

        # Performance assertions
        throughput = len(result) / metrics['duration']
        assert throughput > 1000, f"Throughput too low: {throughput:.0f} records/sec"

        return {
            'result_size': len(result),
            'indicator_count': len(indicators),
            'duration': metrics['duration'],
            'throughput': throughput,
            'memory_delta_mb': metrics['memory_delta_mb']
        }

    @pytest.mark.benchmark(group="client")
    def test_auto_strategy_performance(self, client, populated_storage, perf_monitor):
        """Test automatic strategy selection performance"""
        start_time = datetime(2022, 1, 1)
        end_time = datetime(2022, 1, 31)

        # Mock metadata manager
        with patch.object(client.metadata_mgr, 'metadata_exists', return_value=True), \
             patch.object(client.metadata_mgr, 'get_metadata', return_value={
                 'first_timestamp': start_time - timedelta(days=1),
                 'last_timestamp': end_time + timedelta(days=1),
                 'total_records': 744,  # 31 days * 24 hours
                 'timeframe': '1h'
             }):

            result = client.get_kline(
                exchange='binance',
                symbol='BTC/USDT',
                start_time=start_time,
                end_time=end_time,
                interval='1h',
                auto_strategy=True
            )

        metrics = perf_monitor.get_metrics()

        # Assertions
        assert not result.empty
        assert len(result) == 31 * 24

        # Auto strategy should be fast (decision making overhead minimal)
        assert metrics['duration'] < 1.0, f"Auto strategy too slow: {metrics['duration']*1000:.1f}ms"

        return {
            'result_size': len(result),
            'duration': metrics['duration'],
            'memory_delta_mb': metrics['memory_delta_mb']
        }

    @pytest.mark.benchmark(group="client")
    def test_concurrent_requests_performance(self, client, populated_storage, perf_monitor):
        """Test performance under concurrent requests"""
        import threading
        from concurrent.futures import ThreadPoolExecutor, as_completed

        # Define multiple query scenarios
        queries = [
            {'start': datetime(2022, 1, 1), 'end': datetime(2022, 1, 7), 'name': 'week1'},
            {'start': datetime(2022, 1, 8), 'end': datetime(2022, 1, 14), 'name': 'week2'},
            {'start': datetime(2022, 1, 15), 'end': datetime(2022, 1, 21), 'name': 'week3'},
            {'start': datetime(2022, 1, 22), 'end': datetime(2022, 1, 28), 'name': 'week4'},
            {'start': datetime(2022, 2, 1), 'end': datetime(2022, 2, 7), 'name': 'week5'},
        ]

        def execute_query(query_info):
            """Execute single query"""
            start_time = time.perf_counter()

            result = client.get_kline(
                exchange='binance',
                symbol='BTC/USDT',
                start_time=query_info['start'],
                end_time=query_info['end'],
                interval='1h',
                auto_strategy=False,
                force_strategy='local'
            )

            duration = time.perf_counter() - start_time
            return {
                'name': query_info['name'],
                'result_size': len(result),
                'duration': duration,
                'data': result
            }

        # Execute queries concurrently
        concurrent_results = []
        with ThreadPoolExecutor(max_workers=5) as executor:
            future_to_query = {executor.submit(execute_query, q): q for q in queries}

            for future in as_completed(future_to_query):
                try:
                    result = future.result()
                    concurrent_results.append(result)
                except Exception as exc:
                    pytest.fail(f"Query failed: {exc}")

        metrics = perf_monitor.get_metrics()

        # Assertions
        assert len(concurrent_results) == len(queries)

        total_records = sum(r['result_size'] for r in concurrent_results)
        avg_duration = np.mean([r['duration'] for r in concurrent_results])
        total_duration = max(r['duration'] for r in concurrent_results)

        # Concurrent execution should be faster than serial
        # (This is a rough check - actual speedup depends on I/O vs CPU bound)
        assert total_records > 0
        assert total_duration < avg_duration * len(queries) * 0.8, "Concurrent execution too slow"

        return {
            'total_records': total_records,
            'concurrent_queries': len(queries),
            'avg_duration': avg_duration,
            'total_duration': total_duration,
            'speedup_ratio': (avg_duration * len(queries)) / total_duration if total_duration > 0 else 0
        }

    @pytest.mark.benchmark(group="client")
    @pytest.mark.memory
    def test_memory_efficiency_multiple_calls(self, client, populated_storage, perf_monitor):
        """Test memory efficiency across multiple sequential calls"""
        results = []

        # Execute multiple queries sequentially
        for week in range(1, 11):  # 10 weeks
            start_time = datetime(2022, 1, 1) + timedelta(weeks=week-1)
            end_time = start_time + timedelta(weeks=1)

            result = client.get_kline(
                exchange='binance',
                symbol='BTC/USDT',
                start_time=start_time,
                end_time=end_time,
                interval='1h',
                auto_strategy=False,
                force_strategy='local'
            )

            results.append({
                'week': week,
                'record_count': len(result),
                'memory_at_call': perf_monitor.process.memory_info().rss / 1024 / 1024
            })

            # Clear reference to result
            del result
            gc.collect()  # Force garbage collection

        metrics = perf_monitor.get_metrics()

        # Calculate memory growth
        memory_growth = results[-1]['memory_at_call'] - results[0]['memory_at_call']
        total_records = sum(r['record_count'] for r in results)

        # Assertions
        assert len(results) == 10
        assert total_records == 10 * 7 * 24  # 10 weeks * 7 days * 24 hours

        # Memory growth should be reasonable (less than 100MB for all queries)
        assert memory_growth < 100, f"Memory growth too high: {memory_growth:.1f}MB"

        return {
            'total_records': total_records,
            'query_count': len(results),
            'memory_growth_mb': memory_growth,
            'memory_per_query_mb': memory_growth / len(results),
            'final_memory_mb': metrics['current_memory_mb']
        }

    @pytest.mark.benchmark(group="client")
    def test_large_time_range_performance(self, client, populated_storage, perf_monitor):
        """Test performance with very large time ranges"""
        # Test with 1 year of data
        start_time = datetime(2022, 1, 1)
        end_time = datetime(2023, 1, 1)

        # Monitor CPU during large operation
        import threading
        def monitor_cpu():
            for _ in range(20):
                perf_monitor.sample_cpu()
                time.sleep(0.1)
        cpu_thread = threading.Thread(target=monitor_cpu)
        cpu_thread.start()

        result = client.get_kline(
            exchange='binance',
            symbol='BTC/USDT',
            start_time=start_time,
            end_time=end_time,
            interval='1h',
            auto_strategy=False,
            force_strategy='local'
        )

        cpu_thread.join()
        metrics = perf_monitor.get_metrics()

        # Assertions
        assert not result.empty
        expected_records = 365 * 24  # 1 year * 24 hours (approx)
        assert len(result) >= expected_records * 0.95  # Allow some variance

        # Performance assertions for large datasets
        throughput = len(result) / metrics['duration']
        assert throughput > 5000, f"Large query throughput too low: {throughput:.0f} records/sec"

        # Memory efficiency check
        data_size_mb = len(result) * 8 * 6 / 1024 / 1024
        memory_ratio = metrics['memory_delta_mb'] / data_size_mb if data_size_mb > 0 else 0
        assert memory_ratio < 5.0, f"Memory ratio too high for large query: {memory_ratio:.1f}"

        return {
            'result_size': len(result),
            'duration': metrics['duration'],
            'throughput': throughput,
            'memory_delta_mb': metrics['memory_delta_mb'],
            'memory_ratio': memory_ratio,
            'avg_cpu_percent': metrics['avg_cpu_percent']
        }

    @pytest.mark.benchmark(group="client")
    def test_different_timeframes_performance(self, client, temp_dir, perf_monitor):
        """Test performance across different timeframes"""
        # Create data for different timeframes
        timeframes = ['1m', '5m', '15m', '1h', '4h', '1d']
        results = {}

        base_data = pd.DataFrame({
            'timestamp': pd.date_range('2022-01-01', periods=1440, freq='1m'),  # 1 day of minute data
            'open': np.random.uniform(45000, 55000, 1440),
            'high': np.random.uniform(45000, 55000, 1440),
            'low': np.random.uniform(45000, 55000, 1440),
            'close': np.random.uniform(45000, 55000, 1440),
            'volume': np.random.randint(100000, 1000000, 1440)
        })

        for timeframe in timeframes:
            # Create test data file for this timeframe
            file_path = temp_dir / f"binance_BTC_USDT_{timeframe}.parquet"
            base_data.to_parquet(file_path, index=False)

            # Create metadata
            metadata = {
                'exchange': 'binance',
                'symbol': 'BTC/USDT',
                'timeframe': timeframe,
                'first_timestamp': base_data['timestamp'].min(),
                'last_timestamp': base_data['timestamp'].max(),
                'total_records': len(base_data)
            }

            import json
            metadata_file = temp_dir / f"binance_BTC_USDT_{timeframe}_metadata.json"
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, default=str)

        # Test each timeframe
        for timeframe in timeframes:
            start_time = datetime(2022, 1, 1)
            end_time = datetime(2022, 1, 2)  # 1 day

            query_start = time.perf_counter()
            result = client.get_kline(
                exchange='binance',
                symbol='BTC/USDT',
                start_time=start_time,
                end_time=end_time,
                interval=timeframe,
                auto_strategy=False,
                force_strategy='local'
            )
            query_duration = time.perf_counter() - query_start

            results[timeframe] = {
                'record_count': len(result),
                'duration': query_duration,
                'throughput': len(result) / query_duration if query_duration > 0 else 0
            }

            # Clean up files for next iteration
            file_path = temp_dir / f"binance_BTC_USDT_{timeframe}.parquet"
            metadata_file = temp_dir / f"binance_BTC_USDT_{timeframe}_metadata.json"
            if file_path.exists():
                file_path.unlink()
            if metadata_file.exists():
                metadata_file.unlink()

        metrics = perf_monitor.get_metrics()

        # Assertions
        assert len(results) == len(timeframes)

        # All timeframes should have reasonable performance
        for timeframe, result in results.items():
            assert result['record_count'] > 0, f"No records for {timeframe}"
            assert result['duration'] < 1.0, f"{timeframe} query too slow: {result['duration']*1000:.1f}ms"
            assert result['throughput'] > 100, f"{timeframe} throughput too low: {result['throughput']:.0f} records/sec"

        return {
            'timeframe_results': results,
            'total_duration': metrics['duration'],
            'memory_delta_mb': metrics['memory_delta_mb']
        }