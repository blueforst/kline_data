"""
KlineClient核心功能测试 (Refactored for new architecture)

这个文件包含了SDK客户端的主要功能测试，包括初始化、数据获取、
数据源策略和错误处理等核心功能。
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import pandas as pd
import numpy as np

# 导入被测试的模块
from kline_data.sdk.sdk_client import KlineClient
from kline_data.config import Config

class TestKlineClientInitialization:
    """测试KlineClient初始化"""

    def test_init_with_default_config(self):
        """测试使用默认配置初始化"""
        with patch('kline_data.config.load_config') as mock_load, \
             patch('kline_data.sdk.sdk_client.QueryClient') as mock_query, \
             patch('kline_data.sdk.sdk_client.DownloadClient') as mock_download, \
             patch('kline_data.sdk.sdk_client.IndicatorClient') as mock_indicator, \
             patch('kline_data.sdk.sdk_client.MetadataClient') as mock_metadata:
            
            mock_config = Mock(spec=Config)
            mock_load.return_value = mock_config

            client = KlineClient()

            # 验证配置被加载
            mock_load.assert_called_once()

            # 验证组件被初始化
            mock_query.assert_called_once_with(mock_config)
            mock_download.assert_called_once_with(mock_config)
            mock_indicator.assert_called_once_with(mock_config)
            mock_metadata.assert_called_once_with(mock_config)

            # 验证客户端属性
            assert client.config is mock_config
            assert hasattr(client, 'query')
            assert hasattr(client, 'download_client')
            assert hasattr(client, 'indicator')
            assert hasattr(client, 'metadata')

    def test_init_with_custom_config(self):
        """测试使用自定义配置初始化"""
        mock_config = Mock(spec=Config)
        
        with patch('kline_data.sdk.sdk_client.QueryClient'), \
             patch('kline_data.sdk.sdk_client.DownloadClient'), \
             patch('kline_data.sdk.sdk_client.IndicatorClient'), \
             patch('kline_data.sdk.sdk_client.MetadataClient'):

            client = KlineClient(config=mock_config)

            assert client.config == mock_config

class TestKlineClientDelegation:
    """测试KlineClient的方法委托"""

    @pytest.fixture
    def mock_client(self):
        """创建mock客户端"""
        mock_config = Mock(spec=Config)
        with patch('kline_data.sdk.sdk_client.QueryClient') as mock_query_cls, \
             patch('kline_data.sdk.sdk_client.DownloadClient') as mock_download_cls, \
             patch('kline_data.sdk.sdk_client.IndicatorClient') as mock_indicator_cls, \
             patch('kline_data.sdk.sdk_client.MetadataClient') as mock_metadata_cls:
            
            client = KlineClient(config=mock_config)
            return client

    def test_get_kline_delegation(self, mock_client):
        """测试get_kline委托给QueryClient"""
        start_time = datetime(2024, 1, 1)
        end_time = datetime(2024, 1, 2)
        
        mock_df = pd.DataFrame({'close': [1, 2, 3]})
        mock_client.query.get_kline.return_value = mock_df
        
        result = mock_client.get_kline(
            exchange='binance',
            symbol='BTC/USDT',
            start_time=start_time,
            end_time=end_time,
            interval='1h'
        )
        
        mock_client.query.get_kline.assert_called_once()
        args, kwargs = mock_client.query.get_kline.call_args
        assert args[0] == 'binance'
        assert args[1] == 'BTC/USDT'
        assert args[2] == start_time
        assert args[3] == end_time
        assert args[4] == '1h'
        
        assert result is mock_df

    def test_get_latest_delegation(self, mock_client):
        """测试get_latest委托给QueryClient"""
        mock_df = pd.DataFrame({'close': [1, 2, 3]})
        mock_client.query.get_latest.return_value = mock_df
        
        result = mock_client.get_latest(
            exchange='binance',
            symbol='BTC/USDT',
            interval='1h',
            limit=100
        )
        
        mock_client.query.get_latest.assert_called_once_with('binance', 'BTC/USDT', '1h', 100)
        assert result is mock_df

    def test_download_delegation(self, mock_client):
        """测试download委托给DownloadClient"""
        start_time = datetime(2024, 1, 1)
        end_time = datetime(2024, 1, 2)
        
        mock_client.download_client.download.return_value = {'status': 'success'}
        
        result = mock_client.download(
            exchange='binance',
            symbol='BTC/USDT',
            start_time=start_time,
            end_time=end_time,
            interval='1m'
        )
        
        mock_client.download_client.download.assert_called_once()
        assert result == {'status': 'success'}

    def test_calculate_indicators_delegation(self, mock_client):
        """测试calculate_indicators委托给IndicatorClient"""
        mock_df = pd.DataFrame({'close': [1, 2, 3]})
        mock_result_df = pd.DataFrame({'close': [1, 2, 3], 'MA_20': [1, 2, 3]})
        mock_client.indicator.calculate.return_value = mock_result_df
        
        result = mock_client.calculate_indicators(
            df=mock_df,
            indicators=['MA_20']
        )
        
        mock_client.indicator.calculate.assert_called_once_with(mock_df, ['MA_20'])
        assert result is mock_result_df

    def test_get_metadata_delegation(self, mock_client):
        """测试get_metadata委托给MetadataClient"""
        mock_client.metadata.get_metadata.return_value = {'count': 100}
        
        result = mock_client.get_metadata(
            exchange='binance',
            symbol='BTC/USDT'
        )
        
        mock_client.metadata.get_metadata.assert_called_once_with('binance', 'BTC/USDT')
        assert result['count'] == 100
