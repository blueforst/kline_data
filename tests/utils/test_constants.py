"""测试全局常量模块"""

import pytest
from types import SimpleNamespace
import kline_data.config.manager as config_manager
from kline_data.utils.constants import (
    Timeframe,
    TIMEFRAME_SECONDS,
    TIMEFRAME_TO_PANDAS,
    PANDAS_TO_TIMEFRAME,
    SUPPORTED_EXCHANGES,
    DEFAULT_EXCHANGE,
    DEFAULT_SYMBOL,
    COMMON_INTERVALS,
    DEMO_INTERVALS,
    OHLCV_COLUMNS,
    CCXT_OHLCV_INDEX,
    OHLCV_AGGREGATION_RULES,
    TEST_SYMBOLS,
    DEMO_SYMBOL,
    VALIDATION_METHODS,
    VALIDATION_STATUS,
    LOG_LEVELS,
    DEFAULT_LOG_LEVEL,
    SUPPORTED_STORAGE_FORMATS,
    DEFAULT_STORAGE_FORMAT,
    SUPPORTED_COMPRESSIONS,
    DEFAULT_COMPRESSION,
    INTERNAL_TIMEZONE,
    DISPLAY_TIMEZONES,
    API_VERSION,
    DEFAULT_API_PORT,
    DEFAULT_API_HOST,
    get_timeframe_seconds,
    validate_timeframe,
    validate_exchange,
    get_supported_exchanges,
    get_default_exchange,
    validate_symbol,
    validate_ohlcv_aggregation_rule,
    validate_validation_method,
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
        assert '5s' not in all_timeframes
        assert '15s' not in all_timeframes
        assert '30s' not in all_timeframes
        assert len(all_timeframes) == 15  # 更新后总共15个时间周期
    

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
        assert '5s' not in TIMEFRAME_SECONDS
        assert '15s' not in TIMEFRAME_SECONDS
        assert '30s' not in TIMEFRAME_SECONDS
    
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
        with pytest.raises(ValueError) as exc_info:
            validate_timeframe('5s')
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

    def test_get_supported_exchanges_from_config(self, monkeypatch):
        mock_config = SimpleNamespace(
            ccxt=SimpleNamespace(exchanges=['kraken', 'coinbase']),
            cli=SimpleNamespace(default_exchange='kraken'),
        )
        monkeypatch.setattr(config_manager, 'load_config', lambda: mock_config)
        assert get_supported_exchanges() == ['kraken', 'coinbase']

    def test_get_default_exchange_from_config(self, monkeypatch):
        mock_config = SimpleNamespace(
            ccxt=SimpleNamespace(exchanges=['kraken', 'coinbase']),
            cli=SimpleNamespace(default_exchange='kraken'),
        )
        monkeypatch.setattr(config_manager, 'load_config', lambda: mock_config)
        assert get_default_exchange() == 'kraken'

    def test_validate_exchange_uses_configured_list(self, monkeypatch):
        mock_config = SimpleNamespace(
            ccxt=SimpleNamespace(exchanges=['kraken', 'coinbase']),
            cli=SimpleNamespace(default_exchange='kraken'),
        )
        monkeypatch.setattr(config_manager, 'load_config', lambda: mock_config)

        validate_exchange('kraken')
        with pytest.raises(ValueError):
            validate_exchange('binance')


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


class TestAdditionalConstants:
    """测试其他常量"""

    def test_exchange_constants(self):
        """测试交易所相关常量"""
        # 测试支持的交易所
        assert isinstance(SUPPORTED_EXCHANGES, list)
        assert len(SUPPORTED_EXCHANGES) >= 3
        assert DEFAULT_EXCHANGE in SUPPORTED_EXCHANGES
        assert 'binance' in SUPPORTED_EXCHANGES
        assert 'okx' in SUPPORTED_EXCHANGES

        # 测试交易对常量
        assert isinstance(TEST_SYMBOLS, list)
        assert len(TEST_SYMBOLS) >= 1
        assert DEFAULT_SYMBOL in TEST_SYMBOLS
        assert DEFAULT_SYMBOL == DEMO_SYMBOL
        assert '/' in DEFAULT_SYMBOL  # 验证格式

    def test_interval_constants(self):
        """测试时间周期相关常量"""
        # 测试常用周期
        assert isinstance(COMMON_INTERVALS, list)
        assert '1m' in COMMON_INTERVALS
        assert '1h' in COMMON_INTERVALS
        assert '1d' in COMMON_INTERVALS

        # 测试演示周期
        assert isinstance(DEMO_INTERVALS, list)
        assert len(DEMO_INTERVALS) >= 1

    def test_storage_constants(self):
        """测试存储相关常量"""
        # 测试存储格式
        assert isinstance(SUPPORTED_STORAGE_FORMATS, list)
        assert DEFAULT_STORAGE_FORMAT in SUPPORTED_STORAGE_FORMATS

        # 测试压缩算法
        assert isinstance(SUPPORTED_COMPRESSIONS, list)
        assert DEFAULT_COMPRESSION in SUPPORTED_COMPRESSIONS
        assert 'snappy' in SUPPORTED_COMPRESSIONS

    def test_timezone_constants(self):
        """测试时区相关常量"""
        assert isinstance(INTERNAL_TIMEZONE, str)
        assert INTERNAL_TIMEZONE == 'UTC'

        assert isinstance(DISPLAY_TIMEZONES, list)
        assert 'UTC' in DISPLAY_TIMEZONES

    def test_api_constants(self):
        """测试API相关常量"""
        assert isinstance(API_VERSION, str)
        assert API_VERSION.startswith('v')

        assert isinstance(DEFAULT_API_PORT, int)
        assert DEFAULT_API_PORT > 0

        assert isinstance(DEFAULT_API_HOST, str)

    def test_logging_constants(self):
        """测试日志相关常量"""
        assert isinstance(LOG_LEVELS, list)
        assert DEFAULT_LOG_LEVEL in LOG_LEVELS
        assert 'DEBUG' in LOG_LEVELS
        assert 'INFO' in LOG_LEVELS
        assert 'ERROR' in LOG_LEVELS

    def test_validation_constants(self):
        """测试验证相关常量"""
        assert isinstance(VALIDATION_METHODS, list)
        assert 'iqr' in VALIDATION_METHODS
        assert 'zscore' in VALIDATION_METHODS

        assert isinstance(VALIDATION_STATUS, list)
        assert 'success' in VALIDATION_STATUS
        assert 'error' in VALIDATION_STATUS


class TestExtendedValidationFunctions:
    """测试扩展验证函数"""

    def test_validate_symbol_function(self):
        """测试交易对验证函数"""
        # 测试有效交易对
        validate_symbol(DEFAULT_SYMBOL)
        validate_symbol('BTC/USDT')
        validate_symbol('ETH/USDT')

        # 测试无效交易对
        with pytest.raises(ValueError):
            validate_symbol('INVALID')
        with pytest.raises(ValueError):
            validate_symbol('')
        with pytest.raises(ValueError):
            validate_symbol('BTCUSDT')  # 缺少斜杠

    def test_validate_ohlcv_aggregation_rule_function(self):
        """测试OHLCV聚合规则验证函数"""
        # 测试有效规则
        validate_ohlcv_aggregation_rule('open', 'first')
        validate_ohlcv_aggregation_rule('high', 'max')
        validate_ohlcv_aggregation_rule('low', 'min')
        validate_ohlcv_aggregation_rule('close', 'last')
        validate_ohlcv_aggregation_rule('volume', 'sum')

        # 测试无效字段
        with pytest.raises(ValueError):
            validate_ohlcv_aggregation_rule('invalid_field', 'first')

        # 测试无效规则
        with pytest.raises(ValueError):
            validate_ohlcv_aggregation_rule('open', 'invalid_rule')

    def test_validate_validation_method_function(self):
        """测试验证方法验证函数"""
        # 测试有效方法
        validate_validation_method('iqr')
        validate_validation_method('zscore')

        # 测试无效方法
        with pytest.raises(ValueError):
            validate_validation_method('invalid_method')


class TestConstantsConsistency:
    """测试常量一致性"""

    def test_timeframe_consistency(self):
        """测试时间周期常量一致性"""
        # 验证TIMEFRAME_SECONDS和Timeframe枚举的一致性
        for tf in Timeframe:
            assert tf.value in TIMEFRAME_SECONDS
            assert tf.seconds == TIMEFRAME_SECONDS[tf.value]

        # 验证TIMEFRAME_TO_PANDAS和Timeframe枚举的一致性
        for tf in Timeframe:
            assert tf.value in TIMEFRAME_TO_PANDAS
            assert tf.pandas_freq == TIMEFRAME_TO_PANDAS[tf.value]

        # 验证PANDAS_TO_TIMEFRAME是TIMEFRAME_TO_PANDAS的反向映射
        for tf_str, pandas_freq in TIMEFRAME_TO_PANDAS.items():
            assert PANDAS_TO_TIMEFRAME[pandas_freq] == tf_str

    def test_ohlcv_consistency(self):
        """测试OHLCV常量一致性"""
        # 验证OHLCV_COLUMNS和CCXT_OHLCV_INDEX的一致性
        for i, col in enumerate(OHLCV_COLUMNS):
            assert CCXT_OHLCV_INDEX[col] == i

        # 验证OHLCV_AGGREGATION_RULES包含所有OHLCV字段
        for col in OHLCV_COLUMNS:
            if col != 'timestamp':  # timestamp不需要聚合规则
                assert col in OHLCV_AGGREGATION_RULES

    def test_default_constants_in_lists(self):
        """测试默认值都在对应列表中"""
        assert DEFAULT_EXCHANGE in SUPPORTED_EXCHANGES
        assert DEFAULT_SYMBOL in TEST_SYMBOLS
        assert DEFAULT_STORAGE_FORMAT in SUPPORTED_STORAGE_FORMATS
        assert DEFAULT_COMPRESSION in SUPPORTED_COMPRESSIONS
        assert DEFAULT_LOG_LEVEL in LOG_LEVELS


class TestTimeframeEdgeCases:
    """测试Timeframe枚举边界情况"""

    def test_all_timeframes_have_properties(self):
        """测试所有时间周期都有正确的属性"""
        for tf in Timeframe:
            # 验证每个周期都有seconds属性
            assert hasattr(tf, 'seconds')
            assert isinstance(tf.seconds, int)
            assert tf.seconds > 0

            # 验证每个周期都有pandas_freq属性
            assert hasattr(tf, 'pandas_freq')
            assert isinstance(tf.pandas_freq, str)
            assert len(tf.pandas_freq) > 0



if __name__ == '__main__':
    pytest.main([__file__, '-v'])
