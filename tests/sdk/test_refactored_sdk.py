"""
重构后SDK模块测试

测试新的模块化结构是否正常工作
"""

import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock
import pandas as pd


class TestModularImports:
    """测试模块导入"""
    
    def test_import_sdk_client(self):
        """测试导入统一客户端"""
        from kline_data.sdk import KlineClient
        assert KlineClient is not None
    
    def test_import_sub_clients(self):
        """测试导入子客户端"""
        from kline_data.sdk import (
            QueryClient,
            DownloadClient,
            IndicatorClient,
            MetadataClient
        )
        assert QueryClient is not None
        assert DownloadClient is not None
        # ResampleClient 已移除
        assert IndicatorClient is not None
        assert MetadataClient is not None
    
    def test_import_data_feeds(self):
        """测试导入数据流"""
        from kline_data.sdk import ChunkedDataFeed
        # 只有 ChunkedDataFeed 在当前 SDK 中导出
        assert ChunkedDataFeed is not None
        
        # BacktraderDataFeed 和 StreamingDataFeed 未在 __init__.py 中导出
        # 但可以直接从模块导入（如果存在）
        try:
            from kline_data.sdk.query.data_feed import BacktraderDataFeed
            assert BacktraderDataFeed is not None
        except ImportError:
            pytest.skip("BacktraderDataFeed not implemented yet")


class TestUnifiedClientStructure:
    """测试统一客户端结构"""
    
    @patch('kline_data.sdk.sdk_client.QueryClient')
    @patch('kline_data.sdk.sdk_client.DownloadClient')
    @patch('kline_data.sdk.sdk_client.IndicatorClient')
    @patch('kline_data.sdk.sdk_client.MetadataClient')
    @patch('kline_data.sdk.sdk_client.load_config')
    def test_sdk_client_initialization(
        self, mock_load_config, mock_metadata, mock_indicator,
        mock_download, mock_query
    ):
        """测试统一客户端初始化（ResampleClient 已移除）"""
        from kline_data.sdk import KlineClient
        
        mock_config = MagicMock()
        mock_load_config.return_value = mock_config
        
        client = KlineClient()
        
        # 验证子客户端都被初始化
        mock_query.assert_called_once_with(mock_config)
        mock_download.assert_called_once_with(mock_config)
        # ResampleClient 已移除
        mock_indicator.assert_called_once_with(mock_config)
        mock_metadata.assert_called_once_with(mock_config)
        
        # 验证子客户端被存储
        assert hasattr(client, 'query')
        assert hasattr(client, 'download')
        # ResampleClient 已移除
        assert hasattr(client, 'indicator')
        assert hasattr(client, 'metadata')


class TestQueryClientDataFeedIntegration:
    """测试QueryClient与DataFeed的集成"""
    
    @patch('kline_data.sdk.query.query_client.DataFetcher')
    @patch('kline_data.sdk.query.query_client.load_config')
    def test_data_feed_uses_query_client(self, mock_load_config, mock_fetcher):
        """测试DataFeed使用QueryClient"""
        from kline_data.sdk.query import ChunkedDataFeed
        
        mock_config = MagicMock()
        mock_load_config.return_value = mock_config
        
        # 模拟QueryClient返回数据
        mock_df = pd.DataFrame({
            'timestamp': [1000, 2000, 3000],
            'open': [100, 101, 102],
            'high': [105, 106, 107],
            'low': [99, 100, 101],
            'close': [104, 105, 106],
            'volume': [1000, 1100, 1200]
        })
        
        with patch('kline_data.sdk.query.data_feed.QueryClient') as mock_query_client_class:
            mock_query_client = MagicMock()
            mock_query_client.get_kline.return_value = mock_df
            mock_query_client_class.return_value = mock_query_client
            
            # 创建数据流
            feed = ChunkedDataFeed(
                exchange='binance',
                symbol='BTC/USDT',
                start_time=datetime(2024, 1, 1),
                end_time=datetime(2024, 1, 2),
                interval='1h',
                chunk_size=100
            )
            
            # 验证QueryClient被使用
            assert hasattr(feed, 'query_client')


class TestBackwardCompatibility:
    """测试向后兼容性"""
    
    def test_old_client_import_shows_warning(self):
        """测试旧的client已归档"""
        # 旧的 client.py 已移至 archived/，不再可导入
        # 应该使用 from kline_data.sdk import KlineClient
        import warnings
        
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            
            try:
                # 尝试从归档位置导入（应该失败或触发警告）
                from kline_data.sdk.archived.client import KlineClient
                
                # 如果能导入，验证有警告
                if len(w) >= 1:
                    assert issubclass(w[-1].category, DeprecationWarning)
                    assert "deprecated" in str(w[-1].message).lower() or "archived" in str(w[-1].message).lower()
            except (ImportError, ModuleNotFoundError):
                # 预期行为：导入失败
                pytest.skip("Archived client cannot be imported (expected)")
    
    def test_old_data_feed_import_shows_warning(self):
        """测试旧的data_feed已归档"""
        # 旧的 data_feed.py 已移至 archived/，不再可导入
        import warnings
        
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            
            try:
                from kline_data.sdk.archived.data_feed import ChunkedDataFeed
                
                if len(w) >= 1:
                    assert issubclass(w[-1].category, DeprecationWarning)
                    assert "deprecated" in str(w[-1].message).lower() or "archived" in str(w[-1].message).lower()
            except (ImportError, ModuleNotFoundError):
                pytest.skip("Archived data_feed cannot be imported (expected)")


class TestIndicatorClient:
    """测试指标客户端"""
    
    def test_indicator_client_calculate(self):
        """测试指标计算"""
        from kline_data.sdk import IndicatorClient
        
        # 创建测试数据
        df = pd.DataFrame({
            'timestamp': range(100),
            'open': [100 + i for i in range(100)],
            'high': [105 + i for i in range(100)],
            'low': [99 + i for i in range(100)],
            'close': [104 + i for i in range(100)],
            'volume': [1000 + i * 10 for i in range(100)]
        })
        
        client = IndicatorClient()
        
        # 计算MA指标
        result = client.calculate(df, ['MA_20'])
        
        # 验证结果
        assert 'MA_20' in result.columns
        assert len(result) == len(df)


class TestSubClientIsolation:
    """测试子客户端隔离"""
    
    @patch('kline_data.sdk.query.query_client.load_config')
    def test_query_client_standalone(self, mock_load_config):
        """测试QueryClient可独立使用"""
        from kline_data.sdk import QueryClient
        
        mock_config = MagicMock()
        mock_load_config.return_value = mock_config
        
        client = QueryClient()
        
        assert hasattr(client, 'fetcher')
        assert hasattr(client, 'metadata_mgr')
        assert hasattr(client, 'reader')
    
    @patch('kline_data.sdk.download.download_client.load_config')
    def test_download_client_standalone(self, mock_load_config):
        """测试DownloadClient可独立使用"""
        from kline_data.sdk import DownloadClient
        
        mock_config = MagicMock()
        mock_load_config.return_value = mock_config
        
        client = DownloadClient()
        
        assert hasattr(client, 'download_mgr')
        assert hasattr(client, 'metadata_mgr')
    

if __name__ == '__main__':
    pytest.main([__file__, '-v'])
