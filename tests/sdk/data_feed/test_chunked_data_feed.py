"""
ChunkedDataFeed 单元测试 - 伦敦学派TDD方法

测试重点：
1. 分块数据流的行为验证
2. 迭代器协议的正确实现
3. 内存管理效率
4. 与数据源的协作
5. 错误处理和恢复
"""

import pytest
from unittest.mock import Mock, patch, call
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

from sdk.data_feed import ChunkedDataFeed
from utils.constants import Timeframe


class TestChunkedDataFeedBehavior:
    """ChunkedDataFeed行为测试 - 验证数据流的正确行为"""

    @pytest.mark.unit
    @pytest.mark.mock
    def test_chunked_feed_initialization_behavior(self, mock_config, mock_parquet_reader):
        """
        测试分块数据流初始化行为
        验证：参数验证和内部状态设置
        """
        # Arrange - 设置测试参数
        start_time = datetime(2024, 1, 1)
        end_time = datetime(2024, 1, 2)
        chunk_size = 1000

        # Act - 创建分块数据流
        with patch('sdk.data_feed.ParquetReader', return_value=mock_parquet_reader):
            feed = ChunkedDataFeed(
                exchange='binance',
                symbol='BTC/USDT',
                start_time=start_time,
                end_time=end_time,
                interval='1h',
                chunk_size=chunk_size
            )

        # Assert - 验证初始化行为
        assert feed.exchange == 'binance', "应该正确设置交易所"
        assert feed.symbol == 'BTC/USDT', "应该正确设置交易对"
        assert feed.start_time == start_time, "应该正确设置开始时间"
        assert feed.end_time == end_time, "应该正确设置结束时间"
        assert feed.interval == '1h', "应该正确设置时间周期"
        assert feed.chunk_size == chunk_size, "应该正确设置块大小"
        assert hasattr(feed, 'reader'), "应该有reader属性"
        assert feed.reader is mock_parquet_reader, "应该正确设置reader"

    @pytest.mark.unit
    @pytest.mark.mock
    def test_iterator_protocol_behavior(self, mock_config, sample_kline_data):
        """
        测试迭代器协议行为
        验证：__iter__和__next__方法的正确实现
        """
        # Arrange - 准备测试数据
        chunk_size = 10
        total_rows = len(sample_kline_data)

        mock_reader = Mock()
        # 模拟分块读取
        def mock_read_range(start_time, end_time):
            # 计算应该返回的数据量
            if start_time == sample_kline_data['timestamp'].iloc[0]:
                return sample_kline_data.head(chunk_size)
            else:
                return sample_kline_data.tail(total_rows - chunk_size)

        mock_reader.read_range.side_effect = mock_read_range

        # Act - 创建数据流并迭代
        with patch('sdk.data_feed.ParquetReader', return_value=mock_reader):
            feed = ChunkedDataFeed(
                exchange='binance',
                symbol='BTC/USDT',
                start_time=datetime(2024, 1, 1),
                end_time=datetime(2024, 1, 2),
                interval='1h',
                chunk_size=chunk_size
            )

            chunks = list(feed)  # 迭代所有块

        # Assert - 验证迭代行为
        assert len(chunks) >= 1, "应该至少有一个数据块"
        assert all(isinstance(chunk, pd.DataFrame) for chunk in chunks), "所有块都应该是DataFrame"
        assert all(len(chunk) <= chunk_size for chunk in chunks), "每个块的大小不应超过chunk_size"

        # 验证读取器的调用行为
        assert mock_reader.read_range.call_count >= 1, "应该调用read_range至少一次"

    @pytest.mark.unit
    @pytest.mark.mock
    def test_chunk_size_boundary_behavior(self, mock_config):
        """
        测试块大小边界行为
        验证：不同块大小的处理行为
        """
        # Arrange - 创建测试数据
        total_rows = 50
        test_data = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=total_rows, freq='1h'),
            'open': np.random.uniform(40000, 41000, total_rows),
            'high': np.random.uniform(41000, 42000, total_rows),
            'low': np.random.uniform(39000, 40000, total_rows),
            'close': np.random.uniform(40000, 41000, total_rows),
            'volume': np.random.uniform(100, 1000, total_rows)
        })

        # 测试不同的块大小
        chunk_sizes = [1, 5, 10, 25, 100]

        for chunk_size in chunk_sizes:
            # Arrange - 设置Mock
            mock_reader = Mock()
            mock_reader.read_range.return_value = test_data

            # Act - 创建不同块大小的数据流
            with patch('sdk.data_feed.ParquetReader', return_value=mock_reader):
                feed = ChunkedDataFeed(
                    exchange='binance',
                    symbol='BTC/USDT',
                    start_time=datetime(2024, 1, 1),
                    end_time=datetime(2024, 1, 3),
                    interval='1h',
                    chunk_size=chunk_size
                )

                chunks = list(feed)

            # Assert - 验证块大小行为
            if len(chunks) > 1:
                # 最后一个块可能小于chunk_size
                for chunk in chunks[:-1]:
                    assert len(chunk) <= chunk_size, f"块大小不应超过{chunk_size}"

    @pytest.mark.unit
    @pytest.mark.mock
    def test_memory_efficiency_behavior(self, mock_config, performance_timer):
        """
        测试内存效率行为
        验证：分块加载的内存使用效率
        """
        # Arrange - 创建大数据集
        large_data = pd.DataFrame({
            'timestamp': pd.date_range('2023-01-01', periods=10000, freq='1m'),
            'open': np.random.uniform(30000, 50000, 10000),
            'high': np.random.uniform(30000, 50000, 10000),
            'low': np.random.uniform(30000, 50000, 10000),
            'close': np.random.uniform(30000, 50000, 10000),
            'volume': np.random.uniform(100, 1000, 10000)
        })

        chunk_size = 1000
        call_count = 0

        # Mock读取器，模拟分块读取
        def mock_read_range(start_time, end_time):
            nonlocal call_count
            call_count += 1
            # 返回小块数据而不是整个数据集
            start_idx = (call_count - 1) * chunk_size
            end_idx = min(call_count * chunk_size, len(large_data))
            return large_data.iloc[start_idx:end_idx].copy()

        mock_reader = Mock()
        mock_reader.read_range.side_effect = mock_read_range

        # Act - 测试分块加载性能
        performance_timer.start()

        with patch('sdk.data_feed.ParquetReader', return_value=mock_reader):
            feed = ChunkedDataFeed(
                exchange='binance',
                symbol='BTC/USDT',
                start_time=datetime(2023, 1, 1),
                end_time=datetime(2023, 1, 10),
                interval='1m',
                chunk_size=chunk_size
            )

            chunks = []
            for chunk in feed:
                chunks.append(chunk)
                # 验证每个块的大小
                assert len(chunk) <= chunk_size, f"块大小{len(chunk)}不应超过{chunk_size}"

        performance_timer.stop()

        # Assert - 验证内存效率
        expected_chunks = (len(large_data) + chunk_size - 1) // chunk_size
        assert call_count == expected_chunks, f"应该调用读取器{expected_chunks}次，实际调用{call_count}次"
        assert len(chunks) == expected_chunks, f"应该有{expected_chunks}个数据块"
        assert performance_timer.elapsed < 5.0, "分块加载应该很快"


class TestChunkedDataFeedCollaboration:
    """ChunkedDataFeed协作测试 - 验证与其他组件的交互"""

    @pytest.mark.unit
    @pytest.mark.contract
    def test_parquet_reader_collaboration(self, mock_config):
        """
        测试与ParquetReader的协作
        验证：正确调用读取器方法和参数传递
        """
        # Arrange - 定义协作契约
        test_data = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=24, freq='1h'),
            'open': [40000.0] * 24,
            'high': [40500.0] * 24,
            'low': [39500.0] * 24,
            'close': [40200.0] * 24,
            'volume': [500.0] * 24
        })

        mock_reader = Mock()
        mock_reader.read_range.return_value = test_data

        start_time = datetime(2024, 1, 1)
        end_time = datetime(2024, 1, 2)

        # Act - 执行协作
        with patch('sdk.data_feed.ParquetReader', return_value=mock_reader):
            feed = ChunkedDataFeed(
                exchange='binance',
                symbol='BTC/USDT',
                start_time=start_time,
                end_time=end_time,
                interval='1h',
                chunk_size=10
            )

            # 触发协作
            chunks = list(feed)

        # Assert - 验证协作交互
        mock_reader.read_range.assert_called()

        # 验证调用参数
        call_args = mock_reader.read_range.call_args
        assert 'start_time' in call_args.kwargs, "应该传递start_time参数"
        assert 'end_time' in call_args.kwargs, "应该传递end_time参数"

        # 验证协作结果
        assert len(chunks) >= 1, "应该产生数据块"
        assert isinstance(chunks[0], pd.DataFrame), "数据块应该是DataFrame"

    @pytest.mark.unit
    @pytest.mark.contract
    def test_time_boundary_calculation_collaboration(self, mock_config):
        """
        测试时间边界计算的协作
        验证：正确计算每个块的开始和结束时间
        """
        # Arrange - 设置测试场景
        start_time = datetime(2024, 1, 1, 0, 0, 0)
        end_time = datetime(2024, 1, 2, 0, 0, 0)  # 24小时
        chunk_size = 6  # 6小时一个块

        recorded_calls = []

        def record_read_range(start_time, end_time):
            recorded_calls.append((start_time, end_time))
            return pd.DataFrame({
                'timestamp': pd.date_range(start_time, periods=6, freq='1h'),
                'open': [40000.0] * 6,
                'high': [40500.0] * 6,
                'low': [39500.0] * 6,
                'close': [40200.0] * 6,
                'volume': [500.0] * 6
            })

        mock_reader = Mock()
        mock_reader.read_range.side_effect = record_read_range

        # Act - 执行时间边界计算
        with patch('sdk.data_feed.ParquetReader', return_value=mock_reader):
            feed = ChunkedDataFeed(
                exchange='binance',
                symbol='BTC/USDT',
                start_time=start_time,
                end_time=end_time,
                interval='1h',
                chunk_size=chunk_size
            )

            chunks = list(feed)

        # Assert - 验证时间边界计算
        assert len(recorded_calls) == 4, "应该有4次调用（24小时/6小时）"

        # 验证每个块的时间边界
        expected_boundaries = [
            (datetime(2024, 1, 1, 0, 0, 0), datetime(2024, 1, 1, 6, 0, 0)),
            (datetime(2024, 1, 1, 6, 0, 0), datetime(2024, 1, 1, 12, 0, 0)),
            (datetime(2024, 1, 1, 12, 0, 0), datetime(2024, 1, 1, 18, 0, 0)),
            (datetime(2024, 1, 1, 18, 0, 0), datetime(2024, 1, 2, 0, 0, 0))
        ]

        for i, (actual_start, actual_end) in enumerate(recorded_calls):
            expected_start, expected_end = expected_boundaries[i]
            assert actual_start == expected_start, f"第{i+1}块的开始时间不正确"
            assert actual_end == expected_end, f"第{i+1}块的结束时间不正确"

    @pytest.mark.unit
    @pytest.mark.contract
    def test_error_handling_collaboration(self, mock_config):
        """
        测试错误处理协作
        验证：与错误处理机制的协作
        """
        # Arrange - 设置协作契约（读取器抛出异常）
        mock_reader = Mock()
        mock_reader.read_range.side_effect = [
            pd.DataFrame({  # 第一块成功
                'timestamp': pd.date_range('2024-01-01', periods=6, freq='1h'),
                'open': [40000.0] * 6,
                'high': [40500.0] * 6,
                'low': [39500.0] * 6,
                'close': [40200.0] * 6,
                'volume': [500.0] * 6
            }),
            FileNotFoundError("Data file not found"),  # 第二块失败
            pd.DataFrame({  # 第三块成功（如果有）
                'timestamp': pd.date_range('2024-01-01 12:00:00', periods=6, freq='1h'),
                'open': [40100.0] * 6,
                'high': [40600.0] * 6,
                'low': [39600.0] * 6,
                'close': [40300.0] * 6,
                'volume': [600.0] * 6
            })
        ]

        # Act & Assert - 测试错误协作
        with patch('sdk.data_feed.ParquetReader', return_value=mock_reader):
            feed = ChunkedDataFeed(
                exchange='binance',
                symbol='BTC/USDT',
                start_time=datetime(2024, 1, 1),
                end_time=datetime(2024, 1, 2),
                interval='1h',
                chunk_size=6
            )

            # 应该能够处理部分错误
            chunks = []
            with pytest.raises(FileNotFoundError):
                for chunk in feed:
                    chunks.append(chunk)

            # 验证协作结果
            assert len(chunks) == 1, "应该获取到1个成功的数据块"
            assert mock_reader.read_range.call_count >= 2, "应该尝试读取多次"


class TestChunkedDataFeedEdgeCases:
    """ChunkedDataFeed边界条件测试"""

    @pytest.mark.unit
    @pytest.mark.mock
    def test_empty_data_range_behavior(self, mock_config):
        """
        测试空数据范围行为
        验证：边界条件的正确处理
        """
        # Arrange - 设置空数据范围
        mock_reader = Mock()
        mock_reader.read_range.return_value = pd.DataFrame()

        # Act - 创建空数据范围的数据流
        with patch('sdk.data_feed.ParquetReader', return_value=mock_reader):
            feed = ChunkedDataFeed(
                exchange='binance',
                symbol='BTC/USDT',
                start_time=datetime(2024, 1, 1),
                end_time=datetime(2024, 1, 1),  # 相同时间
                interval='1h',
                chunk_size=10
            )

            chunks = list(feed)

        # Assert - 验证空数据范围处理
        assert len(chunks) == 0, "空数据范围应该返回空列表"
        mock_reader.read_range.assert_called()

    @pytest.mark.unit
    @pytest.mark.mock
    def test_single_chunk_behavior(self, mock_config, sample_kline_data):
        """
        测试单块数据行为
        验证：数据量小于chunk_size时的处理
        """
        # Arrange - 设置单块场景
        mock_reader = Mock()
        mock_reader.read_range.return_value = sample_kline_data.head(5)  # 只有5条数据

        # Act - 创建chunk_size大于数据量的数据流
        with patch('sdk.data_feed.ParquetReader', return_value=mock_reader):
            feed = ChunkedDataFeed(
                exchange='binance',
                symbol='BTC/USDT',
                start_time=datetime(2024, 1, 1),
                end_time=datetime(2024, 1, 1, 5, 0, 0),
                interval='1h',
                chunk_size=100  # 大于实际数据量
            )

            chunks = list(feed)

        # Assert - 验证单块行为
        assert len(chunks) == 1, "应该只有1个数据块"
        assert len(chunks[0]) == 5, "数据块应该包含5条数据"
        mock_reader.read_range.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.mock
    def test_irregular_chunk_sizes_behavior(self, mock_config):
        """
        测试不规则块大小行为
        验证：处理非整数倍数据量的情况
        """
        # Arrange - 设置不规则数据场景
        total_rows = 23  # 不能被chunk_size整除
        chunk_size = 10

        def mock_read_range(start_time, end_time):
            # 模拟实际的数据读取行为
            call_count = mock_reader.read_range.call_count
            if call_count == 1:
                return pd.DataFrame({
                    'timestamp': pd.date_range('2024-01-01', periods=10, freq='1h'),
                    'open': [40000.0] * 10,
                    'high': [40500.0] * 10,
                    'low': [39500.0] * 10,
                    'close': [40200.0] * 10,
                    'volume': [500.0] * 10
                })
            elif call_count == 2:
                return pd.DataFrame({
                    'timestamp': pd.date_range('2024-01-01 10:00:00', periods=10, freq='1h'),
                    'open': [40100.0] * 10,
                    'high': [40600.0] * 10,
                    'low': [39600.0] * 10,
                    'close': [40300.0] * 10,
                    'volume': [600.0] * 10
                })
            else:
                return pd.DataFrame({
                    'timestamp': pd.date_range('2024-01-01 20:00:00', periods=3, freq='1h'),
                    'open': [40200.0] * 3,
                    'high': [40700.0] * 3,
                    'low': [39700.0] * 3,
                    'close': [40400.0] * 3,
                    'volume': [700.0] * 3
                })

        mock_reader = Mock()
        mock_reader.read_range.side_effect = mock_read_range

        # Act - 处理不规则数据量
        with patch('sdk.data_feed.ParquetReader', return_value=mock_reader):
            feed = ChunkedDataFeed(
                exchange='binance',
                symbol='BTC/USDT',
                start_time=datetime(2024, 1, 1),
                end_time=datetime(2024, 1, 1, 23, 0, 0),
                interval='1h',
                chunk_size=chunk_size
            )

            chunks = list(feed)

        # Assert - 验证不规则块处理
        assert len(chunks) == 3, "应该有3个数据块"
        assert len(chunks[0]) == 10, "第1块应该有10条数据"
        assert len(chunks[1]) == 10, "第2块应该有10条数据"
        assert len(chunks[2]) == 3, "第3块应该有3条数据（剩余部分）"

    @pytest.mark.unit
    @pytest.mark.mock
    def test_timezone_handling_behavior(self, mock_config):
        """
        测试时区处理行为
        验证：不同时区的数据处理
        """
        # Arrange - 创建带时区的数据
        timestamp_data = pd.date_range(
            '2024-01-01 00:00:00+00:00',
            periods=24,
            freq='1h'
        )

        test_data = pd.DataFrame({
            'timestamp': timestamp_data,
            'open': [40000.0] * 24,
            'high': [40500.0] * 24,
            'low': [39500.0] * 24,
            'close': [40200.0] * 24,
            'volume': [500.0] * 24
        })

        mock_reader = Mock()
        mock_reader.read_range.return_value = test_data

        # Act - 处理带时区的数据
        with patch('sdk.data_feed.ParquetReader', return_value=mock_reader):
            feed = ChunkedDataFeed(
                exchange='binance',
                symbol='BTC/USDT',
                start_time=datetime(2024, 1, 1),
                end_time=datetime(2024, 1, 2),
                interval='1h',
                chunk_size=6
            )

            chunks = list(feed)

        # Assert - 验证时区处理
        assert len(chunks) >= 1, "应该有数据块"
        assert all('timestamp' in chunk.columns for chunk in chunks), "所有块都应该有timestamp列"

        # 验证时间戳的类型和时区
        for chunk in chunks:
            assert pd.api.types.is_datetime64_any_dtype(chunk['timestamp']), \
                "timestamp应该是datetime类型"


class TestChunkedDataFeedPerformance:
    """ChunkedDataFeed性能测试"""

    @pytest.mark.unit
    @pytest.mark.performance
    def test_large_dataset_performance(self, mock_config, performance_timer):
        """
        测试大数据集性能
        验证：分块处理大数据集的效率
        """
        # Arrange - 创建大数据集
        large_data = pd.DataFrame({
            'timestamp': pd.date_range('2023-01-01', periods=50000, freq='1m'),
            'open': np.random.uniform(30000, 50000, 50000),
            'high': np.random.uniform(30000, 50000, 50000),
            'low': np.random.uniform(30000, 50000, 50000),
            'close': np.random.uniform(30000, 50000, 50000),
            'volume': np.random.uniform(100, 1000, 50000)
        })

        chunk_size = 5000
        processed_chunks = 0

        def mock_read_range(start_time, end_time):
            nonlocal processed_chunks
            processed_chunks += 1
            # 返回小块数据模拟实际读取
            start_idx = (processed_chunks - 1) * chunk_size
            end_idx = min(processed_chunks * chunk_size, len(large_data))
            return large_data.iloc[start_idx:end_idx].copy()

        mock_reader = Mock()
        mock_reader.read_range.side_effect = mock_read_range

        # Act - 测试大数据集处理性能
        performance_timer.start()

        with patch('sdk.data_feed.ParquetReader', return_value=mock_reader):
            feed = ChunkedDataFeed(
                exchange='binance',
                symbol='BTC/USDT',
                start_time=datetime(2023, 1, 1),
                end_time=datetime(2023, 2, 1),
                interval='1m',
                chunk_size=chunk_size
            )

            chunks = []
            for i, chunk in enumerate(feed):
                chunks.append(chunk)
                if i >= 5:  # 只测试前几个块以节省时间
                    break

        performance_timer.stop()

        # Assert - 验证性能
        assert len(chunks) == 6, "应该处理6个数据块"
        assert processed_chunks == 6, "应该调用读取器6次"
        assert performance_timer.elapsed < 3.0, "处理前6个块应该很快"

        # 验证内存使用
        for chunk in chunks:
            assert len(chunk) <= chunk_size, "每个块的大小不应超过chunk_size"

    @pytest.mark.unit
    @pytest.mark.performance
    def test_iterator_overhead_performance(self, mock_config, performance_timer):
        """
        测试迭代器开销性能
        验证：迭代器的性能开销
        """
        # Arrange - 准备测试数据
        test_data = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=1000, freq='1h'),
            'open': np.random.uniform(40000, 41000, 1000),
            'high': np.random.uniform(41000, 42000, 1000),
            'low': np.random.uniform(39000, 40000, 1000),
            'close': np.random.uniform(40000, 41000, 1000),
            'volume': np.random.uniform(100, 1000, 1000)
        })

        mock_reader = Mock()
        mock_reader.read_range.return_value = test_data

        # Act - 测试迭代器性能
        with patch('sdk.data_feed.ParquetReader', return_value=mock_reader):
            feed = ChunkedDataFeed(
                exchange='binance',
                symbol='BTC/USDT',
                start_time=datetime(2024, 1, 1),
                end_time=datetime(2024, 2, 11),  # 约1000小时
                interval='1h',
                chunk_size=100
            )

            performance_timer.start()

            # 测试迭代开销
            chunks = list(feed)

            performance_timer.stop()

        # Assert - 验证性能
        assert len(chunks) == 10, "应该有10个数据块"
        assert performance_timer.elapsed < 1.0, "迭代开销应该很小"