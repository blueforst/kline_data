"""
ChunkedDataFeed Performance Tests

Comprehensive performance testing for ChunkedDataFeed memory efficiency and
large dataset processing capabilities.
"""

import pytest
import pandas as pd
import numpy as np
import time
import gc
from datetime import datetime, timedelta
from pathlib import Path
import threading
import psutil
import os

from kline_data.sdk.data_feed import ChunkedDataFeed


class TestChunkedDataFeedPerformance:
    """Test ChunkedDataFeed performance and memory efficiency"""

    @pytest.fixture
    def large_dataset_file(self, temp_dir, large_ohlcv_dataset):
        """Create large dataset file for ChunkedDataFeed testing"""
        file_path = temp_dir / "binance_BTC_USDT_1h_large.parquet"
        large_ohlcv_dataset.to_parquet(file_path, index=False, compression='snappy')
        return file_path

    @pytest.fixture
    def minute_dataset_file(self, temp_dir, minute_dataset):
        """Create minute dataset file for high-frequency testing"""
        file_path = temp_dir / "binance_BTC_USDT_1m.parquet"
        minute_dataset.to_parquet(file_path, index=False, compression='snappy')
        return file_path

    @pytest.fixture
    def chunked_feed_small(self, large_dataset_file):
        """Create ChunkedDataFeed with small chunks"""
        return ChunkedDataFeed(
            exchange='binance',
            symbol='BTC/USDT',
            start_time=datetime(2022, 1, 1),
            end_time=datetime(2022, 1, 31),
            interval='1h',
            chunk_size=100  # Small chunks for testing
        )

    @pytest.fixture
    def chunked_feed_large(self, large_dataset_file):
        """Create ChunkedDataFeed with large chunks"""
        return ChunkedDataFeed(
            exchange='binance',
            symbol='BTC/USDT',
            start_time=datetime(2022, 1, 1),
            end_time=datetime(2023, 1, 1),
            interval='1h',
            chunk_size=10000  # Large chunks for testing
        )

    @pytest.fixture
    def chunked_feed_minute(self, minute_dataset_file):
        """Create ChunkedDataFeed for minute data"""
        return ChunkedDataFeed(
            exchange='binance',
            symbol='BTC/USDT',
            start_time=datetime(2023, 1, 1),
            end_time=datetime(2023, 1, 8),
            interval='1m',
            chunk_size=1440  # 1 day of minute data per chunk
        )

    @pytest.mark.benchmark(group="memory")
    @pytest.mark.parametrize("chunk_size", [100, 1000, 5000, 10000])
    def test_chunk_size_memory_efficiency(self, temp_dir, large_ohlcv_dataset, perf_monitor, chunk_size):
        """Test memory efficiency with different chunk sizes"""
        # Create test data file
        file_path = temp_dir / f"test_data_{chunk_size}.parquet"
        large_ohlcv_dataset.to_parquet(file_path, index=False)

        feed = ChunkedDataFeed(
            exchange='binance',
            symbol='BTC/USDT',
            start_time=datetime(2022, 1, 1),
            end_time=datetime(2022, 6, 1),  # 5 months
            interval='1h',
            chunk_size=chunk_size
        )

        # Monitor memory during iteration
        memory_samples = []
        iteration_times = []

        total_records = 0
        chunk_count = 0

        for chunk_df in feed:
            chunk_start = time.perf_counter()

            # Sample memory before processing chunk
            memory_before = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024

            # Process chunk (simulate some operations)
            processed_chunk = chunk_df.copy()
            processed_chunk['price_range'] = processed_chunk['high'] - processed_chunk['low']
            processed_chunk['volume_ma'] = processed_chunk['volume'].rolling(20).mean()

            # Sample memory after processing
            memory_after = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024

            chunk_time = time.perf_counter() - chunk_start

            memory_samples.append({
                'chunk': chunk_count,
                'memory_before': memory_before,
                'memory_after': memory_after,
                'memory_delta': memory_after - memory_before,
                'chunk_size': len(chunk_df),
                'processing_time': chunk_time
            })

            iteration_times.append(chunk_time)
            total_records += len(chunk_df)
            chunk_count += 1

            # Clean up
            del processed_chunk
            gc.collect()

        metrics = perf_monitor.get_metrics()

        # Calculate memory statistics
        memory_deltas = [s['memory_delta'] for s in memory_samples]
        avg_memory_delta = np.mean(memory_deltas)
        max_memory_delta = np.max(memory_deltas)

        # Assertions
        assert chunk_count > 0, "No chunks were processed"
        assert total_records > 0, "No records were processed"

        # Memory efficiency should be good (small memory growth per chunk)
        memory_per_record = avg_memory_delta / (chunk_size if chunk_size > 0 else 1)
        assert memory_per_record < 0.001, f"Memory per record too high: {memory_per_record:.6f}MB"

        # Processing time should be reasonable
        avg_iteration_time = np.mean(iteration_times)
        records_per_second = chunk_size / avg_iteration_time if avg_iteration_time > 0 else 0
        assert records_per_second > 1000, f"Processing too slow: {records_per_second:.0f} records/sec"

        return {
            'chunk_size': chunk_size,
            'chunk_count': chunk_count,
            'total_records': total_records,
            'avg_memory_delta_mb': avg_memory_delta,
            'max_memory_delta_mb': max_memory_delta,
            'memory_per_record_mb': memory_per_record,
            'avg_iteration_time': avg_iteration_time,
            'records_per_second': records_per_second
        }

    @pytest.mark.benchmark(group="memory")
    def test_large_dataset_memory_efficiency(self, chunked_feed_large, perf_monitor):
        """Test memory efficiency with large datasets"""
        # Monitor memory continuously during iteration
        memory_monitor = []
        stop_monitoring = False

        def monitor_memory():
            process = psutil.Process(os.getpid())
            while not stop_monitoring:
                memory_mb = process.memory_info().rss / 1024 / 1024
                memory_monitor.append({
                    'timestamp': time.perf_counter(),
                    'memory_mb': memory_mb
                })
                time.sleep(0.1)

        # Start memory monitoring
        monitor_thread = threading.Thread(target=monitor_memory)
        monitor_thread.daemon = True
        monitor_thread.start()

        # Process all chunks
        total_chunks = 0
        total_records = 0
        chunk_sizes = []

        for chunk_df in chunked_feed_large:
            chunk_sizes.append(len(chunk_df))
            total_records += len(chunk_df)
            total_chunks += 1

            # Simulate some processing
            processed = chunk_df.copy()
            processed['returns'] = processed['close'].pct_change()
            processed['volatility'] = processed['returns'].rolling(20).std()

            del processed  # Clean up

        # Stop monitoring
        stop_monitoring = True
        monitor_thread.join(timeout=1)

        metrics = perf_monitor.get_metrics()

        # Analyze memory usage
        memory_values = [m['memory_mb'] for m in memory_monitor]
        initial_memory = memory_values[0] if memory_values else 0
        peak_memory = max(memory_values) if memory_values else 0
        final_memory = memory_values[-1] if memory_values else 0

        memory_growth = peak_memory - initial_memory
        memory_leak = final_memory - initial_memory

        # Calculate data size for comparison
        data_size_estimate = total_records * 8 * 6 / 1024 / 1024  # Rough estimate
        memory_ratio = memory_growth / data_size_estimate if data_size_estimate > 0 else 0

        # Assertions
        assert total_chunks > 0, "No chunks processed"
        assert total_records > 0, "No records processed"

        # Memory efficiency checks
        assert memory_growth < 500, f"Memory growth too high: {memory_growth:.1f}MB"
        assert memory_ratio < 3.0, f"Memory ratio too high: {memory_ratio:.1f}x data size"
        assert memory_leak < 50, f"Potential memory leak: {memory_leak:.1f}MB"

        # Performance checks
        throughput = total_records / metrics['duration'] if metrics['duration'] > 0 else 0
        assert throughput > 10000, f"Throughput too low: {throughput:.0f} records/sec"

        return {
            'total_chunks': total_chunks,
            'total_records': total_records,
            'avg_chunk_size': np.mean(chunk_sizes),
            'memory_growth_mb': memory_growth,
            'memory_ratio': memory_ratio,
            'memory_leak_mb': memory_leak,
            'throughput_records_per_sec': throughput,
            'processing_time': metrics['duration']
        }

    @pytest.mark.benchmark(group="memory")
    def test_minute_data_streaming_performance(self, chunked_feed_minute, perf_monitor):
        """Test performance with high-frequency minute data streaming"""
        # Process minute data in streaming fashion
        processed_rows = 0
        processing_times = []
        memory_samples = []

        start_time = time.perf_counter()

        for chunk_df in chunked_feed_minute:
            chunk_start = time.perf_counter()
            memory_before = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024

            # Simulate real-time processing
            for _, row in chunk_df.iterrows():
                # Simulate processing logic
                price_change = (row['close'] - row['open']) / row['open']
                volume_price_ratio = row['volume'] / row['close']
                processed_rows += 1

                # Process-style processing for backtesting
                # Simulate yield processing without using yield in test

            chunk_time = time.perf_counter() - chunk_start
            memory_after = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024

            processing_times.append(chunk_time)
            memory_samples.append({
                'chunk_size': len(chunk_df),
                'processing_time': chunk_time,
                'memory_delta': memory_after - memory_before
            })

        total_time = time.perf_counter() - start_time
        metrics = perf_monitor.get_metrics()

        # Calculate performance metrics
        avg_chunk_time = np.mean(processing_times)
        rows_per_second = processed_rows / total_time if total_time > 0 else 0

        # Memory efficiency
        memory_deltas = [s['memory_delta'] for s in memory_samples]
        avg_memory_delta = np.mean(memory_deltas) if memory_deltas else 0

        # Assertions
        assert processed_rows > 0, "No rows processed"
        assert rows_per_second > 50000, f"Row processing too slow: {rows_per_second:.0f} rows/sec"

        # Memory should remain stable during streaming
        assert avg_memory_delta < 10, f"Memory growth per chunk too high: {avg_memory_delta:.1f}MB"

        return {
            'processed_rows': processed_rows,
            'total_time': total_time,
            'rows_per_second': rows_per_second,
            'avg_chunk_time': avg_chunk_time,
            'avg_memory_delta_mb': avg_memory_delta,
            'memory_usage_mb': metrics['memory_delta_mb']
        }

    @pytest.mark.benchmark(group="memory")
    def test_concurrent_chunk_processing(self, chunked_feed_small, perf_monitor):
        """Test concurrent processing of multiple chunks"""
        from concurrent.futures import ThreadPoolExecutor, as_completed

        # Collect chunks first (in real scenario, might be processed as they come)
        chunks = list(chunked_feed_small)
        assert len(chunks) > 1, "Not enough chunks for concurrent testing"

        # Process chunks concurrently
        def process_chunk(chunk_data, chunk_id):
            start_time = time.perf_counter()

            # Simulate complex processing
            processed = chunk_data.copy()
            processed['sma_20'] = processed['close'].rolling(20).mean()
            processed['ema_50'] = processed['close'].ewm(span=50).mean()
            processed['rsi_14'] = processed['close'].rolling(14).apply(
                lambda x: 100 - (100 / (1 + x.diff().clip(lower=0).mean() /
                                     x.diff().clip(upper=0).abs().mean()))
            )
            processed['bb_upper'] = processed['sma_20'] + 2 * processed['close'].rolling(20).std()
            processed['bb_lower'] = processed['sma_20'] - 2 * processed['close'].rolling(20).std()

            processing_time = time.perf_counter() - start_time

            return {
                'chunk_id': chunk_id,
                'record_count': len(chunk_data),
                'processing_time': processing_time,
                'throughput': len(chunk_data) / processing_time if processing_time > 0 else 0
            }

        # Sequential processing baseline
        sequential_start = time.perf_counter()
        sequential_results = []
        for i, chunk in enumerate(chunks):
            result = process_chunk(chunk, i)
            sequential_results.append(result)
        sequential_time = time.perf_counter() - sequential_start

        # Concurrent processing
        concurrent_start = time.perf_counter()
        concurrent_results = []
        max_workers = min(4, len(chunks))  # Use up to 4 workers

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_chunk = {
                executor.submit(process_chunk, chunk, i): i
                for i, chunk in enumerate(chunks)
            }

            for future in as_completed(future_to_chunk):
                try:
                    result = future.result()
                    concurrent_results.append(result)
                except Exception as exc:
                    pytest.fail(f"Chunk processing failed: {exc}")

        concurrent_time = time.perf_counter() - concurrent_start
        metrics = perf_monitor.get_metrics()

        # Calculate speedup
        speedup = sequential_time / concurrent_time if concurrent_time > 0 else 0

        # Assertions
        assert len(concurrent_results) == len(sequential_results), "Different number of results"
        assert speedup > 1.5, f"Concurrent processing not efficient enough: {speedup:.2f}x speedup"

        # Memory usage should be reasonable during concurrent processing
        assert metrics['peak_memory_mb'] - metrics['start_memory_mb'] < 200, \
            f"Memory usage too high during concurrent processing: {metrics['peak_memory_mb'] - metrics['start_memory_mb']:.1f}MB"

        return {
            'sequential_time': sequential_time,
            'concurrent_time': concurrent_time,
            'speedup': speedup,
            'max_workers': max_workers,
            'total_chunks': len(chunks),
            'memory_delta_mb': metrics['memory_delta_mb'],
            'peak_memory_mb': metrics['peak_memory_mb']
        }

    @pytest.mark.benchmark(group="memory")
    def test_memory_pressure_handling(self, temp_dir, perf_monitor):
        """Test behavior under memory pressure conditions"""
        # Create a very large dataset
        large_data = pd.DataFrame({
            'timestamp': pd.date_range('2020-01-01', periods=100000, freq='1h'),
            'open': np.random.uniform(30000, 70000, 100000),
            'high': np.random.uniform(30000, 70000, 100000),
            'low': np.random.uniform(30000, 70000, 100000),
            'close': np.random.uniform(30000, 70000, 100000),
            'volume': np.random.randint(100000, 10000000, 100000)
        })

        file_path = temp_dir / "large_memory_test.parquet"
        large_data.to_parquet(file_path, index=False, compression='snappy')

        # Create feed with small chunks to increase memory pressure
        feed = ChunkedDataFeed(
            exchange='binance',
            symbol='BTC/USDT',
            start_time=datetime(2020, 1, 1),
            end_time=datetime(2020, 1, 1) + pd.Timedelta(hours=100000),
            interval='1h',
            chunk_size=1000  # Small chunks to create more objects
        )

        # Monitor memory during processing with memory pressure
        memory_samples = []
        gc_counts = []

        # Pre-load some memory to create pressure
        dummy_data = [np.random.random(1000000) for _ in range(5)]

        processed_chunks = 0
        for chunk_df in feed:
            memory_before = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024
            gc_count_before = gc.collect()

            # Process chunk with memory-intensive operations
            processed = chunk_df.copy()

            # Create multiple temporary arrays to increase pressure
            temp_arrays = []
            for col in ['open', 'high', 'low', 'close']:
                temp_arrays.append(np.array(processed[col].values, dtype=np.float64))
                temp_arrays.append(np.log(processed[col].values))
                temp_arrays.append(np.sqrt(processed[col].values))

            # Clean up temporary arrays
            del temp_arrays
            gc_count_after = gc.collect()
            memory_after = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024

            memory_samples.append({
                'chunk': processed_chunks,
                'memory_before': memory_before,
                'memory_after': memory_after,
                'memory_delta': memory_after - memory_before,
                'gc_collections': gc_count_after - gc_count_before
            })

            gc_counts.append(gc_count_after - gc_count_before)
            processed_chunks += 1

            # Stop after processing some chunks to avoid too much memory usage
            if processed_chunks >= 50:
                break

        # Clean up dummy data
        del dummy_data
        gc.collect()

        metrics = perf_monitor.get_metrics()

        # Analyze memory pressure behavior
        memory_deltas = [s['memory_delta'] for s in memory_samples]
        max_memory_delta = max(memory_deltas) if memory_deltas else 0
        avg_gc_collections = np.mean(gc_counts) if gc_counts else 0

        # Assertions
        assert processed_chunks > 0, "No chunks processed under memory pressure"

        # System should handle memory pressure gracefully
        assert max_memory_delta < 100, f"Memory spike too high: {max_memory_delta:.1f}MB"
        assert avg_gc_collections >= 0, "GC should be working"

        # Performance should remain reasonable under pressure
        throughput = sum(len(c) for c in list(feed)[:processed_chunks]) / metrics['duration'] \
                    if metrics['duration'] > 0 else 0
        assert throughput > 1000, f"Throughput too low under pressure: {throughput:.0f} records/sec"

        return {
            'processed_chunks': processed_chunks,
            'max_memory_delta_mb': max_memory_delta,
            'avg_gc_collections': avg_gc_collections,
            'throughput_records_per_sec': throughput,
            'memory_delta_mb': metrics['memory_delta_mb']
        }

    @pytest.mark.benchmark(group="memory")
    def test_iter_rows_performance(self, chunked_feed_small, perf_monitor):
        """Test performance of row-by-row iteration"""
        # Test both chunk iteration and row iteration
        chunk_times = []
        row_times = []

        # Measure chunk iteration performance
        chunk_start = time.perf_counter()
        chunk_count = 0
        total_records_chunk = 0

        for chunk_df in chunked_feed_small:
            chunk_count += 1
            total_records_chunk += len(chunk_df)

        chunk_iteration_time = time.perf_counter() - chunk_start

        # Measure row iteration performance
        row_start = time.perf_counter()
        row_count = 0

        for row in chunked_feed_small.iter_rows():
            row_count += 1
            # Simulate row processing
            timestamp, open_price, high, low, close, volume = row
            _ = close - open_price  # Simple calculation

        row_iteration_time = time.perf_counter() - row_start
        metrics = perf_monitor.get_metrics()

        # Calculate performance metrics
        chunk_throughput = total_records_chunk / chunk_iteration_time if chunk_iteration_time > 0 else 0
        row_throughput = row_count / row_iteration_time if row_iteration_time > 0 else 0

        # Assertions
        assert total_records_chunk > 0, "No records in chunk iteration"
        assert row_count > 0, "No records in row iteration"
        assert total_records_chunk == row_count, "Different record counts"

        # Both methods should have reasonable performance
        assert chunk_throughput > 100000, f"Chunk throughput too low: {chunk_throughput:.0f} records/sec"
        assert row_throughput > 50000, f"Row throughput too low: {row_throughput:.0f} records/sec"

        # Row iteration should be slower than chunk iteration but not too slow
        overhead_ratio = row_iteration_time / chunk_iteration_time if chunk_iteration_time > 0 else 0
        assert overhead_ratio < 10, f"Row iteration overhead too high: {overhead_ratio:.2f}x"

        return {
            'chunk_iteration_time': chunk_iteration_time,
            'row_iteration_time': row_iteration_time,
            'chunk_throughput': chunk_throughput,
            'row_throughput': row_throughput,
            'overhead_ratio': overhead_ratio,
            'total_records': total_records_chunk,
            'memory_delta_mb': metrics['memory_delta_mb']
        }