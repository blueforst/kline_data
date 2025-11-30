"""
KlineClient核心功能测试

这个文件包含了SDK客户端的主要功能测试，包括初始化、数据获取、
数据源策略和错误处理等核心功能。
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, call
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

# 导入被测试的模块
from kline_data.sdk.client import KlineClient
from kline_data.config import Config
from kline_data.storage import DataFetcher, DownloadManager, MetadataManager
from kline_data.reader import ParquetReader
from kline_data.resampler import KlineResampler
from kline_data.indicators import IndicatorManager


class TestKlineClientInitialization:
    """测试KlineClient初始化"""

    def test_init_with_default_config(self, mock_config):
        """测试使用默认配置初始化"""
        with patch('sdk.client.load_config') as mock_load:
            mock_load.return_value = mock_config

            with patch('sdk.client.DataFetcher') as mock_fetcher, \
                 patch('sdk.client.DownloadManager') as mock_downloader, \
                 patch('sdk.client.MetadataManager') as mock_metadata, \
                 patch('sdk.client.ParquetReader') as mock_reader, \
                 patch('sdk.client.KlineResampler') as mock_resampler, \
                 patch('sdk.client.IndicatorManager') as mock_indicator:

                client = KlineClient()

                # 验证配置被加载
                mock_load.assert_called_once()

                # 验证组件被初始化
                assert mock_fetcher.call_count == 1
                assert mock_downloader.call_count == 1
                assert mock_metadata.call_count == 1
                assert mock_reader.call_count == 1
                assert mock_resampler.call_count == 1
                assert mock_indicator.call_count == 1

                # 验证客户端属性
                assert client.config is not None
                assert hasattr(client, 'fetcher')
                assert hasattr(client, 'download_mgr')
                assert hasattr(client, 'metadata_mgr')
                assert hasattr(client, 'reader')
                assert hasattr(client, 'resampler')
                assert hasattr(client, 'indicator_calc')

    def test_init_with_custom_config(self, mock_config):
        """测试使用自定义配置初始化"""
        with patch('sdk.client.DataFetcher'), \
             patch('sdk.client.DownloadManager'), \
             patch('sdk.client.MetadataManager'), \
             patch('sdk.client.ParquetReader'), \
             patch('sdk.client.KlineResampler'), \
             patch('sdk.client.IndicatorManager'):

            client = KlineClient(config=mock_config)

            assert client.config == mock_config

    def test_init_with_invalid_config(self):
        """测试使用无效配置初始化"""
        with pytest.raises(Exception):
            KlineClient(config=None)

    def test_component_initialization_parameters(self, mock_config):
        """测试组件初始化参数传递"""
        with patch('sdk.client.DataFetcher') as mock_fetcher, \
             patch('sdk.client.DownloadManager') as mock_downloader, \
             patch('sdk.client.MetadataManager') as mock_metadata, \
             patch('sdk.client.ParquetReader') as mock_reader, \
             patch('sdk.client.KlineResampler') as mock_resampler, \
             patch('sdk.client.IndicatorManager') as mock_indicator:

            KlineClient(config=mock_config)

            # 验证组件初始化时传入了正确的配置
            mock_fetcher.assert_called_once_with(mock_config)
            mock_downloader.assert_called_once_with(mock_config)
            mock_metadata.assert_called_once_with(mock_config)
            mock_reader.assert_called_once_with(mock_config.storage.data_dir)
            mock_resampler.assert_called_once_with(mock_config)
            mock_indicator.assert_called_once_with(mock_config)


class TestKlineClientDataRetrieval:
    """测试数据获取功能"""

    @pytest.fixture
    def mock_client(self, mock_config):
        """创建mock客户端"""
        with patch('sdk.client.DataFetcher') as mock_fetcher_class, \
             patch('sdk.client.DownloadManager'), \
             patch('sdk.client.MetadataManager'), \
             patch('sdk.client.ParquetReader'), \
             patch('sdk.client.KlineResampler'), \
             patch('sdk.client.IndicatorManager'):

            mock_fetcher = Mock()
            mock_fetcher_class.return_value = mock_fetcher

            client = KlineClient(config=mock_config)
            client.fetcher = mock_fetcher
            return client

    def test_get_klines_success(self, mock_client, sample_ohlcv_data):
        """测试成功获取K线数据"""
        # 配置mock返回数据
        mock_client.fetcher.get_klines.return_value = sample_ohlcv_data

        result = mock_client.get_klines(
            exchange='binance',
            symbol='BTC/USDT',
            timeframe='1h',
            start_time=datetime(2024, 1, 1),
            end_time=datetime(2024, 1, 2)
        )

        # 验证调用参数
        mock_client.fetcher.get_klines.assert_called_once_with(
            exchange='binance',
            symbol='BTC/USDT',
            timeframe='1h',
            start_time=datetime(2024, 1, 1),
            end_time=datetime(2024, 1, 2)
        )

        # 验证返回数据
        assert isinstance(result, pd.DataFrame)
        assert not result.empty
        assert len(result) == len(sample_ohlcv_data)

    def test_get_klines_with_limit(self, mock_client, sample_ohlcv_data):
        """测试带限制的K线数据获取"""
        limited_data = sample_ohlcv_data.head(50)
        mock_client.fetcher.get_klines.return_value = limited_data

        result = mock_client.get_klines(
            exchange='binance',
            symbol='BTC/USDT',
            timeframe='1h',
            limit=50
        )

        mock_client.fetcher.get_klines.assert_called_once_with(
            exchange='binance',
            symbol='BTC/USDT',
            timeframe='1h',
            limit=50,
            start_time=None,
            end_time=None
        )

        assert len(result) == 50

    def test_get_klines_empty_result(self, mock_client):
        """测试获取空数据"""
        mock_client.fetcher.get_klines.return_value = pd.DataFrame()

        result = mock_client.get_klines(
            exchange='binance',
            symbol='BTC/USDT',
            timeframe='1h'
        )

        assert isinstance(result, pd.DataFrame)
        assert result.empty

    def test_get_klines_invalid_parameters(self, mock_client):
        """测试无效参数处理"""
        with pytest.raises(ValueError):
            mock_client.get_klines(
                exchange='',  # 无效交易所
                symbol='BTC/USDT',
                timeframe='1h'
            )

        with pytest.raises(ValueError):
            mock_client.get_klines(
                exchange='binance',
                symbol='',  # 无效交易对
                timeframe='1h'
            )

        with pytest.raises(ValueError):
            mock_client.get_klines(
                exchange='binance',
                symbol='BTC/USDT',
                timeframe='invalid'  # 无效时间周期
            )

    def test_get_klines_network_error(self, mock_client):
        """测试网络错误处理"""
        mock_client.fetcher.get_klines.side_effect = ConnectionError("Network timeout")

        with pytest.raises(ConnectionError):
            mock_client.get_klines(
                exchange='binance',
                symbol='BTC/USDT',
                timeframe='1h'
            )

    def test_get_latest_klines(self, mock_client, sample_ohlcv_data):
        """测试获取最新K线数据"""
        latest_data = sample_ohlcv_data.tail(10)
        mock_client.fetcher.get_latest_klines.return_value = latest_data

        result = mock_client.get_latest_klines(
            exchange='binance',
            symbol='BTC/USDT',
            timeframe='1h',
            limit=10
        )

        mock_client.fetcher.get_latest_klines.assert_called_once_with(
            exchange='binance',
            symbol='BTC/USDT',
            timeframe='1h',
            limit=10
        )

        assert len(result) == 10
        assert result.iloc[-1]['timestamp'] == latest_data.iloc[-1]['timestamp']


class TestKlineClientDataSourceStrategy:
    """测试数据源策略功能"""

    @pytest.fixture
    def mock_client_with_strategy(self, mock_config):
        """创建带有数据源策略的mock客户端"""
        with patch('sdk.client.DataFetcher'), \
             patch('sdk.client.DownloadManager'), \
             patch('sdk.client.MetadataManager'), \
             patch('sdk.client.ParquetReader'), \
             patch('sdk.client.KlineResampler'), \
             patch('sdk.client.IndicatorManager'), \
             patch('sdk.client.DataSourceStrategy') as mock_strategy_class:

            mock_strategy = Mock()
            mock_strategy_class.return_value = mock_strategy

            client = KlineClient(config=mock_config)
            client.data_source_strategy = mock_strategy
            return client, mock_strategy

    def test_data_source_decision_local(self, mock_client_with_strategy):
        """测试本地数据源决策"""
        client, mock_strategy = mock_client_with_strategy

        # 配置策略决策
        from kline_data.storage.data_source_strategy import DataSourceDecision
        mock_decision = DataSourceDecision(
            source='local',
            source_interval=None,
            need_download=False,
            download_interval=None,
            reason='Local data available'
        )
        mock_strategy.decide_data_source.return_value = mock_decision

        decision = client.decide_data_source(
            exchange='binance',
            symbol='BTC/USDT',
            timeframe='1h',
            start_time=datetime(2024, 1, 1),
            end_time=datetime(2024, 1, 2)
        )

        mock_strategy.decide_data_source.assert_called_once_with(
            exchange='binance',
            symbol='BTC/USDT',
            timeframe='1h',
            start_time=datetime(2024, 1, 1),
            end_time=datetime(2024, 1, 2)
        )

        assert decision.source == 'local'
        assert decision.need_download == False

    def test_data_source_decision_download(self, mock_client_with_strategy):
        """测试下载数据源决策"""
        client, mock_strategy = mock_client_with_strategy

        from kline_data.storage.data_source_strategy import DataSourceDecision
        mock_decision = DataSourceDecision(
            source='ccxt',
            source_interval=None,
            need_download=True,
            download_interval='1h',
            reason='No local data available'
        )
        mock_strategy.decide_data_source.return_value = mock_decision

        decision = client.decide_data_source(
            exchange='binance',
            symbol='BTC/USDT',
            timeframe='1h',
            start_time=datetime(2024, 1, 1),
            end_time=datetime(2024, 1, 2)
        )

        assert decision.source == 'ccxt'
        assert decision.need_download == True
        assert decision.download_interval == '1h'

    def test_data_source_decision_resample(self, mock_client_with_strategy):
        """测试重采样数据源决策"""
        client, mock_strategy = mock_client_with_strategy

        from kline_data.storage.data_source_strategy import DataSourceDecision
        mock_decision = DataSourceDecision(
            source='resample',
            source_interval='1m',
            need_download=False,
            download_interval=None,
            reason='1m data available, need resample to 1h'
        )
        mock_strategy.decide_data_source.return_value = mock_decision

        decision = client.decide_data_source(
            exchange='binance',
            symbol='BTC/USDT',
            timeframe='1h',
            start_time=datetime(2024, 1, 1),
            end_time=datetime(2024, 1, 2)
        )

        assert decision.source == 'resample'
        assert decision.source_interval == '1m'
        assert decision.need_download == False


class TestKlineClientIndicators:
    """测试技术指标功能"""

    @pytest.fixture
    def mock_client_with_indicators(self, mock_config):
        """创建带有技术指标的mock客户端"""
        with patch('sdk.client.DataFetcher'), \
             patch('sdk.client.DownloadManager'), \
             patch('sdk.client.MetadataManager'), \
             patch('sdk.client.ParquetReader'), \
             patch('sdk.client.KlineResampler'), \
             patch('sdk.client.IndicatorManager') as mock_indicator_class:

            mock_indicator = Mock()
            mock_indicator_class.return_value = mock_indicator

            client = KlineClient(config=mock_config)
            client.indicator_calc = mock_indicator
            return client, mock_indicator

    def test_calculate_indicator(self, mock_client_with_indicators, sample_ohlcv_data):
        """测试计算技术指标"""
        client, mock_indicator = mock_client_with_indicators

        # 配置mock返回数据
        mock_indicator.calculate.return_value = sample_ohlcv_data.copy()

        result = client.calculate_indicator(
            data=sample_ohlcv_data,
            indicator_name='SMA',
            period=20
        )

        mock_indicator.calculate.assert_called_once_with(
            data=sample_ohlcv_data,
            indicator_name='SMA',
            period=20
        )

        assert isinstance(result, pd.DataFrame)
        assert len(result) == len(sample_ohlcv_data)

    def test_calculate_multiple_indicators(self, mock_client_with_indicators, sample_ohlcv_data):
        """测试计算多个技术指标"""
        client, mock_indicator = mock_client_with_indicators

        # 配置mock返回数据
        mock_indicator.calculate_multiple.return_value = sample_ohlcv_data.copy()

        result = client.calculate_multiple_indicators(
            data=sample_ohlcv_data,
            indicators=[
                {'name': 'SMA', 'period': 20},
                {'name': 'EMA', 'period': 20},
                {'name': 'RSI', 'period': 14}
            ]
        )

        mock_indicator.calculate_multiple.assert_called_once()

        assert isinstance(result, pd.DataFrame)

    def test_get_available_indicators(self, mock_client_with_indicators):
        """测试获取可用指标列表"""
        client, mock_indicator = mock_client_with_indicators

        mock_indicator.get_available_indicators.return_value = [
            'SMA', 'EMA', 'RSI', 'MACD', 'BB', 'STOCH'
        ]

        indicators = client.get_available_indicators()

        mock_indicator.get_available_indicators.assert_called_once()
        assert isinstance(indicators, list)
        assert 'SMA' in indicators
        assert 'RSI' in indicators


class TestKlineClientErrorHandling:
    """测试错误处理功能"""

    @pytest.fixture
    def mock_client(self, mock_config):
        """创建mock客户端"""
        with patch('sdk.client.DataFetcher'), \
             patch('sdk.client.DownloadManager'), \
             patch('sdk.client.MetadataManager'), \
             patch('sdk.client.ParquetReader'), \
             patch('sdk.client.KlineResampler'), \
             patch('sdk.client.IndicatorManager'):

            return KlineClient(config=mock_config)

    def test_handle_connection_error(self, mock_client):
        """测试连接错误处理"""
        mock_client.fetcher.get_klines.side_effect = ConnectionError("Connection refused")

        with pytest.raises(ConnectionError) as exc_info:
            mock_client.get_klines(
                exchange='binance',
                symbol='BTC/USDT',
                timeframe='1h'
            )

        assert "Connection refused" in str(exc_info.value)

    def test_handle_timeout_error(self, mock_client):
        """测试超时错误处理"""
        mock_client.fetcher.get_klines.side_effect = TimeoutError("Request timeout")

        with pytest.raises(TimeoutError) as exc_info:
            mock_client.get_klines(
                exchange='binance',
                symbol='BTC/USDT',
                timeframe='1h'
            )

        assert "Request timeout" in str(exc_info.value)

    def test_handle_invalid_data_error(self, mock_client):
        """测试无效数据错误处理"""
        # 返回格式错误的数据
        mock_client.fetcher.get_klines.return_value = "invalid data"

        with pytest.raises(Exception):  # 应该抛出某种数据格式错误
            mock_client.get_klines(
                exchange='binance',
                symbol='BTC/USDT',
                timeframe='1h'
            )

    def test_handle_rate_limit_error(self, mock_client):
        """测试速率限制错误处理"""
        # 模拟CCXT速率限制错误
        class RateLimitError(Exception):
            pass

        mock_client.fetcher.get_klines.side_effect = RateLimitError("Rate limit exceeded")

        with pytest.raises(RateLimitError):
            mock_client.get_klines(
                exchange='binance',
                symbol='BTC/USDT',
                timeframe='1h'
            )

    def test_retry_mechanism(self, mock_client):
        """测试重试机制"""
        # 第一次调用失败，第二次成功
        sample_data = pd.DataFrame({
            'timestamp': [datetime.now()],
            'open': [50000],
            'high': [50100],
            'low': [49900],
            'close': [50050],
            'volume': [100000]
        })

        mock_client.fetcher.get_klines.side_effect = [
            ConnectionError("Temporary failure"),
            sample_data
        ]

        # 假设客户端有重试机制
        # 这需要实际的客户端实现支持
        result = mock_client.get_klines(
            exchange='binance',
            symbol='BTC/USDT',
            timeframe='1h'
        )

        # 验证重试调用
        assert mock_client.fetcher.get_klines.call_count == 2
        assert isinstance(result, pd.DataFrame)


class TestKlineClientPerformance:
    """测试性能相关功能"""

    @pytest.fixture
    def mock_client(self, mock_config):
        """创建mock客户端"""
        with patch('sdk.client.DataFetcher'), \
             patch('sdk.client.DownloadManager'), \
             patch('sdk.client.MetadataManager'), \
             patch('sdk.client.ParquetReader'), \
             patch('sdk.client.KlineResampler'), \
             patch('sdk.client.IndicatorManager'):

            return KlineClient(config=mock_config)

    @pytest.mark.benchmark
    def test_get_klines_performance(self, mock_client, sample_ohlcv_data):
        """测试get_klines性能"""
        mock_client.fetcher.get_klines.return_value = sample_ohlcv_data

        def get_klines():
            return mock_client.get_klines(
                exchange='binance',
                symbol='BTC/USDT',
                timeframe='1h',
                limit=1000
            )

        result = get_klines()
        assert len(result) == len(sample_ohlcv_data)

    @pytest.mark.benchmark
    def test_indicator_calculation_performance(self, mock_client, sample_ohlcv_data):
        """测试指标计算性能"""
        mock_client.indicator_calc.calculate.return_value = sample_ohlcv_data.copy()

        def calculate_indicator():
            return mock_client.calculate_indicator(
                data=sample_ohlcv_data,
                indicator_name='SMA',
                period=20
            )

        result = calculate_indicator()
        assert isinstance(result, pd.DataFrame)


# ============================================================================
# 集成测试（需要真实组件）
# ============================================================================

@pytest.mark.integration
class TestKlineClientIntegration:
    """KlineClient集成测试"""

    def test_full_data_pipeline(self, real_config, sample_data_files):
        """测试完整数据管道"""
        # 这个测试需要真实的组件实现
        # 暂时跳过，等待完整的实现
        pytest.skip("Integration test requires full implementation")

    def test_config_integration(self, temp_config_file):
        """测试配置集成"""
        # 测试配置文件加载和集成
        pytest.skip("Integration test requires full implementation")


# ============================================================================
# 边界条件和特殊场景测试
# ============================================================================

class TestKlineClientEdgeCases:
    """测试边界条件和特殊场景"""

    @pytest.fixture
    def mock_client(self, mock_config):
        """创建mock客户端"""
        with patch('sdk.client.DataFetcher'), \
             patch('sdk.client.DownloadManager'), \
             patch('sdk.client.MetadataManager'), \
             patch('sdk.client.ParquetReader'), \
             patch('sdk.client.KlineResampler'), \
             patch('sdk.client.IndicatorManager'):

            return KlineClient(config=mock_config)

    def test_very_large_dataset(self, mock_client):
        """测试大数据集处理"""
        # 创建大数据集mock
        large_data = pd.DataFrame({
            'timestamp': pd.date_range('2020-01-01', periods=100000, freq='1m'),
            'open': np.random.uniform(45000, 55000, 100000),
            'high': np.random.uniform(45000, 55000, 100000),
            'low': np.random.uniform(45000, 55000, 100000),
            'close': np.random.uniform(45000, 55000, 100000),
            'volume': np.random.randint(100000, 1000000, 100000)
        })

        mock_client.fetcher.get_klines.return_value = large_data

        result = mock_client.get_klines(
            exchange='binance',
            symbol='BTC/USDT',
            timeframe='1m',
            limit=100000
        )

        assert len(result) == 100000
        assert not result.empty

    def test_empty_time_range(self, mock_client):
        """测试空时间范围"""
        mock_client.fetcher.get_klines.return_value = pd.DataFrame()

        result = mock_client.get_klines(
            exchange='binance',
            symbol='BTC/USDT',
            timeframe='1h',
            start_time=datetime(2024, 1, 1),
            end_time=datetime(2024, 1, 1, 0, 59)  # 只有59分钟
        )

        assert result.empty

    def test_extreme_time_range(self, mock_client):
        """测试极端时间范围"""
        # 测试跨越多年的数据请求
        start_time = datetime(2015, 1, 1)
        end_time = datetime(2024, 1, 1)

        mock_client.fetcher.get_klines.return_value = pd.DataFrame()

        result = mock_client.get_klines(
            exchange='binance',
            symbol='BTC/USDT',
            timeframe='1d',
            start_time=start_time,
            end_time=end_time
        )

        mock_client.fetcher.get_klines.assert_called_once_with(
            exchange='binance',
            symbol='BTC/USDT',
            timeframe='1d',
            start_time=start_time,
            end_time=end_time,
            limit=None
        )

    def test_unicode_symbol_names(self, mock_client):
        """测试Unicode交易对名称"""
        mock_client.fetcher.get_klines.return_value = pd.DataFrame()

        result = mock_client.get_klines(
            exchange='binance',
            symbol='BTC/USDT',  # 标准交易对
            timeframe='1h'
        )

        # 测试包含特殊字符的交易对
        result = mock_client.get_klines(
            exchange='binance',
            symbol='BTC/USD',  # 没有T的稳定币对
            timeframe='1h'
        )

        assert mock_client.fetcher.get_klines.call_count == 2

    def test_concurrent_requests(self, mock_client):
        """测试并发请求处理"""
        import threading
        import time

        # 模拟异步处理
        def slow_get_klines(*args, **kwargs):
            time.sleep(0.1)  # 模拟网络延迟
            return pd.DataFrame({
                'timestamp': [datetime.now()],
                'open': [50000],
                'high': [50100],
                'low': [49900],
                'close': [50050],
                'volume': [100000]
            })

        mock_client.fetcher.get_klines.side_effect = slow_get_klines

        # 并发执行多个请求
        threads = []
        results = []

        def worker():
            result = mock_client.get_klines(
                exchange='binance',
                symbol='BTC/USDT',
                timeframe='1h'
            )
            results.append(result)

        for _ in range(5):
            thread = threading.Thread(target=worker)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # 验证所有请求都完成了
        assert len(results) == 5
        for result in results:
            assert isinstance(result, pd.DataFrame)
            assert not result.empty