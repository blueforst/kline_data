"""测试数据流模块"""

import pytest
import pandas as pd
from datetime import datetime, timedelta
from sdk.data_feed import ChunkedDataFeed, BacktraderDataFeed, StreamingDataFeed
from config import load_config
from utils.constants import Timeframe, DEFAULT_EXCHANGE, DEFAULT_SYMBOL


class TestChunkedDataFeed:
    """测试ChunkedDataFeed"""
    
    @pytest.fixture
    def config(self):
        """加载配置"""
        return load_config()
    
    @pytest.fixture
    def feed(self, config):
        """创建测试数据流"""
        return ChunkedDataFeed(
            exchange=DEFAULT_EXCHANGE,
            symbol=DEFAULT_SYMBOL,
            start_time=datetime(2024, 1, 1),
            end_time=datetime(2024, 1, 2),
            interval=Timeframe.H1.value,
            chunk_size=10,
            config=config
        )
    
    def test_initialization(self, feed):
        """测试初始化"""
        assert feed.exchange == DEFAULT_EXCHANGE
        assert feed.symbol == DEFAULT_SYMBOL
        assert feed.interval == Timeframe.H1.value
        assert feed.chunk_size == 10
    
    def test_chunk_iteration(self, feed):
        """测试块迭代"""
        chunks = list(feed)
        
        # 应该有数据
        assert len(chunks) > 0
        
        # 每个块都是DataFrame
        for chunk in chunks:
            assert isinstance(chunk, pd.DataFrame)
            assert not chunk.empty
            assert 'timestamp' in chunk.columns
            assert 'open' in chunk.columns
            assert 'high' in chunk.columns
            assert 'low' in chunk.columns
            assert 'close' in chunk.columns
            assert 'volume' in chunk.columns
    
    def test_row_iteration(self, feed):
        """测试行迭代"""
        rows = []
        for row in feed.iter_rows():
            rows.append(row)
            if len(rows) >= 5:  # 只测试前5行
                break
        
        assert len(rows) > 0
        
        # 检查元组格式
        for timestamp, open_price, high, low, close, volume in rows:
            assert isinstance(timestamp, pd.Timestamp)
            assert isinstance(open_price, (int, float))
            assert isinstance(high, (int, float))
            assert isinstance(low, (int, float))
            assert isinstance(close, (int, float))
            assert isinstance(volume, (int, float))
            
            # 基本价格关系
            assert high >= low
            assert high >= open_price
            assert high >= close
            assert low <= open_price
            assert low <= close
    
    def test_dict_iteration(self, feed):
        """测试字典迭代"""
        dicts = []
        for bar in feed.iter_dicts():
            dicts.append(bar)
            if len(dicts) >= 5:
                break
        
        assert len(dicts) > 0
        
        # 检查字典格式
        for bar in dicts:
            assert 'timestamp' in bar
            assert 'open' in bar
            assert 'high' in bar
            assert 'low' in bar
            assert 'close' in bar
            assert 'volume' in bar
    
    def test_to_dataframe(self, feed):
        """测试转换为DataFrame"""
        df = feed.to_dataframe(max_rows=20)
        
        assert isinstance(df, pd.DataFrame)
        assert len(df) <= 20
        assert not df.empty
        
        # 检查列
        required_columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        for col in required_columns:
            assert col in df.columns
    
    def test_reset(self, feed):
        """测试重置"""
        # 第一次迭代
        first_chunks = list(feed)
        first_count = len(first_chunks)
        
        # 重置
        feed.reset()
        
        # 第二次迭代
        second_chunks = list(feed)
        second_count = len(second_chunks)
        
        # 应该得到相同数量的块
        assert first_count == second_count
    
    def test_get_stats(self, feed):
        """测试获取统计信息"""
        # 消费一些数据
        for _ in feed:
            break
        
        stats = feed.get_stats()
        
        assert 'exchange' in stats
        assert 'symbol' in stats
        assert 'interval' in stats
        assert 'chunk_size' in stats
        assert 'chunks_loaded' in stats
        assert 'total_rows_loaded' in stats
        assert stats['exchange'] == DEFAULT_EXCHANGE
        assert stats['symbol'] == DEFAULT_SYMBOL
    
    def test_empty_range(self, config):
        """测试空时间范围"""
        # 未来时间应该没有数据
        feed = ChunkedDataFeed(
            exchange=DEFAULT_EXCHANGE,
            symbol=DEFAULT_SYMBOL,
            start_time=datetime(2099, 1, 1),
            end_time=datetime(2099, 1, 2),
            interval=Timeframe.H1.value,
            chunk_size=10,
            config=config
        )
        
        chunks = list(feed)
        assert len(chunks) == 0 or all(chunk.empty for chunk in chunks)


class TestBacktraderDataFeed:
    """测试BacktraderDataFeed"""
    
    @pytest.fixture
    def config(self):
        """加载配置"""
        return load_config()
    
    @pytest.fixture
    def bt_feed(self, config):
        """创建测试数据流"""
        return BacktraderDataFeed(
            exchange=DEFAULT_EXCHANGE,
            symbol=DEFAULT_SYMBOL,
            start_time=datetime(2024, 1, 1),
            end_time=datetime(2024, 1, 2),
            interval=Timeframe.H1.value,
            chunk_size=10,
            config=config
        )
    
    def test_to_backtrader_format(self, bt_feed):
        """测试转换为backtrader格式"""
        df = bt_feed.to_backtrader_format(max_rows=20)
        
        assert isinstance(df, pd.DataFrame)
        
        if not df.empty:
            # 检查索引是datetime
            assert isinstance(df.index, pd.DatetimeIndex)
            
            # 检查必需的列
            required_columns = ['open', 'high', 'low', 'close', 'volume', 'openinterest']
            for col in required_columns:
                assert col in df.columns
            
            # openinterest应该是0
            assert all(df['openinterest'] == 0)
    
    def test_get_backtrader_params(self, bt_feed):
        """测试获取backtrader参数"""
        params = bt_feed.get_backtrader_params()
        
        assert isinstance(params, dict)
        assert 'datetime' in params
        assert 'open' in params
        assert 'high' in params
        assert 'low' in params
        assert 'close' in params
        assert 'volume' in params
        assert 'openinterest' in params
        
        # 检查值
        assert params['open'] == 'open'
        assert params['high'] == 'high'
        assert params['low'] == 'low'
        assert params['close'] == 'close'
        assert params['volume'] == 'volume'
        assert params['openinterest'] == 'openinterest'


class TestStreamingDataFeed:
    """测试StreamingDataFeed"""
    
    @pytest.fixture
    def config(self):
        """加载配置"""
        return load_config()
    
    @pytest.fixture
    def stream_feed(self, config):
        """创建测试数据流"""
        return StreamingDataFeed(
            exchange=DEFAULT_EXCHANGE,
            symbol=DEFAULT_SYMBOL,
            start_time=datetime(2024, 1, 1),
            end_time=datetime(2024, 1, 1, 1, 0),  # 1小时数据
            interval=Timeframe.M1.value,
            chunk_size=10,
            config=config,
            playback_speed=100.0  # 100倍速
        )
    
    def test_playback_speed(self, stream_feed):
        """测试播放速度"""
        assert stream_feed.playback_speed == 100.0
    
    def test_get_sleep_time(self, stream_feed):
        """测试获取延迟时间"""
        sleep_time = stream_feed.get_sleep_time()
        
        # 1分钟 / 100倍速 = 0.6秒
        expected_sleep = 60.0 / 100.0
        assert abs(sleep_time - expected_sleep) < 0.01
    
    def test_stream(self, stream_feed):
        """测试流式迭代"""
        bars = []
        
        # 只测试前几根
        for bar in stream_feed.stream():
            bars.append(bar)
            if len(bars) >= 3:
                break
        
        assert len(bars) > 0
        
        # 检查字典格式
        for bar in bars:
            assert 'timestamp' in bar
            assert 'close' in bar


class TestDataFeedEdgeCases:
    """测试边界情况"""
    
    @pytest.fixture
    def config(self):
        """加载配置"""
        return load_config()
    
    def test_single_chunk(self, config):
        """测试单个块的情况"""
        feed = ChunkedDataFeed(
            exchange=DEFAULT_EXCHANGE,
            symbol=DEFAULT_SYMBOL,
            start_time=datetime(2024, 1, 1),
            end_time=datetime(2024, 1, 1, 5, 0),  # 5小时
            interval=Timeframe.H1.value,
            chunk_size=100,  # 大于数据量
            config=config
        )
        
        chunks = list(feed)
        
        # 应该只有1个或0个块（如果没有数据）
        assert len(chunks) <= 1
    
    def test_very_small_chunk(self, config):
        """测试非常小的块大小"""
        feed = ChunkedDataFeed(
            exchange=DEFAULT_EXCHANGE,
            symbol=DEFAULT_SYMBOL,
            start_time=datetime(2024, 1, 1),
            end_time=datetime(2024, 1, 2),
            interval=Timeframe.H1.value,
            chunk_size=1,  # 每次只加载1条
            config=config
        )
        
        chunks = list(feed)
        
        # 应该有多个块
        if chunks:
            # 每个块最多1条数据
            for chunk in chunks:
                assert len(chunk) <= 1
    
    def test_invalid_time_range(self, config):
        """测试无效的时间范围"""
        # 结束时间早于开始时间
        with pytest.raises(Exception):
            feed = ChunkedDataFeed(
                exchange=DEFAULT_EXCHANGE,
                symbol=DEFAULT_SYMBOL,
                start_time=datetime(2024, 1, 2),
                end_time=datetime(2024, 1, 1),  # 早于开始时间
                interval=Timeframe.H1.value,
                chunk_size=10,
                config=config
            )
            # 尝试迭代
            list(feed)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
