"""读取层测试"""

import pytest
import pandas as pd
import tempfile
from pathlib import Path
from datetime import datetime, timedelta

from config import load_config
from storage import ParquetWriter
from reader import (
    LRUCache,
    DataCache,
    ParquetReader,
    QueryEngine,
    QueryBuilder,
)


class TestLRUCache:
    """测试LRU缓存"""
    
    def test_cache_put_and_get(self):
        """测试存入和获取"""
        cache = LRUCache(max_size_mb=10, ttl_seconds=60)
        
        df = pd.DataFrame({'a': [1, 2, 3]})
        cache.put('test_key', df)
        
        result = cache.get('test_key')
        assert result is not None
        assert len(result) == 3
    
    def test_cache_miss(self):
        """测试缓存未命中"""
        cache = LRUCache(max_size_mb=10, ttl_seconds=60)
        
        result = cache.get('nonexistent_key')
        assert result is None
    
    def test_cache_eviction(self):
        """测试缓存淘汰"""
        cache = LRUCache(max_size_mb=1, ttl_seconds=60)
        
        # 创建大数据
        large_df = pd.DataFrame({'a': range(100000)})
        
        cache.put('key1', large_df)
        cache.put('key2', large_df)
        
        # key1应该被淘汰
        assert cache.get('key1') is None
        assert cache.get('key2') is not None
    
    def test_cache_stats(self):
        """测试统计信息"""
        cache = LRUCache(max_size_mb=10, ttl_seconds=60)
        
        df = pd.DataFrame({'a': [1, 2, 3]})
        cache.put('key1', df)
        
        cache.get('key1')  # 命中
        cache.get('key2')  # 未命中
        
        stats = cache.get_stats()
        assert stats['hits'] == 1
        assert stats['misses'] == 1
        assert stats['size'] == 1


class TestDataCache:
    """测试数据缓存"""
    
    def test_get_or_compute(self):
        """测试获取或计算"""
        cache = DataCache(max_size_mb=10, ttl_seconds=60)
        
        def compute_data():
            return pd.DataFrame({'a': [1, 2, 3]})
        
        # 第一次调用应该计算
        result1 = cache.get_or_compute('key1', compute_data)
        assert len(result1) == 3
        
        # 第二次调用应该从缓存获取
        result2 = cache.get_or_compute('key1', compute_data)
        assert len(result2) == 3
    
    def test_invalidate_pattern(self):
        """测试模式匹配删除"""
        cache = DataCache(max_size_mb=10, ttl_seconds=60)
        
        df = pd.DataFrame({'a': [1, 2, 3]})
        cache.put('user:1:data', df)
        cache.put('user:2:data', df)
        cache.put('admin:1:data', df)
        
        # 删除所有user相关的缓存
        count = cache.invalidate_pattern('user:')
        assert count == 2
        
        assert cache.get('user:1:data') is None
        assert cache.get('admin:1:data') is not None


class TestParquetReader:
    """测试Parquet读取器"""
    
    @pytest.fixture
    def temp_config(self):
        """创建临时配置"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = load_config('config/config.yaml')
            config.storage.root_path = tmpdir
            config.memory.cache.enabled = True
            yield config
    
    @pytest.fixture
    def sample_data(self, temp_config):
        """创建示例数据"""
        # 创建测试数据
        start_date = datetime(2024, 1, 1)
        dates = pd.date_range(start_date, periods=1000, freq='1s')
        
        df = pd.DataFrame({
            'timestamp': dates,
            'open': 100.0,
            'high': 105.0,
            'low': 95.0,
            'close': 102.0,
            'volume': 1000.0,
        })
        
        # 写入文件
        writer = ParquetWriter(temp_config)
        writer.write_partitioned(df, 'binance', 'BTC/USDT', '1s')
        
        return df
    
    def test_read_range(self, temp_config, sample_data):
        """测试读取范围数据"""
        reader = ParquetReader(temp_config)
        
        start = datetime(2024, 1, 1)
        end = datetime(2024, 1, 1, 0, 5)
        
        df = reader.read_range('binance', 'BTC/USDT', start, end, '1s')
        
        assert not df.empty
        assert len(df) > 0
        assert 'timestamp' in df.columns
    
    def test_read_with_cache(self, temp_config, sample_data):
        """测试缓存读取"""
        reader = ParquetReader(temp_config)
        
        start = datetime(2024, 1, 1)
        end = datetime(2024, 1, 1, 0, 5)
        
        # 第一次读取（缓存未命中）
        df1 = reader.read_range('binance', 'BTC/USDT', start, end, '1s')
        stats1 = reader.get_cache_stats()
        
        # 第二次读取（缓存命中）
        df2 = reader.read_range('binance', 'BTC/USDT', start, end, '1s')
        stats2 = reader.get_cache_stats()
        
        assert len(df1) == len(df2)
        assert stats2['hits'] > stats1['hits']
    
    def test_read_latest(self, temp_config, sample_data):
        """测试读取最新数据"""
        reader = ParquetReader(temp_config)
        
        df = reader.read_latest('binance', 'BTC/USDT', '1s', limit=10)
        
        assert not df.empty
        assert len(df) <= 10
    
    def test_get_available_dates(self, temp_config, sample_data):
        """测试获取可用日期"""
        reader = ParquetReader(temp_config)
        
        dates = reader.get_available_dates('binance', 'BTC/USDT', '1s')
        
        assert len(dates) > 0
        assert all(isinstance(d, datetime) for d in dates)


class TestQueryEngine:
    """测试查询引擎"""
    
    @pytest.fixture
    def temp_config(self):
        """创建临时配置"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = load_config('config/config.yaml')
            config.storage.root_path = tmpdir
            yield config
    
    @pytest.fixture
    def sample_data(self, temp_config):
        """创建示例数据"""
        start_date = datetime(2024, 1, 1)
        dates = pd.date_range(start_date, periods=1000, freq='1s')
        
        df = pd.DataFrame({
            'timestamp': dates,
            'open': 100.0,
            'high': 105.0,
            'low': 95.0,
            'close': 102.0,
            'volume': 1000.0,
        })
        
        writer = ParquetWriter(temp_config)
        writer.write_partitioned(df, 'binance', 'BTC/USDT', '1s')
        
        return df
    
    def test_basic_query(self, temp_config, sample_data):
        """测试基本查询"""
        engine = QueryEngine(temp_config)
        
        start = datetime(2024, 1, 1)
        end = datetime(2024, 1, 1, 0, 5)
        
        df = engine.query('binance', 'BTC/USDT', start, end, '1s')
        
        assert not df.empty
        assert 'timestamp' in df.columns
    
    def test_query_with_condition(self, temp_config, sample_data):
        """测试条件查询"""
        engine = QueryEngine(temp_config)
        
        start = datetime(2024, 1, 1)
        end = datetime(2024, 1, 1, 0, 5)
        
        df = engine.query_with_condition(
            'binance',
            'BTC/USDT',
            start,
            end,
            '1s',
            'volume > 500'
        )
        
        assert not df.empty
        assert all(df['volume'] > 500)
    
    def test_query_statistics(self, temp_config, sample_data):
        """测试统计查询"""
        engine = QueryEngine(temp_config)
        
        start = datetime(2024, 1, 1)
        end = datetime(2024, 1, 1, 0, 5)
        
        stats = engine.query_statistics('binance', 'BTC/USDT', start, end, '1s')
        
        assert 'count' in stats
        assert 'price' in stats
        assert 'volume' in stats
        assert stats['count'] > 0


class TestQueryBuilder:
    """测试查询构建器"""
    
    @pytest.fixture
    def temp_config(self):
        """创建临时配置"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = load_config('config/config.yaml')
            config.storage.root_path = tmpdir
            yield config
    
    @pytest.fixture
    def sample_data(self, temp_config):
        """创建示例数据"""
        start_date = datetime(2024, 1, 1)
        dates = pd.date_range(start_date, periods=1000, freq='1s')
        
        df = pd.DataFrame({
            'timestamp': dates,
            'open': 100.0,
            'high': 105.0,
            'low': 95.0,
            'close': 102.0,
            'volume': 1000.0,
        })
        
        writer = ParquetWriter(temp_config)
        writer.write_partitioned(df, 'binance', 'BTC/USDT', '1s')
        
        return df
    
    def test_builder_basic(self, temp_config, sample_data):
        """测试基本构建器"""
        engine = QueryEngine(temp_config)
        builder = QueryBuilder(engine)
        
        start = datetime(2024, 1, 1)
        end = datetime(2024, 1, 1, 0, 5)
        
        df = (builder
              .exchange('binance')
              .symbol('BTC/USDT')
              .time_range(start, end)
              .interval('1s')
              .execute())
        
        assert not df.empty
    
    def test_builder_with_limit(self, temp_config, sample_data):
        """测试限制数量"""
        engine = QueryEngine(temp_config)
        builder = QueryBuilder(engine)
        
        start = datetime(2024, 1, 1)
        end = datetime(2024, 1, 1, 0, 5)
        
        df = (builder
              .exchange('binance')
              .symbol('BTC/USDT')
              .time_range(start, end)
              .limit(10)
              .execute())
        
        assert len(df) <= 10
    
    def test_builder_with_columns(self, temp_config, sample_data):
        """测试指定列"""
        engine = QueryEngine(temp_config)
        builder = QueryBuilder(engine)
        
        start = datetime(2024, 1, 1)
        end = datetime(2024, 1, 1, 0, 5)
        
        df = (builder
              .exchange('binance')
              .symbol('BTC/USDT')
              .time_range(start, end)
              .columns('timestamp', 'close')
              .execute())
        
        assert not df.empty
        assert set(df.columns) == {'timestamp', 'close'}


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
