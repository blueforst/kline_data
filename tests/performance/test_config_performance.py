"""
Configuration Loading and Caching Performance Tests

Comprehensive performance testing for configuration management including
loading speed, caching efficiency, and memory usage.
"""

import pytest
import pandas as pd
import numpy as np
import time
import json
import yaml
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import psutil

from kline_data.config.manager import ConfigManager
from kline_data.config.schemas import ConfigSchema


class TestConfigPerformance:
    """Test configuration loading and caching performance"""

    @pytest.fixture
    def large_config_data(self):
        """Generate large configuration data for testing"""
        config_data = {
            'storage': {
                'data_dir': '/tmp/test_data',
                'compression': 'snappy',
                'batch_size': 10000,
                'max_file_size_mb': 100,
                'cache_enabled': True,
                'cache_size_mb': 200,
                'cleanup_interval_hours': 24
            },
            'download': {
                'enabled': True,
                'rate_limit': 100,
                'max_concurrent': 5,
                'retry_attempts': 3,
                'retry_delay_seconds': 1,
                'timeout_seconds': 30,
                'chunk_size': 1000
            },
            'resample': {
                'enabled': True,
                'cache_intermediate': True,
                'memory_limit_mb': 500
            },
            'api': {
                'host': '0.0.0.0',
                'port': 8000,
                'debug': False,
                'cors_enabled': True,
                'rate_limit_per_minute': 1000,
                'max_request_size_mb': 50,
                'timeout_seconds': 60
            },
            'reader': {
                'cache_enabled': True,
                'cache_size_mb': 100,
                'preload_cache': True,
                'memory_efficient': True
            },
            'exchanges': {},
            'logging': {
                'level': 'INFO',
                'format': 'detailed',
                'file_rotation': True,
                'max_file_size_mb': 10,
                'backup_count': 5
            }
        }

        # Add many exchange configurations
        exchanges = ['binance', 'okx', 'coinbase', 'kraken', 'bitstamp', 'huobi', 'kucoin', 'bybit']
        symbols = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'ADA/USDT', 'SOL/USDT', 'DOT/USDT', 'MATIC/USDT', 'AVAX/USDT']

        for exchange in exchanges:
            config_data['exchanges'][exchange] = {
                'enabled': True,
                'api_key': f'test_key_{exchange}',
                'api_secret': f'test_secret_{exchange}',
                'rate_limit': np.random.randint(50, 200),
                'timeout_seconds': np.random.randint(10, 60),
                'retry_attempts': np.random.randint(2, 5),
                'supported_symbols': symbols,
                'supported_timeframes': ['1m', '5m', '15m', '1h', '4h', '1d'],
                'features': {
                    'fetch_ohlcv': True,
                    'fetch_ticker': True,
                    'fetch_order_book': True,
                    'fetch_trades': False
                },
                'custom_params': {
                    f'param_{i}': f'value_{i}' for i in range(20)
                }
            }

        return config_data

    @pytest.fixture
    def config_manager(self, temp_dir):
        """Create ConfigManager instance"""
        return ConfigManager(config_dir=str(temp_dir))

    @pytest.mark.benchmark(group="config")
    @pytest.mark.parametrize("config_format", ["json", "yaml"])
    @pytest.mark.parametrize("config_size", ["small", "medium", "large"])
    def test_config_loading_performance(self, config_manager, temp_dir, perf_monitor, config_format, config_size):
        """Test configuration loading performance with different formats and sizes"""
        # Generate config based on size
        if config_size == "small":
            config_data = {
                'storage': {'data_dir': str(temp_dir)},
                'api': {'port': 8000},
                'download': {'enabled': True}
            }
        elif config_size == "medium":
            config_data = {
                'storage': {
                    'data_dir': str(temp_dir),
                    'compression': 'snappy',
                    'batch_size': 1000
                },
                'api': {
                    'host': 'localhost',
                    'port': 8000,
                    'debug': False
                },
                'download': {
                    'enabled': True,
                    'rate_limit': 100,
                    'retry_attempts': 3
                },
                'exchanges': {
                    'binance': {'enabled': True, 'api_key': 'test'},
                    'okx': {'enabled': True, 'api_key': 'test'}
                }
            }
        else:  # large
            config_data = self.large_config_data()

        # Write config file
        config_file = temp_dir / f"test_config.{config_format}"

        if config_format == "json":
            with open(config_file, 'w') as f:
                json.dump(config_data, f, indent=2, default=str)
        else:  # yaml
            with open(config_file, 'w') as f:
                yaml.dump(config_data, f, default_flow_style=False)

        file_size = config_file.stat().st_size

        # Test loading performance
        start_time = time.perf_counter()
        loaded_config = config_manager.load_config(f"test_config.{config_format}")
        load_time = time.perf_counter() - start_time

        metrics = perf_monitor.get_metrics()

        # Calculate performance metrics
        load_throughput = file_size / 1024 / load_time if load_time > 0 else 0  # KB/sec

        # Assertions
        assert loaded_config is not None, "Config should be loaded"
        assert load_time > 0, "Load time should be positive"

        # Performance assertions
        assert load_time < 1.0, f"Config loading too slow: {load_time*1000:.1f}ms"
        assert load_throughput > 100, f"Loading throughput too low: {load_throughput:.0f} KB/sec"

        # Memory should be reasonable
        assert metrics['memory_delta_mb'] < 10, f"Memory usage too high: {metrics['memory_delta_mb']:.1f}MB"

        return {
            'config_format': config_format,
            'config_size': config_size,
            'file_size_bytes': file_size,
            'load_time': load_time,
            'load_throughput_kb_per_sec': load_throughput,
            'memory_delta_mb': metrics['memory_delta_mb']
        }

    @pytest.mark.benchmark(group="config")
    def test_config_caching_performance(self, config_manager, temp_dir, perf_monitor):
        """Test configuration caching performance"""
        # Create test config
        config_data = self.large_config_data()
        config_file = temp_dir / "cache_test_config.yaml"

        with open(config_file, 'w') as f:
            yaml.dump(config_data, f, default_flow_style=False)

        # Test first load (cache miss)
        start_time = time.perf_counter()
        config1 = config_manager.load_config("cache_test_config.yaml")
        first_load_time = time.perf_counter() - start_time

        # Test subsequent loads (cache hits)
        cache_times = []
        for i in range(20):
            start_time = time.perf_counter()
            config2 = config_manager.load_config("cache_test_config.yaml")
            cache_time = time.perf_counter() - start_time
            cache_times.append(cache_time)

        metrics = perf_monitor.get_metrics()

        # Calculate caching metrics
        avg_cache_time = np.mean(cache_times)
        min_cache_time = min(cache_times)
        max_cache_time = max(cache_times)
        cache_speedup = first_load_time / avg_cache_time if avg_cache_time > 0 else 0

        # Assertions
        assert config1 is not None, "First load should succeed"
        assert config2 is not None, "Cached load should succeed"

        # Cache should be significantly faster
        assert cache_speedup > 10, f"Caching not effective: {cache_speedup:.1f}x speedup"
        assert avg_cache_time < 0.01, f"Cache access too slow: {avg_cache_time*1000:.1f}ms"

        # Configs should be the same object (cached reference)
        assert id(config1) == id(config2), "Config should be cached as same object"

        return {
            'first_load_time': first_load_time,
            'avg_cache_time': avg_cache_time,
            'min_cache_time': min_cache_time,
            'max_cache_time': max_cache_time,
            'cache_speedup': cache_speedup,
            'cache_samples': len(cache_times),
            'memory_delta_mb': metrics['memory_delta_mb']
        }

    @pytest.mark.benchmark(group="config")
    def test_concurrent_config_loading(self, config_manager, temp_dir, perf_monitor):
        """Test concurrent configuration loading performance"""
        # Create multiple config files
        config_files = []
        num_configs = 10

        for i in range(num_configs):
            config_data = {
                'storage': {
                    'data_dir': str(temp_dir / f"data_{i}"),
                    'batch_size': 1000 + i * 100
                },
                'api': {
                    'port': 8000 + i,
                    'debug': i % 2 == 0
                },
                'download': {
                    'enabled': True,
                    'rate_limit': 100 + i * 10
                },
                'version': f'1.0.{i}'
            }

            config_file = temp_dir / f"concurrent_config_{i}.yaml"
            with open(config_file, 'w') as f:
                yaml.dump(config_data, f, default_flow_style=False)

            config_files.append(config_file)

        def load_config_file(config_file):
            """Load a single config file"""
            start_time = time.perf_counter()
            config = config_manager.load_config(config_file.name)
            load_time = time.perf_counter() - start_time

            return {
                'file_name': config_file.name,
                'load_time': load_time,
                'success': config is not None
            }

        # Sequential loading baseline
        sequential_start = time.perf_counter()
        sequential_results = []
        for config_file in config_files:
            result = load_config_file(config_file)
            sequential_results.append(result)
        sequential_time = time.perf_counter() - sequential_start

        # Clear cache for fair comparison
        config_manager.clear_cache()

        # Concurrent loading
        concurrent_start = time.perf_counter()
        concurrent_results = []

        with ThreadPoolExecutor(max_workers=5) as executor:
            future_to_file = {
                executor.submit(load_config_file, config_file): config_file
                for config_file in config_files
            }

            for future in as_completed(future_to_file):
                try:
                    result = future.result()
                    concurrent_results.append(result)
                except Exception as exc:
                    config_file = future_to_file[future]
                    concurrent_results.append({
                        'file_name': config_file.name,
                        'load_time': 0,
                        'success': False,
                        'error': str(exc)
                    })

        concurrent_time = time.perf_counter() - concurrent_start
        metrics = perf_monitor.get_metrics()

        # Calculate performance metrics
        speedup = sequential_time / concurrent_time if concurrent_time > 0 else 0
        successful_sequential = sum(1 for r in sequential_results if r['success'])
        successful_concurrent = sum(1 for r in concurrent_results if r['success'])

        # Assertions
        assert len(concurrent_results) == len(sequential_results), "Different number of results"
        assert successful_sequential == num_configs, "Sequential loading failed"
        assert successful_concurrent == num_configs, "Concurrent loading failed"
        assert speedup > 1.2, f"Concurrent loading should be faster: {speedup:.2f}x speedup"

        return {
            'num_configs': num_configs,
            'sequential_time': sequential_time,
            'concurrent_time': concurrent_time,
            'speedup': speedup,
            'successful_sequential': successful_sequential,
            'successful_concurrent': successful_concurrent,
            'memory_delta_mb': metrics['memory_delta_mb']
        }

    @pytest.mark.benchmark(group="config")
    def test_config_validation_performance(self, config_manager, perf_monitor):
        """Test configuration validation performance"""
        # Create config schema
        schema = ConfigSchema()

        # Generate configs with varying complexity
        test_configs = [
            # Simple valid config
            {
                'storage': {'data_dir': '/tmp'},
                'api': {'port': 8000}
            },
            # Medium config
            {
                'storage': {
                    'data_dir': '/tmp',
                    'compression': 'snappy',
                    'batch_size': 1000
                },
                'api': {
                    'host': 'localhost',
                    'port': 8000,
                    'debug': False
                },
                'download': {
                    'enabled': True,
                    'rate_limit': 100
                }
            },
            # Complex valid config
            self.large_config_data(),
            # Config with validation errors
            {
                'storage': {
                    'data_dir': '/tmp',
                    'compression': 'invalid_compression',
                    'batch_size': -100
                },
                'api': {
                    'port': 'invalid_port'
                }
            }
        ]

        validation_results = []

        for i, config_data in enumerate(test_configs):
            start_time = time.perf_counter()

            try:
                validated_config = schema.validate(config_data)
                validation_time = time.perf_counter() - start_time
                is_valid = True
                errors = []
            except Exception as e:
                validation_time = time.perf_counter() - start_time
                is_valid = False
                errors = [str(e)]
                validated_config = None

            validation_results.append({
                'config_index': i,
                'validation_time': validation_time,
                'is_valid': is_valid,
                'errors_count': len(errors),
                'config_size': len(str(config_data))
            })

        metrics = perf_monitor.get_metrics()

        # Calculate validation metrics
        avg_validation_time = np.mean([r['validation_time'] for r in validation_results])
        max_validation_time = max([r['validation_time'] for r in validation_results])
        total_valid_configs = sum(1 for r in validation_results if r['is_valid'])

        # Assertions
        assert len(validation_results) == len(test_configs), "Not all configs validated"
        assert total_valid_configs >= 2, "Expected at least 2 valid configs"

        # Validation should be fast
        assert avg_validation_time < 0.1, f"Average validation too slow: {avg_validation_time*1000:.1f}ms"
        assert max_validation_time < 0.5, f"Max validation too slow: {max_validation_time*1000:.1f}ms"

        # Memory usage should be reasonable
        assert metrics['memory_delta_mb'] < 20, f"Memory usage too high: {metrics['memory_delta_mb']:.1f}MB"

        return {
            'validation_results': validation_results,
            'avg_validation_time': avg_validation_time,
            'max_validation_time': max_validation_time,
            'total_valid_configs': total_valid_configs,
            'memory_delta_mb': metrics['memory_delta_mb']
        }

    @pytest.mark.benchmark(group="config")
    def test_config_update_performance(self, config_manager, temp_dir, perf_monitor):
        """Test configuration update and reload performance"""
        # Create initial config
        initial_config = {
            'storage': {
                'data_dir': str(temp_dir),
                'compression': 'snappy',
                'batch_size': 1000
            },
            'api': {'port': 8000}
        }

        config_file = temp_dir / "update_test_config.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(initial_config, f, default_flow_style=False)

        # Load initial config
        config = config_manager.load_config("update_test_config.yaml")
        assert config is not None, "Initial config should load"

        update_results = []

        # Perform multiple updates
        for i in range(10):
            # Update config
            updated_config = initial_config.copy()
            updated_config['storage']['batch_size'] = 1000 + i * 100
            updated_config['api']['port'] = 8000 + i
            updated_config['update_timestamp'] = datetime.now().isoformat()
            updated_config['version'] = f"1.0.{i}"

            # Write updated config
            with open(config_file, 'w') as f:
                yaml.dump(updated_config, f, default_flow_style=False)

            # Test reload performance
            start_time = time.perf_counter()
            reloaded_config = config_manager.load_config("update_test_config.yaml")
            reload_time = time.perf_counter() - start_time

            update_results.append({
                'update_index': i,
                'reload_time': reload_time,
                'new_batch_size': updated_config['storage']['batch_size'],
                'new_port': updated_config['api']['port'],
                'success': reloaded_config is not None
            })

        metrics = perf_monitor.get_metrics()

        # Calculate update metrics
        avg_reload_time = np.mean([r['reload_time'] for r in update_results])
        max_reload_time = max([r['reload_time'] for r in update_results])
        successful_updates = sum(1 for r in update_results if r['success'])

        # Assertions
        assert len(update_results) == 10, "Not all updates performed"
        assert successful_updates == 10, "Some updates failed"

        # Updates should be fast
        assert avg_reload_time < 0.05, f"Average reload too slow: {avg_reload_time*1000:.1f}ms"
        assert max_reload_time < 0.1, f"Max reload too slow: {max_reload_time*1000:.1f}ms"

        # Check latest config values
        latest_result = update_results[-1]
        assert latest_result['new_batch_size'] == 1900, "Latest batch size incorrect"
        assert latest_result['new_port'] == 8009, "Latest port incorrect"

        return {
            'update_results': update_results,
            'avg_reload_time': avg_reload_time,
            'max_reload_time': max_reload_time,
            'successful_updates': successful_updates,
            'memory_delta_mb': metrics['memory_delta_mb']
        }

    @pytest.mark.benchmark(group="config")
    def test_config_memory_efficiency(self, config_manager, temp_dir, perf_monitor):
        """Test configuration memory efficiency"""
        # Create many config files
        num_configs = 50
        config_sizes = []

        for i in range(num_configs):
            # Vary config size
            if i < 20:  # Small configs
                config_data = {
                    'storage': {'data_dir': f'/tmp/data_{i}'},
                    'api': {'port': 8000 + i}
                }
            elif i < 40:  # Medium configs
                config_data = {
                    'storage': {
                        'data_dir': f'/tmp/data_{i}',
                        'compression': 'snappy',
                        'batch_size': 1000 + i * 50
                    },
                    'api': {
                        'host': 'localhost',
                        'port': 8000 + i,
                        'debug': i % 2 == 0
                    },
                    'download': {'enabled': True, 'rate_limit': 100 + i}
                }
            else:  # Large configs
                config_data = self.large_config_data().copy()
                config_data['storage']['data_dir'] = f'/tmp/data_{i}'
                config_data['api']['port'] = 8000 + i

            config_file = temp_dir / f"memory_test_{i}.yaml"
            with open(config_file, 'w') as f:
                yaml.dump(config_data, f, default_flow_style=False)

            config_sizes.append(config_file.stat().st_size)

        # Monitor memory usage
        memory_samples = []

        def sample_memory():
            memory_mb = psutil.Process().memory_info().rss / 1024 / 1024
            memory_samples.append(memory_mb)

        sample_memory()  # Initial sample

        # Load all configs
        loaded_configs = []
        for i in range(num_configs):
            config = config_manager.load_config(f"memory_test_{i}.yaml")
            loaded_configs.append(config)

            # Sample memory every 10 configs
            if i % 10 == 0:
                sample_memory()

        sample_memory()  # Final sample

        metrics = perf_monitor.get_metrics()

        # Calculate memory efficiency metrics
        total_config_size = sum(config_sizes)
        memory_growth = memory_samples[-1] - memory_samples[0]
        memory_per_kb_config = memory_growth * 1024 / total_config_size if total_config_size > 0 else 0
        memory_per_config = memory_growth / num_configs

        # Assertions
        assert len(loaded_configs) == num_configs, "Not all configs loaded"
        assert all(config is not None for config in loaded_configs), "Some configs failed to load"

        # Memory efficiency checks
        assert memory_growth < 100, f"Memory growth too high: {memory_growth:.1f}MB"
        assert memory_per_kb_config < 0.1, f"Memory per KB config too high: {memory_per_kb_config:.6f}MB"
        assert memory_per_config < 2, f"Memory per config too high: {memory_per_config:.3f}MB"

        return {
            'num_configs': num_configs,
            'total_config_size_bytes': total_config_size,
            'memory_growth_mb': memory_growth,
            'memory_per_config_mb': memory_per_config,
            'memory_per_kb_config_mb': memory_per_kb_config,
            'memory_samples_count': len(memory_samples),
            'memory_delta_mb': metrics['memory_delta_mb']
        }

    @pytest.mark.benchmark(group="config")
    def test_config_hot_reload_performance(self, config_manager, temp_dir, perf_monitor):
        """Test hot reload performance for configuration changes"""
        # Create initial config
        config_data = {
            'storage': {
                'data_dir': str(temp_dir),
                'batch_size': 1000
            },
            'api': {'port': 8000}
        }

        config_file = temp_dir / "hot_reload_test.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f, default_flow_style=False)

        # Enable hot reload (mock file watching)
        with patch('watchdog.observers.Observer') as mock_observer:
            mock_observer.return_value.start.return_value = None
            mock_observer.return_value.stop.return_value = None

            # Load initial config
            config = config_manager.load_config("hot_reload_test.yaml")
            initial_batch_size = config.storage.batch_size

            reload_times = []
            reload_count = 20

            # Simulate hot reload scenarios
            for i in range(reload_count):
                # Update config file
                updated_data = config_data.copy()
                updated_data['storage']['batch_size'] = 1000 + i * 50
                updated_data['hot_reload_counter'] = i

                with open(config_file, 'w') as f:
                    yaml.dump(updated_data, f, default_flow_style=False)

                # Simulate hot reload trigger
                start_time = time.perf_counter()
                try:
                    # Force reload (simulating file change detection)
                    config_manager.clear_cache()
                    reloaded_config = config_manager.load_config("hot_reload_test.yaml")
                    reload_time = time.perf_counter() - start_time
                    reload_success = reloaded_config is not None
                except Exception:
                    reload_time = time.perf_counter() - start_time
                    reload_success = False

                reload_times.append(reload_time)

                if not reload_success:
                    pytest.fail(f"Hot reload {i} failed")

            metrics = perf_monitor.get_metrics()

        # Calculate hot reload metrics
        avg_reload_time = np.mean(reload_times)
        max_reload_time = max(reload_times)
        min_reload_time = min(reload_times)
        reload_time_std = np.std(reload_times)

        # Assertions
        assert len(reload_times) == reload_count, "Not all reloads performed"
        assert avg_reload_time > 0, "Reload time should be positive"

        # Hot reload should be fast and consistent
        assert avg_reload_time < 0.1, f"Average hot reload too slow: {avg_reload_time*1000:.1f}ms"
        assert max_reload_time < 0.2, f"Max hot reload too slow: {max_reload_time*1000:.1f}ms"
        assert reload_time_std < 0.05, f"Reload times inconsistent: std={reload_time_std*1000:.1f}ms"

        # Check final config was updated
        final_config = config_manager.load_config("hot_reload_test.yaml")
        assert final_config.storage.batch_size == initial_batch_size + (reload_count - 1) * 50, \
            "Final config not updated correctly"

        return {
            'reload_count': reload_count,
            'avg_reload_time': avg_reload_time,
            'max_reload_time': max_reload_time,
            'min_reload_time': min_reload_time,
            'reload_time_std': reload_time_std,
            'reload_times': reload_times,
            'memory_delta_mb': metrics['memory_delta_mb']
        }