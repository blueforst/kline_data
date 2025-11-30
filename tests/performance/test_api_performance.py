"""
API Service Performance Tests

Comprehensive performance testing for API service including concurrent access,
multi-user scenarios, load testing, and response time analysis.
"""

import pytest
import pandas as pd
import numpy as np
import time
import threading
import asyncio
import aiohttp
import requests
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import Mock, patch, AsyncMock
import psutil
import json
import tempfile
from pathlib import Path
import tempfile as tf

from kline_data.service.server import app
from kline_data.service.api import KlineAPI
from fastapi.testclient import TestClient


class TestAPIServicePerformance:
    """Test API service performance under various load conditions"""

    @pytest.fixture
    def api_client(self):
        """Create FastAPI test client"""
        return TestClient(app)

    @pytest.fixture
    def mock_api_data(self):
        """Create mock API response data"""
        np.random.seed(42)
        periods = 1000
        timestamps = pd.date_range('2022-01-01', periods=periods, freq='1h')

        data = []
        for i, ts in enumerate(timestamps):
            base_price = 50000.0
            price = base_price * (1 + np.random.normal(0, 0.01))
            data.append([
                int(ts.timestamp() * 1000),  # timestamp in ms
                round(price, 2),  # open
                round(price * 1.01, 2),  # high
                round(price * 0.99, 2),  # low
                round(price * 1.005, 2),  # close
                np.random.randint(100000, 1000000)  # volume
            ])

        return data

    @pytest.fixture
    def populated_storage(self, temp_dir):
        """Create populated storage for API testing"""
        # Create test data files
        file_configs = [
            {'exchange': 'binance', 'symbol': 'BTC/USDT', 'timeframe': '1h'},
            {'exchange': 'binance', 'symbol': 'ETH/USDT', 'timeframe': '1h'},
            {'exchange': 'okx', 'symbol': 'BTC/USDT', 'timeframe': '1h'},
            {'exchange': 'binance', 'symbol': 'BNB/USDT', 'timeframe': '1h'}
        ]

        created_files = []

        for config in file_configs:
            np.random.seed(42)
            test_data = pd.DataFrame({
                'timestamp': pd.date_range('2022-01-01', periods=5000, freq='1h'),
                'open': np.random.uniform(100, 1000, 5000),
                'high': np.random.uniform(100, 1000, 5000),
                'low': np.random.uniform(100, 1000, 5000),
                'close': np.random.uniform(100, 1000, 5000),
                'volume': np.random.randint(10000, 100000, 5000)
            })

            file_path = temp_dir / f"{config['exchange']}_{config['symbol']}_{config['timeframe']}.parquet"
            test_data.to_parquet(file_path, index=False, compression='snappy')
            created_files.append(file_path)

            # Create metadata
            metadata = {
                'exchange': config['exchange'],
                'symbol': config['symbol'],
                'timeframe': config['timeframe'],
                'first_timestamp': test_data['timestamp'].min(),
                'last_timestamp': test_data['timestamp'].max(),
                'total_records': len(test_data),
                'file_size_bytes': file_path.stat().st_size
            }

            metadata_file = temp_dir / f"{config['exchange']}_{config['symbol']}_{config['timeframe']}_metadata.json"
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, default=str)

        return created_files

    @pytest.mark.benchmark(group="api")
    @pytest.mark.parametrize("endpoint", [
        ("/api/v1/kline", "GET"),
        ("/api/v1/kline/latest", "GET"),
        ("/api/v1/indicators", "POST"),
        ("/api/v1/metadata", "GET")
    ])
    def test_single_endpoint_performance(self, api_client, populated_storage, perf_monitor, endpoint):
        """Test performance of individual API endpoints"""
        endpoint_path, method = endpoint

        # Prepare request based on endpoint
        if endpoint_path == "/api/v1/kline":
            params = {
                "exchange": "binance",
                "symbol": "BTC/USDT",
                "interval": "1h",
                "start_time": "2022-01-01T00:00:00Z",
                "end_time": "2022-01-31T23:59:59Z"
            }
            response = api_client.get(endpoint_path, params=params)
        elif endpoint_path == "/api/v1/kline/latest":
            params = {
                "exchange": "binance",
                "symbol": "BTC/USDT",
                "interval": "1h",
                "limit": 100
            }
            response = api_client.get(endpoint_path, params=params)
        elif endpoint_path == "/api/v1/indicators":
            data = {
                "exchange": "binance",
                "symbol": "BTC/USDT",
                "interval": "1h",
                "start_time": "2022-01-01T00:00:00Z",
                "end_time": "2022-01-07T23:59:59Z",
                "indicators": [
                    {"name": "SMA", "period": 20},
                    {"name": "EMA", "period": 50},
                    {"name": "RSI", "period": 14}
                ]
            }
            response = api_client.post(endpoint_path, json=data)
        else:  # metadata
            params = {
                "exchange": "binance",
                "symbol": "BTC/USDT",
                "interval": "1h"
            }
            response = api_client.get(endpoint_path, params=params)

        metrics = perf_monitor.get_metrics()

        # Assertions
        assert response.status_code == 200, f"Endpoint {endpoint_path} failed: {response.text}"

        # Performance assertions
        if hasattr(response, 'elapsed'):
            response_time = response.elapsed.total_seconds()
        else:
            response_time = metrics['duration']

        # Response time should be reasonable
        assert response_time < 2.0, f"Endpoint {endpoint_path} too slow: {response_time*1000:.1f}ms"

        # Memory usage should be reasonable
        assert metrics['memory_delta_mb'] < 50, f"Memory usage too high for {endpoint_path}: {metrics['memory_delta_mb']:.1f}MB"

        # Check response content
        if endpoint_path in ["/api/v1/kline", "/api/v1/kline/latest"]:
            response_data = response.json()
            assert "data" in response_data, f"No data in response for {endpoint_path}"
            assert len(response_data["data"]) > 0, f"Empty data response for {endpoint_path}"

        return {
            'endpoint': endpoint_path,
            'method': method,
            'response_time': response_time,
            'memory_delta_mb': metrics['memory_delta_mb'],
            'status_code': response.status_code
        }

    @pytest.mark.benchmark(group="api")
    @pytest.mark.parametrize("concurrent_users", [1, 5, 10, 20, 50])
    def test_concurrent_user_performance(self, api_client, populated_storage, perf_monitor, concurrent_users):
        """Test API performance with concurrent users"""
        # Define user requests
        def make_user_request(user_id):
            """Simulate user request"""
            request_start = time.perf_counter()

            # Each user makes a slightly different request
            params = {
                "exchange": ["binance", "okx"][user_id % 2],
                "symbol": ["BTC/USDT", "ETH/USDT", "BNB/USDT"][user_id % 3],
                "interval": "1h",
                "start_time": "2022-01-01T00:00:00Z",
                "end_time": f"2022-01-{(user_id % 28) + 1:02d}T23:59:59Z"
            }

            response = api_client.get("/api/v1/kline", params=params)
            request_time = time.perf_counter() - request_start

            return {
                'user_id': user_id,
                'status_code': response.status_code,
                'response_time': request_time,
                'data_count': len(response.json().get('data', [])),
                'success': response.status_code == 200
            }

        # Execute requests concurrently
        start_time = time.perf_counter()
        user_results = []

        with ThreadPoolExecutor(max_workers=concurrent_users) as executor:
            future_to_user = {
                executor.submit(make_user_request, user_id): user_id
                for user_id in range(concurrent_users)
            }

            for future in as_completed(future_to_user):
                try:
                    result = future.result()
                    user_results.append(result)
                except Exception as exc:
                    user_results.append({
                        'user_id': future_to_user[future],
                        'status_code': 500,
                        'response_time': 0,
                        'data_count': 0,
                        'success': False,
                        'error': str(exc)
                    })

        total_time = time.perf_counter() - start_time
        metrics = perf_monitor.get_metrics()

        # Calculate performance metrics
        successful_requests = [r for r in user_results if r['success']]
        failed_requests = [r for r in user_results if not r['success']]

        avg_response_time = np.mean([r['response_time'] for r in successful_requests]) if successful_requests else 0
        max_response_time = max([r['response_time'] for r in successful_requests]) if successful_requests else 0
        p95_response_time = np.percentile([r['response_time'] for r in successful_requests], 95) if successful_requests else 0

        total_records = sum(r['data_count'] for r in successful_requests)
        throughput = total_records / total_time if total_time > 0 else 0
        requests_per_second = concurrent_users / total_time if total_time > 0 else 0

        # Assertions
        assert len(user_results) == concurrent_users, "Not all user requests completed"
        assert len(failed_requests) == 0, f"Some requests failed: {failed_requests}"
        assert len(successful_requests) > 0, "No successful requests"

        # Performance assertions
        assert avg_response_time < 1.0, f"Average response time too high: {avg_response_time*1000:.1f}ms"
        assert p95_response_time < 2.0, f"P95 response time too high: {p95_response_time*1000:.1f}ms"
        assert requests_per_second > 10, f"Requests per second too low: {requests_per_second:.1f}"

        # Memory should be reasonable under concurrent load
        assert metrics['memory_delta_mb'] < 100, f"Memory usage too high: {metrics['memory_delta_mb']:.1f}MB"

        return {
            'concurrent_users': concurrent_users,
            'total_time': total_time,
            'successful_requests': len(successful_requests),
            'failed_requests': len(failed_requests),
            'avg_response_time': avg_response_time,
            'max_response_time': max_response_time,
            'p95_response_time': p95_response_time,
            'requests_per_second': requests_per_second,
            'throughput_records_per_sec': throughput,
            'memory_delta_mb': metrics['memory_delta_mb']
        }

    @pytest.mark.benchmark(group="api")
    def test_load_test_ramp_up(self, api_client, populated_storage, perf_monitor):
        """Test API performance under gradually increasing load"""
        load_stages = [1, 5, 10, 20, 30, 40, 50]
        stage_results = []

        for stage, user_count in enumerate(load_stages):
            print(f"Load test stage {stage + 1}: {user_count} concurrent users")

            def make_request(stage_id):
                """Make request for load test"""
                start_time = time.perf_counter()

                params = {
                    "exchange": "binance",
                    "symbol": "BTC/USDT",
                    "interval": "1h",
                    "start_time": f"2022-01-{(stage_id % 28) + 1:02d}T00:00:00Z",
                    "end_time": f"2022-01-{(stage_id % 28) + 7:02d}T23:59:59Z"
                }

                response = api_client.get("/api/v1/kline", params=params)
                response_time = time.perf_counter() - start_time

                return {
                    'stage': stage_id,
                    'status_code': response.status_code,
                    'response_time': response_time,
                    'success': response.status_code == 200
                }

            # Execute stage
            stage_start = time.perf_counter()
            stage_user_results = []

            with ThreadPoolExecutor(max_workers=user_count) as executor:
                future_to_user = {
                    executor.submit(make_request, i): i
                    for i in range(user_count)
                }

                for future in as_completed(future_to_user):
                    try:
                        result = future.result()
                        stage_user_results.append(result)
                    except Exception as exc:
                        stage_user_results.append({
                            'stage': future_to_user[future],
                            'status_code': 500,
                            'response_time': 0,
                            'success': False,
                            'error': str(exc)
                        })

            stage_time = time.perf_counter() - stage_start

            # Calculate stage metrics
            successful_stage = [r for r in stage_user_results if r['success']]
            stage_response_times = [r['response_time'] for r in successful_stage]

            stage_result = {
                'user_count': user_count,
                'stage_time': stage_time,
                'successful_requests': len(successful_stage),
                'failed_requests': len(stage_user_results) - len(successful_stage),
                'avg_response_time': np.mean(stage_response_times) if stage_response_times else 0,
                'max_response_time': max(stage_response_times) if stage_response_times else 0,
                'p95_response_time': np.percentile(stage_response_times, 95) if stage_response_times else 0,
                'requests_per_second': user_count / stage_time if stage_time > 0 else 0
            }

            stage_results.append(stage_result)

            # Brief pause between stages
            time.sleep(1)

        metrics = perf_monitor.get_metrics()

        # Analyze load test results
        max_p95_response = max([s['p95_response_time'] for s in stage_results])
        min_throughput = min([s['requests_per_second'] for s in stage_results])
        total_successful = sum([s['successful_requests'] for s in stage_results])
        total_failed = sum([s['failed_requests'] for s in stage_results])

        # Assertions
        assert total_failed == 0, f"Load test had failures: {total_failed} failed requests"
        assert max_p95_response < 5.0, f"P95 response time too high at peak load: {max_p95_response*1000:.1f}ms"
        assert min_throughput > 5, f"Minimum throughput too low: {min_throughput:.1f} req/sec"

        # System should handle increasing load gracefully
        response_times = [s['avg_response_time'] for s in stage_results]
        response_time_growth = response_times[-1] - response_times[0] if len(response_times) > 1 else 0
        assert response_time_growth < 2.0, f"Response time degraded too much: {response_time_growth:.2f}s"

        return {
            'load_stages': load_stages,
            'stage_results': stage_results,
            'total_successful_requests': total_successful,
            'total_failed_requests': total_failed,
            'max_p95_response_time': max_p95_response,
            'min_throughput': min_throughput,
            'memory_delta_mb': metrics['memory_delta_mb'],
            'peak_memory_mb': metrics['peak_memory_mb']
        }

    @pytest.mark.benchmark(group="api")
    @pytest.mark.parametrize("request_size", ["small", "medium", "large"])
    def test_request_size_performance(self, api_client, populated_storage, perf_monitor, request_size):
        """Test performance with different request sizes"""
        # Define request parameters based on size
        if request_size == "small":
            params = {
                "exchange": "binance",
                "symbol": "BTC/USDT",
                "interval": "1h",
                "start_time": "2022-01-01T00:00:00Z",
                "end_time": "2022-01-02T00:00:00Z"  # 1 day
            }
            expected_records = 24
        elif request_size == "medium":
            params = {
                "exchange": "binance",
                "symbol": "BTC/USDT",
                "interval": "1h",
                "start_time": "2022-01-01T00:00:00Z",
                "end_time": "2022-01-31T23:59:59Z"  # 1 month
            }
            expected_records = 744
        else:  # large
            params = {
                "exchange": "binance",
                "symbol": "BTC/USDT",
                "interval": "1h",
                "start_time": "2022-01-01T00:00:00Z",
                "end_time": "2022-06-30T23:59:59Z"  # 6 months
            }
            expected_records = 4320

        # Monitor memory during request processing
        memory_samples = []
        def sample_memory():
            memory_mb = psutil.Process().memory_info().rss / 1024 / 1024
            memory_samples.append(memory_mb)

        sample_memory()  # Sample before request

        start_time = time.perf_counter()
        response = api_client.get("/api/v1/kline", params=params)
        request_time = time.perf_counter() - start_time

        sample_memory()  # Sample after request

        metrics = perf_monitor.get_metrics()

        # Analyze response
        assert response.status_code == 200, f"Request failed: {response.text}"

        response_data = response.json()
        actual_records = len(response_data.get('data', []))

        # Calculate response size
        response_size_mb = len(response.content) / 1024 / 1024
        memory_growth = memory_samples[-1] - memory_samples[0] if len(memory_samples) >= 2 else 0

        # Performance assertions
        assert request_time < 10.0, f"Request too slow for {request_size} size: {request_time*1000:.1f}ms"
        assert actual_records > expected_records * 0.9, f"Too few records returned: {actual_records} vs expected {expected_records}"

        # Memory efficiency
        memory_per_record = memory_growth / actual_records if actual_records > 0 else 0
        assert memory_per_record < 0.01, f"Memory per record too high: {memory_per_record:.6f}MB"

        # Response size efficiency
        size_per_record = response_size_mb / actual_records if actual_records > 0 else 0
        assert size_per_record < 0.001, f"Response size per record too high: {size_per_record:.6f}MB"

        return {
            'request_size': request_size,
            'request_time': request_time,
            'actual_records': actual_records,
            'expected_records': expected_records,
            'response_size_mb': response_size_mb,
            'memory_growth_mb': memory_growth,
            'memory_per_record_mb': memory_per_record,
            'size_per_record_mb': size_per_record,
            'throughput_records_per_sec': actual_records / request_time
        }

    @pytest.mark.benchmark(group="api")
    def test_indicator_calculation_api_performance(self, api_client, populated_storage, perf_monitor):
        """Test API performance for indicator calculations"""
        # Define indicator configurations with varying complexity
        indicator_configs = [
            {
                'name': 'Simple',
                'indicators': [{'name': 'SMA', 'period': 20}],
                'expected_complexity': 'low'
            },
            {
                'name': 'Medium',
                'indicators': [
                    {'name': 'SMA', 'period': 20},
                    {'name': 'EMA', 'period': 50},
                    {'name': 'RSI', 'period': 14}
                ],
                'expected_complexity': 'medium'
            },
            {
                'name': 'Complex',
                'indicators': [
                    {'name': 'SMA', 'period': 20},
                    {'name': 'EMA', 'period': 50},
                    {'name': 'RSI', 'period': 14},
                    {'name': 'MACD', 'fast_period': 12, 'slow_period': 26, 'signal_period': 9},
                    {'name': 'BB', 'period': 20, 'std_dev': 2},
                    {'name': 'ATR', 'period': 14},
                    {'name': 'STOCH', 'k_period': 14, 'd_period': 3}
                ],
                'expected_complexity': 'high'
            }
        ]

        results = []

        for config in indicator_configs:
            request_data = {
                "exchange": "binance",
                "symbol": "BTC/USDT",
                "interval": "1h",
                "start_time": "2022-01-01T00:00:00Z",
                "end_time": "2022-01-31T23:59:59Z",
                "indicators": config['indicators']
            }

            # CPU monitoring during indicator calculation
            cpu_samples = []
            def monitor_cpu():
                for _ in range(30):
                    perf_monitor.sample_cpu()
                    time.sleep(0.05)

            cpu_thread = threading.Thread(target=monitor_cpu)
            cpu_thread.start()

            start_time = time.perf_counter()
            response = api_client.post("/api/v1/indicators", json=request_data)
            calculation_time = time.perf_counter() - start_time

            cpu_thread.join()
            current_metrics = perf_monitor.get_metrics()

            assert response.status_code == 200, f"Indicator calculation failed: {response.text}"

            response_data = response.json()
            indicators_data = response_data.get('data', [])

            # Count indicator columns
            base_cols = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
            indicator_cols = [col for col in indicators_data[0].keys() if col not in base_cols] if indicators_data else []

            result = {
                'config_name': config['name'],
                'complexity': config['expected_complexity'],
                'indicator_count': len(config['indicators']),
                'indicator_columns_count': len(indicator_cols),
                'calculation_time': calculation_time,
                'records_processed': len(indicators_data),
                'throughput': len(indicators_data) / calculation_time if calculation_time > 0 else 0,
                'avg_cpu_percent': current_metrics['avg_cpu_percent'],
                'memory_delta_mb': current_metrics['memory_delta_mb']
            }

            results.append(result)

        # Analyze results
        avg_calculation_time = np.mean([r['calculation_time'] for r in results])
        max_calculation_time = max([r['calculation_time'] for r in results])
        min_throughput = min([r['throughput'] for r in results])

        # Assertions
        assert len(results) == len(indicator_configs), "Not all indicator configurations tested"
        assert max_calculation_time < 30.0, f"Complex indicator calculation too slow: {max_calculation_time:.1f}s"
        assert min_throughput > 100, f"Indicator calculation throughput too low: {min_throughput:.0f} records/sec"

        # CPU should be utilized efficiently during calculations
        max_cpu = max([r['avg_cpu_percent'] for r in results])
        assert max_cpu > 20, f"CPU utilization too low: {max_cpu:.1f}%"

        return {
            'indicator_configs': results,
            'avg_calculation_time': avg_calculation_time,
            'max_calculation_time': max_calculation_time,
            'min_throughput': min_throughput,
            'max_cpu_percent': max_cpu
        }

    @pytest.mark.benchmark(group="api")
    def test_api_error_handling_performance(self, api_client, perf_monitor):
        """Test API performance with error scenarios"""
        error_scenarios = [
            {
                'name': 'Invalid exchange',
                'params': {
                    "exchange": "invalid_exchange",
                    "symbol": "BTC/USDT",
                    "interval": "1h",
                    "start_time": "2022-01-01T00:00:00Z",
                    "end_time": "2022-01-02T00:00:00Z"
                },
                'expected_status': 404
            },
            {
                'name': 'Invalid timeframe',
                'params': {
                    "exchange": "binance",
                    "symbol": "BTC/USDT",
                    "interval": "invalid_interval",
                    "start_time": "2022-01-01T00:00:00Z",
                    "end_time": "2022-01-02T00:00:00Z"
                },
                'expected_status': 400
            },
            {
                'name': 'Invalid date range',
                'params': {
                    "exchange": "binance",
                    "symbol": "BTC/USDT",
                    "interval": "1h",
                    "start_time": "2023-01-01T00:00:00Z",
                    "end_time": "2022-01-01T00:00:00Z"  # End before start
                },
                'expected_status': 400
            },
            {
                'name': 'Malformed data in indicators',
                'data': {
                    "exchange": "binance",
                    "symbol": "BTC/USDT",
                    "interval": "1h",
                    "start_time": "2022-01-01T00:00:00Z",
                    "end_time": "2022-01-02T00:00:00Z",
                    "indicators": [{"name": "INVALID_INDICATOR", "period": 20}]
                },
                'expected_status': 400,
                'method': 'POST'
            }
        ]

        results = []

        for scenario in error_scenarios:
            start_time = time.perf_counter()

            if scenario.get('method') == 'POST':
                response = api_client.post("/api/v1/indicators", json=scenario['data'])
            else:
                response = api_client.get("/api/v1/kline", params=scenario['params'])

            error_response_time = time.perf_counter() - start_time

            result = {
                'scenario_name': scenario['name'],
                'expected_status': scenario['expected_status'],
                'actual_status': response.status_code,
                'response_time': error_response_time,
                'status_correct': response.status_code == scenario['expected_status']
            }

            results.append(result)

        metrics = perf_monitor.get_metrics()

        # Analyze error handling performance
        avg_error_response_time = np.mean([r['response_time'] for r in results])
        max_error_response_time = max([r['response_time'] for r in results])
        correct_status_count = sum([1 for r in results if r['status_correct']])

        # Assertions
        assert len(results) == len(error_scenarios), "Not all error scenarios tested"
        assert correct_status_count == len(error_scenarios), "Some error scenarios returned wrong status codes"

        # Error responses should be fast
        assert avg_error_response_time < 0.5, f"Average error response time too slow: {avg_error_response_time*1000:.1f}ms"
        assert max_error_response_time < 1.0, f"Max error response time too slow: {max_error_response_time*1000:.1f}ms"

        # Memory usage during error handling should be minimal
        assert metrics['memory_delta_mb'] < 10, f"Memory usage too high during error handling: {metrics['memory_delta_mb']:.1f}MB"

        return {
            'error_scenarios': results,
            'avg_error_response_time': avg_error_response_time,
            'max_error_response_time': max_error_response_time,
            'correct_status_count': correct_status_count,
            'memory_delta_mb': metrics['memory_delta_mb']
        }

    @pytest.mark.benchmark(group="api")
    def test_api_memory_leak_detection(self, api_client, populated_storage, perf_monitor):
        """Test for memory leaks during extended API usage"""
        # Make many requests to detect memory leaks
        num_requests = 100
        memory_samples = []
        request_times = []

        initial_memory = psutil.Process().memory_info().rss / 1024 / 1024
        memory_samples.append(initial_memory)

        for i in range(num_requests):
            # Vary the request to avoid caching effects
            params = {
                "exchange": "binance",
                "symbol": "BTC/USDT",
                "interval": "1h",
                "start_time": f"2022-01-{(i % 28) + 1:02d}T00:00:00Z",
                "end_time": f"2022-01-{(i % 28) + 2:02d}T23:59:59Z"
            }

            request_start = time.perf_counter()
            response = api_client.get("/api/v1/kline", params=params)
            request_time = time.perf_counter() - request_start
            request_times.append(request_time)

            # Sample memory every 10 requests
            if i % 10 == 0:
                current_memory = psutil.Process().memory_info().rss / 1024 / 1024
                memory_samples.append(current_memory)

            assert response.status_code == 200, f"Request {i} failed: {response.text}"

        final_memory = psutil.Process().memory_info().rss / 1024 / 1024
        memory_samples.append(final_memory)

        metrics = perf_monitor.get_metrics()

        # Calculate memory leak metrics
        memory_growth = final_memory - initial_memory
        memory_per_request = memory_growth / num_requests
        max_memory = max(memory_samples)

        # Analyze request time performance
        avg_request_time = np.mean(request_times)
        p95_request_time = np.percentile(request_times, 95)

        # Assertions
        assert len(memory_samples) > 0, "No memory samples collected"
        assert len(request_times) == num_requests, "Not all requests completed"

        # Memory leak detection
        assert memory_growth < 50, f"Potential memory leak detected: {memory_growth:.1f}MB growth over {num_requests} requests"
        assert memory_per_request < 0.5, f"Memory per request too high: {memory_per_request:.3f}MB"

        # Performance stability
        assert avg_request_time < 1.0, f"Average request time degraded: {avg_request_time*1000:.1f}ms"
        assert p95_request_time < 2.0, f"P95 request time degraded: {p95_request_time*1000:.1f}ms"

        return {
            'num_requests': num_requests,
            'memory_growth_mb': memory_growth,
            'memory_per_request_mb': memory_per_request,
            'max_memory_mb': max_memory,
            'avg_request_time': avg_request_time,
            'p95_request_time': p95_request_time,
            'memory_samples_count': len(memory_samples),
            'total_memory_delta_mb': metrics['memory_delta_mb']
        }