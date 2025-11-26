"""
测试数据工厂 - 使用Factory Boy创建测试数据

提供各种测试数据的工厂类，确保测试数据的可重复性和真实性。
"""

import factory
import random
from datetime import datetime, timedelta
from typing import Dict, Any, List
import pandas as pd
import numpy as np
from faker import Faker

# 初始化Faker
fake = Faker()
Faker.seed(42)  # 确保可重复性

# 设置随机种子
random.seed(42)
np.random.seed(42)


# ============================================================================
# OHLCV数据工厂
# ============================================================================

class OHLCVDataFactory(factory.Factory):
    """OHLCV数据工厂"""

    class Meta:
        model = dict

    # 基础价格字段
    timestamp = factory.LazyFunction(lambda: datetime.now())
    open = factory.Faker('pyfloat', left_digits=5, right_digits=2, min_value=100, max_value=100000)
    close = factory.Faker('pyfloat', left_digits=5, right_digits=2, min_value=100, max_value=100000)
    volume = factory.Faker('pyint', min_value=100, max_value=10000000)

    class Params:
        """参数化配置"""
        price_range = factory.Trait(
            open=factory.Faker('pyfloat', left_digits=5, right_digits=2, min_value=20000, max_value=80000),
            close=factory.Faker('pyfloat', left_digits=5, right_digits=2, min_value=20000, max_value=80000),
        )

        altcoin_range = factory.Trait(
            open=factory.Faker('pyfloat', left_digits=3, right_digits=4, min_value=0.001, max_value=10),
            close=factory.Faker('pyfloat', left_digits=3, right_digits=4, min_value=0.001, max_value=10),
        )

        high_volume = factory.Trait(
            volume=factory.Faker('pyint', min_value=1000000, max_value=100000000),
        )

    @factory.lazy_attribute
    def high(self):
        """生成合理的高价"""
        base_price = max(self.open, self.close)
        return base_price * (1 + random.uniform(0.001, 0.02))  # 0.1%-2%的涨幅

    @factory.lazy_attribute
    def low(self):
        """生成合理的低价"""
        base_price = min(self.open, self.close)
        return base_price * (1 - random.uniform(0.001, 0.02))  # 0.1%-2%的跌幅


# ============================================================================
# K线数据时间序列工厂
# ============================================================================

class KlineTimeSeriesFactory(factory.Factory):
    """K线时间序列数据工厂"""

    class Meta:
        model = pd.DataFrame

    @classmethod
    def create(cls, **kwargs):
        """创建时间序列数据"""
        # 参数解析
        count = kwargs.get('count', 100)
        timeframe = kwargs.get('timeframe', '1h')
        start_time = kwargs.get('start_time', datetime.now() - timedelta(days=count))
        base_price = kwargs.get('base_price', 50000.0)
        volatility = kwargs.get('volatility', 0.02)
        trend = kwargs.get('trend', 0.0)  # 趋势：正值为上涨，负值为下跌

        # 计算时间间隔
        if timeframe == '1m':
            freq = '1min'
            periods = count
        elif timeframe == '5m':
            freq = '5min'
            periods = count
        elif timeframe == '15m':
            freq = '15min'
            periods = count
        elif timeframe == '1h':
            freq = '1h'
            periods = count
        elif timeframe == '4h':
            freq = '4h'
            periods = count
        elif timeframe == '1d':
            freq = '1D'
            periods = count
        else:
            raise ValueError(f"Unsupported timeframe: {timeframe}")

        # 生成时间戳
        timestamps = pd.date_range(start=start_time, periods=periods, freq=freq)

        # 生成价格序列（带趋势的随机游走）
        returns = np.random.normal(trend/periods, volatility/np.sqrt(periods), periods)
        prices = [base_price]

        for ret in returns:
            prices.append(max(prices[-1] * (1 + ret), 1.0))  # 确保价格为正

        prices = prices[1:]  # 移除初始价格

        # 生成OHLCV数据
        data = []
        for i, ts in enumerate(timestamps):
            current_price = prices[i]

            # 确定开盘价（第一条数据的开盘价为base_price）
            if i == 0:
                open_price = base_price
            else:
                open_price = prices[i-1]

            close_price = current_price

            # 生成高低价（基于波动性）
            price_range = current_price * volatility * random.uniform(0.5, 1.5)
            high = max(open_price, close_price) + price_range * random.uniform(0.3, 1.0)
            low = min(open_price, close_price) - price_range * random.uniform(0.3, 1.0)

            # 确保价格逻辑正确
            high = max(high, open_price, close_price)
            low = min(low, open_price, close_price)

            # 生成成交量（与价格变化相关）
            price_change_pct = abs(close_price - open_price) / open_price
            base_volume = random.randint(1000, 100000)
            volume_multiplier = 1 + price_change_pct * 5  # 价格变化大时成交量增加
            volume = int(base_volume * volume_multiplier)

            data.append({
                'timestamp': ts,
                'open': round(open_price, 2),
                'high': round(high, 2),
                'low': round(low, 2),
                'close': round(close_price, 2),
                'volume': volume
            })

        return pd.DataFrame(data)


# ============================================================================
# 元数据工厂
# ============================================================================

class MetadataFactory(factory.Factory):
    """文件元数据工厂"""

    class Meta:
        model = dict

    exchange = factory.Faker('random_element', elements=['binance', 'okx', 'huobi', 'coinbase'])
    symbol = factory.Faker('cryptocurrency_name')
    timeframe = factory.Faker('random_element', elements=['1m', '5m', '15m', '1h', '4h', '1d'])
    first_timestamp = factory.LazyFunction(lambda: datetime.now() - timedelta(days=365))
    last_timestamp = factory.LazyFunction(datetime.now)
    total_records = factory.Faker('pyint', min_value=1000, max_value=1000000)
    file_size = factory.Faker('pyint', min_value=1024*1024, max_value=1024*1024*1024)  # 1MB-1GB
    compression = factory.Faker('random_element', elements=['snappy', 'gzip', 'lz4', None])
    created_at = factory.LazyFunction(datetime.now)
    updated_at = factory.LazyFunction(datetime.now)

    class Params:
        """特定场景的参数配置"""
        recent_file = factory.Trait(
            created_at=factory.LazyFunction(lambda: datetime.now() - timedelta(hours=1)),
            updated_at=factory.LazyFunction(lambda: datetime.now() - timedelta(minutes=30)),
        )

        old_file = factory.Trait(
            created_at=factory.LazyFunction(lambda: datetime.now() - timedelta(days=365)),
            updated_at=factory.LazyFunction(lambda: datetime.now() - timedelta(days=300)),
        )

        large_file = factory.Trait(
            total_records=factory.Faker('pyint', min_value=500000, max_value=1000000),
            file_size=factory.Faker('pyint', min_value=500*1024*1024, max_value=1024*1024*1024),
        )


# ============================================================================
# 配置对象工厂
# ============================================================================

class ConfigFactory(factory.Factory):
    """配置对象工厂"""

    class Meta:
        model = dict

    # 存储配置
    storage = factory.lazy_attribute(lambda o: {
        'data_dir': fake.file_path(),
        'use_compression': fake.boolean(),
        'chunk_size': fake.pyint(min_value=1000, max_value=10000),
        'max_file_size': fake.pyint(min_value=100*1024*1024, max_value=1024*1024*1024),
    })

    # API配置
    api = factory.lazy_attribute(lambda o: {
        'host': fake.ipv4(),
        'port': fake.pyint(min_value=8000, max_value=9000),
        'debug': fake.boolean(),
        'cors_origins': [fake.url() for _ in range(fake.pyint(min_value=1, max_value=5))],
    })

    # CCXT配置
    ccxt = factory.lazy_attribute(lambda o: {
        'rate_limit': fake.pyint(min_value=100, max_value=2000),
        'timeout': fake.pyint(min_value=5000, max_value=60000),
        'enable_rate_limit': True,
        'retries': fake.pyint(min_value=1, max_value=5),
    })

    # 下载配置
    download = factory.lazy_attribute(lambda o: {
        'max_concurrent': fake.pyint(min_value=1, max_value=10),
        'retry_attempts': fake.pyint(min_value=1, max_value=5),
        'retry_delay': fake.pyint(min_value=1, max_value=60),
        'chunk_size': fake.pyint(min_value=100, max_value=1000),
    })

    # 日志配置
    logging = factory.lazy_attribute(lambda o: {
        'level': fake.random_element(elements=['DEBUG', 'INFO', 'WARNING', 'ERROR']),
        'file': fake.file_name(extension='log'),
        'max_size': fake.pyint(min_value=1024*1024, max_value=100*1024*1024),
        'backup_count': fake.pyint(min_value=1, max_value=10),
    })


# ============================================================================
# 技术指标数据工厂
# ============================================================================

class IndicatorDataFactory(factory.Factory):
    """技术指标数据工厂"""

    class Meta:
        model = dict

    indicator_name = factory.Faker('random_element', elements=[
        'SMA', 'EMA', 'RSI', 'MACD', 'BB', 'STOCH', 'ADX', 'ATR', 'OBV', 'VWAP'
    ])
    period = factory.Faker('pyint', min_value=5, max_value=200)
    parameters = factory.lazy_attribute(lambda o: {
        'period': o.period,
        'source': fake.random_element(elements=['close', 'open', 'high', 'low', 'hl2', 'hlc3', 'ohlc4']),
        'price_adjustment': fake.random_element(elements=[None, 'close', 'weighted']),
    })
    timestamp = factory.LazyFunction(datetime.now)

    class Params:
        """特定指标的参数"""
        moving_average = factory.Trait(
            indicator_name=factory.Faker('random_element', elements=['SMA', 'EMA', 'WMA']),
            parameters=factory.lazy_attribute(lambda o: {
                'period': o.period,
                'source': 'close',
            })
        )

        oscillator = factory.Trait(
            indicator_name=factory.Faker('random_element', elements=['RSI', 'STOCH', 'CCI', 'MFI']),
            parameters=factory.lazy_attribute(lambda o: {
                'period': o.period,
                'upper_band': 70,
                'lower_band': 30,
            })
        )

        volatility = factory.Trait(
            indicator_name=factory.Faker('random_element', elements=['BB', 'ATR', 'KC']),
            parameters=factory.lazy_attribute(lambda o: {
                'period': o.period,
                'std_dev': 2.0,
            })
        )


# ============================================================================
# 数据源策略决策工厂
# ============================================================================

class DataSourceDecisionFactory(factory.Factory):
    """数据源策略决策工厂"""

    class Meta:
        model = dict

    source = factory.Faker('random_element', elements=['local', 'ccxt', 'resample', 'hybrid'])
    source_interval = factory.Faker('random_element', elements=[None, '1m', '5m', '1h'])
    need_download = factory.Faker('boolean')
    download_interval = factory.Faker('random_element', elements=[None, '1m', '5m', '1h'])
    reason = factory.Faker('sentence', nb_words=10)

    class Params:
        """特定决策场景"""
        local_available = factory.Trait(
            source='local',
            need_download=False,
            reason=factory.Faker('sentence', nb_words=5),
        )

        need_download = factory.Trait(
            source='ccxt',
            need_download=True,
            download_interval=factory.Faker('random_element', elements=['1m', '5m', '1h']),
            reason=factory.Faker('sentence', nb_words=8),
        )

        need_resample = factory.Trait(
            source='resample',
            source_interval=factory.Faker('random_element', elements=['1m', '5m']),
            need_download=False,
            reason=factory.Faker('sentence', nb_words=6),
        )


# ============================================================================
# 错误场景数据工厂
# ============================================================================

class ErrorScenarioFactory(factory.Factory):
    """错误场景数据工厂"""

    class Meta:
        model = dict

    error_type = factory.Faker('random_element', elements=[
        'NetworkError', 'TimeoutError', 'RateLimitError', 'InvalidDataError',
        'FileNotFoundError', 'PermissionError', 'MemoryError', 'ValidationError'
    ])
    message = factory.Faker('sentence', nb_words=15)
    timestamp = factory.LazyFunction(datetime.now)
    retry_count = factory.Faker('pyint', min_value=0, max_value=5)
    context = factory.lazy_attribute(lambda o: {
        'exchange': o.exchange if hasattr(o, 'exchange') else fake.company(),
        'symbol': o.symbol if hasattr(o, 'symbol') else fake.word(),
        'timeframe': o.timeframe if hasattr(o, 'timeframe') else '1h',
        'request_id': fake.uuid4(),
        'user_agent': fake.user_agent(),
    })

    class Params:
        """网络错误"""
        network_error = factory.Trait(
            error_type='NetworkError',
            message=factory.Faker('sentence', nb_words=10, ext_word_list=['connection', 'refused', 'timeout']),
        )

        # 速率限制错误
        rate_limit = factory.Trait(
            error_type='RateLimitError',
            message=factory.Faker('sentence', nb_words=10, ext_word_list=['rate', 'limit', 'exceeded']),
            retry_count=factory.Faker('pyint', min_value=1, max_value=3),
        )

        # 数据验证错误
        validation_error = factory.Trait(
            error_type='ValidationError',
            message=factory.Faker('sentence', nb_words=10, ext_word_list=['invalid', 'data', 'format']),
        )


# ============================================================================
# 批量数据创建工具
# ============================================================================

class DataFactory:
    """批量数据创建工具类"""

    @staticmethod
    def create_ohlcv_batch(
        count: int = 100,
        timeframe: str = '1h',
        exchanges: List[str] = None,
        symbols: List[str] = None
    ) -> Dict[str, pd.DataFrame]:
        """创建批量OHLCV数据"""
        if exchanges is None:
            exchanges = ['binance', 'okx', 'huobi']
        if symbols is None:
            symbols = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT']

        data_dict = {}
        for exchange in exchanges:
            for symbol in symbols:
                key = f"{exchange}_{symbol}_{timeframe}"
                data_dict[key] = KlineTimeSeriesFactory.create(
                    count=count,
                    timeframe=timeframe,
                    base_price=random.uniform(100, 60000)
                )

        return data_dict

    @staticmethod
    def create_corrupted_data() -> pd.DataFrame:
        """创建损坏的数据用于测试错误处理"""
        data = [
            {'timestamp': datetime.now(), 'open': 100, 'high': 105, 'low': 95, 'close': 102, 'volume': 1000},
            {'timestamp': datetime.now(), 'open': 102, 'high': 107, 'low': 97, 'close': 104},  # 缺少volume
            {'timestamp': datetime.now(), 'open': 104, 'high': 109, 'low': 99, 'close': 106, 'volume': -100},  # 负成交量
            {'timestamp': datetime.now(), 'open': 106, 'high': 101, 'low': 111, 'close': 108, 'volume': 1000},  # high < low
            {'timestamp': datetime.now(), 'open': None, 'high': 111, 'low': 103, 'close': 110, 'volume': 1000},  # None值
        ]

        return pd.DataFrame(data)

    @staticmethod
    def create_gap_data(gap_size: int = 2) -> pd.DataFrame:
        """创建包含时间间隔的数据"""
        base_time = datetime.now() - timedelta(days=1)
        data = []

        # 前半段数据
        for i in range(10):
            ts = base_time + timedelta(hours=i)
            price = 50000 + i * 10
            data.append({
                'timestamp': ts,
                'open': price,
                'high': price * 1.01,
                'low': price * 0.99,
                'close': price * 1.005,
                'volume': 100000
            })

        # 跳过gap_size小时
        gap_start_time = base_time + timedelta(hours=10 + gap_size)

        # 后半段数据
        for i in range(10):
            ts = gap_start_time + timedelta(hours=i)
            price = 50100 + i * 10
            data.append({
                'timestamp': ts,
                'open': price,
                'high': price * 1.01,
                'low': price * 0.99,
                'close': price * 1.005,
                'volume': 100000
            })

        return pd.DataFrame(data)


# ============================================================================
# 使用示例
# ============================================================================

if __name__ == "__main__":
    # 创建示例数据
    print("=== 创建OHLCV数据 ===")
    ohlcv = OHLCVDataFactory()
    print(ohlcv)

    print("\n=== 创建价格范围数据 ===")
    price_range_data = OHLCVDataFactory(price_range=True)
    print(price_range_data)

    print("\n=== 创建时间序列数据 ===")
    series_data = KlineTimeSeriesFactory.create(count=50, timeframe='1h')
    print(f"时间序列数据形状: {series_data.shape}")
    print(f"列名: {series_data.columns.tolist()}")

    print("\n=== 创建批量数据 ===")
    batch_data = DataFactory.create_ohlcv_batch(count=20, exchanges=['binance'], symbols=['BTC/USDT'])
    print(f"批量数据键: {list(batch_data.keys())}")

    print("\n=== 创建损坏数据 ===")
    corrupted = DataFactory.create_corrupted_data()
    print(f"损坏数据:\n{corrupted}")

    print("\n=== 创建间隔数据 ===")
    gap_data = DataFactory.create_gap_data(gap_size=3)
    print(f"间隔数据形状: {gap_data.shape}")
    print(f"时间跨度: {gap_data['timestamp'].max() - gap_data['timestamp'].min()}")