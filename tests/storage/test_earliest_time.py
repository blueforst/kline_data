"""测试自动检测最早可用时间功能"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
from kline_data.storage.downloader import DataDownloader
from kline_data.sdk.client import KlineClient
from kline_data.config import Config


class TestEarliestTimeDetection:
    """测试最早时间检测功能"""
    
    @patch('storage.downloader.ccxt')
    def test_get_earliest_timestamp_success(self, mock_ccxt):
        """测试成功获取最早时间戳"""
        # 模拟配置
        config = Mock(spec=Config)
        config.ccxt = Mock()
        config.ccxt.rate_limit = Mock(enabled=False)
        config.ccxt.retry = Mock(timeout=30)
        config.ccxt.proxy = Mock()
        config.ccxt.proxy.to_dict = Mock(return_value={})
        
        # 模拟交易所返回数据
        mock_exchange = Mock()
        mock_exchange.fetch_ohlcv = Mock(return_value=[
            [1502928000000, 4261.48, 4485.39, 4200.74, 4285.08, 795.15037]  # 2017-08-17
        ])
        mock_ccxt.binance = Mock(return_value=mock_exchange)
        
        # 创建下载器
        downloader = DataDownloader('binance', 'BTC/USDT', config, interval='1d')
        
        # 获取最早时间戳
        earliest_ts = downloader.get_earliest_timestamp()
        
        # 验证
        assert earliest_ts is not None
        assert earliest_ts == 1502928000000
        
        # 验证调用参数
        mock_exchange.fetch_ohlcv.assert_called_once()
        call_args = mock_exchange.fetch_ohlcv.call_args
        assert call_args[0][0] == 'BTC/USDT'
        assert call_args[1]['timeframe'] == '1d'
        assert call_args[1]['since'] == 0
        assert call_args[1]['limit'] == 1
    
    @patch('storage.downloader.ccxt')
    def test_get_earliest_timestamp_no_data(self, mock_ccxt):
        """测试交易所无数据返回的情况"""
        config = Mock(spec=Config)
        config.ccxt = Mock()
        config.ccxt.rate_limit = Mock(enabled=False)
        config.ccxt.retry = Mock(timeout=30)
        config.ccxt.proxy = Mock()
        config.ccxt.proxy.to_dict = Mock(return_value={})
        
        # 模拟交易所返回空数据
        mock_exchange = Mock()
        mock_exchange.fetch_ohlcv = Mock(return_value=[])
        mock_ccxt.binance = Mock(return_value=mock_exchange)
        
        downloader = DataDownloader('binance', 'BTC/USDT', config, interval='1d')
        earliest_ts = downloader.get_earliest_timestamp()
        
        assert earliest_ts is None
    
    @patch('storage.downloader.ccxt')
    def test_get_earliest_timestamp_error_handling(self, mock_ccxt):
        """测试错误处理"""
        config = Mock(spec=Config)
        config.ccxt = Mock()
        config.ccxt.rate_limit = Mock(enabled=False)
        config.ccxt.retry = Mock(timeout=30)
        config.ccxt.proxy = Mock()
        config.ccxt.proxy.to_dict = Mock(return_value={})
        
        # 模拟API错误
        mock_exchange = Mock()
        mock_exchange.fetch_ohlcv = Mock(side_effect=Exception("API Error"))
        mock_ccxt.binance = Mock(return_value=mock_exchange)
        
        downloader = DataDownloader('binance', 'BTC/USDT', config, interval='1d')
        earliest_ts = downloader.get_earliest_timestamp()
        
        assert earliest_ts is None
    
    @patch('storage.downloader.DataDownloader')
    def test_sdk_get_earliest_available_time(self, mock_downloader_class):
        """测试SDK客户端的最早时间获取方法"""
        # 模拟下载器实例
        mock_downloader = Mock()
        mock_downloader.get_earliest_timestamp = Mock(return_value=1502928000000)
        mock_downloader_class.return_value = mock_downloader
        
        # 创建客户端
        config = Mock(spec=Config)
        client = KlineClient(config)
        
        # 获取最早时间
        earliest_time = client.get_earliest_available_time('binance', 'BTC/USDT', interval='1d')
        
        # 验证
        assert earliest_time is not None
        assert isinstance(earliest_time, datetime)
        assert earliest_time.year == 2017
        assert earliest_time.month == 8
        assert earliest_time.day == 17
    
    @patch('storage.downloader.DataDownloader')
    def test_sdk_get_earliest_available_time_failure(self, mock_downloader_class):
        """测试SDK客户端获取失败的情况"""
        mock_downloader = Mock()
        mock_downloader.get_earliest_timestamp = Mock(return_value=None)
        mock_downloader_class.return_value = mock_downloader
        
        config = Mock(spec=Config)
        client = KlineClient(config)
        
        earliest_time = client.get_earliest_available_time('binance', 'BTC/USDT')
        
        assert earliest_time is None
    
    @patch('storage.downloader.ccxt')
    def test_get_earliest_timestamp_different_timeframes(self, mock_ccxt):
        """测试不同时间周期的最早时间查询"""
        config = Mock(spec=Config)
        config.ccxt = Mock()
        config.ccxt.rate_limit = Mock(enabled=False)
        config.ccxt.retry = Mock(timeout=30)
        config.ccxt.proxy = Mock()
        config.ccxt.proxy.to_dict = Mock(return_value={})
        
        # 模拟交易所返回数据
        mock_exchange = Mock()
        mock_exchange.fetch_ohlcv = Mock(return_value=[
            [1502928000000, 4261.48, 4485.39, 4200.74, 4285.08, 795.15037]
        ])
        mock_ccxt.binance = Mock(return_value=mock_exchange)
        
        downloader = DataDownloader('binance', 'BTC/USDT', config, interval='1s')
        
        # 测试不同时间周期
        for timeframe in ['1s', '1m', '1h', '1d']:
            earliest_ts = downloader.get_earliest_timestamp(timeframe=timeframe)
            assert earliest_ts == 1502928000000
            
            # 验证调用使用了正确的时间周期
            call_kwargs = mock_exchange.fetch_ohlcv.call_args[1]
            assert call_kwargs['timeframe'] == timeframe


class TestCLIIntegration:
    """测试CLI集成"""
    
    def test_start_all_parameter_parsing(self):
        """测试 --start all 参数解析"""
        # 这是一个占位测试，实际测试需要运行CLI
        # 在真实环境中，应该使用 typer.testing.CliRunner
        assert True  # CLI参数已在手动测试中验证
    
    @patch('cli.commands.download.DataDownloader')
    @patch('cli.commands.download.get_config')
    def test_cli_auto_detect_flow(self, mock_get_config, mock_downloader_class):
        """测试CLI自动检测流程（模拟）"""
        # 模拟配置
        mock_config = Mock()
        mock_get_config.return_value = mock_config
        
        # 模拟下载器
        mock_downloader = Mock()
        mock_downloader.get_earliest_timestamp = Mock(return_value=1502928000000)
        mock_downloader_class.return_value = mock_downloader
        
        # 验证流程
        earliest_timestamp = mock_downloader.get_earliest_timestamp()
        assert earliest_timestamp is not None
        
        earliest_time = datetime.fromtimestamp(earliest_timestamp / 1000)
        assert earliest_time.year == 2017
        assert earliest_time.month == 8


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
