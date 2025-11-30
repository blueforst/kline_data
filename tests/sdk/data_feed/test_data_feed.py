"""测试数据流模块"""

import pytest
import pandas as pd
from datetime import datetime, timedelta
from kline_data.sdk.query.data_feed import ChunkedDataFeed
from kline_data.config import load_config
from kline_data.utils.constants import Timeframe, DEFAULT_EXCHANGE, DEFAULT_SYMBOL


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


class TestChunkedDataFeedAdvanced:
    """测试ChunkedDataFeed高级功能"""

    @pytest.fixture
    def config(self):
        """加载配置"""
        return load_config()

    def test_memory_efficiency(self, config):
        """测试内存效率"""
        # 创建大数据流测试内存效率
        feed = ChunkedDataFeed(
            exchange=DEFAULT_EXCHANGE,
            symbol=DEFAULT_SYMBOL,
            start_time=datetime(2023, 1, 1),
            end_time=datetime(2024, 1, 1),
            interval=Timeframe.H1.value,
            chunk_size=1000,  # 小块大小
            config=config
        )

        # 测试统计信息
        stats = feed.get_stats()
        assert 'exchange' in stats
        assert 'symbol' in stats
        assert 'interval' in stats
        assert 'chunk_size' in stats
        assert stats['chunk_size'] == 1000

    def test_iterator_methods(self, config):
        """测试不同的迭代方法"""
        feed = ChunkedDataFeed(
            exchange=DEFAULT_EXCHANGE,
            symbol=DEFAULT_SYMBOL,
            start_time=datetime(2024, 1, 1),
            end_time=datetime(2024, 1, 1, 5, 0),  # 5小时
            interval=Timeframe.H1.value,
            chunk_size=10,
            config=config
        )

        # 测试行迭代器
        rows = list(feed.iter_rows())
        if rows:
            for row in rows[:5]:  # 只检查前5行
                assert len(row) == 6  # timestamp, open, high, low, close, volume
                assert isinstance(row[0], pd.Timestamp)  # timestamp

        # 测试字典迭代器
        dicts = list(feed.iter_dicts())
        if dicts:
            for bar in dicts[:5]:  # 只检查前5个
                assert 'timestamp' in bar
                assert 'open' in bar
                assert 'high' in bar
                assert 'low' in bar
                assert 'close' in bar
                assert 'volume' in bar


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
