"""重采样层测试

测试文件已更新为使用统一的全局常量定义。
"""

import pytest
import pandas as pd
import tempfile
from pathlib import Path
from datetime import datetime, timedelta

from kline_data.config import load_config
from kline_data.storage import ParquetWriter

# 导入更新后的resampler模块（现在使用utils.constants）
from kline_data.resampler import (
    Timeframe,
    TimeframeConverter,
    get_timeframe_seconds,
    can_resample,
    validate_timeframe,
    KlineResampler,
    OHLCV_COLUMNS,
)

# 从常量模块导入验证函数（推荐使用方式）
from kline_data.utils.constants import (
    SUPPORTED_EXCHANGES,
    DEFAULT_EXCHANGE,
    DEFAULT_SYMBOL,
    DEMO_SYMBOL,
    TEST_SYMBOLS,
    validate_exchange,
    validate_symbol,
    OHLCV_AGGREGATION_RULES,
    VALIDATION_METHODS,
    CCXT_OHLCV_INDEX,
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
        assert Timeframe.S1.pandas_freq == '1s'
        assert Timeframe.M1.pandas_freq == '1min'
        assert Timeframe.H1.pandas_freq == '1h'
    
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
        assert TimeframeConverter.to_pandas('1s') == '1s'
        assert TimeframeConverter.to_pandas('1m') == '1min'
        assert TimeframeConverter.to_pandas('1h') == '1h'
    
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
        # 使用常量定义的pandas频率
        dates = pd.date_range(start_date, periods=3600, freq=Timeframe.S1.pandas_freq)  # 1小时

        df = pd.DataFrame({
            OHLCV_COLUMNS[0]: dates,  # 'timestamp'
            OHLCV_COLUMNS[1]: 100.0,  # 'open'
            OHLCV_COLUMNS[2]: 105.0,  # 'high'
            OHLCV_COLUMNS[3]: 95.0,   # 'low'
            OHLCV_COLUMNS[4]: 102.0,  # 'close'
            OHLCV_COLUMNS[5]: 10.0,   # 'volume'
        })

        return df
    
    def test_resample_1s_to_1m(self, temp_config, sample_1s_data):
        """测试1秒到1分钟重采样"""
        resampler = KlineResampler(temp_config)

        resampled = resampler.resample(
            sample_1s_data,
            Timeframe.S1.value,
            Timeframe.M1.value
        )

        # 应该有60行（3600秒 / 60秒）
        assert len(resampled) == 60

        # 使用常量检查OHLC列
        assert OHLCV_COLUMNS[1] in resampled.columns  # 'open'
        assert OHLCV_COLUMNS[2] in resampled.columns  # 'high'
        assert OHLCV_COLUMNS[3] in resampled.columns  # 'low'
        assert OHLCV_COLUMNS[4] in resampled.columns  # 'close'

        # 检查成交量（应该是原来的60倍）
        assert resampled[OHLCV_COLUMNS[5]].iloc[0] == 60 * 10.0  # 'volume'
    
    def test_resample_1s_to_1h(self, temp_config, sample_1s_data):
        """测试1秒到1小时重采样"""
        resampler = KlineResampler(temp_config)

        resampled = resampler.resample(
            sample_1s_data,
            Timeframe.S1.value,
            Timeframe.H1.value
        )

        # 应该有1行
        assert len(resampled) == 1

        # 成交量应该是总和（使用常量定义的列名）
        assert resampled[OHLCV_COLUMNS[5]].iloc[0] == 3600 * 10.0  # 'volume'
    
    def test_resample_1m_to_5m(self, temp_config):
        """测试1分钟到5分钟重采样"""
        # 创建1分钟数据
        start_date = datetime(2024, 1, 1)
        dates = pd.date_range(start_date, periods=60, freq=Timeframe.M1.pandas_freq)

        df = pd.DataFrame({
            OHLCV_COLUMNS[0]: dates,  # 'timestamp'
            OHLCV_COLUMNS[1]: 100.0,  # 'open'
            OHLCV_COLUMNS[2]: 105.0,  # 'high'
            OHLCV_COLUMNS[3]: 95.0,   # 'low'
            OHLCV_COLUMNS[4]: 102.0,  # 'close'
            OHLCV_COLUMNS[5]: 10.0,   # 'volume'
        })

        resampler = KlineResampler(temp_config)

        resampled = resampler.resample(
            df,
            Timeframe.M1.value,
            Timeframe.M5.value
        )

        # 应该有12行（60分钟 / 5分钟）
        assert len(resampled) == 12

        # 成交量应该是原来的5倍（使用常量定义的列名）
        assert resampled[OHLCV_COLUMNS[5]].iloc[0] == 5 * 10.0  # 'volume'
    
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
            DEFAULT_EXCHANGE,
            DEFAULT_SYMBOL,
            Timeframe.S1.value
        )
        
        resampler = KlineResampler(temp_config)
        
        start = datetime(2024, 1, 1)
        end = datetime(2024, 1, 1, 1, 0)
        
        results = resampler.batch_resample(
            DEFAULT_EXCHANGE,
            DEFAULT_SYMBOL,
            start,
            end,
            Timeframe.S1.value,
            [Timeframe.M1.value, Timeframe.M5.value, Timeframe.M15.value],
            save=False
        )
        
        assert Timeframe.M1.value in results
        assert Timeframe.M5.value in results
        assert Timeframe.M15.value in results

        assert len(results[Timeframe.M1.value]) == 60
        assert len(results[Timeframe.M5.value]) == 12
        assert len(results[Timeframe.M15.value]) == 4
    
    def test_verify_resample(self, temp_config, sample_1s_data):
        """测试重采样验证"""
        resampler = KlineResampler(temp_config)

        resampled = resampler.resample(
            sample_1s_data,
            Timeframe.S1.value,
            Timeframe.M1.value
        )

        result = resampler.verify_resample(
            sample_1s_data,
            resampled,
            Timeframe.S1.value,
            Timeframe.M1.value
        )
        
        assert result['valid'] is True
        assert len(result['errors']) == 0


class TestConstantsValidation:
    """测试常量验证功能"""

    def test_validate_exchange_function(self):
        """测试交易所验证函数"""
        # 测试有效的交易所
        validate_exchange(DEFAULT_EXCHANGE)
        for exchange in SUPPORTED_EXCHANGES[:3]:  # 测试前3个交易所
            validate_exchange(exchange)

        # 测试无效的交易所
        with pytest.raises(ValueError) as exc_info:
            validate_exchange('invalid_exchange')
        assert 'Unsupported exchange' in str(exc_info.value)

    def test_validate_symbol_function(self):
        """测试交易对验证函数"""
        # 测试有效的交易对
        validate_symbol(DEFAULT_SYMBOL)
        for symbol in TEST_SYMBOLS:
            validate_symbol(symbol)

        # 测试无效的交易对
        with pytest.raises(ValueError) as exc_info:
            validate_symbol('INVALID')
        assert 'Invalid symbol format' in str(exc_info.value)

        with pytest.raises(ValueError) as exc_info:
            validate_symbol('')
        assert 'Invalid symbol format' in str(exc_info.value)

    def test_ohlcv_constants_consistency(self):
        """测试OHLCV常量的一致性"""
        # 验证OHLCV列名常量
        assert len(OHLCV_COLUMNS) == 6
        assert OHLCV_COLUMNS[0] == 'timestamp'
        assert OHLCV_COLUMNS[1] == 'open'
        assert OHLCV_COLUMNS[2] == 'high'
        assert OHLCV_COLUMNS[3] == 'low'
        assert OHLCV_COLUMNS[4] == 'close'
        assert OHLCV_COLUMNS[5] == 'volume'

        # 验证CCXT索引一致性
        assert CCXT_OHLCV_INDEX['timestamp'] == 0
        assert CCXT_OHLCV_INDEX['open'] == 1
        assert CCXT_OHLCV_INDEX['high'] == 2
        assert CCXT_OHLCV_INDEX['low'] == 3
        assert CCXT_OHLCV_INDEX['close'] == 4
        assert CCXT_OHLCV_INDEX['volume'] == 5

        # 验证聚合规则
        assert OHLCV_AGGREGATION_RULES['open'] == 'first'
        assert OHLCV_AGGREGATION_RULES['high'] == 'max'
        assert OHLCV_AGGREGATION_RULES['low'] == 'min'
        assert OHLCV_AGGREGATION_RULES['close'] == 'last'
        assert OHLCV_AGGREGATION_RULES['volume'] == 'sum'

    def test_exchange_constants(self):
        """测试交易所相关常量"""
        # 验证默认交易所
        assert DEFAULT_EXCHANGE in SUPPORTED_EXCHANGES
        assert DEFAULT_EXCHANGE == 'binance'

        # 验证测试符号
        assert DEFAULT_SYMBOL in TEST_SYMBOLS
        assert DEFAULT_SYMBOL == 'BTC/USDT'

        # 验证交易所列表包含主要交易所
        required_exchanges = ['binance', 'okx', 'bybit']
        for exchange in required_exchanges:
            assert exchange in SUPPORTED_EXCHANGES

    def test_validation_methods_constants(self):
        """测试验证方法常量"""
        assert isinstance(VALIDATION_METHODS, list)
        assert 'iqr' in VALIDATION_METHODS
        assert 'zscore' in VALIDATION_METHODS


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
