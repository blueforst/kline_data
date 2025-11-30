"""测试KlineClient.get_latest方法"""

import pytest
import pandas as pd
from datetime import datetime
from unittest.mock import Mock, patch
from kline_data.sdk.sdk_client import KlineClient
from kline_data.utils.constants import DEFAULT_EXCHANGE, DEFAULT_SYMBOL, Timeframe


class TestGetLatest:
    """测试get_latest方法"""
    
    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        with patch('kline_data.config.load_config'):
            return KlineClient()
    
    @pytest.fixture
    def sample_df(self):
        """创建示例数据"""
        return pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=200, freq='1H'),
            'open': [100.0] * 200,
            'high': [110.0] * 200,
            'low': [90.0] * 200,
            'close': [105.0] * 200,
            'volume': [1000.0] * 200,
        })
    
    def test_get_latest_default_limit(self, client, sample_df):
        """测试默认限制数量"""
        # 模拟元数据返回
        end_timestamp = int(datetime(2024, 1, 8).timestamp() * 1000)
        client.metadata_mgr.get_data_range = Mock(return_value=(0, end_timestamp))
        client.get_kline = Mock(return_value=sample_df)
        
        df = client.get_latest(
            exchange=DEFAULT_EXCHANGE,
            symbol=DEFAULT_SYMBOL,
            interval=Timeframe.H1.value
        )
        
        assert len(df) <= 100  # DEFAULT_QUERY_LIMIT
    
    def test_get_latest_custom_limit(self, client, sample_df):
        """测试自定义限制数量"""
        end_timestamp = int(datetime(2024, 1, 8).timestamp() * 1000)
        client.metadata_mgr.get_data_range = Mock(return_value=(0, end_timestamp))
        client.get_kline = Mock(return_value=sample_df)
        
        limit = 50
        df = client.get_latest(
            exchange=DEFAULT_EXCHANGE,
            symbol=DEFAULT_SYMBOL,
            interval=Timeframe.H1.value,
            limit=limit
        )
        
        assert len(df) <= limit
    
    def test_get_latest_with_indicators(self, client, sample_df):
        """测试带指标"""
        end_timestamp = int(datetime(2024, 1, 8).timestamp() * 1000)
        client.metadata_mgr.get_data_range = Mock(return_value=(0, end_timestamp))
        
        # 添加指标到sample_df
        sample_df_with_indicators = sample_df.copy()
        sample_df_with_indicators['MA_20'] = 100.0
        client.get_kline = Mock(return_value=sample_df_with_indicators)
        
        df = client.get_latest(
            exchange=DEFAULT_EXCHANGE,
            symbol=DEFAULT_SYMBOL,
            interval=Timeframe.H1.value,
            with_indicators=['MA_20']
        )
        
        assert 'MA_20' in df.columns
    
    def test_get_latest_no_data(self, client):
        """测试无数据情况"""
        client.metadata_mgr.get_data_range = Mock(return_value=None)
        
        df = client.get_latest(
            exchange=DEFAULT_EXCHANGE,
            symbol=DEFAULT_SYMBOL,
            interval=Timeframe.H1.value
        )
        
        assert df.empty
    
    def test_get_latest_returns_tail(self, client, sample_df):
        """测试返回最新数据"""
        end_timestamp = int(datetime(2024, 1, 8).timestamp() * 1000)
        client.metadata_mgr.get_data_range = Mock(return_value=(0, end_timestamp))
        client.get_kline = Mock(return_value=sample_df)
        
        limit = 10
        df = client.get_latest(
            exchange=DEFAULT_EXCHANGE,
            symbol=DEFAULT_SYMBOL,
            interval=Timeframe.H1.value,
            limit=limit
        )
        
        # 验证返回的是最后的数据
        assert len(df) == limit
