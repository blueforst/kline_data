"""测试KlineClient初始化"""

import pytest
from unittest.mock import Mock, patch
from sdk.client import KlineClient
from config import Config


class TestClientInitialization:
    """测试客户端初始化"""
    
    def test_init_with_default_config(self):
        """测试使用默认配置初始化"""
        with patch('sdk.client.load_config') as mock_load:
            mock_config = Mock(spec=Config)
            mock_load.return_value = mock_config
            
            client = KlineClient()
            
            assert client.config is not None
            assert hasattr(client, 'fetcher')
            assert hasattr(client, 'download_mgr')
            assert hasattr(client, 'metadata_mgr')
            assert hasattr(client, 'reader')
            assert hasattr(client, 'resampler')
            assert hasattr(client, 'indicator_calc')
    
    def test_init_with_custom_config(self):
        """测试使用自定义配置初始化"""
        config = Mock(spec=Config)
        client = KlineClient(config=config)
        
        assert client.config is config
    
    def test_context_manager(self):
        """测试上下文管理器支持"""
        with patch('sdk.client.load_config'):
            with KlineClient() as client:
                assert isinstance(client, KlineClient)
    
    def test_components_initialized(self):
        """测试所有组件正确初始化"""
        with patch('sdk.client.load_config'):
            client = KlineClient()
            
            # 验证所有必要组件都已初始化
            assert client.fetcher is not None
            assert client.download_mgr is not None
            assert client.metadata_mgr is not None
            assert client.reader is not None
            assert client.resampler is not None
            assert client.indicator_calc is not None
