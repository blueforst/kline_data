"""测试全局常量模块"""

import pytest
from utils.constants import (
    Timeframe,
    TIMEFRAME_SECONDS,
    TIMEFRAME_TO_PANDAS,
    PANDAS_TO_TIMEFRAME,
    SUPPORTED_EXCHANGES,
    COMMON_INTERVALS,
    OHLCV_COLUMNS,
    get_timeframe_seconds,
    validate_timeframe,
    validate_exchange,
)


class TestTimeframeEnum:
    """测试Timeframe枚举"""
    
    def test_enum_values(self):
        """测试枚举值"""
        assert Timeframe.S1.value == '1s'
        assert Timeframe.M1.value == '1m'
        assert Timeframe.M5.value == '5m'
        assert Timeframe.H1.value == '1h'
        assert Timeframe.D1.value == '1d'
        assert Timeframe.W1.value == '1w'
        assert Timeframe.MO1.value == '1M'
    
    def test_seconds_property(self):
        """测试seconds属性"""
        assert Timeframe.S1.seconds == 1
        assert Timeframe.M1.seconds == 60
        assert Timeframe.M5.seconds == 300
        assert Timeframe.H1.seconds == 3600
        assert Timeframe.D1.seconds == 86400
    
    def test_pandas_freq_property(self):
        """测试pandas_freq属性"""
        assert Timeframe.M1.pandas_freq == '1min'
        assert Timeframe.M5.pandas_freq == '5min'
        assert Timeframe.H1.pandas_freq == '1h'
        assert Timeframe.D1.pandas_freq == '1D'
    
    def test_from_string(self):
        """测试from_string方法"""
        assert Timeframe.from_string('1m') == Timeframe.M1
        assert Timeframe.from_string('5m') == Timeframe.M5
        assert Timeframe.from_string('1h') == Timeframe.H1
        assert Timeframe.from_string('1d') == Timeframe.D1
        
        # 测试无效值
        with pytest.raises(ValueError):
            Timeframe.from_string('invalid')
    
    def test_list_all(self):
        """测试list_all方法"""
        all_timeframes = Timeframe.list_all()
        assert isinstance(all_timeframes, list)
        assert '1s' in all_timeframes
        assert '1m' in all_timeframes
        assert '1h' in all_timeframes
        assert '1d' in all_timeframes
        assert len(all_timeframes) == 18  # 总共18个时间周期
    
    def test_is_valid_resample_from(self):
        """测试is_valid_resample_from方法"""
        # 可以从小周期重采样到大周期
        assert Timeframe.H1.is_valid_resample_from(Timeframe.M1) is True
        assert Timeframe.D1.is_valid_resample_from(Timeframe.H1) is True
        assert Timeframe.M5.is_valid_resample_from(Timeframe.M1) is True
        
        # 不能从大周期重采样到小周期
        assert Timeframe.M1.is_valid_resample_from(Timeframe.H1) is False
        assert Timeframe.H1.is_valid_resample_from(Timeframe.D1) is False
        
        # 周期相同时可以
        assert Timeframe.M1.is_valid_resample_from(Timeframe.M1) is True
        
        # 不是整数倍时不可以
        assert Timeframe.M5.is_valid_resample_from(Timeframe.M3) is False


class TestTimeframeConstants:
    """测试时间周期常量"""
    
    def test_timeframe_seconds(self):
        """测试TIMEFRAME_SECONDS常量"""
        assert TIMEFRAME_SECONDS['1s'] == 1
        assert TIMEFRAME_SECONDS['1m'] == 60
        assert TIMEFRAME_SECONDS['5m'] == 300
        assert TIMEFRAME_SECONDS['15m'] == 900
        assert TIMEFRAME_SECONDS['1h'] == 3600
        assert TIMEFRAME_SECONDS['1d'] == 86400
        assert TIMEFRAME_SECONDS['1w'] == 604800
    
    def test_timeframe_to_pandas(self):
        """测试TIMEFRAME_TO_PANDAS常量"""
        assert TIMEFRAME_TO_PANDAS['1m'] == '1min'
        assert TIMEFRAME_TO_PANDAS['5m'] == '5min'
        assert TIMEFRAME_TO_PANDAS['1h'] == '1h'
        assert TIMEFRAME_TO_PANDAS['1d'] == '1D'
    
    def test_pandas_to_timeframe(self):
        """测试PANDAS_TO_TIMEFRAME常量"""
        assert PANDAS_TO_TIMEFRAME['1min'] == '1m'
        assert PANDAS_TO_TIMEFRAME['5min'] == '5m'
        assert PANDAS_TO_TIMEFRAME['1h'] == '1h'
        assert PANDAS_TO_TIMEFRAME['1D'] == '1d'


class TestHelperFunctions:
    """测试辅助函数"""
    
    def test_get_timeframe_seconds(self):
        """测试get_timeframe_seconds函数"""
        assert get_timeframe_seconds('1m') == 60
        assert get_timeframe_seconds('5m') == 300
        assert get_timeframe_seconds('1h') == 3600
        assert get_timeframe_seconds('1d') == 86400
        
        # 测试无效值
        with pytest.raises(ValueError) as exc_info:
            get_timeframe_seconds('invalid')
        assert 'Unknown timeframe' in str(exc_info.value)
    
    def test_validate_timeframe(self):
        """测试validate_timeframe函数"""
        # 有效的时间周期
        validate_timeframe('1m')
        validate_timeframe('5m')
        validate_timeframe('1h')
        validate_timeframe('1d')
        
        # 无效的时间周期
        with pytest.raises(ValueError) as exc_info:
            validate_timeframe('invalid')
        assert 'Invalid timeframe' in str(exc_info.value)
    
    def test_validate_exchange(self):
        """测试validate_exchange函数"""
        # 支持的交易所
        validate_exchange('binance')
        validate_exchange('okx')
        validate_exchange('bybit')
        
        # 不支持的交易所
        with pytest.raises(ValueError) as exc_info:
            validate_exchange('invalid_exchange')
        assert 'Unsupported exchange' in str(exc_info.value)


class TestOtherConstants:
    """测试其他常量"""
    
    def test_supported_exchanges(self):
        """测试SUPPORTED_EXCHANGES常量"""
        assert isinstance(SUPPORTED_EXCHANGES, list)
        assert 'binance' in SUPPORTED_EXCHANGES
        assert 'okx' in SUPPORTED_EXCHANGES
        assert 'bybit' in SUPPORTED_EXCHANGES
        assert len(SUPPORTED_EXCHANGES) >= 3
    
    def test_common_intervals(self):
        """测试COMMON_INTERVALS常量"""
        assert isinstance(COMMON_INTERVALS, list)
        assert '1m' in COMMON_INTERVALS
        assert '5m' in COMMON_INTERVALS
        assert '1h' in COMMON_INTERVALS
        assert '1d' in COMMON_INTERVALS
    
    def test_ohlcv_columns(self):
        """测试OHLCV_COLUMNS常量"""
        assert isinstance(OHLCV_COLUMNS, list)
        assert len(OHLCV_COLUMNS) == 6
        assert 'timestamp' in OHLCV_COLUMNS
        assert 'open' in OHLCV_COLUMNS
        assert 'high' in OHLCV_COLUMNS
        assert 'low' in OHLCV_COLUMNS
        assert 'close' in OHLCV_COLUMNS
        assert 'volume' in OHLCV_COLUMNS


class TestBackwardCompatibility:
    """测试向后兼容性"""
    
    def test_import_from_resampler(self):
        """测试从resampler模块导入（向后兼容）"""
        from resampler.timeframe import Timeframe as OldTimeframe
        from resampler.timeframe import TIMEFRAME_SECONDS as OLD_SECONDS
        
        # 应该是同一个对象
        assert OldTimeframe.M1.value == '1m'
        assert OLD_SECONDS['1m'] == 60
    
    def test_import_from_top_level(self):
        """测试从顶层模块导入"""
        from kline_data import Timeframe as TopTimeframe
        
        assert TopTimeframe.M1.value == '1m'
        assert TopTimeframe.M1.seconds == 60


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
