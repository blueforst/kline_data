"""
Data Download and Resampling Performance Tests

Comprehensive performance testing for data download and resampling operations
including network efficiency, computational performance, and memory usage.
"""

import pytest
import pandas as pd
import numpy as np
import time
import threading
from datetime import datetime, timedelta
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import Mock, patch, AsyncMock
import psutil
import tempfile

from kline_data.storage.downloader import DownloadManager
from kline_data.resampler.kline_resampler import KlineResampler
from kline_data.resampler.timeframe import Timeframe
from kline_data.storage.fetcher import DataFetcher


class TestDownloadResamplePerformance:
    """Test data download and resampling performance"""

    @pytest.fixture
    def download_manager(self, temp_dir):
        """Create DownloadManager instance"""
        config = Mock()
        config.storage.data_dir = str(temp_dir)
        config.download.enabled = True
        config.download.rate_limit = 100
        config.download.max_concurrent = 3
        config.download.retry_attempts = 3
        config.download.timeout_seconds = 30
        config.download.chunk_size = 1000

        return DownloadManager(config)

    @pytest.fixture
    def resampler(self):
        """Create KlineResampler instance"""
        config = Mock()
        config.resample.enabled = True
        config.resample.cache_intermediate = True
        config.resample.memory_limit_mb = 500

        return KlineResampler(config)

    @pytest.fixture
    def data_fetcher(self, temp_dir):
        """Create DataFetcher instance"""
        config = Mock()
        config.storage.data_dir = str(temp_dir)

        return DataFetcher(config)

    @pytest.fixture
    def mock_ccxt_exchange(self):
        """Mock CCXT exchange with realistic data generation"""
        exchange = Mock()
        exchange.name = 'binance'
        exchange.rateLimit = 100
        exchange.has = {'fetchOHLCV': True}

        def mock_fetch_ohlcv(symbol, timeframe, since=None, limit=None, params=None):
            # Simulate network latency (10-50ms)
            time.sleep(0.01 + np.random.uniform(0, 0.04))

            # Generate realistic OHLCV data
            timeframe_seconds = {
                '1m': 60, '5m': 300, '15m': 900, '1h': 3600,
                '4h': 14400, '1d': 86400, '1w': 604800
            }.get(timeframe, 3600)

            now = int(datetime.now().timestamp() * 1000)
            limit_count = min(limit or 100, 1000)

            # Generate base price for symbol
            base_prices = {
                'BTC/USDT': 50000,
                'ETH/USDT': 3000,
                'BNB/USDT': 300,
                'ADA/USDT': 0.5
            }
            base_price = base_prices.get(symbol, 100)

            data = []
            for i in range(limit_count):
                timestamp = now - (i * timeframe_seconds * 1000)

                # Generate realistic price movement
                price_change = np.random.normal(0, 0.002)  # 0.2% volatility
                current_price = base_price * (1 + price_change)

                # Generate OHLC with intrabar movement
                volatility = 0.005
                high = current_price * (1 + np.random.uniform(0, volatility))
                low = current_price * (1 - np.random.uniform(0, volatility))
                open_price = current_price * (1 + np.random.uniform(-volatility/2, volatility/2))
                close_price = current_price

                # Volume correlated with price movement
                volume_base = np.random.randint(10000, 100000)
                volume_multiplier = 1 + abs(price_change) * 10
                volume = int(volume_base * volume_multiplier)

                data.append([timestamp, open_price, high, low, close_price, volume])

            return data

        exchange.fetch_ohlcv = mock_fetch_ohlcv
        exchange.load_markets = Mock(return_value={})
        return exchange

    @pytest.fixture
    def large_minute_dataset(self):
        """Generate large minute dataset for resampling testing"""
        np.random.seed(42)
        periods = 43200  # 30 days of minute data
        timestamps = pd.date_range('2023-01-01', periods=periods, freq='1min')

        base_price = 50000.0
        volatility = 0.02 / np.sqrt(24*60)  # Daily volatility converted to minutes

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

            # Realistic intrabar movement
            intrabar_vol = 0.003
            high = max(open_price, close_price) * (1 + np.random.uniform(0, intrabar_vol))
            low = min(open_price, close_price) * (1 - np.random.uniform(0, intrabar_vol))

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

    @pytest.mark.benchmark(group="download")
    @pytest.mark.parametrize("symbol", ["BTC/USDT", "ETH/USDT", "BNB/USDT"])
    @pytest.mark.parametrize("timeframe", ["1m", "5m", "1h", "1d"])
    @pytest.mark.parametrize("limit", [100, 500, 1000])
    def test_download_performance_by_params(self, download_manager, mock_ccxt_exchange, perf_monitor, symbol, timeframe, limit):
        """Test download performance with different parameters"""
        with patch('ccxt.binance', return_value=mock_ccxt_exchange):
            # Monitor network I/O
            disk_io_before = psutil.disk_io_counters()
            start_time = time.perf_counter()

            # Perform download
            result = download_manager.download_data(
                exchange='binance',
                symbol=symbol,
                timeframe=timeframe,
                limit=limit
            )

            download_time = time.perf_counter() - start_time
            disk_io_after = psutil.disk_io_counters()

            metrics = perf_monitor.get_metrics()

            # Calculate performance metrics
            records_per_second = len(result) / download_time if download_time > 0 else 0

            if disk_io_before and disk_io_after:
                bytes_written = disk_io_after.write_bytes - disk_io_before.write_bytes
                write_ops = disk_io_after.write_count - disk_io_before.write_count
            else:
                bytes_written = write_ops = 0

            # File size
            if len(result) > 0:
                # Estimate file size (rough calculation)
                estimated_size = len(result) * 8 * 6  # 8 bytes per float * 6 columns
                size_per_record = estimated_size / len(result)
            else:
                estimated_size = size_per_record = 0

            # Assertions
            assert not result.empty, f"Download failed for {symbol} {timeframe}"
            assert len(result) == limit, f"Incorrect record count: {len(result)} vs {limit}"

            # Performance assertions
            assert records_per_second > 100, f"Download too slow: {records_per_second:.0f} records/sec"
            assert download_time < 10.0, f"Download took too long: {download_time:.2f}s"

            # Memory efficiency
            memory_per_record = metrics['memory_delta_mb'] / len(result) if len(result) > 0 else 0
            assert memory_per_record < 0.01, f"Memory per record too high: {memory_per_record:.6f}MB"

            return {
                'symbol': symbol,
                'timeframe': timeframe,
                'limit': limit,
                'download_time': download_time,
                'records_per_second': records_per_second,
                'bytes_written': bytes_written,
                'write_ops': write_ops,
                'estimated_size_bytes': estimated_size,
                'size_per_record_bytes': size_per_record,
                'memory_per_record_mb': memory_per_record,
                'memory_delta_mb': metrics['memory_delta_mb']
            }

    @pytest.mark.benchmark(group="download")
    def test_concurrent_download_performance(self, download_manager, mock_ccxt_exchange, perf_monitor):
        """Test concurrent download performance"""
        # Define download tasks
        download_tasks = [
            {'exchange': 'binance', 'symbol': 'BTC/USDT', 'timeframe': '1h', 'limit': 500},
            {'exchange': 'binance', 'symbol': 'ETH/USDT', 'timeframe': '1h', 'limit': 500},
            {'exchange': 'binance', 'symbol': 'BNB/USDT', 'timeframe': '1h', 'limit': 500},
            {'exchange': 'binance', 'symbol': 'BTC/USDT', 'timeframe': '4h', 'limit': 200},
            {'exchange': 'binance', 'symbol': 'ETH/USDT', 'timeframe': '4h', 'limit': 200},
        ]

        def download_task(task):
            """Execute single download task"""
            start_time = time.perf_counter()

            with patch('ccxt.binance', return_value=mock_ccxt_exchange):
                result = download_manager.download_data(
                    exchange=task['exchange'],
                    symbol=task['symbol'],
                    timeframe=task['timeframe'],
                    limit=task['limit']
                )

            task_time = time.perf_counter() - start_time

            return {
                'task': task,
                'record_count': len(result),
                'task_time': task_time,
                'throughput': len(result) / task_time if task_time > 0 else 0,
                'success': len(result) == task['limit']
            }

        # Sequential download baseline
        sequential_start = time.perf_counter()
        sequential_results = []
        for task in download_tasks:
            result = download_task(task)
            sequential_results.append(result)
        sequential_time = time.perf_counter() - sequential_start

        # Concurrent download
        concurrent_start = time.perf_counter()
        concurrent_results = []

        with ThreadPoolExecutor(max_workers=3) as executor:
            future_to_task = {
                executor.submit(download_task, task): task
                for task in download_tasks
            }

            for future in as_completed(future_to_task):
                try:
                    result = future.result()
                    concurrent_results.append(result)
                except Exception as exc:
                    task = future_to_task[future]
                    concurrent_results.append({
                        'task': task,
                        'record_count': 0,
                        'task_time': 0,
                        'throughput': 0,
                        'success': False,
                        'error': str(exc)
                    })

        concurrent_time = time.perf_counter() - concurrent_start
        metrics = perf_monitor.get_metrics()

        # Calculate performance metrics
        speedup = sequential_time / concurrent_time if concurrent_time > 0 else 0
        total_records_sequential = sum(r['record_count'] for r in sequential_results)
        total_records_concurrent = sum(r['record_count'] for r in concurrent_results)
        successful_concurrent = sum(1 for r in concurrent_results if r['success'])

        # Assertions
        assert len(concurrent_results) == len(download_tasks), "Not all tasks completed"
        assert successful_concurrent == len(download_tasks), "Some concurrent downloads failed"
        assert total_records_concurrent == total_records_sequential, "Record count mismatch"
        assert speedup > 1.5, f"Concurrent download not efficient: {speedup:.2f}x speedup"

        # Performance checks
        avg_throughput = np.mean([r['throughput'] for r in concurrent_results])
        assert avg_throughput > 50, f"Average throughput too low: {avg_throughput:.0f} records/sec"

        return {
            'task_count': len(download_tasks),
            'sequential_time': sequential_time,
            'concurrent_time': concurrent_time,
            'speedup': speedup,
            'total_records': total_records_concurrent,
            'avg_throughput': avg_throughput,
            'successful_tasks': successful_concurrent,
            'memory_delta_mb': metrics['memory_delta_mb']
        }

    @pytest.mark.benchmark(group="resample")
    @pytest.mark.parametrize("from_timeframe", ["1m", "5m", "15m", "1h"])
    @pytest.mark.parametrize("to_timeframe", ["5m", "15m", "1h", "4h", "1d"])
    def test_resampling_performance(self, resampler, large_minute_dataset, perf_monitor, from_timeframe, to_timeframe):
        """Test resampling performance between different timeframes"""
        # Skip invalid resampling combinations
        timeframe_order = ['1m', '5m', '15m', '1h', '4h', '1d']
        from_idx = timeframe_order.index(from_timeframe)
        to_idx = timeframe_order.index(to_timeframe)

        if from_idx >= to_idx:
            pytest.skip(f"Cannot resample from {from_timeframe} to {to_timeframe}")

        # Prepare data for from_timeframe (resample from minute data if needed)
        if from_timeframe == '1m':
            source_data = large_minute_dataset.copy()
        else:
            # Resample from minute to from_timeframe first
            source_data = resampler.resample(
                data=large_minute_dataset,
                target_timeframe=from_timeframe
            )

        # Monitor CPU during resampling
        cpu_samples = []
        def monitor_cpu():
            for _ in range(20):
                perf_monitor.sample_cpu()
                time.sleep(0.05)

        cpu_thread = threading.Thread(target=monitor_cpu)
        cpu_thread.start()

        # Perform resampling
        start_time = time.perf_counter()
        result = resampler.resample(
            data=source_data,
            target_timeframe=to_timeframe
        )
        resample_time = time.perf_counter() - start_time

        cpu_thread.join()
        metrics = perf_monitor.get_metrics()

        # Calculate performance metrics
        throughput = len(source_data) / resample_time if resample_time > 0 else 0
        compression_ratio = len(result) / len(source_data) if len(source_data) > 0 else 0
        records_per_second = len(result) / resample_time if resample_time > 0 else 0

        # Assertions
        assert not result.empty, f"Resampling failed from {from_timeframe} to {to_timeframe}"
        assert len(result) > 0, "Empty result after resampling"

        # Validate OHLCV aggregation
        assert 'timestamp' in result.columns
        assert 'open' in result.columns
        assert 'high' in result.columns
        assert 'low' in result.columns
        assert 'close' in result.columns
        assert 'volume' in result.columns

        # Performance assertions
        assert throughput > 10000, f"Resampling throughput too low: {throughput:.0f} source records/sec"
        assert records_per_second > 1000, f"Output rate too low: {records_per_second:.0f} output records/sec"

        # CPU should be utilized efficiently
        avg_cpu = metrics['avg_cpu_percent']
        assert avg_cpu > 20, f"CPU utilization too low: {avg_cpu:.1f}%"

        # Memory efficiency
        memory_per_record = metrics['memory_delta_mb'] / len(source_data) if len(source_data) > 0 else 0
        assert memory_per_record < 0.001, f"Memory per record too high: {memory_per_record:.6f}MB"

        return {
            'from_timeframe': from_timeframe,
            'to_timeframe': to_timeframe,
            'source_records': len(source_data),
            'output_records': len(result),
            'resample_time': resample_time,
            'throughput': throughput,
            'records_per_second': records_per_second,
            'compression_ratio': compression_ratio,
            'avg_cpu_percent': avg_cpu,
            'memory_per_record_mb': memory_per_record,
            'memory_delta_mb': metrics['memory_delta_mb']
        }

    @pytest.mark.benchmark(group="resample")
    def test_multiple_timeframe_resampling(self, resampler, large_minute_dataset, perf_monitor):
        """Test performance when resampling to multiple timeframes simultaneously"""
        target_timeframes = ['5m', '15m', '1h', '4h', '1d']

        # Monitor CPU and memory
        cpu_samples = []
        memory_samples = []

        def monitor_resources():
            process = psutil.Process()
            for _ in range(30):
                perf_monitor.sample_cpu()
                memory_mb = process.memory_info().rss / 1024 / 1024
                memory_samples.append(memory_mb)
                time.sleep(0.1)

        monitor_thread = threading.Thread(target=monitor_resources)
        monitor_thread.start()

        # Resample to all timeframes
        start_time = time.perf_counter()
        results = {}

        for timeframe in target_timeframes:
            tf_start = time.perf_counter()
            result = resampler.resample(
                data=large_minute_dataset,
                target_timeframe=timeframe
            )
            tf_time = time.perf_counter() - tf_start

            results[timeframe] = {
                'result': result,
                'output_records': len(result),
                'resample_time': tf_time,
                'throughput': len(large_minute_dataset) / tf_time if tf_time > 0 else 0
            }

        total_time = time.perf_counter() - start_time
        monitor_thread.join()
        metrics = perf_monitor.get_metrics()

        # Calculate performance metrics
        total_output_records = sum(r['output_records'] for r in results.values())
        total_throughput = len(large_minute_dataset) * len(target_timeframes) / total_time if total_time > 0 else 0
        avg_timeframe_time = np.mean([r['resample_time'] for r in results.values()])

        # Memory analysis
        memory_growth = max(memory_samples) - min(memory_samples) if memory_samples else 0

        # Assertions
        assert len(results) == len(target_timeframes), "Not all timeframes processed"
        assert all(not r['result'].empty for r in results.values()), "Some resampling results are empty"
        assert total_output_records > 0, "No output records generated"

        # Performance assertions
        assert total_throughput > 5000, f"Total resampling throughput too low: {total_throughput:.0f} records/sec"
        assert avg_timeframe_time < 5.0, f"Average timeframe time too long: {avg_timeframe_time:.2f}s"

        # Memory should be reasonable
        assert memory_growth < 100, f"Memory growth too high: {memory_growth:.1f}MB"

        return {
            'target_timeframes': target_timeframes,
            'source_records': len(large_minute_dataset),
            'total_time': total_time,
            'total_output_records': total_output_records,
            'total_throughput': total_throughput,
            'avg_timeframe_time': avg_timeframe_time,
            'timeframe_results': {tf: {
                'output_records': r['output_records'],
                'resample_time': r['resample_time'],
                'throughput': r['throughput']
            } for tf, r in results.items()},
            'memory_growth_mb': memory_growth,
            'memory_delta_mb': metrics['memory_delta_mb']
        }

    @pytest.mark.benchmark(group="download")
    def test_download_with_resampling_performance(self, download_manager, resampler, mock_ccxt_exchange, perf_monitor):
        """Test performance when downloading and immediately resampling"""
        # Define download and resample tasks
        tasks = [
            {
                'symbol': 'BTC/USDT',
                'download_timeframe': '1m',
                'download_limit': 5000,
                'resample_to': '5m'
            },
            {
                'symbol': 'ETH/USDT',
                'download_timeframe': '5m',
                'download_limit': 2000,
                'resample_to': '1h'
            },
            {
                'symbol': 'BNB/USDT',
                'download_timeframe': '15m',
                'download_limit': 1000,
                'resample_to': '4h'
            }
        ]

        def download_and_resample(task):
            """Download and resample in one operation"""
            start_time = time.perf_counter()

            # Download data
            with patch('ccxt.binance', return_value=mock_ccxt_exchange):
                downloaded_data = download_manager.download_data(
                    exchange='binance',
                    symbol=task['symbol'],
                    timeframe=task['download_timeframe'],
                    limit=task['download_limit']
                )

            # Convert to DataFrame (mock conversion)
            if not downloaded_data.empty:
                # Convert to expected format for resampler
                df_data = {
                    'timestamp': pd.to_datetime(downloaded_data.index, unit='ms'),
                    'open': downloaded_data['open'],
                    'high': downloaded_data['high'],
                    'low': downloaded_data['low'],
                    'close': downloaded_data['close'],
                    'volume': downloaded_data['volume']
                }
                source_df = pd.DataFrame(df_data)
            else:
                source_df = pd.DataFrame()

            # Resample
            resampled_data = resampler.resample(
                data=source_df,
                target_timeframe=task['resample_to']
            )

            total_time = time.perf_counter() - start_time

            return {
                'task': task,
                'downloaded_records': len(downloaded_data),
                'resampled_records': len(resampled_data),
                'total_time': total_time,
                'download_throughput': len(downloaded_data) / total_time if total_time > 0 else 0,
                'resample_throughput': len(source_df) / total_time if total_time > 0 and len(source_df) > 0 else 0
            }

        # Execute tasks
        start_time = time.perf_counter()
        results = []

        with ThreadPoolExecutor(max_workers=3) as executor:
            future_to_task = {
                executor.submit(download_and_resample, task): task
                for task in tasks
            }

            for future in as_completed(future_to_task):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as exc:
                    task = future_to_task[future]
                    results.append({
                        'task': task,
                        'downloaded_records': 0,
                        'resampled_records': 0,
                        'total_time': 0,
                        'error': str(exc)
                    })

        total_time = time.perf_counter() - start_time
        metrics = perf_monitor.get_metrics()

        # Calculate aggregate metrics
        total_downloaded = sum(r['downloaded_records'] for r in results)
        total_resampled = sum(r['resampled_records'] for r in results)
        successful_tasks = sum(1 for r in results if 'error' not in r)

        # Assertions
        assert len(results) == len(tasks), "Not all tasks completed"
        assert successful_tasks == len(tasks), "Some tasks failed"
        assert total_downloaded > 0, "No records downloaded"
        assert total_resampled > 0, "No records resampled"

        # Performance assertions
        download_throughput = total_downloaded / total_time if total_time > 0 else 0
        assert download_throughput > 50, f"Combined download throughput too low: {download_throughput:.0f} records/sec"

        # Memory efficiency
        memory_per_downloaded = metrics['memory_delta_mb'] / total_downloaded if total_downloaded > 0 else 0
        assert memory_per_downloaded < 0.01, f"Memory per downloaded record too high: {memory_per_downloaded:.6f}MB"

        return {
            'task_count': len(tasks),
            'total_time': total_time,
            'total_downloaded': total_downloaded,
            'total_resampled': total_resampled,
            'successful_tasks': successful_tasks,
            'download_throughput': download_throughput,
            'memory_per_downloaded_mb': memory_per_downloaded,
            'memory_delta_mb': metrics['memory_delta_mb'],
            'task_results': results
        }

    @pytest.mark.benchmark(group="download")
    def test_download_error_handling_performance(self, download_manager, mock_ccxt_exchange, perf_monitor):
        """Test performance when handling download errors"""
        # Modify mock to simulate occasional failures
        original_fetch = mock_ccxt_exchange.fetch_ohlcv
        call_count = 0

        def failing_fetch(*args, **kwargs):
            nonlocal call_count
            call_count += 1

            # Simulate 20% failure rate
            if call_count % 5 == 0:
                raise Exception("Network timeout")

            return original_fetch(*args, **kwargs)

        mock_ccxt_exchange.fetch_ohlcv = failing_fetch

        error_test_results = []

        # Test download with retries
        for i in range(10):
            start_time = time.perf_counter()

            try:
                with patch('ccxt.binance', return_value=mock_ccxt_exchange):
                    result = download_manager.download_data(
                        exchange='binance',
                        symbol='BTC/USDT',
                        timeframe='1h',
                        limit=100
                    )
                success = True
                record_count = len(result)
                error_msg = None
            except Exception as e:
                success = False
                record_count = 0
                error_msg = str(e)

            test_time = time.perf_counter() - start_time

            error_test_results.append({
                'test_index': i,
                'success': success,
                'record_count': record_count,
                'test_time': test_time,
                'error_message': error_msg
            })

        metrics = perf_monitor.get_metrics()

        # Calculate error handling metrics
        successful_tests = sum(1 for r in error_test_results if r['success'])
        failed_tests = len(error_test_results) - successful_tests
        avg_success_time = np.mean([r['test_time'] for r in error_test_results if r['success']]) if successful_tests > 0 else 0
        avg_failure_time = np.mean([r['test_time'] for r in error_test_results if not r['success']]) if failed_tests > 0 else 0

        # Assertions
        assert len(error_test_results) == 10, "Not all error tests completed"
        assert successful_tests > 5, "Too many failures during error test"

        # Error handling should be reasonably fast
        if avg_success_time > 0:
            assert avg_success_time < 5.0, f"Average success time too slow: {avg_success_time:.2f}s"
        if avg_failure_time > 0:
            assert avg_failure_time < 2.0, f"Average failure time too slow: {avg_failure_time:.2f}s"

        # Memory should not grow significantly during error handling
        assert metrics['memory_delta_mb'] < 20, f"Memory growth too high during error handling: {metrics['memory_delta_mb']:.1f}MB"

        return {
            'total_tests': len(error_test_results),
            'successful_tests': successful_tests,
            'failed_tests': failed_tests,
            'avg_success_time': avg_success_time,
            'avg_failure_time': avg_failure_time,
            'memory_delta_mb': metrics['memory_delta_mb'],
            'error_test_results': error_test_results
        }

    @pytest.mark.benchmark(group="resample")
    def test_resampling_memory_stress(self, resampler, perf_monitor):
        """Test resampling performance under memory stress"""
        # Create very large dataset
        np.random.seed(42)
        periods = 200000  # ~138 days of minute data
        timestamps = pd.date_range('2022-01-01', periods=periods, freq='1min')

        # Generate price data
        base_price = 50000.0
        volatility = 0.02 / np.sqrt(24*60)

        prices = [base_price]
        for _ in range(periods):
            change = np.random.normal(0, volatility)
            prices.append(max(prices[-1] * (1 + change), 1.0))
        prices = prices[1:]

        data = []
        for i, ts in enumerate(timestamps):
            current_price = prices[i]
            open_price = prices[i-1] if i > 0 else current_price

            data.append({
                'timestamp': ts,
                'open': round(open_price, 2),
                'high': round(current_price * 1.002, 2),
                'low': round(current_price * 0.998, 2),
                'close': round(current_price, 2),
                'volume': np.random.randint(1000, 5000)
            })

        large_df = pd.DataFrame(data)

        # Monitor memory during resampling
        memory_samples = []
        process = psutil.Process()

        def sample_memory():
            memory_mb = process.memory_info().rss / 1024 / 1024
            memory_samples.append(memory_mb)

        sample_memory()  # Initial sample

        # Resample to multiple timeframes
        target_timeframes = ['5m', '15m', '1h', '4h']
        resample_results = {}

        for timeframe in target_timeframes:
            start_time = time.perf_counter()

            result = resampler.resample(
                data=large_df,
                target_timeframe=timeframe
            )

            resample_time = time.perf_counter() - start_time
            sample_memory()

            resample_results[timeframe] = {
                'output_records': len(result),
                'resample_time': resample_time,
                'throughput': len(large_df) / resample_time if resample_time > 0 else 0
            }

        sample_memory()  # Final sample
        metrics = perf_monitor.get_metrics()

        # Analyze memory usage
        memory_growth = memory_samples[-1] - memory_samples[0]
        max_memory = max(memory_samples)
        memory_per_record = memory_growth / len(large_df) if len(large_df) > 0 else 0

        # Calculate aggregate performance
        total_output = sum(r['output_records'] for r in resample_results.values())
        total_throughput = len(large_df) * len(target_timeframes) / sum(r['resample_time'] for r in resample_results.values())

        # Assertions
        assert len(resample_results) == len(target_timeframes), "Not all timeframes processed"
        assert total_output > 0, "No output records generated"

        # Memory efficiency for large datasets
        assert memory_growth < 300, f"Memory growth too high for large dataset: {memory_growth:.1f}MB"
        assert memory_per_record < 0.001, f"Memory per record too high: {memory_per_record:.6f}MB"

        # Performance should remain reasonable
        assert total_throughput > 20000, f"Large dataset throughput too low: {total_throughput:.0f} records/sec"

        return {
            'input_records': len(large_df),
            'target_timeframes': target_timeframes,
            'total_output_records': total_output,
            'total_throughput': total_throughput,
            'memory_growth_mb': memory_growth,
            'max_memory_mb': max_memory,
            'memory_per_record_mb': memory_per_record,
            'resample_results': resample_results,
            'memory_delta_mb': metrics['memory_delta_mb']
        }