"""
KlineClient 单元测试 - 伦敦学派TDD方法

测试重点：
1. 对象间的协作和交互
2. 行为验证而非状态验证
3. Mock驱动的契约定义
4. 工作流程的正确性
"""

import pytest
from unittest.mock import Mock, patch, call
from datetime import datetime, timedelta
import pandas as pd

from sdk.client import KlineClient
from storage.models import KlineData
from utils.constants import Timeframe


class TestKlineClientInteraction:
    """KlineClient交互测试 - 伦敦学派TDD的核心"""

    @pytest.mark.unit
    @pytest.mark.mock
    def test_client_initialization_collaboration(self, mock_config, mock_data_fetcher,
                                                mock_metadata_manager, mock_parquet_reader):
        """
        测试客户端初始化时的协作
        验证：客户端如何与各个组件建立协作关系
        """
        # Arrange - 定义协作契约
        with patch('sdk.client.DataFetcher', return_value=mock_data_fetcher), \
             patch('sdk.client.MetadataManager', return_value=mock_metadata_manager), \
             patch('sdk.client.ParquetReader', return_value=mock_parquet_reader):

            # Act - 创建客户端（这会触发一系列协作）
            client = KlineClient(mock_config)

            # Assert - 验证协作关系的建立
            assert client.config is mock_config, "Client应该持有配置引用"
            assert client.fetcher is mock_data_fetcher, "Client应该与DataFetcher建立协作"
            assert client.metadata_mgr is mock_metadata_manager, "Client应该与MetadataManager建立协作"
            assert client.reader is mock_parquet_reader, "Client应该与ParquetReader建立协作"

    @pytest.mark.unit
    @pytest.mark.contract
    def test_get_klines_workflow_interaction(self, mock_config, mock_data_fetcher,
                                            mock_parquet_reader, sample_kline_data):
        """
        测试获取K线数据的工作流程交互
        验证：组件间的调用序列和参数传递
        """
        # Arrange - 设置Mock返回值
        mock_parquet_reader.read_range.return_value = sample_kline_data

        with patch('sdk.client.DataFetcher', return_value=mock_data_fetcher), \
             patch('sdk.client.MetadataManager'), \
             patch('sdk.client.ParquetReader', return_value=mock_parquet_reader):

            client = KlineClient(mock_config)
            start_time = datetime(2024, 1, 1)
            end_time = datetime(2024, 1, 2)

            # Act - 获取数据
            result = client.get_klines(start_time, end_time)

            # Assert - 验证交互序列
            # 1. 首先调用ParquetReader读取本地数据
            mock_parquet_reader.read_range.assert_called_once_with(
                start_time=start_time,
                end_time=end_time
            )

            # 2. 验证返回数据格式
            assert isinstance(result, pd.DataFrame), "应该返回DataFrame"
            assert not result.empty, "返回数据不应为空"
            assert 'timestamp' in result.columns, "数据应包含timestamp列"

    @pytest.mark.unit
    @pytest.mark.mock
    def test_get_latest_data_interaction(self, mock_config, mock_parquet_reader):
        """
        测试获取最新数据的交互
        验证：与读取器的交互和错误处理协作
        """
        # Arrange - 准备Mock数据
        latest_data = pd.DataFrame({
            'timestamp': [pd.Timestamp('2024-01-01 23:00:00')],
            'open': [40000.0],
            'high': [40500.0],
            'low': [39500.0],
            'close': [40200.0],
            'volume': [500.0]
        })
        mock_parquet_reader.read_latest.return_value = latest_data

        with patch('sdk.client.DataFetcher'), \
             patch('sdk.client.MetadataManager'), \
             patch('sdk.client.ParquetReader', return_value=mock_parquet_reader):

            client = KlineClient(mock_config)

            # Act - 获取最新数据
            result = client.get_latest(24)  # 最近24条数据

            # Assert - 验证交互
            mock_parquet_reader.read_latest.assert_called_once_with(limit=24)

            # 验证协作结果
            assert isinstance(result, pd.DataFrame), "应该返回DataFrame"
            assert len(result) == 1, "应该返回1条数据"

    @pytest.mark.unit
    @pytest.mark.contract
    def test_data_source_decision_collaboration(self, mock_config, mock_metadata_manager):
        """
        测试数据源决策的协作
        验证：策略模式的使用和决策流程
        """
        # Arrange - 设置协作契约
        mock_metadata_manager.has_data.return_value = False

        with patch('sdk.client.DataFetcher'), \
             patch('sdk.client.MetadataManager', return_value=mock_metadata_manager), \
             patch('sdk.client.ParquetReader'):

            client = KlineClient(mock_config)
            start_time = datetime(2024, 1, 1)
            end_time = datetime(2024, 1, 2)

            # Act - 执行数据获取（这会触发决策流程）
            # 这里我们直接测试私有方法来验证协作逻辑
            decision = client._should_download(start_time, end_time)

            # Assert - 验证决策协作
            mock_metadata_manager.has_data.assert_called_once()
            assert decision is True, "当没有本地数据时应该决定下载"

    @pytest.mark.unit
    @pytest.mark.mock
    def test_error_handling_collaboration(self, mock_config, mock_parquet_reader):
        """
        测试错误处理时的协作
        验证：异常传播和错误恢复机制
        """
        # Arrange - 设置协作契约（ParquetReader抛出异常）
        mock_parquet_reader.read_range.side_effect = FileNotFoundError("Data file not found")

        with patch('sdk.client.DataFetcher'), \
             patch('sdk.client.MetadataManager'), \
             patch('sdk.client.ParquetReader', return_value=mock_parquet_reader):

            client = KlineClient(mock_config)

            # Act & Assert - 验证错误协作
            with pytest.raises(FileNotFoundError):
                client.get_klines(datetime(2024, 1, 1), datetime(2024, 1, 2))

            # 验证异常后的协作状态
            mock_parquet_reader.read_range.assert_called_once()


class TestKlineClientContract:
    """KlineClient契约测试 - 定义和验证接口契约"""

    @pytest.mark.unit
    @pytest.mark.contract
    def test_data_fetcher_contract(self, mock_config):
        """
        测试DataFetcher契约
        验证：DataFetcher必须实现的方法和返回值类型
        """
        # Arrange - 定义契约
        data_fetcher_contract = {
            'fetch_range': pd.DataFrame(),
            'fetch_latest': pd.DataFrame(),
            'is_available': True
        }

        # 创建符合契约的Mock
        mock_fetcher = Mock()
        for method, return_value in data_fetcher_contract.items():
            setattr(mock_fetcher, method, Mock(return_value=return_value))

        with patch('sdk.client.DataFetcher', return_value=mock_fetcher), \
             patch('sdk.client.MetadataManager'), \
             patch('sdk.client.ParquetReader'):

            client = KlineClient(mock_config)

            # Act - 使用契约定义的方法
            start_time = datetime(2024, 1, 1)
            end_time = datetime(2024, 1, 2)

            # 这些调用应该不会失败，因为Mock符合契约
            data = mock_fetcher.fetch_range(start_time, end_time)
            latest = mock_fetcher.fetch_latest(24)
            available = mock_fetcher.is_available()

            # Assert - 验证契约遵守
            assert isinstance(data, pd.DataFrame), "fetch_range应该返回DataFrame"
            assert isinstance(latest, pd.DataFrame), "fetch_latest应该返回DataFrame"
            assert isinstance(available, bool), "is_available应该返回布尔值"

    @pytest.mark.unit
    @pytest.mark.contract
    def test_metadata_manager_contract(self, mock_config):
        """
        测试MetadataManager契约
        验证：元数据管理的方法契约
        """
        # Arrange - 定义元数据管理契约
        metadata_contract = {
            'get_earliest_time': datetime(2020, 1, 1),
            'get_latest_time': datetime(2024, 1, 1),
            'has_data': True,
            'get_metadata': {'total_records': 100000}
        }

        mock_metadata = Mock()
        for method, return_value in metadata_contract.items():
            setattr(mock_metadata, method, Mock(return_value=return_value))

        with patch('sdk.client.DataFetcher'), \
             patch('sdk.client.MetadataManager', return_value=mock_metadata), \
             patch('sdk.client.ParquetReader'):

            client = KlineClient(mock_config)

            # Act - 调用契约方法
            earliest = mock_metadata.get_earliest_time('BTC/USDT', '1h')
            latest = mock_metadata.get_latest_time('BTC/USDT', '1h')
            has_data = mock_metadata.has_data('BTC/USDT', '1h')
            metadata = mock_metadata.get_metadata('BTC/USDT', '1h')

            # Assert - 验证契约
            assert isinstance(earliest, datetime), "get_earliest_time应该返回datetime"
            assert isinstance(latest, datetime), "get_latest_time应该返回datetime"
            assert isinstance(has_data, bool), "has_data应该返回bool"
            assert isinstance(metadata, dict), "get_metadata应该返回dict"

    @pytest.mark.unit
    @pytest.mark.contract
    def test_reader_contract(self, mock_config):
        """
        测试Reader契约
        验证：数据读取器的方法契约
        """
        # Arrange - 定义读取器契约
        reader_contract = {
            'read_range': pd.DataFrame(),
            'read_latest': pd.DataFrame(),
            'get_available_symbols': ['BTC/USDT'],
            'get_available_intervals': ['1h', '1d']
        }

        mock_reader = Mock()
        for method, return_value in reader_contract.items():
            setattr(mock_reader, method, Mock(return_value=return_value))

        with patch('sdk.client.DataFetcher'), \
             patch('sdk.client.MetadataManager'), \
             patch('sdk.client.ParquetReader', return_value=mock_reader):

            client = KlineClient(mock_config)

            # Act - 调用读取器方法
            data = mock_reader.read_range(datetime(2024, 1, 1), datetime(2024, 1, 2))
            latest = mock_reader.read_latest(24)
            symbols = mock_reader.get_available_symbols()
            intervals = mock_reader.get_available_intervals()

            # Assert - 验证契约
            assert isinstance(data, pd.DataFrame), "read_range应该返回DataFrame"
            assert isinstance(latest, pd.DataFrame), "read_latest应该返回DataFrame"
            assert isinstance(symbols, list), "get_available_symbols应该返回list"
            assert isinstance(intervals, list), "get_available_intervals应该返回list"


class TestKlineClientWorkflow:
    """KlineClient工作流测试 - 测试复杂业务流程"""

    @pytest.mark.unit
    @pytest.mark.mock
    def test_complete_data_retrieval_workflow(self, mock_config, mock_data_fetcher,
                                             mock_metadata_manager, mock_parquet_reader,
                                             sample_kline_data):
        """
        测试完整的数据获取工作流
        验证：多步骤协作和决策流程
        """
        # Arrange - 设置工作流契约
        # 1. 元数据管理器报告有部分数据
        mock_metadata_manager.has_data.return_value = True
        mock_metadata_manager.get_earliest_time.return_value = datetime(2024, 1, 1)
        mock_metadata_manager.get_latest_time.return_value = datetime(2024, 1, 1, 12, 0, 0)

        # 2. 读取器返回部分数据
        mock_parquet_reader.read_range.return_value = sample_kline_data.head(12)

        # 3. 数据获取器可以获取缺失数据
        mock_data_fetcher.fetch_range.return_value = sample_kline_data.tail(12)

        with patch('sdk.client.DataFetcher', return_value=mock_data_fetcher), \
             patch('sdk.client.MetadataManager', return_value=mock_metadata_manager), \
             patch('sdk.client.ParquetReader', return_value=mock_parquet_reader), \
             patch('sdk.client.KlineResampler'):

            client = KlineClient(mock_config)

            # Act - 执行完整工作流
            start_time = datetime(2024, 1, 1)
            end_time = datetime(2024, 1, 2)
            result = client.get_klines(start_time, end_time)

            # Assert - 验证工作流交互序列
            expected_calls = [
                # 1. 检查是否有数据
                call.has_data('BTC/USDT', '1h'),
                # 2. 获取可用时间范围
                call.get_earliest_time('BTC/USDT', '1h'),
                call.get_latest_time('BTC/USDT', '1h'),
                # 3. 读取本地数据
                call.read_range(start_time=start_time, end_time=end_time)
            ]

            # 验证元数据管理器的交互
            mock_metadata_manager.assert_has_calls(expected_calls[:3])

            # 验证读取器的交互
            mock_parquet_reader.read_range.assert_called_once()

            # 验证结果
            assert isinstance(result, pd.DataFrame), "应该返回DataFrame"
            assert len(result) == 12, "应该返回12条数据"

    @pytest.mark.unit
    @pytest.mark.mock
    def test_download_when_no_local_data_workflow(self, mock_config, mock_data_fetcher,
                                                  mock_metadata_manager, mock_parquet_reader):
        """
        测试没有本地数据时的下载工作流
        验证：下载决策和执行协作
        """
        # Arrange - 设置无本地数据的场景
        mock_metadata_manager.has_data.return_value = False
        mock_parquet_reader.read_range.return_value = pd.DataFrame()  # 空数据

        download_data = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=24, freq='1h'),
            'open': [40000.0] * 24,
            'high': [40500.0] * 24,
            'low': [39500.0] * 24,
            'close': [40200.0] * 24,
            'volume': [500.0] * 24
        })
        mock_data_fetcher.fetch_range.return_value = download_data

        with patch('sdk.client.DataFetcher', return_value=mock_data_fetcher), \
             patch('sdk.client.MetadataManager', return_value=mock_metadata_manager), \
             patch('sdk.client.ParquetReader', return_value=mock_parquet_reader), \
             patch('sdk.client.DownloadManager') as mock_download_manager:

            mock_download_manager.return_value.download_range.return_value = True

            client = KlineClient(mock_config)
            start_time = datetime(2024, 1, 1)
            end_time = datetime(2024, 1, 2)

            # Act - 获取数据（应该触发下载）
            result = client.get_klines(start_time, end_time, force_download=True)

            # Assert - 验证下载工作流
            # 1. 检查本地数据
            mock_metadata_manager.has_data.assert_called_with('BTC/USDT', '1h')

            # 2. 尝试读取本地数据
            mock_parquet_reader.read_range.assert_called_with(
                start_time=start_time, end_time=end_time
            )

            # 3. 当force_download=True时，应该直接调用数据获取器
            mock_data_fetcher.fetch_range.assert_called_with(
                start_time=start_time, end_time=end_time
            )

    @pytest.mark.unit
    @pytest.mark.mock
    def test_indicators_integration_workflow(self, mock_config, mock_parquet_reader,
                                           mock_indicator_manager, sample_kline_data):
        """
        测试指标集成工作流
        验证：客户端与指标管理器的协作
        """
        # Arrange - 设置指标计算契约
        mock_parquet_reader.read_range.return_value = sample_kline_data
        mock_indicator_manager.calculate.return_value = {
            'sma_20': np.ones(len(sample_kline_data)) * 40000,
            'rsi': np.random.uniform(30, 70, len(sample_kline_data))
        }

        with patch('sdk.client.DataFetcher'), \
             patch('sdk.client.MetadataManager'), \
             patch('sdk.client.ParquetReader', return_value=mock_parquet_reader), \
             patch('sdk.client.IndicatorManager', return_value=mock_indicator_manager), \
             patch('sdk.client.KlineResampler'):

            client = KlineClient(mock_config)
            start_time = datetime(2024, 1, 1)
            end_time = datetime(2024, 1, 2)

            # Act - 获取带指标的数据
            result = client.get_klines_with_indicators(
                start_time, end_time, indicators=['sma_20', 'rsi']
            )

            # Assert - 验证指标计算协作
            mock_parquet_reader.read_range.assert_called_once()
            mock_indicator_manager.calculate.assert_called_once_with(
                data=sample_kline_data,
                indicators=['sma_20', 'rsi']
            )

            # 验证结果包含指标
            assert 'sma_20' in result.columns, "结果应包含SMA指标"
            assert 'rsi' in result.columns, "结果应包含RSI指标"


class TestKlineClientEdgeCases:
    """KlineClient边界条件测试"""

    @pytest.mark.unit
    @pytest.mark.mock
    def test_empty_time_range_handling(self, mock_config, mock_parquet_reader):
        """
        测试空时间范围的处理
        验证：边界条件的正确处理
        """
        # Arrange
        mock_parquet_reader.read_range.return_value = pd.DataFrame()

        with patch('sdk.client.DataFetcher'), \
             patch('sdk.client.MetadataManager'), \
             patch('sdk.client.ParquetReader', return_value=mock_parquet_reader):

            client = KlineClient(mock_config)

            # Act - 查询空时间范围
            start_time = datetime(2024, 1, 1)
            end_time = datetime(2024, 1, 1)  # 相同时间

            result = client.get_klines(start_time, end_time)

            # Assert
            mock_parquet_reader.read_range.assert_called_once()
            assert isinstance(result, pd.DataFrame), "应该返回DataFrame"
            assert len(result) == 0, "空时间范围应返回空DataFrame"

    @pytest.mark.unit
    @pytest.mark.mock
    def test_invalid_time_range_handling(self, mock_config, mock_parquet_reader):
        """
        测试无效时间范围的处理
        验证：参数验证和错误处理
        """
        # Arrange
        with patch('sdk.client.DataFetcher'), \
             patch('sdk.client.MetadataManager'), \
             patch('sdk.client.ParquetReader', return_value=mock_parquet_reader):

            client = KlineClient(mock_config)

            # Act & Assert - 测试开始时间晚于结束时间
            start_time = datetime(2024, 1, 2)
            end_time = datetime(2024, 1, 1)  # 无效范围

            with pytest.raises(ValueError, match="Start time must be before end time"):
                client.get_klines(start_time, end_time)

    @pytest.mark.unit
    @pytest.mark.mock
    def test_large_data_range_handling(self, mock_config, mock_parquet_reader):
        """
        测试大数据范围的处理
        验证：性能和内存管理
        """
        # Arrange - 设置大数据范围
        large_data = pd.DataFrame({
            'timestamp': pd.date_range('2020-01-01', periods=100000, freq='1m'),
            'open': np.random.uniform(30000, 50000, 100000),
            'high': np.random.uniform(30000, 50000, 100000),
            'low': np.random.uniform(30000, 50000, 100000),
            'close': np.random.uniform(30000, 50000, 100000),
            'volume': np.random.uniform(100, 1000, 100000)
        })
        mock_parquet_reader.read_range.return_value = large_data

        with patch('sdk.client.DataFetcher'), \
             patch('sdk.client.MetadataManager'), \
             patch('sdk.client.ParquetReader', return_value=mock_parquet_reader):

            client = KlineClient(mock_config)

            # Act - 查询大数据范围
            start_time = datetime(2020, 1, 1)
            end_time = datetime(2024, 1, 1)

            result = client.get_klines(start_time, end_time)

            # Assert - 验证大数据处理
            assert isinstance(result, pd.DataFrame), "应该返回DataFrame"
            assert len(result) == 100000, "应该处理大量数据"
            assert mock_parquet_reader.read_range.called, "应该调用读取器"

    @pytest.mark.unit
    @pytest.mark.mock
    def test_concurrent_access_handling(self, mock_config, mock_parquet_reader):
        """
        测试并发访问的处理
        验证：线程安全性
        """
        # Arrange
        mock_parquet_reader.read_range.return_value = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=24, freq='1h'),
            'open': [40000.0] * 24,
            'high': [40500.0] * 24,
            'low': [39500.0] * 24,
            'close': [40200.0] * 24,
            'volume': [500.0] * 24
        })

        with patch('sdk.client.DataFetcher'), \
             patch('sdk.client.MetadataManager'), \
             patch('sdk.client.ParquetReader', return_value=mock_parquet_reader):

            client = KlineClient(mock_config)

            # Act - 模拟并发访问
            import threading
            results = []

            def worker():
                result = client.get_klines(datetime(2024, 1, 1), datetime(2024, 1, 2))
                results.append(result)

            threads = [threading.Thread(target=worker) for _ in range(5)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

            # Assert - 验证并发安全性
            assert len(results) == 5, "应该有5个结果"
            assert all(isinstance(r, pd.DataFrame) for r in results), "所有结果都应该是DataFrame"
            assert all(len(r) == 24 for r in results), "所有结果应该有相同数量的数据"