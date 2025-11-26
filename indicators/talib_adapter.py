"""
TA-Lib适配器 - 提供统一的技术指标接口
处理TA-Lib版本兼容性和异常情况
"""
import pandas as pd
import numpy as np
from typing import Optional, Union, Dict, Any
import warnings

try:
    import talib
    TALIB_AVAILABLE = True
except ImportError:
    TALIB_AVAILABLE = False
    warnings.warn("TA-Lib not available. Using pandas implementations.")

class TalibAdapter:
    """TA-Lib适配器类"""

    @staticmethod
    def is_available() -> bool:
        """检查TA-Lib是否可用"""
        return TALIB_AVAILABLE

    @staticmethod
    def sma(data: Union[pd.Series, np.ndarray], period: int = 20) -> np.ndarray:
        """简单移动平均"""
        if TALIB_AVAILABLE:
            try:
                return talib.SMA(data, timeperiod=period)
            except Exception as e:
                warnings.warn(f"TA-Lib SMA计算失败: {e}, 使用pandas实现")
                return TalibAdapter._sma_pandas(data, period)
        else:
            return TalibAdapter._sma_pandas(data, period)

    @staticmethod
    def _sma_pandas(data: Union[pd.Series, np.ndarray], period: int) -> np.ndarray:
        """Pandas实现的SMA"""
        if isinstance(data, pd.Series):
            return data.rolling(window=period).mean().values
        else:
            return pd.Series(data).rolling(window=period).mean().values

    @staticmethod
    def ema(data: Union[pd.Series, np.ndarray], period: int = 20) -> np.ndarray:
        """指数移动平均"""
        if TALIB_AVAILABLE:
            try:
                return talib.EMA(data, timeperiod=period)
            except Exception as e:
                warnings.warn(f"TA-Lib EMA计算失败: {e}, 使用pandas实现")
                return TalibAdapter._ema_pandas(data, period)
        else:
            return TalibAdapter._ema_pandas(data, period)

    @staticmethod
    def _ema_pandas(data: Union[pd.Series, np.ndarray], period: int) -> np.ndarray:
        """Pandas实现的EMA"""
        if isinstance(data, pd.Series):
            return data.ewm(span=period).mean().values
        else:
            return pd.Series(data).ewm(span=period).mean().values

    @staticmethod
    def macd(data: Union[pd.Series, np.ndarray],
             fast_period: int = 12,
             slow_period: int = 26,
             signal_period: int = 9) -> Dict[str, np.ndarray]:
        """MACD指标"""
        if TALIB_AVAILABLE:
            try:
                macd, signal, histogram = talib.MACD(
                    data, fastperiod=fast_period,
                    slowperiod=slow_period, signalperiod=signal_period
                )
                return {
                    'macd': macd,
                    'signal': signal,
                    'histogram': histogram
                }
            except Exception as e:
                warnings.warn(f"TA-Lib MACD计算失败: {e}, 使用pandas实现")
                return TalibAdapter._macd_pandas(data, fast_period, slow_period, signal_period)
        else:
            return TalibAdapter._macd_pandas(data, fast_period, slow_period, signal_period)

    @staticmethod
    def _macd_pandas(data: Union[pd.Series, np.ndarray],
                    fast_period: int = 12,
                    slow_period: int = 26,
                    signal_period: int = 9) -> Dict[str, np.ndarray]:
        """Pandas实现的MACD"""
        if isinstance(data, pd.Series):
            data_series = data
        else:
            data_series = pd.Series(data)

        ema_fast = data_series.ewm(span=fast_period).mean()
        ema_slow = data_series.ewm(span=slow_period).mean()
        macd = ema_fast - ema_slow
        signal = macd.ewm(span=signal_period).mean()
        histogram = macd - signal

        return {
            'macd': macd.values,
            'signal': signal.values,
            'histogram': histogram.values
        }

    @staticmethod
    def rsi(data: Union[pd.Series, np.ndarray], period: int = 14) -> np.ndarray:
        """相对强弱指标"""
        if TALIB_AVAILABLE:
            try:
                return talib.RSI(data, timeperiod=period)
            except Exception as e:
                warnings.warn(f"TA-Lib RSI计算失败: {e}, 使用pandas实现")
                return TalibAdapter._rsi_pandas(data, period)
        else:
            return TalibAdapter._rsi_pandas(data, period)

    @staticmethod
    def _rsi_pandas(data: Union[pd.Series, np.ndarray], period: int = 14) -> np.ndarray:
        """Pandas实现的RSI"""
        if isinstance(data, pd.Series):
            data_series = data
        else:
            data_series = pd.Series(data)

        delta = data_series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

        # 避免除零错误
        rs = gain / loss.replace(0, np.inf)
        rsi = 100 - (100 / (1 + rs))

        return rsi.values

    @staticmethod
    def bollinger_bands(data: Union[pd.Series, np.ndarray],
                       period: int = 20,
                       std_dev: float = 2.0) -> Dict[str, np.ndarray]:
        """布林带"""
        if TALIB_AVAILABLE:
            try:
                upper, middle, lower = talib.BBANDS(
                    data, timeperiod=period, nbdevup=std_dev, nbdevdn=std_dev
                )
                return {
                    'upper': upper,
                    'middle': middle,
                    'lower': lower
                }
            except Exception as e:
                warnings.warn(f"TA-Lib Bollinger Bands计算失败: {e}, 使用pandas实现")
                return TalibAdapter._bollinger_bands_pandas(data, period, std_dev)
        else:
            return TalibAdapter._bollinger_bands_pandas(data, period, std_dev)

    @staticmethod
    def _bollinger_bands_pandas(data: Union[pd.Series, np.ndarray],
                               period: int = 20,
                               std_dev: float = 2.0) -> Dict[str, np.ndarray]:
        """Pandas实现的布林带"""
        if isinstance(data, pd.Series):
            data_series = data
        else:
            data_series = pd.Series(data)

        middle = data_series.rolling(window=period).mean()
        std = data_series.rolling(window=period).std()
        upper = middle + (std * std_dev)
        lower = middle - (std * std_dev)

        return {
            'upper': upper.values,
            'middle': middle.values,
            'lower': lower.values
        }

    @staticmethod
    def get_available_functions() -> list:
        """获取可用的TA-Lib函数列表"""
        if not TALIB_AVAILABLE:
            return []

        functions = ['SMA', 'EMA', 'MACD', 'RSI', 'BBANDS']
        available = []

        for func in functions:
            if hasattr(talib, func):
                try:
                    # 尝试调用函数以验证其可用性
                    getattr(talib, func)
                    available.append(func)
                except:
                    pass

        return available

# 全局适配器实例
talib_adapter = TalibAdapter()