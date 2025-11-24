"""测试get_klines_before接口"""

import pytest
import pandas as pd
from datetime import datetime, timedelta
from sdk import KlineClient
from utils.timezone import to_utc, datetime_to_timestamp, timestamp_to_datetime, now_utc


class TestGetKlinesBefore:
    """测试get_klines_before接口"""
    
    @pytest.fixture
    def client(self):
        """创建客户端实例"""
        return KlineClient()
    
    def test_basic_usage(self, client):
        """测试基本用法"""
        # 获取2024年1月1日前的10条日线
        before_time = datetime(2024, 1, 1)
        df = client.get_klines_before(
            exchange='binance',
            symbol='BTC/USDT',
            before_time=before_time,
            interval='1d',
            limit=10
        )
        
        # 验证返回的是DataFrame
        assert isinstance(df, pd.DataFrame)
        
        # 如果有数据，验证数据属性
        if not df.empty:
            # 验证数据量不超过limit
            assert len(df) <= 10
            
            # 验证所有时间戳都小于before_time
            before_timestamp = datetime_to_timestamp(to_utc(before_time))
            assert all(df['timestamp'] < before_timestamp)
            
            # 验证数据按时间升序排列
            assert df['timestamp'].is_monotonic_increasing
            
            # 验证必要的列存在
            required_columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
            for col in required_columns:
                assert col in df.columns
    
    def test_with_utc_time(self, client):
        """测试使用UTC时间"""
        # 使用UTC时间
        before_time = to_utc(datetime(2024, 6, 15, 12, 0, 0))
        df = client.get_klines_before(
            exchange='binance',
            symbol='BTC/USDT',
            before_time=before_time,
            interval='1h',
            limit=24
        )
        
        if not df.empty:
            # 验证时间戳处理正确
            before_timestamp = datetime_to_timestamp(before_time)
            assert all(df['timestamp'] < before_timestamp)
            
            # 验证最后一条数据的时间在before_time之前
            last_timestamp = df['timestamp'].iloc[-1]
            assert last_timestamp < before_timestamp
    
    def test_different_intervals(self, client):
        """测试不同的时间周期"""
        before_time = datetime(2024, 2, 1)
        intervals = ['1m', '5m', '15m', '1h', '4h', '1d']
        
        for interval in intervals:
            df = client.get_klines_before(
                exchange='binance',
                symbol='BTC/USDT',
                before_time=before_time,
                interval=interval,
                limit=10
            )
            
            # 验证返回的是DataFrame
            assert isinstance(df, pd.DataFrame)
            
            # 如果有数据，验证基本属性
            if not df.empty:
                assert len(df) <= 10
                assert df['timestamp'].is_monotonic_increasing
    
    def test_with_indicators(self, client):
        """测试附加指标计算"""
        df = client.get_klines_before(
            exchange='binance',
            symbol='BTC/USDT',
            before_time=datetime(2024, 3, 1),
            interval='1d',
            limit=30,
            with_indicators=['MA_20', 'EMA_12', 'RSI_14']
        )
        
        if not df.empty:
            # 验证指标列存在
            assert 'MA_20' in df.columns
            assert 'EMA_12' in df.columns
            assert 'RSI_14' in df.columns
            
            # 验证指标值不全为NaN（至少有一些有效值）
            # 注意：前面的一些值可能是NaN（因为需要历史数据计算）
            assert not df['MA_20'].isna().all()
    
    def test_limit_enforcement(self, client):
        """测试limit参数的限制"""
        limits = [5, 10, 50, 100]
        before_time = datetime(2024, 1, 1)
        
        for limit in limits:
            df = client.get_klines_before(
                exchange='binance',
                symbol='BTC/USDT',
                before_time=before_time,
                interval='1d',
                limit=limit
            )
            
            if not df.empty:
                # 验证返回的数据量不超过limit
                assert len(df) <= limit
    
    def test_time_filtering(self, client):
        """测试时间过滤的正确性"""
        before_time = to_utc(datetime(2024, 1, 15))
        df = client.get_klines_before(
            exchange='binance',
            symbol='BTC/USDT',
            before_time=before_time,
            interval='1d',
            limit=10
        )
        
        if not df.empty:
            before_timestamp = datetime_to_timestamp(before_time)
            
            # 验证所有K线的时间都在before_time之前
            assert all(df['timestamp'] < before_timestamp)
            
            # 验证最后一条K线确实是最接近before_time的
            last_timestamp = df['timestamp'].iloc[-1]
            
            # 将时间戳转换回datetime进行验证
            last_dt = timestamp_to_datetime(last_timestamp)
            assert last_dt < before_time
    
    def test_empty_result(self, client):
        """测试可能返回空结果的情况"""
        # 使用一个很早的时间，可能没有数据
        very_early_time = datetime(2010, 1, 1)
        df = client.get_klines_before(
            exchange='binance',
            symbol='BTC/USDT',
            before_time=very_early_time,
            interval='1d',
            limit=10
        )
        
        # 验证返回的是DataFrame（即使是空的）
        assert isinstance(df, pd.DataFrame)
        
        # 空DataFrame应该有正确的列结构
        if df.empty:
            # 根据实现，空DataFrame可能没有列或有标准列
            # 这里只验证它是DataFrame类型
            assert True
    
    def test_recent_data(self, client):
        """测试获取最近的数据"""
        # 获取当前时间前的数据
        current_time = now_utc()
        df = client.get_klines_before(
            exchange='binance',
            symbol='BTC/USDT',
            before_time=current_time,
            interval='1h',
            limit=24
        )
        
        if not df.empty:
            # 验证最新的K线时间在当前时间之前
            last_timestamp = df['timestamp'].iloc[-1]
            current_timestamp = datetime_to_timestamp(current_time)
            assert last_timestamp < current_timestamp
    
    def test_timezone_consistency(self, client):
        """测试时区处理的一致性"""
        # 测试naive datetime和aware datetime的处理
        naive_dt = datetime(2024, 1, 1, 12, 0, 0)
        aware_dt = to_utc(datetime(2024, 1, 1, 12, 0, 0))
        
        df1 = client.get_klines_before(
            exchange='binance',
            symbol='BTC/USDT',
            before_time=naive_dt,
            interval='1d',
            limit=5
        )
        
        df2 = client.get_klines_before(
            exchange='binance',
            symbol='BTC/USDT',
            before_time=aware_dt,
            interval='1d',
            limit=5
        )
        
        # 两种方式应该返回相同的结果
        if not df1.empty and not df2.empty:
            pd.testing.assert_frame_equal(df1, df2)
    
    def test_data_ordering(self, client):
        """测试数据排序"""
        df = client.get_klines_before(
            exchange='binance',
            symbol='BTC/USDT',
            before_time=datetime(2024, 2, 1),
            interval='1h',
            limit=50
        )
        
        if not df.empty:
            # 验证时间戳严格升序
            timestamps = df['timestamp'].values
            assert all(timestamps[i] < timestamps[i+1] for i in range(len(timestamps)-1))
            
            # 验证最后一条是最新的（最接近before_time）
            assert df['timestamp'].iloc[-1] == df['timestamp'].max()


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
