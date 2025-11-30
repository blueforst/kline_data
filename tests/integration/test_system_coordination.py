"""
系统集成协调测试 - 伦敦学派TDD方法

测试重点：
1. 组件间的协作流程
2. 端到端的工作流程验证
3. 系统集成的正确性
4. 错误传播和处理
5. 性能和资源协调
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import tempfile
from pathlib import Path

from kline_data.sdk import KlineClient
from kline_data.sdk import ChunkedDataFeed
from kline_data.storage.data_source_strategy import DataSourceStrategy
from kline_data.storage.models import KlineData
from kline_data.config.manager import ConfigManager
from kline_data.indicators.manager import IndicatorManager


class TestSystemWorkflowIntegration:
    """系统工作流集成测试 - 验证完整业务流程"""

    @pytest.mark.integration
    @pytest.mark.mock
    def test_complete_data_retrieval_workflow(self, mock_config, sample_kline_data):
        """
        测试完整数据获取工作流
        验证：从请求到数据返回的完整流程
        """
        # Arrange - 设置完整的协作契约
        mock_data_fetcher = Mock()
        mock_parquet_reader = Mock()
        mock_metadata_manager = Mock()
        mock_download_manager = Mock()

        # 模拟本地数据存在但不完整
        mock_metadata_manager.has_data.return_value = True
        mock_metadata_manager.get_earliest_time.return_value = datetime(2024, 1, 1)
        mock_metadata_manager.get_latest_time.return_value = datetime(2024, 1, 1, 12, 0, 0)

        # 本地数据返回前12小时
        mock_parquet_reader.read_range.return_value = sample_kline_data.head(12)

        # 下载管理器处理缺失数据
        mock_download_manager.download_range.return_value = True

        # 设置协作序列验证
        interaction_sequence = []

        def track_read_range(*args, **kwargs):
            interaction_sequence.append(('read_range', args, kwargs))
            return sample_kline_data.head(12)

        def track_download(*args, **kwargs):
            interaction_sequence.append(('download', args, kwargs))
            return True

        mock_parquet_reader.read_range.side_effect = track_read_range
        mock_download_manager.download_range.side_effect = track_download

        # Act - 执行完整工作流
        with patch('sdk.client.DataFetcher', return_value=mock_data_fetcher), \
             patch('sdk.client.MetadataManager', return_value=mock_metadata_manager), \
             patch('sdk.client.ParquetReader', return_value=mock_parquet_reader), \
             patch('sdk.client.DownloadManager', return_value=mock_download_manager):

            client = KlineClient(mock_config)

            # 请求24小时数据（本地只有前12小时）
            start_time = datetime(2024, 1, 1)
            end_time = datetime(2024, 1, 2)

            result = client.get_klines(start_time, end_time)

        # Assert - 验证工作流协作
        # 1. 首先检查本地数据
        mock_metadata_manager.has_data.assert_called_with('BTC/USDT', '1h')

        # 2. 获取本地数据范围
        mock_metadata_manager.get_earliest_time.assert_called_with('BTC/USDT', '1h')
        mock_metadata_manager.get_latest_time.assert_called_with('BTC/USDT', '1h')

        # 3. 读取本地数据
        assert len(interaction_sequence) >= 1, "应该有数据读取交互"
        read_call = next(call for call in interaction_sequence if call[0] == 'read_range')
        assert read_call[1][0] == start_time, "读取开始时间应该正确"
        assert read_call[1][1] == end_time, "读取结束时间应该正确"

        # 4. 验证返回结果
        assert isinstance(result, pd.DataFrame), "应该返回DataFrame"
        assert len(result) == 12, "应该返回12条本地数据"

    @pytest.mark.integration
    @pytest.mark.mock
    def test_chunked_data_feed_integration(self, mock_config):
        """
        测试分块数据流集成
        验证：数据流的完整迭代过程
        """
        # Arrange - 设置数据流协作
        total_chunks = 3
        chunk_size = 10

        mock_parquet_reader = Mock()
        chunks = []

        def mock_read_range(start_time, end_time):
            # 模拟返回不同的数据块
            chunk_data = pd.DataFrame({
                'timestamp': pd.date_range(start_time, periods=chunk_size, freq='1h'),
                'open': np.random.uniform(40000, 41000, chunk_size),
                'high': np.random.uniform(41000, 42000, chunk_size),
                'low': np.random.uniform(39000, 40000, chunk_size),
                'close': np.random.uniform(40000, 41000, chunk_size),
                'volume': np.random.uniform(100, 1000, chunk_size)
            })
            chunks.append(len(chunk_data))
            return chunk_data

        mock_parquet_reader.read_range.side_effect = mock_read_range

        # Act - 执行数据流集成
        with patch('sdk.data_feed.ParquetReader', return_value=mock_parquet_reader):
            feed = ChunkedDataFeed(
                exchange='binance',
                symbol='BTC/USDT',
                start_time=datetime(2024, 1, 1),
                end_time=datetime(2024, 1, 3),  # 48小时
                interval='1h',
                chunk_size=chunk_size
            )

            # 迭代所有数据块
            result_chunks = list(feed)

        # Assert - 验证数据流集成
        assert len(result_chunks) == total_chunks, f"应该有{total_chunks}个数据块"
        assert mock_parquet_reader.read_range.call_count == total_chunks, \
            f"应该调用read_range {total_chunks}次"

        # 验证每个块的协作
        for i, chunk in enumerate(result_chunks):
            assert isinstance(chunk, pd.DataFrame), f"第{i+1}块应该是DataFrame"
            assert len(chunk) == chunk_size, f"第{i+1}块应该有{chunk_size}条数据"

    @pytest.mark.integration
    @pytest.mark.mock
    def test_indicator_calculation_integration(self, mock_config, sample_kline_data):
        """
        测试指标计算集成
        验证：指标计算与数据处理的协作
        """
        # Arrange - 设置指标计算协作
        close_prices = sample_kline_data['close'].values
        manager = IndicatorManager()

        # 注册多个指标
        manager.register_indicator('sma_10', Mock())
        manager.register_indicator('sma_20', Mock())
        manager.register_indicator('rsi', Mock())

        # 设置指标计算契约
        def mock_calculate_sma(data):
            return np.random.uniform(40000, 41000, len(data) - 9)

        def mock_calculate_sma_20(data):
            return np.random.uniform(40000, 41000, len(data) - 19)

        def mock_calculate_rsi(data):
            return np.random.uniform(30, 70, len(data) - 13)

        manager.indicators['sma_10'].calculate.side_effect = mock_calculate_sma
        manager.indicators['sma_20'].calculate.side_effect = mock_calculate_sma_20
        manager.indicators['rsi'].calculate.side_effect = mock_calculate_rsi

        # Act - 执行指标计算集成
        results = manager.calculate_batch(
            close_prices,
            ['sma_10', 'sma_20', 'rsi']
        )

        # Assert - 验证指标计算协作
        assert len(results) == 3, "应该返回3个指标结果"
        assert 'sma_10' in results, "应该包含sma_10指标"
        assert 'sma_20' in results, "应该包含sma_20指标"
        assert 'rsi' in results, "应该包含rsi指标"

        # 验证每个指标的计算调用
        manager.indicators['sma_10'].calculate.assert_called_once_with(close_prices)
        manager.indicators['sma_20'].calculate.assert_called_once_with(close_prices)
        manager.indicators['rsi'].calculate.assert_called_once_with(close_prices)

    @pytest.mark.integration
    @pytest.mark.mock
    def test_config_manager_integration(self, mock_config_file):
        """
        测试配置管理器集成
        验证：配置加载和使用的完整流程
        """
        # Arrange - 准备配置数据
        config_data = {
            'exchange': 'binance',
            'symbol': 'BTC/USDT',
            'interval': '1h',
            'data_dir': '/data/kline',
            'cache_dir': '/cache/kline',
            'api': {
                'rate_limit': 1200,
                'timeout': 30
            }
        }

        # Act - 执行配置管理集成
        with patch('builtins.open', mock_open(read_data=str(config_data))), \
             patch('pathlib.Path.exists', return_value=True), \
             patch('yaml.safe_load', return_value=config_data):

            # 加载配置
            manager = ConfigManager()
            config = manager.load(mock_config_file)

            # 获取配置值
            exchange = manager.get('exchange')
            symbol = manager.get('symbol')
            rate_limit = manager.get('api.rate_limit')

        # Assert - 验证配置集成
        assert exchange == 'binance', "应该正确获取exchange配置"
        assert symbol == 'BTC/USDT', "应该正确获取symbol配置"
        assert rate_limit == 1200, "应该正确获取嵌套配置"


class TestSystemErrorHandling:
    """系统错误处理集成测试"""

    @pytest.mark.integration
    @pytest.mark.mock
    def test_cascading_error_handling(self, mock_config):
        """
        测试级联错误处理
        验证：一个组件错误如何影响整个系统
        """
        # Arrange - 设置错误传播场景
        mock_data_fetcher = Mock()
        mock_parquet_reader = Mock()
        mock_metadata_manager = Mock()

        # 模拟元数据管理器错误
        mock_metadata_manager.has_data.side_effect = Exception("Metadata access failed")

        # Act & Assert - 验证错误传播
        with patch('sdk.client.DataFetcher', return_value=mock_data_fetcher), \
             patch('sdk.client.MetadataManager', return_value=mock_metadata_manager), \
             patch('sdk.client.ParquetReader', return_value=mock_parquet_reader):

            client = KlineClient(mock_config)

            # 错误应该传播到客户端
            with pytest.raises(Exception, match="Metadata access failed"):
                client.get_klines(datetime(2024, 1, 1), datetime(2024, 1, 2))

    @pytest.mark.integration
    @pytest.mark.mock
    def test_partial_failure_recovery(self, mock_config, sample_kline_data):
        """
        测试部分失败恢复
        验证：系统在部分组件失败时的恢复能力
        """
        # Arrange - 设置部分失败场景
        mock_data_fetcher = Mock()
        mock_parquet_reader = Mock()
        mock_metadata_manager = Mock()

        # 本地数据检查成功，但读取部分失败
        mock_metadata_manager.has_data.return_value = True

        # 第一次调用成功，后续调用失败
        call_count = 0
        def failing_read_range(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return sample_kline_data.head(10)
            else:
                raise Exception("Read failed")

        mock_parquet_reader.read_range.side_effect = failing_read_range

        # Act & Assert - 验证部分失败处理
        with patch('sdk.client.DataFetcher', return_value=mock_data_fetcher), \
             patch('sdk.client.MetadataManager', return_value=mock_metadata_manager), \
             patch('sdk.client.ParquetReader', return_value=mock_parquet_reader):

            client = KlineClient(mock_config)

            # 第一次调用应该成功
            result1 = client.get_klines(datetime(2024, 1, 1), datetime(2024, 1, 1, 10, 0, 0))
            assert len(result1) == 10, "第一次调用应该成功"

            # 第二次调用应该失败
            with pytest.raises(Exception, match="Read failed"):
                client.get_klines(datetime(2024, 1, 1), datetime(2024, 1, 2))

    @pytest.mark.integration
    @pytest.mark.mock
    def test_resource_exhaustion_handling(self, mock_config):
        """
        测试资源耗尽处理
        验证：系统在资源不足时的行为
        """
        # Arrange - 模拟内存不足
        mock_parquet_reader = Mock()

        def memory_error_read(*args, **kwargs):
            raise MemoryError("Not enough memory")

        mock_parquet_reader.read_range.side_effect = memory_error_read

        # Act & Assert - 验证资源耗尽处理
        with patch('sdk.client.DataFetcher'), \
             patch('sdk.client.MetadataManager'), \
             patch('sdk.client.ParquetReader', return_value=mock_parquet_reader):

            client = KlineClient(mock_config)

            # 内存错误应该被适当处理
            with pytest.raises(MemoryError, match="Not enough memory"):
                client.get_klines(datetime(2024, 1, 1), datetime(2024, 1, 2))


class TestSystemPerformanceCoordination:
    """系统性能协调测试"""

    @pytest.mark.integration
    @pytest.mark.performance
    def test_large_dataset_processing_performance(self, mock_config, performance_timer):
        """
        测试大数据集处理性能协调
        验证：多组件协作处理大数据时的性能
        """
        # Arrange - 准备大数据集
        large_data = pd.DataFrame({
            'timestamp': pd.date_range('2020-01-01', periods=10000, freq='1h'),
            'open': np.random.uniform(30000, 50000, 10000),
            'high': np.random.uniform(30000, 50000, 10000),
            'low': np.random.uniform(30000, 50000, 10000),
            'close': np.random.uniform(30000, 50000, 10000),
            'volume': np.random.uniform(100, 1000, 10000)
        })

        mock_parquet_reader = Mock()
        mock_parquet_reader.read_range.return_value = large_data

        # Act - 测试性能协调
        performance_timer.start()

        with patch('sdk.client.DataFetcher'), \
             patch('sdk.client.MetadataManager'), \
             patch('sdk.client.ParquetReader', return_value=mock_parquet_reader):

            client = KlineClient(mock_config)

            # 处理大数据集
            start_time = datetime(2020, 1, 1)
            end_time = datetime(2021, 2, 1)

            result = client.get_klines(start_time, end_time)

        performance_timer.stop()

        # Assert - 验证性能协调结果
        assert len(result) == 10000, "应该处理所有数据"
        assert performance_timer.elapsed < 2.0, "大数据集处理应该在2秒内完成"

    @pytest.mark.integration
    @pytest.mark.performance
    def test_concurrent_operations_coordination(self, mock_config, performance_timer):
        """
        测试并发操作协调
        验证：多个并发操作的协调和性能
        """
        # Arrange - 准备并发测试
        mock_parquet_reader = Mock()

        def create_mock_data(start_idx, size):
            return pd.DataFrame({
                'timestamp': pd.date_range('2024-01-01', periods=size, freq='1h'),
                'open': np.random.uniform(40000, 41000, size),
                'high': np.random.uniform(41000, 42000, size),
                'low': np.random.uniform(39000, 40000, size),
                'close': np.random.uniform(40000, 41000, size),
                'volume': np.random.uniform(100, 1000, size)
            })

        call_count = 0
        def concurrent_read(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return create_mock_data(call_count, 100)

        mock_parquet_reader.read_range.side_effect = concurrent_read

        # Act - 测试并发协调
        performance_timer.start()

        with patch('sdk.client.DataFetcher'), \
             patch('sdk.client.MetadataManager'), \
             patch('sdk.client.ParquetReader', return_value=mock_parquet_reader):

            client = KlineClient(mock_config)

            # 模拟并发请求
            import threading
            results = []

            def worker():
                result = client.get_klines(datetime(2024, 1, 1), datetime(2024, 1, 2))
                results.append(result)

            threads = [threading.Thread(target=worker) for _ in range(3)]

            for t in threads:
                t.start()

            for t in threads:
                t.join()

        performance_timer.stop()

        # Assert - 验证并发协调结果
        assert len(results) == 3, "应该有3个结果"
        assert all(len(result) == 100 for result in results), "每个结果应该有100条数据"
        assert call_count == 3, "应该调用3次读取操作"
        assert performance_timer.elapsed < 1.0, "并发操作应该在1秒内完成"


class TestSystemDataIntegrity:
    """系统数据完整性集成测试"""

    @pytest.mark.integration
    @pytest.mark.mock
    def test_data_consistency_across_components(self, mock_config, sample_kline_data):
        """
        测试跨组件数据一致性
        验证：数据在不同组件间传递时的一致性
        """
        # Arrange - 设置数据一致性测试
        original_data = sample_kline_data.copy()

        mock_parquet_reader = Mock()
        mock_parquet_reader.read_range.return_value = original_data

        # Act - 验证数据一致性
        with patch('sdk.client.DataFetcher'), \
             patch('sdk.client.MetadataManager'), \
             patch('sdk.client.ParquetReader', return_value=mock_parquet_reader):

            # 通过客户端获取数据
            client = KlineClient(mock_config)
            result = client.get_klines(datetime(2024, 1, 1), datetime(2024, 1, 2))

            # 通过数据流获取数据
            feed = ChunkedDataFeed(
                exchange='binance',
                symbol='BTC/USDT',
                start_time=datetime(2024, 1, 1),
                end_time=datetime(2024, 1, 2),
                interval='1h',
                chunk_size=50
            )
            feed_chunks = list(feed)

            # 计算指标验证数据一致性
            manager = IndicatorManager()
            manager.register_indicator('sma', Mock())

            # 设置SMA计算保持数据一致性
            def consistent_sma(data):
                return np.mean(data[-20:]) if len(data) >= 20 else np.mean(data)

            manager.indicators['sma'].calculate.side_effect = consistent_sma

            sma_result = manager.calculate(result['close'].values, 'sma')

        # Assert - 验证数据一致性
        # 客户端返回的数据应该与原始数据一致
        pd.testing.assert_frame_equal(result.sort_values('timestamp').reset_index(drop=True),
                                     original_data.sort_values('timestamp').reset_index(drop=True),
                                     check_names=False)

        # 数据流的总数据应该与原始数据一致
        combined_feed_data = pd.concat(feed_chunks, ignore_index=True)
        assert len(combined_feed_data) == len(original_data), "数据流数据量应该与原始数据一致"

        # 指标计算应该基于一致的数据
        assert manager.indicators['sma'].calculate.called, "SMA应该被调用"
        assert isinstance(sma_result, (np.ndarray, list)), "SMA结果应该是数组或列表"

    @pytest.mark.integration
    @pytest.mark.mock
    def test_timestamp_consistency(self, mock_config):
        """
        测试时间戳一致性
        验证：时间戳在系统中的正确处理
        """
        # Arrange - 创建时间戳测试数据
        base_timestamp = datetime(2024, 1, 1)
        time_stamps = pd.date_range(base_timestamp, periods=24, freq='1h')

        test_data = pd.DataFrame({
            'timestamp': time_stamps,
            'open': 40000.0,
            'high': 41000.0,
            'low': 39000.0,
            'close': 40500.0,
            'volume': 1000.0
        })

        mock_parquet_reader = Mock()
        mock_parquet_reader.read_range.return_value = test_data

        # Act - 验证时间戳一致性
        with patch('sdk.client.DataFetcher'), \
             patch('sdk.client.MetadataManager'), \
             patch('sdk.client.ParquetReader', return_value=mock_parquet_reader):

            client = KlineClient(mock_config)
            result = client.get_klines(base_timestamp, base_timestamp + timedelta(hours=24))

        # Assert - 验证时间戳一致性
        assert len(result) == 24, "应该有24条数据"
        assert pd.api.types.is_datetime64_any_dtype(result['timestamp']), "时间戳应该是datetime类型"

        # 验证时间戳的连续性和顺序
        result_sorted = result.sort_values('timestamp')
        time_diffs = result_sorted['timestamp'].diff().dropna()
        expected_diff = pd.Timedelta(hours=1)

        assert all(time_diffs == expected_diff), "时间戳应该是连续的每小时"

        # 验证时间戳范围
        assert result['timestamp'].min() == base_timestamp, "最小时间戳应该正确"
        assert result['timestamp'].max() == base_timestamp + timedelta(hours=23), "最大时间戳应该正确"

    @pytest.mark.integration
    @pytest.mark.mock
    def test_numeric_precision_preservation(self, mock_config):
        """
        测试数值精度保持
        验证：浮点数精度在系统中的保持
        """
        # Arrange - 创建高精度测试数据
        high_precision_data = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=10, freq='1h'),
            'open': 40000.123456789,
            'high': 41000.987654321,
            'low': 39000.111222333,
            'close': 40500.555666777,
            'volume': 1500.123456789
        })

        mock_parquet_reader = Mock()
        mock_parquet_reader.read_range.return_value = high_precision_data

        # Act - 验证数值精度
        with patch('sdk.client.DataFetcher'), \
             patch('sdk.client.MetadataManager'), \
             patch('sdk.client.ParquetReader', return_value=mock_parquet_reader):

            client = KlineClient(mock_config)
            result = client.get_klines(datetime(2024, 1, 1), datetime(2024, 1, 1, 10, 0, 0))

        # Assert - 验证精度保持
        tolerance = 1e-10  # 设置精度容忍度
        assert abs(result['open'].iloc[0] - 40000.123456789) < tolerance, "开盘价精度应该保持"
        assert abs(result['high'].iloc[0] - 41000.987654321) < tolerance, "最高价精度应该保持"
        assert abs(result['low'].iloc[0] - 39000.111222333) < tolerance, "最低价精度应该保持"
        assert abs(result['close'].iloc[0] - 40500.555666777) < tolerance, "收盘价精度应该保持"
        assert abs(result['volume'].iloc[0] - 1500.123456789) < tolerance, "成交量精度应该保持"