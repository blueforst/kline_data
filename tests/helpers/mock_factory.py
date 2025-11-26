"""
Mock工厂 - 提供统一的Mock对象创建
"""
from unittest.mock import Mock, MagicMock
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List

class MockFactory:
    """Mock对象工厂"""

    @staticmethod
    def create_klines_data(length: int = 100,
                          start_date: Optional[datetime] = None,
                          base_price: float = 50000) -> pd.DataFrame:
        """创建模拟K线数据"""
        if start_date is None:
            start_date = datetime.now() - timedelta(days=length)

        dates = pd.date_range(start=start_date, periods=length, freq='1H')

        # 生成模拟价格数据
        np.random.seed(42)  # 确保可重复性
        price_changes = np.random.randn(length) * 1000  # 价格变化
        prices = base_price + np.cumsum(price_changes)  # 累积价格

        # 生成OHLCV数据
        data = {
            'timestamp': dates,
            'open': prices,
            'high': prices + np.abs(np.random.randn(length) * 500),  # 最高价
            'low': prices - np.abs(np.random.randn(length) * 500),   # 最低价
            'close': prices + np.random.randn(length) * 200,        # 收盘价
            'volume': np.abs(np.random.randn(length) * 1000000) + 100000  # 成交量
        }

        df = pd.DataFrame(data)
        df.set_index('timestamp', inplace=True)

        # 确保OHLC逻辑正确
        df['high'] = df[['open', 'high', 'close']].max(axis=1)
        df['low'] = df[['open', 'low', 'close']].min(axis=1)

        # 确保价格数据合理性
        df['high'] = df['high'].clip(lower=df[['open', 'close']].max(axis=1))
        df['low'] = df['low'].clip(upper=df[['open', 'close']].min(axis=1))

        return df

    @staticmethod
    def create_client(klines_data: Optional[pd.DataFrame] = None,
                     has_get_klines_before: bool = True,
                     has_get_klines: bool = False) -> Mock:
        """创建模拟客户端"""
        if klines_data is None:
            klines_data = MockFactory.create_klines_data()

        client = Mock()

        if has_get_klines_before:
            client.get_klines_before.return_value = klines_data

        if has_get_klines:
            client.get_klines.return_value = klines_data

        # 添加其他常用方法
        client.get_exchanges.return_value = ['binance', 'okx', 'huobi']
        client.get_symbols.return_value = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT']
        client.get_timeframes.return_value = ['1m', '5m', '15m', '1h', '4h', '1d']

        # 添加属性
        client.is_connected = True
        client.api_rate_limit = 1200

        return client

    @staticmethod
    def create_config() -> Dict[str, Any]:
        """创建模拟配置"""
        return {
            'exchanges': {
                'binance': {
                    'api_key': 'test_binance_key',
                    'secret': 'test_binance_secret',
                    'sandbox': True,
                    'rate_limit': 1200
                },
                'okx': {
                    'api_key': 'test_okx_key',
                    'secret': 'test_okx_secret',
                    'sandbox': True,
                    'rate_limit': 20
                }
            },
            'timeframes': ['1m', '5m', '15m', '1h', '4h', '1d'],
            'default_limit': 100,
            'cache_enabled': True,
            'cache_ttl': 300
        }

    @staticmethod
    def create_indicator_data(length: int = 100,
                            indicators: Optional[List[str]] = None) -> pd.DataFrame:
        """创建模拟指标数据"""
        klines_data = MockFactory.create_klines_data(length)

        if indicators is None:
            indicators = ['sma_20', 'ema_12', 'macd', 'rsi', 'bb_upper', 'bb_middle', 'bb_lower']

        # 添加移动平均指标
        if 'sma_20' in indicators:
            klines_data['sma_20'] = klines_data['close'].rolling(20).mean()

        if 'ema_12' in indicators:
            klines_data['ema_12'] = klines_data['close'].ewm(span=12).mean()

        # 添加MACD
        if any(ind in indicators for ind in ['macd', 'macd_signal', 'macd_histogram']):
            ema_12 = klines_data['close'].ewm(span=12).mean()
            ema_26 = klines_data['close'].ewm(span=26).mean()
            macd_line = ema_12 - ema_26
            signal_line = macd_line.ewm(span=9).mean()
            histogram = macd_line - signal_line

            if 'macd' in indicators:
                klines_data['macd'] = macd_line
            if 'macd_signal' in indicators:
                klines_data['macd_signal'] = signal_line
            if 'macd_histogram' in indicators:
                klines_data['macd_histogram'] = histogram

        # 添加RSI
        if 'rsi' in indicators:
            delta = klines_data['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rs = gain / loss.replace(0, np.inf)
            klines_data['rsi'] = 100 - (100 / (1 + rs))

        # 添加布林带
        if any(ind in indicators for ind in ['bb_upper', 'bb_middle', 'bb_lower']):
            bb_period = 20
            bb_std = 2.0
            middle = klines_data['close'].rolling(bb_period).mean()
            std = klines_data['close'].rolling(bb_period).std()
            upper = middle + (std * bb_std)
            lower = middle - (std * bb_std)

            if 'bb_upper' in indicators:
                klines_data['bb_upper'] = upper
            if 'bb_middle' in indicators:
                klines_data['bb_middle'] = middle
            if 'bb_lower' in indicators:
                klines_data['bb_lower'] = lower

        return klines_data

    @staticmethod
    def create_empty_klines_data() -> pd.DataFrame:
        """创建空的K线数据"""
        return pd.DataFrame(columns=[
            'open', 'high', 'low', 'close', 'volume'
        ])

    @staticmethod
    def create_invalid_klines_data() -> pd.DataFrame:
        """创建无效的K线数据（包含负数价格）"""
        data = MockFactory.create_klines_data(10)
        # 故意设置一些无效数据
        data.loc[data.index[0], 'close'] = -100  # 负价格
        data.loc[data.index[1], 'volume'] = -1000  # 负成交量
        data.loc[data.index[2], 'high'] = data.loc[data.index[2], 'low'] - 100  # 高价低于低价
        return data

    @staticmethod
    def create_test_scenario(scenario_type: str) -> Dict[str, Any]:
        """创建特定测试场景的数据"""
        scenarios = {
            'empty_data': {
                'klines': MockFactory.create_empty_klines_data(),
                'description': '空数据测试场景'
            },
            'insufficient_data': {
                'klines': MockFactory.create_klines_data(length=5),
                'description': '数据不足测试场景'
            },
            'invalid_data': {
                'klines': MockFactory.create_invalid_klines_data(),
                'description': '无效数据测试场景'
            },
            'single_period': {
                'klines': MockFactory.create_klines_data(length=1),
                'description': '单周期数据测试场景'
            },
            'large_dataset': {
                'klines': MockFactory.create_klines_data(length=1000),
                'description': '大数据集测试场景'
            }
        }

        return scenarios.get(scenario_type, {
            'klines': MockFactory.create_klines_data(),
            'description': '默认测试场景'
        })

    @staticmethod
    def create_multi_exchange_data() -> Dict[str, pd.DataFrame]:
        """创建多交易所的模拟数据"""
        exchanges = ['binance', 'okx', 'huobi']
        data = {}

        base_prices = {
            'binance': 50000,
            'okx': 50100,
            'huobi': 49900
        }

        for exchange in exchanges:
            data[exchange] = MockFactory.create_klines_data(
                length=100,
                base_price=base_prices[exchange]
            )

        return data

    @staticmethod
    def create_multi_symbol_data() -> Dict[str, pd.DataFrame]:
        """创建多交易对的模拟数据"""
        symbols = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT']
        data = {}

        base_prices = {
            'BTC/USDT': 50000,
            'ETH/USDT': 3000,
            'BNB/USDT': 400
        }

        for symbol in symbols:
            data[symbol] = MockFactory.create_klines_data(
                length=100,
                base_price=base_prices[symbol]
            )

        return data