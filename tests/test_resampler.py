"""重采样层测试"""

import pytest
import pandas as pd
import tempfile
from pathlib import Path
from datetime import datetime, timedelta

from config import load_config
from storage import ParquetWriter
from resampler import (
    Timeframe,
    TimeframeConverter,
    get_timeframe_seconds,
    can_resample,
    validate_timeframe,
    KlineResampler,
)


class TestTimeframe:
    """测试时间周期"""
    
    def test_timeframe_enum(self):
        """测试时间周期枚举"""
        assert Timeframe.S1.value == '1s'
        assert Timeframe.M1.value == '1m'
        assert Timeframe.H1.value == '1h'
        assert Timeframe.D1.value == '1d'
    
    def test_timeframe_seconds(self):
        """测试获取秒数"""
        assert Timeframe.S1.seconds == 1
        assert Timeframe.M1.seconds == 60
        assert Timeframe.H1.seconds == 3600
        assert Timeframe.D1.seconds == 86400
    
    def test_timeframe_pandas_freq(self):
        """测试pandas频率"""
        assert Timeframe.S1.pandas_freq == '1S'
        assert Timeframe.M1.pandas_freq == '1T'
        assert Timeframe.H1.pandas_freq == '1H'
    
    def test_from_string(self):
        """测试从字符串创建"""
        tf = Timeframe.from_string('1m')
        assert tf == Timeframe.M1
    
    def test_is_valid_resample_from(self):
        """测试重采样有效性"""
        assert Timeframe.M1.is_valid_resample_from(Timeframe.S1)
        assert Timeframe.H1.is_valid_resample_from(Timeframe.M1)
        assert not Timeframe.S1.is_valid_resample_from(Timeframe.M1)


class TestTimeframeConverter:
    """测试时间周期转换器"""
    
    def test_to_seconds(self):
        """测试转换为秒"""
        assert TimeframeConverter.to_seconds('1s') == 1
        assert TimeframeConverter.to_seconds('1m') == 60
        assert TimeframeConverter.to_seconds('1h') == 3600
    
    def test_to_pandas(self):
        """测试转换为pandas频率"""
        assert TimeframeConverter.to_pandas('1s') == '1S'
        assert TimeframeConverter.to_pandas('1m') == '1T'
        assert TimeframeConverter.to_pandas('1h') == '1H'
    
    def test_compare(self):
        """测试比较"""
        assert TimeframeConverter.compare('1s', '1m') < 0
        assert TimeframeConverter.compare('1m', '1s') > 0
        assert TimeframeConverter.compare('1m', '1m') == 0
    
    def test_get_smaller(self):
        """测试获取较小周期"""
        assert TimeframeConverter.get_smaller('1s', '1m') == '1s'
        assert TimeframeConverter.get_smaller('1h', '1m') == '1m'
    
    def test_get_larger(self):
        """测试获取较大周期"""
        assert TimeframeConverter.get_larger('1s', '1m') == '1m'
        assert TimeframeConverter.get_larger('1h', '1m') == '1h'


class TestCanResample:
    """测试重采样有效性检查"""
    
    def test_valid_resample(self):
        """测试有效的重采样"""
        assert can_resample('1s', '1m') is True
        assert can_resample('1m', '1h') is True
        assert can_resample('1s', '1h') is True
    
    def test_invalid_resample(self):
        """测试无效的重采样"""
        assert can_resample('1m', '1s') is False
        assert can_resample('1h', '1m') is False
    
    def test_same_timeframe(self):
        """测试相同周期"""
        assert can_resample('1m', '1m') is True


class TestKlineResampler:
    """测试K线重采样器"""
    
    @pytest.fixture
    def temp_config(self):
        """创建临时配置"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = load_config('config/config.yaml')
            config.storage.root_path = tmpdir
            yield config
    
    @pytest.fixture
    def sample_1s_data(self):
        """创建1秒数据"""
        start_date = datetime(2024, 1, 1)
        dates = pd.date_range(start_date, periods=3600, freq='1s')  # 1小时
        
        df = pd.DataFrame({
            'timestamp': dates,
            'open': 100.0,
            'high': 105.0,
            'low': 95.0,
            'close': 102.0,
            'volume': 10.0,
        })
        
        return df
    
    def test_resample_1s_to_1m(self, temp_config, sample_1s_data):
        """测试1秒到1分钟重采样"""
        resampler = KlineResampler(temp_config)
        
        resampled = resampler.resample(
            sample_1s_data,
            '1s',
            '1m'
        )
        
        # 应该有60行（3600秒 / 60秒）
        assert len(resampled) == 60
        
        # 检查OHLC
        assert 'open' in resampled.columns
        assert 'high' in resampled.columns
        assert 'low' in resampled.columns
        assert 'close' in resampled.columns
        
        # 检查成交量（应该是原来的60倍）
        assert resampled['volume'].iloc[0] == 60 * 10.0
    
    def test_resample_1s_to_1h(self, temp_config, sample_1s_data):
        """测试1秒到1小时重采样"""
        resampler = KlineResampler(temp_config)
        
        resampled = resampler.resample(
            sample_1s_data,
            '1s',
            '1h'
        )
        
        # 应该有1行
        assert len(resampled) == 1
        
        # 成交量应该是总和
        assert resampled['volume'].iloc[0] == 3600 * 10.0
    
    def test_resample_1m_to_5m(self, temp_config):
        """测试1分钟到5分钟重采样"""
        # 创建1分钟数据
        start_date = datetime(2024, 1, 1)
        dates = pd.date_range(start_date, periods=60, freq='1T')
        
        df = pd.DataFrame({
            'timestamp': dates,
            'open': 100.0,
            'high': 105.0,
            'low': 95.0,
            'close': 102.0,
            'volume': 10.0,
        })
        
        resampler = KlineResampler(temp_config)
        
        resampled = resampler.resample(df, '1m', '5m')
        
        # 应该有12行（60分钟 / 5分钟）
        assert len(resampled) == 12
        
        # 成交量应该是原来的5倍
        assert resampled['volume'].iloc[0] == 5 * 10.0
    
    def test_resample_ohlc_logic(self, temp_config):
        """测试OHLC逻辑正确性"""
        # 创建有变化的数据
        start_date = datetime(2024, 1, 1)
        dates = pd.date_range(start_date, periods=60, freq='1s')
        
        # 第一分钟价格递增，第二分钟价格递减
        prices = list(range(100, 130)) + list(range(130, 100, -1))
        
        df = pd.DataFrame({
            'timestamp': dates,
            'open': prices,
            'high': [p + 1 for p in prices],
            'low': [p - 1 for p in prices],
            'close': prices,
            'volume': 10.0,
        })
        
        resampler = KlineResampler(temp_config)
        
        resampled = resampler.resample(df, '1s', '1m')
        
        # 检查第一行
        first = resampled.iloc[0]
        assert first['open'] == 100  # 第一个open
        assert first['high'] == 130  # 最大的high
        assert first['low'] == 99    # 最小的low
        assert first['close'] == 129  # 最后一个close
    
    def test_resample_empty_data(self, temp_config):
        """测试空数据重采样"""
        resampler = KlineResampler(temp_config)
        
        empty_df = pd.DataFrame()
        resampled = resampler.resample(empty_df, '1s', '1m')
        
        assert resampled.empty
    
    def test_resample_same_timeframe(self, temp_config, sample_1s_data):
        """测试相同周期重采样"""
        resampler = KlineResampler(temp_config)
        
        resampled = resampler.resample(
            sample_1s_data,
            '1s',
            '1s'
        )
        
        # 应该返回相同的数据
        assert len(resampled) == len(sample_1s_data)
    
    def test_invalid_resample(self, temp_config, sample_1s_data):
        """测试无效的重采样"""
        resampler = KlineResampler(temp_config)
        
        # 尝试从大周期重采样到小周期
        with pytest.raises(ValueError):
            resampler.resample(sample_1s_data, '1m', '1s')
    
    def test_batch_resample(self, temp_config, sample_1s_data):
        """测试批量重采样"""
        # 先保存1秒数据
        writer = ParquetWriter(temp_config)
        writer.write_partitioned(
            sample_1s_data,
            'binance',
            'BTC/USDT',
            '1s'
        )
        
        resampler = KlineResampler(temp_config)
        
        start = datetime(2024, 1, 1)
        end = datetime(2024, 1, 1, 1, 0)
        
        results = resampler.batch_resample(
            'binance',
            'BTC/USDT',
            start,
            end,
            '1s',
            ['1m', '5m', '15m'],
            save=False
        )
        
        assert '1m' in results
        assert '5m' in results
        assert '15m' in results
        
        assert len(results['1m']) == 60
        assert len(results['5m']) == 12
        assert len(results['15m']) == 4
    
    def test_verify_resample(self, temp_config, sample_1s_data):
        """测试重采样验证"""
        resampler = KlineResampler(temp_config)
        
        resampled = resampler.resample(
            sample_1s_data,
            '1s',
            '1m'
        )
        
        result = resampler.verify_resample(
            sample_1s_data,
            resampled,
            '1s',
            '1m'
        )
        
        assert result['valid'] is True
        assert len(result['errors']) == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
