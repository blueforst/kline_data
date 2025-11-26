"""
Performance Threshold Validation and Regression Detection

Comprehensive performance regression testing with threshold validation,
trend analysis, and automated performance monitoring.
"""

import pytest
import pandas as pd
import numpy as np
import time
import json
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch
import tempfile
import psutil
import statistics
import gc

from sdk.client import KlineClient
from reader.parquet_reader import ParquetReader
from storage.writer import ParquetWriter
from indicators.manager import IndicatorManager


class PerformanceThresholdValidator:
    """Validates performance against predefined thresholds"""

    def __init__(self, config_file=None):
        """Initialize threshold validator"""
        self.thresholds = self._load_default_thresholds()
        if config_file and Path(config_file).exists():
            self._load_custom_thresholds(config_file)

        self.performance_history = []
        self.regression_detected = []

    def _load_default_thresholds(self):
        """Load default performance thresholds"""
        return {
            'query': {
                'response_time_ms': {
                    'small_data': 50,     # < 1K records
                    'medium_data': 200,   # 1K-10K records
                    'large_data': 1000,   # > 10K records
                    'xlarge_data': 5000   # > 100K records
                },
                'throughput_records_per_sec': {
                    'min_read': 10000,
                    'min_write': 5000,
                    'min_indicator': 50000
                },
                'memory_efficiency': {
                    'max_memory_ratio': 5.0,      # Memory should not exceed 5x data size
                    'warning_memory_ratio': 3.0,
                    'memory_per_record_mb': 0.01
                }
            },
            'api': {
                'response_time_ms': {
                    'simple': 200,         # Basic query
                    'complex': 2000,       # With indicators
                    'concurrent': 5000     # Under load
                },
                'throughput_requests_per_sec': {
                    'min_single': 10,
                    'min_concurrent': 50,
                    'peak_target': 100
                },
                'error_handling': {
                    'max_error_response_ms': 500,
                    'min_success_rate': 0.99
                }
            },
            'storage': {
                'io_performance': {
                    'min_read_throughput_mb_per_sec': 100,
                    'min_write_throughput_mb_per_sec': 50,
                    'max_io_wait_ms': 100
                },
                'compression_efficiency': {
                    'min_compression_ratio': 0.3,  # Should compress to 30% or less
                    'max_overhead_ratio': 2.0       # I/O overhead should not exceed 2x
                }
            },
            'indicators': {
                'calculation_time': {
                    'simple': 0.1,         # SMA, EMA
                    'complex': 1.0,        # MACD, Bollinger Bands
                    'multiple': 2.0        # Multiple indicators
                },
                'throughput': {
                    'min_records_per_sec': 10000,
                    'min_multiple_per_sec': 5000
                },
                'cpu_efficiency': {
                    'max_cpu_percent': 80,
                    'min_cpu_utilization': 20
                }
            },
            'memory': {
                'leak_detection': {
                    'max_growth_mb_per_100_operations': 10,
                    'max_growth_rate_mb_per_sec': 1.0
                },
                'efficiency': {
                    'max_memory_per_record_mb': 0.001,
                    'max_gc_frequency_percent': 5.0
                }
            }
        }

    def _load_custom_thresholds(self, config_file):
        """Load custom thresholds from configuration file"""
        try:
            with open(config_file, 'r') as f:
                custom_thresholds = json.load(f)

            # Merge with default thresholds
            for category, thresholds in custom_thresholds.items():
                if category in self.thresholds:
                    self.thresholds[category].update(thresholds)
                else:
                    self.thresholds[category] = thresholds
        except Exception as e:
            print(f"Warning: Could not load custom thresholds: {e}")

    def validate_performance(self, test_name, category, metrics, data_size=None):
        """Validate performance metrics against thresholds"""
        validation_result = {
            'test_name': test_name,
            'category': category,
            'timestamp': datetime.now().isoformat(),
            'data_size': data_size,
            'passed': True,
            'violations': [],
            'warnings': [],
            'metrics': metrics
        }

        # Get relevant thresholds
        category_thresholds = self.thresholds.get(category, {})

        # Validate response time
        if 'duration' in metrics or 'response_time' in metrics:
            response_time_ms = (metrics.get('duration') or metrics.get('response_time', 0)) * 1000

            if data_size:
                if data_size < 1000:
                    threshold = category_thresholds.get('response_time_ms', {}).get('small_data', 1000)
                elif data_size < 10000:
                    threshold = category_thresholds.get('response_time_ms', {}).get('medium_data', 1000)
                elif data_size < 100000:
                    threshold = category_thresholds.get('response_time_ms', {}).get('large_data', 1000)
                else:
                    threshold = category_thresholds.get('response_time_ms', {}).get('xlarge_data', 10000)

                if response_time_ms > threshold:
                    validation_result['violations'].append({
                        'type': 'response_time',
                        'threshold': threshold,
                        'actual': response_time_ms,
                        'severity': 'high'
                    })
                    validation_result['passed'] = False
                elif response_time_ms > threshold * 0.8:
                    validation_result['warnings'].append({
                        'type': 'response_time',
                        'threshold': threshold,
                        'actual': response_time_ms,
                        'severity': 'medium'
                    })

        # Validate throughput
        if 'throughput' in metrics or 'records_per_second' in metrics:
            throughput = metrics.get('throughput') or metrics.get('records_per_second', 0)

            if category == 'query':
                min_throughput = category_thresholds.get('throughput_records_per_sec', {}).get('min_read', 1000)
            elif category == 'storage':
                min_throughput = category_thresholds.get('io_performance', {}).get('min_read_throughput_mb_per_sec', 10)
            elif category == 'indicators':
                min_throughput = category_thresholds.get('throughput', {}).get('min_records_per_sec', 1000)
            else:
                min_throughput = 1000

            if throughput < min_throughput:
                validation_result['violations'].append({
                    'type': 'throughput',
                    'threshold': min_throughput,
                    'actual': throughput,
                    'severity': 'high'
                })
                validation_result['passed'] = False
            elif throughput < min_throughput * 1.2:
                validation_result['warnings'].append({
                    'type': 'throughput',
                    'threshold': min_throughput,
                    'actual': throughput,
                    'severity': 'medium'
                })

        # Validate memory efficiency
        if 'memory_delta_mb' in metrics and data_size:
            memory_delta = metrics['memory_delta_mb']
            data_size_mb = data_size * 8 * 6 / 1024 / 1024  # Rough estimate

            if data_size_mb > 0:
                memory_ratio = memory_delta / data_size_mb
                max_ratio = category_thresholds.get('memory_efficiency', {}).get('max_memory_ratio', 5.0)
                warning_ratio = category_thresholds.get('memory_efficiency', {}).get('warning_memory_ratio', 3.0)

                if memory_ratio > max_ratio:
                    validation_result['violations'].append({
                        'type': 'memory_efficiency',
                        'threshold': max_ratio,
                        'actual': memory_ratio,
                        'severity': 'high'
                    })
                    validation_result['passed'] = False
                elif memory_ratio > warning_ratio:
                    validation_result['warnings'].append({
                        'type': 'memory_efficiency',
                        'threshold': warning_ratio,
                        'actual': memory_ratio,
                        'severity': 'medium'
                    })

        # Validate CPU usage
        if 'avg_cpu_percent' in metrics:
            cpu_percent = metrics['avg_cpu_percent']

            if category == 'indicators':
                max_cpu = category_thresholds.get('cpu_efficiency', {}).get('max_cpu_percent', 90)
                min_cpu = category_thresholds.get('cpu_efficiency', {}).get('min_cpu_utilization', 10)

                if cpu_percent > max_cpu:
                    validation_result['violations'].append({
                        'type': 'cpu_usage',
                        'threshold': max_cpu,
                        'actual': cpu_percent,
                        'severity': 'high'
                    })
                    validation_result['passed'] = False
                elif cpu_percent < min_cpu:
                    validation_result['warnings'].append({
                        'type': 'cpu_underutilization',
                        'threshold': min_cpu,
                        'actual': cpu_percent,
                        'severity': 'low'
                    })

        # Store validation result
        self.performance_history.append(validation_result)

        # Check for regressions
        self._check_regression(test_name, validation_result)

        return validation_result

    def _check_regression(self, test_name, current_result):
        """Check for performance regressions compared to historical data"""
        # Get last 10 results for the same test
        historical_results = [
            r for r in self.performance_history[-20:]
            if r['test_name'] == test_name and r != current_result
        ]

        if len(historical_results) < 3:
            return  # Not enough historical data

        # Calculate averages for key metrics
        avg_response_times = []
        avg_throughputs = []
        avg_memory_usage = []

        for result in historical_results:
            metrics = result['metrics']
            if 'duration' in metrics:
                avg_response_times.append(metrics['duration'])
            if 'throughput' in metrics:
                avg_throughputs.append(metrics['throughput'])
            if 'memory_delta_mb' in metrics:
                avg_memory_usage.append(metrics['memory_delta_mb'])

        # Compare current performance with historical averages
        current_metrics = current_result['metrics']

        # Check response time regression (50% increase)
        if avg_response_times and 'duration' in current_metrics:
            avg_time = statistics.mean(avg_response_times)
            current_time = current_metrics['duration']

            if current_time > avg_time * 1.5:
                self.regression_detected.append({
                    'test_name': test_name,
                    'type': 'response_time_regression',
                    'historical_avg': avg_time,
                    'current': current_time,
                    'regression_factor': current_time / avg_time,
                    'timestamp': datetime.now().isoformat()
                })

        # Check throughput regression (30% decrease)
        if avg_throughputs and 'throughput' in current_metrics:
            avg_throughput = statistics.mean(avg_throughputs)
            current_throughput = current_metrics['throughput']

            if current_throughput < avg_throughput * 0.7:
                self.regression_detected.append({
                    'test_name': test_name,
                    'type': 'throughput_regression',
                    'historical_avg': avg_throughput,
                    'current': current_throughput,
                    'regression_factor': avg_throughput / current_throughput,
                    'timestamp': datetime.now().isoformat()
                })

        # Check memory regression (2x increase)
        if avg_memory_usage and 'memory_delta_mb' in current_metrics:
            avg_memory = statistics.mean(avg_memory_usage)
            current_memory = current_metrics['memory_delta_mb']

            if current_memory > avg_memory * 2.0:
                self.regression_detected.append({
                    'test_name': test_name,
                    'type': 'memory_regression',
                    'historical_avg': avg_memory,
                    'current': current_memory,
                    'regression_factor': current_memory / avg_memory,
                    'timestamp': datetime.now().isoformat()
                })

    def get_regression_report(self):
        """Get comprehensive regression report"""
        return {
            'total_regressions': len(self.regression_detected),
            'regressions_by_type': {
                'response_time': len([r for r in self.regression_detected if r['type'] == 'response_time_regression']),
                'throughput': len([r for r in self.regression_detected if r['type'] == 'throughput_regression']),
                'memory': len([r for r in self.regression_detected if r['type'] == 'memory_regression'])
            },
            'recent_regressions': self.regression_detected[-10:],  # Last 10 regressions
            'performance_summary': self._generate_performance_summary()
        }

    def _generate_performance_summary(self):
        """Generate performance summary from historical data"""
        if not self.performance_history:
            return {}

        # Group by category
        categories = {}
        for result in self.performance_history[-50:]:  # Last 50 results
            category = result['category']
            if category not in categories:
                categories[category] = {
                    'total_tests': 0,
                    'passed_tests': 0,
                    'violations': 0,
                    'warnings': 0,
                    'avg_response_time': [],
                    'avg_throughput': []
                }

            cat_data = categories[category]
            cat_data['total_tests'] += 1

            if result['passed']:
                cat_data['passed_tests'] += 1

            cat_data['violations'] += len(result['violations'])
            cat_data['warnings'] += len(result['warnings'])

            metrics = result['metrics']
            if 'duration' in metrics:
                cat_data['avg_response_time'].append(metrics['duration'])
            if 'throughput' in metrics:
                cat_data['avg_throughput'].append(metrics['throughput'])

        # Calculate averages
        for category, data in categories.items():
            if data['avg_response_time']:
                data['avg_response_time'] = statistics.mean(data['avg_response_time'])
            else:
                data['avg_response_time'] = 0

            if data['avg_throughput']:
                data['avg_throughput'] = statistics.mean(data['avg_throughput'])
            else:
                data['avg_throughput'] = 0

            data['pass_rate'] = data['passed_tests'] / data['total_tests'] if data['total_tests'] > 0 else 0

        return categories


class TestPerformanceRegression:
    """Comprehensive performance regression testing"""

    @pytest.fixture
    def performance_validator(self, temp_dir):
        """Create performance threshold validator"""
        # Create custom thresholds file
        thresholds_config = {
            'query': {
                'response_time_ms': {
                    'small_data': 100,     # Slightly relaxed for testing
                    'medium_data': 300,
                    'large_data': 1500,
                    'xlarge_data': 8000
                }
            },
            'memory': {
                'leak_detection': {
                    'max_growth_mb_per_100_operations': 20  # Relaxed for testing
                }
            }
        }

        config_file = temp_dir / "custom_thresholds.json"
        with open(config_file, 'w') as f:
            json.dump(thresholds_config, f, indent=2)

        return PerformanceThresholdValidator(str(config_file))

    @pytest.fixture
    def test_dataset(self):
        """Create test dataset for regression testing"""
        np.random.seed(42)
        periods = 5000
        timestamps = pd.date_range('2022-01-01', periods=periods, freq='1h')

        base_price = 50000.0
        volatility = 0.02

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
                'high': round(current_price * 1.01, 2),
                'low': round(current_price * 0.99, 2),
                'close': round(current_price, 2),
                'volume': np.random.randint(100000, 1000000)
            })

        return pd.DataFrame(data)

    def test_query_performance_regression(self, performance_validator, test_dataset, temp_dir, perf_monitor):
        """Test for query performance regressions"""
        # Create test data file
        file_path = temp_dir / "regression_test.parquet"
        test_dataset.to_parquet(file_path, index=False, compression='snappy')

        # Mock KlineClient
        config = Mock()
        config.storage.data_dir = str(temp_dir)
        client = KlineClient(config)

        # Perform multiple test iterations to establish baseline
        test_iterations = 5
        results = []

        for i in range(test_iterations):
            start_time = time.perf_counter()

            # Mock the query operation
            result = client.get_kline(
                exchange='binance',
                symbol='BTC/USDT',
                start_time=datetime(2022, 1, 1),
                end_time=datetime(2022, 3, 1),
                interval='1h',
                auto_strategy=False,
                force_strategy='local'
            )

            query_time = time.perf_counter() - start_time
            metrics = perf_monitor.get_metrics()

            # Validate performance
            validation_result = performance_validator.validate_performance(
                test_name=f'query_regression_test_{i}',
                category='query',
                metrics={
                    'duration': query_time,
                    'throughput': len(result) / query_time if query_time > 0 else 0,
                    'memory_delta_mb': metrics['memory_delta_mb']
                },
                data_size=len(result)
            )

            results.append({
                'iteration': i,
                'query_time': query_time,
                'record_count': len(result),
                'throughput': len(result) / query_time if query_time > 0 else 0,
                'validation_passed': validation_result['passed'],
                'violations': len(validation_result['violations']),
                'warnings': len(validation_result['warnings'])
            })

        # Analyze results for regressions
        query_times = [r['query_time'] for r in results]
        throughputs = [r['throughput'] for r in results]
        violations = sum(r['violations'] for r in results)

        # Assertions
        assert len(results) == test_iterations, "Not all test iterations completed"
        assert violations == 0, f"Performance violations detected: {violations}"
        assert all(r['validation_passed'] for r in results), "Some validation checks failed"

        # Performance consistency checks
        avg_query_time = statistics.mean(query_times)
        max_query_time = max(query_times)
        time_variance = statistics.variance(query_times)

        assert avg_query_time < 1.0, f"Average query time too high: {avg_query_time:.3f}s"
        assert max_query_time < avg_query_time * 2.0, f"Query time variance too high: {max_query_time:.3f}s vs avg {avg_query_time:.3f}s"
        assert time_variance < 0.1, f"Query time variance too high: {time_variance:.6f}"

        # Get regression report
        regression_report = performance_validator.get_regression_report()

        return {
            'test_iterations': test_iterations,
            'avg_query_time': avg_query_time,
            'max_query_time': max_query_time,
            'time_variance': time_variance,
            'avg_throughput': statistics.mean(throughputs),
            'violations': violations,
            'regression_report': regression_report,
            'results': results
        }

    def test_memory_leak_regression(self, performance_validator, test_dataset, perf_monitor):
        """Test for memory leak regressions"""
        # Create multiple test iterations to detect memory leaks
        iterations = 50
        memory_samples = []

        initial_memory = psutil.Process().memory_info().rss / 1024 / 1024
        memory_samples.append(initial_memory)

        for i in range(iterations):
            # Perform memory-intensive operation
            temp_data = test_dataset.copy()
            temp_data['returns'] = temp_data['close'].pct_change()
            temp_data['volatility'] = temp_data['returns'].rolling(20).std()

            # Clean up
            del temp_data

            # Sample memory every 10 iterations
            if i % 10 == 0:
                current_memory = psutil.Process().memory_info().rss / 1024 / 1024
                memory_samples.append(current_memory)

        final_memory = psutil.Process().memory_info().rss / 1024 / 1024
        memory_samples.append(final_memory)

        metrics = perf_monitor.get_metrics()

        # Calculate memory growth
        memory_growth = final_memory - initial_memory
        memory_growth_per_iteration = memory_growth / iterations
        max_memory = max(memory_samples)

        # Validate memory performance
        validation_result = performance_validator.validate_performance(
            test_name='memory_leak_regression_test',
            category='memory',
            metrics={
                'memory_delta_mb': memory_growth,
                'max_memory_mb': max_memory - initial_memory,
                'memory_per_iteration_mb': memory_growth_per_iteration
            }
        )

        # Assertions
        assert memory_growth < 50, f"Memory growth too high: {memory_growth:.1f}MB over {iterations} iterations"
        assert memory_growth_per_iteration < 1.0, f"Memory growth per iteration too high: {memory_growth_per_iteration:.3f}MB"
        assert validation_result['passed'], f"Memory validation failed: {validation_result['violations']}"

        # Check for memory leaks (non-linear growth)
        if len(memory_samples) > 3:
            # Linear regression to check growth trend
            x = list(range(len(memory_samples)))
            y = memory_samples
            slope = np.polyfit(x, y, 1)[0]  # First-order coefficient

            assert slope < 0.5, f"Memory growth trend too steep: {slope:.3f}MB per sample"

        return {
            'iterations': iterations,
            'initial_memory_mb': initial_memory,
            'final_memory_mb': final_memory,
            'memory_growth_mb': memory_growth,
            'memory_per_iteration_mb': memory_growth_per_iteration,
            'max_memory_mb': max_memory - initial_memory,
            'validation_passed': validation_result['passed'],
            'memory_samples': memory_samples
        }

    def test_throughput_regression(self, performance_validator, test_dataset, perf_monitor):
        """Test for throughput regressions"""
        # Test with different data sizes
        data_sizes = [1000, 5000, 10000]
        throughput_results = []

        for size in data_sizes:
            # Subset data for this test
            subset_data = test_dataset.head(size)

            start_time = time.perf_counter()

            # Simulate processing operation
            processed_data = subset_data.copy()
            processed_data['sma_20'] = processed_data['close'].rolling(20).mean()
            processed_data['ema_50'] = processed_data['close'].ewm(span=50).mean()
            processed_data['volatility'] = processed_data['close'].pct_change().rolling(20).std()

            processing_time = time.perf_counter() - start_time
            throughput = size / processing_time if processing_time > 0 else 0

            # Validate performance
            validation_result = performance_validator.validate_performance(
                test_name=f'throughput_test_size_{size}',
                category='indicators',
                metrics={
                    'duration': processing_time,
                    'throughput': throughput,
                    'avg_cpu_percent': metrics.get('avg_cpu_percent', 0)
                },
                data_size=size
            )

            throughput_results.append({
                'data_size': size,
                'processing_time': processing_time,
                'throughput': throughput,
                'validation_passed': validation_result['passed'],
                'violations': len(validation_result['violations'])
            })

        # Analyze throughput scalability
        throughputs = [r['throughput'] for r in throughput_results]
        min_throughput = min(throughputs)
        throughput_variance = statistics.variance(throughputs)

        # Assertions
        assert len(throughput_results) == len(data_sizes), "Not all throughput tests completed"
        assert all(r['validation_passed'] for r in throughput_results), "Some throughput validations failed"
        assert sum(r['violations'] for r in throughput_results) == 0, "Performance violations detected"

        # Throughput should not degrade significantly with data size
        assert min_throughput > 1000, f"Minimum throughput too low: {min_throughput:.0f} records/sec"
        assert throughput_variance < 1000000, f"Throughput variance too high: {throughput_variance:.0f}"

        # Check scaling (throughput shouldn't decrease dramatically with size)
        if len(throughputs) > 1:
            scaling_factor = throughputs[0] / throughputs[-1]  # Small vs large dataset
            assert scaling_factor < 3.0, f"Throughput scaling too poor: {scaling_factor:.2f}x degradation"

        return {
            'data_sizes': data_sizes,
            'throughput_results': throughput_results,
            'min_throughput': min_throughput,
            'throughput_variance': throughput_variance,
            'scaling_factor': scaling_factor if len(throughputs) > 1 else 1.0
        }

    def test_concurrent_performance_regression(self, performance_validator, temp_dir, perf_monitor):
        """Test for concurrent performance regressions"""
        # Create multiple test files
        file_configs = [
            {'exchange': 'binance', 'symbol': 'BTC/USDT', 'timeframe': '1h'},
            {'exchange': 'binance', 'symbol': 'ETH/USDT', 'timeframe': '1h'},
            {'exchange': 'okx', 'symbol': 'BTC/USDT', 'timeframe': '1h'}
        ]

        # Create test data files
        for i, config in enumerate(file_configs):
            test_data = test_dataset.copy()
            file_path = temp_dir / f"concurrent_test_{i}.parquet"
            test_data.to_parquet(file_path, index=False)

        # Test concurrent operations
        from concurrent.futures import ThreadPoolExecutor, as_completed

        def concurrent_operation(file_index):
            start_time = time.perf_counter()

            # Simulate file reading and processing
            file_path = temp_dir / f"concurrent_test_{file_index}.parquet"
            data = pd.read_parquet(file_path)

            # Process data
            processed_data = data.copy()
            processed_data['returns'] = processed_data['close'].pct_change()
            processed_data['cumulative_returns'] = (1 + processed_data['returns']).cumprod()

            operation_time = time.perf_counter() - start_time
            return {
                'file_index': file_index,
                'record_count': len(data),
                'operation_time': operation_time,
                'throughput': len(data) / operation_time if operation_time > 0 else 0
            }

        # Execute concurrent operations
        start_time = time.perf_counter()
        results = []

        with ThreadPoolExecutor(max_workers=3) as executor:
            future_to_file = {
                executor.submit(concurrent_operation, i): i
                for i in range(len(file_configs))
            }

            for future in as_completed(future_to_file):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as exc:
                    file_index = future_to_file[future]
                    results.append({
                        'file_index': file_index,
                        'record_count': 0,
                        'operation_time': 0,
                        'throughput': 0,
                        'error': str(exc)
                    })

        total_time = time.perf_counter() - start_time
        metrics = perf_monitor.get_metrics()

        # Validate concurrent performance
        successful_results = [r for r in results if 'error' not in r]
        total_records = sum(r['record_count'] for r in successful_results)
        avg_operation_time = statistics.mean([r['operation_time'] for r in successful_results]) if successful_results else 0

        validation_result = performance_validator.validate_performance(
            test_name='concurrent_performance_test',
            category='api',
            metrics={
                'duration': total_time,
                'throughput': total_records / total_time if total_time > 0 else 0,
                'memory_delta_mb': metrics['memory_delta_mb']
            },
            data_size=total_records
        )

        # Assertions
        assert len(successful_results) == len(file_configs), "Not all concurrent operations succeeded"
        assert total_records > 0, "No records processed"
        assert validation_result['passed'], f"Concurrent validation failed: {validation_result['violations']}"
        assert avg_operation_time < 2.0, f"Average concurrent operation time too high: {avg_operation_time:.3f}s"

        return {
            'file_configs': len(file_configs),
            'successful_operations': len(successful_results),
            'total_records': total_records,
            'total_time': total_time,
            'avg_operation_time': avg_operation_time,
            'validation_passed': validation_result['passed'],
            'results': results
        }

    def test_performance_trend_analysis(self, performance_validator, test_dataset, perf_monitor):
        """Test performance trend analysis over multiple runs"""
        trend_data = []

        # Run the same test multiple times to analyze trends
        for run in range(10):
            start_time = time.perf_counter()

            # Perform standardized test operation
            processed_data = test_dataset.copy()
            processed_data['sma_20'] = processed_data['close'].rolling(20).mean()
            processed_data['volatility'] = processed_data['close'].pct_change().rolling(20).std()

            operation_time = time.perf_counter() - start_time

            # Validate and store result
            validation_result = performance_validator.validate_performance(
                test_name=f'trend_analysis_run_{run}',
                category='indicators',
                metrics={
                    'duration': operation_time,
                    'throughput': len(test_dataset) / operation_time if operation_time > 0 else 0,
                    'memory_delta_mb': perf_monitor.get_metrics()['memory_delta_mb']
                },
                data_size=len(test_dataset)
            )

            trend_data.append({
                'run': run,
                'duration': operation_time,
                'throughput': len(test_dataset) / operation_time if operation_time > 0 else 0,
                'memory_delta_mb': perf_monitor.get_metrics()['memory_delta_mb'],
                'validation_passed': validation_result['passed'],
                'violations': len(validation_result['violations'])
            })

        # Analyze trends
        durations = [r['duration'] for r in trend_data]
        throughputs = [r['throughput'] for r in trend_data]
        memory_usage = [r['memory_delta_mb'] for r in trend_data]

        duration_trend = np.polyfit(range(len(durations)), durations, 1)[0]  # Linear trend
        throughput_trend = np.polyfit(range(len(throughputs)), throughputs, 1)[0]
        memory_trend = np.polyfit(range(len(memory_usage)), memory_usage, 1)[0]

        # Assertions
        assert len(trend_data) == 10, "Not all trend analysis runs completed"
        assert all(r['validation_passed'] for r in trend_data), "Some trend runs failed"
        assert sum(r['violations'] for r in trend_data) == 0, "Performance violations in trend analysis"

        # Trends should be stable (no significant degradation)
        assert abs(duration_trend) < 0.01, f"Duration trend shows degradation: {duration_trend:.6f}s per run"
        assert throughput_trend > -100, f"Throughput trend shows degradation: {throughput_trend:.0f} records/sec per run"
        assert memory_trend < 1.0, f"Memory trend shows growth: {memory_trend:.3f}MB per run"

        # Performance should be consistent
        duration_std = statistics.stdev(durations)
        throughput_std = statistics.stdev(throughputs)

        assert duration_std < 0.1, f"Duration variability too high: {duration_std:.4f}s"
        assert throughput_std < 1000, f"Throughput variability too high: {throughput_std:.0f} records/sec"

        return {
            'runs': len(trend_data),
            'duration_trend': duration_trend,
            'throughput_trend': throughput_trend,
            'memory_trend': memory_trend,
            'duration_std': duration_std,
            'throughput_std': throughput_std,
            'avg_duration': statistics.mean(durations),
            'avg_throughput': statistics.mean(throughputs),
            'trend_data': trend_data
        }

    def test_comprehensive_regression_report(self, performance_validator):
        """Generate comprehensive regression detection report"""
        # Get detailed regression analysis
        regression_report = performance_validator.get_regression_report()
        performance_summary = regression_report['performance_summary']

        # Assertions about overall performance health
        assert regression_report['total_regressions'] == 0, f"Performance regressions detected: {regression_report['total_regressions']}"

        # Check that we have performance data
        assert len(performance_summary) > 0, "No performance summary data available"

        # Validate performance health by category
        for category, data in performance_summary.items():
            assert data['pass_rate'] >= 0.95, f"Pass rate too low for {category}: {data['pass_rate']:.2%}"
            assert data['violations'] == 0, f"Violations detected in {category}: {data['violations']}"

        return {
            'regression_report': regression_report,
            'performance_summary': performance_summary,
            'overall_health': 'GOOD' if regression_report['total_regressions'] == 0 else 'NEEDS_ATTENTION'
        }