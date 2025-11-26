"""
Storage Layer I/O Performance Tests

Comprehensive performance testing for storage layer components including
read/write throughput, compression efficiency, and concurrent I/O operations.
"""

import pytest
import pandas as pd
import numpy as np
import time
import gc
import threading
import psutil
import os
from datetime import datetime, timedelta
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import Mock, patch

from storage.writer import ParquetWriter
from reader.parquet_reader import ParquetReader
from storage.metadata_manager import MetadataManager
from storage.downloader import DownloadManager


class TestStorageIOPerformance:
    """Test storage layer I/O performance"""

    @pytest.fixture
    def parquet_writer(self, temp_dir):
        """Create ParquetWriter instance"""
        config = Mock()
        config.storage.data_dir = str(temp_dir)
        config.storage.compression = 'snappy'
        config.storage.batch_size = 10000
        return ParquetWriter(config)

    @pytest.fixture
    def parquet_reader(self, temp_dir):
        """Create ParquetReader instance"""
        config = Mock()
        config.storage.data_dir = str(temp_dir)
        config.reader.cache_enabled = True
        config.reader.cache_size_mb = 100
        return ParquetReader(config)

    @pytest.fixture
    def metadata_manager(self, temp_dir):
        """Create MetadataManager instance"""
        config = Mock()
        config.storage.data_dir = str(temp_dir)
        return MetadataManager(config)

    @pytest.fixture
    def large_test_data(self):
        """Generate large test dataset for I/O testing"""
        np.random.seed(42)
        periods = 50000  # ~5.5 years of hourly data
        timestamps = pd.date_range('2018-01-01', periods=periods, freq='1h')

        base_price = 45000.0
        volatility = 0.015

        # Generate price series with trends and cycles
        trend = np.sin(np.linspace(0, 10*np.pi, periods)) * 0.2
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

            # Realistic OHLC generation
            intrabar_vol = 0.008
            price_range = current_price * intrabar_vol

            high = max(open_price, close_price) + price_range * np.random.uniform(0.2, 0.8)
            low = min(open_price, close_price) - price_range * np.random.uniform(0.2, 0.8)
            high = max(high, open_price, close_price)
            low = min(low, open_price, close_price)

            # Volume correlated with price movement
            price_change = abs((close_price - open_price) / open_price)
            base_volume = np.random.randint(50000, 500000)
            volume = int(base_volume * (1 + price_change * 5) * np.random.uniform(0.5, 2.0))

            data.append({
                'timestamp': ts,
                'open': round(open_price, 2),
                'high': round(high, 2),
                'low': round(low, 2),
                'close': round(close_price, 2),
                'volume': volume
            })

        return pd.DataFrame(data)

    @pytest.mark.benchmark(group="storage")
    @pytest.mark.parametrize("compression", ['snappy', 'gzip', 'brotli', None])
    @pytest.mark.parametrize("data_size", [1000, 10000, 50000])
    def test_write_performance_by_compression(self, parquet_writer, perf_monitor, compression, data_size):
        """Test write performance with different compression algorithms"""
        # Create test data of specified size
        np.random.seed(42)
        test_data = pd.DataFrame({
            'timestamp': pd.date_range('2022-01-01', periods=data_size, freq='1h'),
            'open': np.random.uniform(40000, 60000, data_size),
            'high': np.random.uniform(40000, 60000, data_size),
            'low': np.random.uniform(40000, 60000, data_size),
            'close': np.random.uniform(40000, 60000, data_size),
            'volume': np.random.randint(100000, 1000000, data_size)
        })

        # Monitor disk I/O
        disk_io_before = psutil.disk_io_counters()
        initial_size = 0

        # Write with specified compression
        start_time = time.perf_counter()
        file_path = parquet_writer.write_data(
            exchange='binance',
            symbol='BTC/USDT',
            timeframe='1h',
            data=test_data,
            compression=compression
        )
        write_time = time.perf_counter() - start_time

        disk_io_after = psutil.disk_io_counters()

        # Calculate I/O metrics
        if disk_io_before and disk_io_after:
            bytes_written = disk_io_after.write_bytes - disk_io_before.write_bytes
            write_count = disk_io_after.write_count - disk_io_before.write_count
        else:
            bytes_written = 0
            write_count = 0

        # Get file size
        if Path(file_path).exists():
            file_size = Path(file_path).stat().st_size
        else:
            file_size = 0

        metrics = perf_monitor.get_metrics()

        # Calculate performance metrics
        write_throughput = data_size / write_time if write_time > 0 else 0
        compression_ratio = file_size / (data_size * 8 * 6) if data_size > 0 else 0  # Rough estimate

        # Assertions
        assert Path(file_path).exists(), "File was not created"
        assert write_time > 0, "Write time should be positive"
        assert write_throughput > 1000, f"Write throughput too low: {write_throughput:.0f} records/sec"

        # Compression should reduce file size (except for None)
        if compression:
            assert compression_ratio < 1.0, f"Compression {compression} not effective: {compression_ratio:.3f}"

        # Performance should be reasonable for different compressions
        max_acceptable_time = data_size / 1000  # 1000 records/sec minimum
        if compression == 'brotli':  # Slower but better compression
            max_acceptable_time *= 3

        assert write_time < max_acceptable_time, f"Write too slow with {compression}: {write_time:.2f}s"

        return {
            'compression': compression,
            'data_size': data_size,
            'write_time': write_time,
            'write_throughput': write_throughput,
            'bytes_written': bytes_written,
            'file_size': file_size,
            'compression_ratio': compression_ratio,
            'write_count': write_count,
            'memory_delta_mb': metrics['memory_delta_mb']
        }

    @pytest.mark.benchmark(group="storage")
    @pytest.mark.parametrize("compression", ['snappy', 'gzip', 'brotli'])
    def test_read_performance_by_compression(self, parquet_writer, parquet_reader, perf_monitor, compression):
        """Test read performance with different compression formats"""
        # Create test data and write with compression
        np.random.seed(42)
        test_data = pd.DataFrame({
            'timestamp': pd.date_range('2022-01-01', periods=20000, freq='1h'),
            'open': np.random.uniform(40000, 60000, 20000),
            'high': np.random.uniform(40000, 60000, 20000),
            'low': np.random.uniform(40000, 60000, 20000),
            'close': np.random.uniform(40000, 60000, 20000),
            'volume': np.random.randint(100000, 1000000, 20000)
        })

        # Write data
        file_path = parquet_writer.write_data(
            exchange='binance',
            symbol='BTC/USDT',
            timeframe='1h',
            data=test_data,
            compression=compression
        )

        # Monitor disk I/O during read
        disk_io_before = psutil.disk_io_counters()

        # Read data
        start_time = time.perf_counter()
        result = parquet_reader.read_data(
            exchange='binance',
            symbol='BTC/USDT',
            timeframe='1h',
            start_time=datetime(2022, 1, 1),
            end_time=datetime(2022, 1, 1) + pd.Timedelta(hours=20000)
        )
        read_time = time.perf_counter() - start_time

        disk_io_after = psutil.disk_io_counters()

        # Calculate I/O metrics
        if disk_io_before and disk_io_after:
            bytes_read = disk_io_after.read_bytes - disk_io_before.read_bytes
            read_count = disk_io_after.read_count - disk_io_before.read_count
        else:
            bytes_read = 0
            read_count = 0

        metrics = perf_monitor.get_metrics()

        # Calculate performance metrics
        read_throughput = len(result) / read_time if read_time > 0 else 0
        file_size = Path(file_path).stat().st_size if Path(file_path).exists() else 0
        read_efficiency = len(result) / (bytes_read / 1024 / 1024) if bytes_read > 0 else 0  # records per MB

        # Assertions
        assert not result.empty, "Read result is empty"
        assert len(result) == len(test_data), "Read data size mismatch"
        assert read_throughput > 5000, f"Read throughput too low: {read_throughput:.0f} records/sec"

        # CPU should be reasonable during decompression
        avg_cpu = metrics['avg_cpu_percent']
        if compression == 'brotli':
            assert avg_cpu < 90, f"CPU usage too high for {compression}: {avg_cpu:.1f}%"
        else:
            assert avg_cpu < 70, f"CPU usage too high for {compression}: {avg_cpu:.1f}%"

        return {
            'compression': compression,
            'data_size': len(result),
            'read_time': read_time,
            'read_throughput': read_throughput,
            'bytes_read': bytes_read,
            'file_size': file_size,
            'read_efficiency': read_efficiency,
            'read_count': read_count,
            'avg_cpu_percent': avg_cpu,
            'memory_delta_mb': metrics['memory_delta_mb']
        }

    @pytest.mark.benchmark(group="storage")
    def test_concurrent_read_performance(self, parquet_writer, parquet_reader, temp_dir, perf_monitor):
        """Test concurrent read performance"""
        # Create multiple files for concurrent reading
        file_configs = [
            {'exchange': 'binance', 'symbol': 'BTC/USDT', 'timeframe': '1h'},
            {'exchange': 'binance', 'symbol': 'ETH/USDT', 'timeframe': '1h'},
            {'exchange': 'okx', 'symbol': 'BTC/USDT', 'timeframe': '1h'},
            {'exchange': 'binance', 'symbol': 'BNB/USDT', 'timeframe': '1h'},
            {'exchange': 'binance', 'symbol': 'ADA/USDT', 'timeframe': '1h'}
        ]

        # Write test data files
        np.random.seed(42)
        file_paths = []

        for config in file_configs:
            test_data = pd.DataFrame({
                'timestamp': pd.date_range('2022-01-01', periods=10000, freq='1h'),
                'open': np.random.uniform(100, 1000, 10000),
                'high': np.random.uniform(100, 1000, 10000),
                'low': np.random.uniform(100, 1000, 10000),
                'close': np.random.uniform(100, 1000, 10000),
                'volume': np.random.randint(10000, 100000, 10000)
            })

            file_path = parquet_writer.write_data(
                exchange=config['exchange'],
                symbol=config['symbol'],
                timeframe=config['timeframe'],
                data=test_data
            )
            file_paths.append(file_path)

        def read_file(file_config, file_path):
            """Read single file"""
            start_time = time.perf_counter()

            result = parquet_reader.read_data(
                exchange=file_config['exchange'],
                symbol=file_config['symbol'],
                timeframe=file_config['timeframe'],
                start_time=datetime(2022, 1, 1),
                end_time=datetime(2022, 1, 1) + pd.Timedelta(hours=10000)
            )

            read_time = time.perf_counter() - start_time

            return {
                'config': file_config,
                'file_path': file_path,
                'record_count': len(result),
                'read_time': read_time,
                'throughput': len(result) / read_time if read_time > 0 else 0
            }

        # Sequential reading baseline
        sequential_start = time.perf_counter()
        sequential_results = []
        for config, path in zip(file_configs, file_paths):
            result = read_file(config, path)
            sequential_results.append(result)
        sequential_time = time.perf_counter() - sequential_start

        # Concurrent reading
        concurrent_start = time.perf_counter()
        concurrent_results = []

        with ThreadPoolExecutor(max_workers=5) as executor:
            future_to_file = {
                executor.submit(read_file, config, path): (config, path)
                for config, path in zip(file_configs, file_paths)
            }

            for future in as_completed(future_to_file):
                try:
                    result = future.result()
                    concurrent_results.append(result)
                except Exception as exc:
                    pytest.fail(f"Concurrent read failed: {exc}")

        concurrent_time = time.perf_counter() - concurrent_start
        metrics = perf_monitor.get_metrics()

        # Calculate speedup
        speedup = sequential_time / concurrent_time if concurrent_time > 0 else 0

        # Assertions
        assert len(concurrent_results) == len(sequential_results), "Different number of results"
        assert speedup > 1.5, f"Concurrent reading not efficient: {speedup:.2f}x speedup"

        # Verify all reads were successful
        total_records = sum(r['record_count'] for r in concurrent_results)
        assert total_records == len(file_configs) * 10000, "Missing records in concurrent reads"

        # Performance checks
        avg_throughput = np.mean([r['throughput'] for r in concurrent_results])
        assert avg_throughput > 3000, f"Average throughput too low: {avg_throughput:.0f} records/sec"

        return {
            'sequential_time': sequential_time,
            'concurrent_time': concurrent_time,
            'speedup': speedup,
            'file_count': len(file_configs),
            'total_records': total_records,
            'avg_throughput': avg_throughput,
            'memory_delta_mb': metrics['memory_delta_mb'],
            'peak_memory_mb': metrics['peak_memory_mb']
        }

    @pytest.mark.benchmark(group="storage")
    def test_concurrent_write_performance(self, parquet_writer, temp_dir, perf_monitor):
        """Test concurrent write performance"""
        # Prepare data for concurrent writing
        write_configs = [
            {'exchange': 'binance', 'symbol': 'BTC/USDT', 'timeframe': '1h', 'offset': 0},
            {'exchange': 'binance', 'symbol': 'ETH/USDT', 'timeframe': '1h', 'offset': 10000},
            {'exchange': 'okx', 'symbol': 'BTC/USDT', 'timeframe': '1h', 'offset': 20000},
            {'exchange': 'binance', 'symbol': 'BNB/USDT', 'timeframe': '1h', 'offset': 30000},
            {'exchange': 'binance', 'symbol': 'ADA/USDT', 'timeframe': '1h', 'offset': 40000}
        ]

        np.random.seed(42)

        def write_data(config):
            """Write single dataset"""
            # Generate unique data for each config
            test_data = pd.DataFrame({
                'timestamp': pd.date_range('2022-01-01', periods=8000, freq='1h'),
                'open': np.random.uniform(config['offset'] + 100, config['offset'] + 1000, 8000),
                'high': np.random.uniform(config['offset'] + 100, config['offset'] + 1000, 8000),
                'low': np.random.uniform(config['offset'] + 100, config['offset'] + 1000, 8000),
                'close': np.random.uniform(config['offset'] + 100, config['offset'] + 1000, 8000),
                'volume': np.random.randint(10000, 100000, 8000)
            })

            start_time = time.perf_counter()

            file_path = parquet_writer.write_data(
                exchange=config['exchange'],
                symbol=config['symbol'],
                timeframe=config['timeframe'],
                data=test_data
            )

            write_time = time.perf_counter() - start_time

            return {
                'config': config,
                'file_path': file_path,
                'record_count': len(test_data),
                'write_time': write_time,
                'throughput': len(test_data) / write_time if write_time > 0 else 0
            }

        # Sequential writing baseline
        sequential_start = time.perf_counter()
        sequential_results = []
        for config in write_configs:
            result = write_data(config)
            sequential_results.append(result)
        sequential_time = time.perf_counter() - sequential_start

        # Clean up files for concurrent test
        for result in sequential_results:
            if Path(result['file_path']).exists():
                Path(result['file_path']).unlink()

        # Concurrent writing
        concurrent_start = time.perf_counter()
        concurrent_results = []

        with ThreadPoolExecutor(max_workers=3) as executor:  # Limit workers for disk I/O
            future_to_config = {
                executor.submit(write_data, config): config
                for config in write_configs
            }

            for future in as_completed(future_to_config):
                try:
                    result = future.result()
                    concurrent_results.append(result)
                except Exception as exc:
                    pytest.fail(f"Concurrent write failed: {exc}")

        concurrent_time = time.perf_counter() - concurrent_start
        metrics = perf_monitor.get_metrics()

        # Calculate speedup (should be modest for disk I/O)
        speedup = sequential_time / concurrent_time if concurrent_time > 0 else 0

        # Assertions
        assert len(concurrent_results) == len(sequential_results), "Different number of results"
        assert speedup > 1.0, f"Concurrent writing should be faster: {speedup:.2f}x speedup"

        # Verify all writes were successful
        total_records = sum(r['record_count'] for r in concurrent_results)
        assert total_records == len(write_configs) * 8000, "Missing records in concurrent writes"

        # Check all files were created
        for result in concurrent_results:
            assert Path(result['file_path']).exists(), f"File not created: {result['file_path']}"

        # Performance checks
        avg_throughput = np.mean([r['throughput'] for r in concurrent_results])
        assert avg_throughput > 500, f"Average write throughput too low: {avg_throughput:.0f} records/sec"

        return {
            'sequential_time': sequential_time,
            'concurrent_time': concurrent_time,
            'speedup': speedup,
            'file_count': len(write_configs),
            'total_records': total_records,
            'avg_throughput': avg_throughput,
            'memory_delta_mb': metrics['memory_delta_mb']
        }

    @pytest.mark.benchmark(group="storage")
    def test_metadata_performance(self, metadata_manager, temp_dir, perf_monitor):
        """Test metadata manager performance"""
        # Create test metadata entries
        metadata_entries = []

        for i in range(100):
            entry = {
                'exchange': f'exchange_{i % 5}',
                'symbol': f'SYMBOL_{i % 10}',
                'timeframe': ['1m', '5m', '15m', '1h', '4h', '1d'][i % 6],
                'first_timestamp': datetime(2022, 1, 1) + timedelta(days=i),
                'last_timestamp': datetime(2023, 1, 1) - timedelta(days=i),
                'total_records': 1000 + i * 100,
                'file_size_bytes': 100000 + i * 10000,
                'compression': 'snappy',
                'created_at': datetime.now(),
                'version': f'1.0.{i % 10}'
            }
            metadata_entries.append(entry)

        # Test write performance
        start_time = time.perf_counter()
        written_entries = []

        for entry in metadata_entries:
            file_path = metadata_manager.save_metadata(
                exchange=entry['exchange'],
                symbol=entry['symbol'],
                timeframe=entry['timeframe'],
                metadata=entry
            )
            written_entries.append(file_path)

        write_time = time.perf_counter() - start_time

        # Test read performance
        start_time = time.perf_counter()
        read_entries = []

        for entry in metadata_entries:
            metadata = metadata_manager.get_metadata(
                exchange=entry['exchange'],
                symbol=entry['symbol'],
                timeframe=entry['timeframe']
            )
            read_entries.append(metadata)

        read_time = time.perf_counter() - start_time

        # Test batch query performance
        start_time = time.perf_counter()

        batch_results = metadata_manager.query_metadata(
            exchange='exchange_1',
            symbol='SYMBOL_1',
            timeframes=['1h', '4h', '1d']
        )

        batch_time = time.perf_counter() - start_time

        metrics = perf_monitor.get_metrics()

        # Assertions
        assert len(written_entries) == len(metadata_entries), "Not all metadata entries written"
        assert len(read_entries) == len(metadata_entries), "Not all metadata entries read"
        assert len(batch_results) > 0, "Batch query returned no results"

        # Performance assertions
        write_throughput = len(metadata_entries) / write_time
        read_throughput = len(metadata_entries) / read_time
        assert write_throughput > 100, f"Metadata write too slow: {write_throughput:.0f} entries/sec"
        assert read_throughput > 500, f"Metadata read too slow: {read_throughput:.0f} entries/sec"
        assert batch_time < 0.1, f"Batch query too slow: {batch_time*1000:.1f}ms"

        return {
            'entry_count': len(metadata_entries),
            'write_time': write_time,
            'read_time': read_time,
            'batch_time': batch_time,
            'write_throughput': write_throughput,
            'read_throughput': read_throughput,
            'memory_delta_mb': metrics['memory_delta_mb']
        }

    @pytest.mark.benchmark(group="storage")
    def test_large_file_handling(self, parquet_writer, parquet_reader, large_test_data, perf_monitor):
        """Test performance with very large files"""
        # Monitor disk space and I/O
        disk_before = psutil.disk_usage(tempfile.gettempdir().split('/')[0])
        disk_io_before = psutil.disk_io_counters()

        # Write large dataset
        start_time = time.perf_counter()
        file_path = parquet_writer.write_data(
            exchange='binance',
            symbol='BTC/USDT',
            timeframe='1h',
            data=large_test_data,
            compression='snappy'
        )
        write_time = time.perf_counter() - start_time

        # Check file was created and get size
        assert Path(file_path).exists(), "Large file not created"
        file_size = Path(file_path).stat().st_size

        disk_io_mid = psutil.disk_io_counters()

        # Read large dataset
        start_time = time.perf_counter()
        result = parquet_reader.read_data(
            exchange='binance',
            symbol='BTC/USDT',
            timeframe='1h',
            start_time=datetime(2018, 1, 1),
            end_time=datetime(2023, 7, 1)
        )
        read_time = time.perf_counter() - start_time

        disk_io_after = psutil.disk_io_counters()

        metrics = perf_monitor.get_metrics()

        # Calculate comprehensive I/O metrics
        if disk_io_before and disk_io_after:
            total_bytes_written = disk_io_mid.write_bytes - disk_io_before.write_bytes
            total_bytes_read = disk_io_after.read_bytes - disk_io_mid.read_bytes
            total_write_ops = disk_io_mid.write_count - disk_io_before.write_count
            total_read_ops = disk_io_after.read_count - disk_io_mid.read_count
        else:
            total_bytes_written = total_bytes_read = 0
            total_write_ops = total_read_ops = 0

        # Performance calculations
        write_throughput = len(large_test_data) / write_time
        read_throughput = len(result) / read_time
        write_io_efficiency = total_bytes_written / file_size if file_size > 0 else 0
        read_io_efficiency = total_bytes_read / file_size if file_size > 0 else 0

        # Assertions
        assert not result.empty, "Large file read returned empty result"
        assert len(result) == len(large_test_data), "Data size mismatch"
        assert file_size > 0, "File size should be positive"

        # Performance assertions for large files
        assert write_throughput > 2000, f"Large file write throughput too low: {write_throughput:.0f} records/sec"
        assert read_throughput > 10000, f"Large file read throughput too low: {read_throughput:.0f} records/sec"

        # Memory should be reasonable for large file operations
        assert metrics['memory_delta_mb'] < 500, f"Memory usage too high: {metrics['memory_delta_mb']:.1f}MB"

        # I/O efficiency checks
        assert write_io_efficiency < 5.0, f"Write I/O efficiency poor: {write_io_efficiency:.2f}x"
        assert read_io_efficiency < 3.0, f"Read I/O efficiency poor: {read_io_efficiency:.2f}x"

        return {
            'data_size': len(large_test_data),
            'file_size': file_size,
            'write_time': write_time,
            'read_time': read_time,
            'write_throughput': write_throughput,
            'read_throughput': read_throughput,
            'bytes_written': total_bytes_written,
            'bytes_read': total_bytes_read,
            'write_io_efficiency': write_io_efficiency,
            'read_io_efficiency': read_io_efficiency,
            'memory_delta_mb': metrics['memory_delta_mb']
        }

    @pytest.mark.benchmark(group="storage")
    def test_storage_stress_test(self, parquet_writer, parquet_reader, temp_dir, perf_monitor):
        """Stress test storage layer with high volume operations"""
        np.random.seed(42)

        # Stress parameters
        num_files = 20
        records_per_file = 5000

        # Generate and write multiple files
        write_results = []

        for i in range(num_files):
            test_data = pd.DataFrame({
                'timestamp': pd.date_range(f'2022-{(i%12)+1:02d}-01', periods=records_per_file, freq='1h'),
                'open': np.random.uniform(100 + i*10, 1000 + i*10, records_per_file),
                'high': np.random.uniform(100 + i*10, 1000 + i*10, records_per_file),
                'low': np.random.uniform(100 + i*10, 1000 + i*10, records_per_file),
                'close': np.random.uniform(100 + i*10, 1000 + i*10, records_per_file),
                'volume': np.random.randint(10000, 100000, records_per_file)
            })

            start_time = time.perf_counter()
            file_path = parquet_writer.write_data(
                exchange=f'exchange_{i % 3}',
                symbol=f'SYMBOL_{i % 5}',
                timeframe='1h',
                data=test_data
            )
            write_time = time.perf_counter() - start_time

            write_results.append({
                'file_index': i,
                'file_path': file_path,
                'record_count': records_per_file,
                'write_time': write_time,
                'throughput': records_per_file / write_time
            })

        # Read all files back
        read_results = []

        for write_result in write_results:
            start_time = time.perf_counter()

            result = parquet_reader.read_data(
                exchange=f'exchange_{write_result["file_index"] % 3}',
                symbol=f'SYMBOL_{write_result["file_index"] % 5}',
                timeframe='1h',
                start_time=datetime(2022, 1, 1),
                end_time=datetime(2023, 1, 1)
            )

            read_time = time.perf_counter() - start_time

            read_results.append({
                'file_index': write_result['file_index'],
                'record_count': len(result),
                'read_time': read_time,
                'throughput': len(result) / read_time if read_time > 0 else 0
            })

        metrics = perf_monitor.get_metrics()

        # Calculate stress test metrics
        total_records_written = sum(r['record_count'] for r in write_results)
        total_records_read = sum(r['record_count'] for r in read_results)
        total_write_time = sum(r['write_time'] for r in write_results)
        total_read_time = sum(r['read_time'] for r in read_results)

        avg_write_throughput = total_records_written / total_write_time if total_write_time > 0 else 0
        avg_read_throughput = total_records_read / total_read_time if total_read_time > 0 else 0

        # Assertions
        assert len(write_results) == num_files, "Not all files written"
        assert len(read_results) == num_files, "Not all files read"
        assert total_records_written == total_records_read, "Record count mismatch"
        assert total_records_written == num_files * records_per_file, "Expected record count mismatch"

        # Stress test performance assertions
        assert avg_write_throughput > 1000, f"Stress test write throughput too low: {avg_write_throughput:.0f} records/sec"
        assert avg_read_throughput > 5000, f"Stress test read throughput too low: {avg_read_throughput:.0f} records/sec"

        # Memory should not grow excessively during stress test
        assert metrics['memory_delta_mb'] < 200, f"Memory growth too high in stress test: {metrics['memory_delta_mb']:.1f}MB"

        return {
            'num_files': num_files,
            'records_per_file': records_per_file,
            'total_records': total_records_written,
            'avg_write_throughput': avg_write_throughput,
            'avg_read_throughput': avg_read_throughput,
            'total_write_time': total_write_time,
            'total_read_time': total_read_time,
            'memory_delta_mb': metrics['memory_delta_mb'],
            'peak_memory_mb': metrics['peak_memory_mb']
        }