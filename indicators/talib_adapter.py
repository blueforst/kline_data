"""
TA-Lib适配器 - 提供统一的技术指标接口
处理TA-Lib版本兼容性和异常情况，增强pandas兼容性
"""
import pandas as pd
import numpy as np
from typing import Optional, Union, Dict, Any, Tuple
import warnings
import logging

logger = logging.getLogger(__name__)

try:
    import talib
    TALIB_AVAILABLE = True
    logger.info("TA-Lib is available")
except ImportError:
    TALIB_AVAILABLE = False
    logger.warning("TA-Lib not available. Using pandas implementations.")

class TalibAdapter:
    """
    TA-Lib适配器类
    提供TA-Lib和Pandas的统一接口，自动回退到pandas实现
    """

    @staticmethod
    def is_available() -> bool:
        """检查TA-Lib是否可用"""
        return TALIB_AVAILABLE

    @staticmethod
    def _to_array(data: Union[pd.Series, np.ndarray]) -> np.ndarray:
        """统一转换为numpy数组（double类型）"""
        if isinstance(data, pd.Series):
            return data.values.astype(np.float64)
        elif isinstance(data, np.ndarray):
            return data.astype(np.float64)
        else:
            return np.array(data, dtype=np.float64)

    @staticmethod
    def sma(data: Union[pd.Series, np.ndarray], period: int = 20) -> np.ndarray:
        """简单移动平均"""
        if TALIB_AVAILABLE:
            try:
                data_array = TalibAdapter._to_array(data)
                return talib.SMA(data_array, timeperiod=period)
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
                data_array = TalibAdapter._to_array(data)
                return talib.EMA(data_array, timeperiod=period)
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
                data_array = TalibAdapter._to_array(data)
                return talib.RSI(data_array, timeperiod=period)
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
    def atr(high: Union[pd.Series, np.ndarray],
            low: Union[pd.Series, np.ndarray],
            close: Union[pd.Series, np.ndarray],
            period: int = 14) -> np.ndarray:
        """平均真实范围（ATR）"""
        if TALIB_AVAILABLE:
            try:
                return talib.ATR(high, low, close, timeperiod=period)
            except Exception as e:
                logger.warning(f"TA-Lib ATR计算失败: {e}, 使用pandas实现")
                return TalibAdapter._atr_pandas(high, low, close, period)
        else:
            return TalibAdapter._atr_pandas(high, low, close, period)

    @staticmethod
    def _atr_pandas(high: Union[pd.Series, np.ndarray],
                    low: Union[pd.Series, np.ndarray],
                    close: Union[pd.Series, np.ndarray],
                    period: int = 14) -> np.ndarray:
        """Pandas实现的ATR"""
        # 转换为Series以便计算
        if not isinstance(high, pd.Series):
            high = pd.Series(high)
            low = pd.Series(low)
            close = pd.Series(close)

        # 计算真实范围
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        # 计算ATR
        atr = tr.rolling(window=period).mean()
        return atr.values

    @staticmethod
    def stoch(high: Union[pd.Series, np.ndarray],
              low: Union[pd.Series, np.ndarray],
              close: Union[pd.Series, np.ndarray],
              fastk_period: int = 14,
              slowk_period: int = 3,
              slowd_period: int = 3) -> Tuple[np.ndarray, np.ndarray]:
        """随机指标（Stochastic）"""
        if TALIB_AVAILABLE:
            try:
                slowk, slowd = talib.STOCH(
                    high, low, close,
                    fastk_period=fastk_period,
                    slowk_period=slowk_period,
                    slowd_period=slowd_period
                )
                return slowk, slowd
            except Exception as e:
                logger.warning(f"TA-Lib STOCH计算失败: {e}, 使用pandas实现")
                return TalibAdapter._stoch_pandas(high, low, close, fastk_period, slowk_period, slowd_period)
        else:
            return TalibAdapter._stoch_pandas(high, low, close, fastk_period, slowk_period, slowd_period)

    @staticmethod
    def _stoch_pandas(high: Union[pd.Series, np.ndarray],
                      low: Union[pd.Series, np.ndarray],
                      close: Union[pd.Series, np.ndarray],
                      fastk_period: int = 14,
                      slowk_period: int = 3,
                      slowd_period: int = 3) -> Tuple[np.ndarray, np.ndarray]:
        """Pandas实现的随机指标"""
        if not isinstance(high, pd.Series):
            high = pd.Series(high)
            low = pd.Series(low)
            close = pd.Series(close)

        # 计算%K
        lowest_low = low.rolling(window=fastk_period).min()
        highest_high = high.rolling(window=fastk_period).max()
        fastk = 100 * (close - lowest_low) / (highest_high - lowest_low)

        # 计算Slow %K（对Fast %K进行平滑）
        slowk = fastk.rolling(window=slowk_period).mean()

        # 计算%D（对Slow %K进行平滑）
        slowd = slowk.rolling(window=slowd_period).mean()

        return slowk.values, slowd.values

    @staticmethod
    def adx(high: Union[pd.Series, np.ndarray],
            low: Union[pd.Series, np.ndarray],
            close: Union[pd.Series, np.ndarray],
            period: int = 14) -> np.ndarray:
        """平均趋向指标（ADX）"""
        if TALIB_AVAILABLE:
            try:
                return talib.ADX(high, low, close, timeperiod=period)
            except Exception as e:
                logger.warning(f"TA-Lib ADX计算失败: {e}, 使用pandas实现")
                return TalibAdapter._adx_pandas(high, low, close, period)
        else:
            return TalibAdapter._adx_pandas(high, low, close, period)

    @staticmethod
    def _adx_pandas(high: Union[pd.Series, np.ndarray],
                    low: Union[pd.Series, np.ndarray],
                    close: Union[pd.Series, np.ndarray],
                    period: int = 14) -> np.ndarray:
        """Pandas实现的ADX"""
        if not isinstance(high, pd.Series):
            high = pd.Series(high)
            low = pd.Series(low)
            close = pd.Series(close)

        # 计算+DM和-DM
        high_diff = high.diff()
        low_diff = -low.diff()
        
        plus_dm = high_diff.where((high_diff > low_diff) & (high_diff > 0), 0)
        minus_dm = low_diff.where((low_diff > high_diff) & (low_diff > 0), 0)

        # 计算TR
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        # 平滑+DM、-DM和TR
        atr = tr.rolling(window=period).mean()
        plus_di = 100 * (plus_dm.rolling(window=period).mean() / atr)
        minus_di = 100 * (minus_dm.rolling(window=period).mean() / atr)

        # 计算DX和ADX
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        adx = dx.rolling(window=period).mean()

        return adx.values

    @staticmethod
    def obv(close: Union[pd.Series, np.ndarray],
            volume: Union[pd.Series, np.ndarray]) -> np.ndarray:
        """能量潮（OBV）"""
        if TALIB_AVAILABLE:
            try:
                close_array = TalibAdapter._to_array(close)
                volume_array = TalibAdapter._to_array(volume)
                return talib.OBV(close_array, volume_array)
            except Exception as e:
                logger.warning(f"TA-Lib OBV计算失败: {e}, 使用pandas实现")
                return TalibAdapter._obv_pandas(close, volume)
        else:
            return TalibAdapter._obv_pandas(close, volume)

    @staticmethod
    def _obv_pandas(close: Union[pd.Series, np.ndarray],
                    volume: Union[pd.Series, np.ndarray]) -> np.ndarray:
        """Pandas实现的OBV"""
        if not isinstance(close, pd.Series):
            close = pd.Series(close)
            volume = pd.Series(volume)

        obv = (np.sign(close.diff()) * volume).fillna(0).cumsum()
        return obv.values

    @staticmethod
    def cci(high: Union[pd.Series, np.ndarray],
            low: Union[pd.Series, np.ndarray],
            close: Union[pd.Series, np.ndarray],
            period: int = 14) -> np.ndarray:
        """商品通道指数（CCI）"""
        if TALIB_AVAILABLE:
            try:
                return talib.CCI(high, low, close, timeperiod=period)
            except Exception as e:
                logger.warning(f"TA-Lib CCI计算失败: {e}, 使用pandas实现")
                return TalibAdapter._cci_pandas(high, low, close, period)
        else:
            return TalibAdapter._cci_pandas(high, low, close, period)

    @staticmethod
    def _cci_pandas(high: Union[pd.Series, np.ndarray],
                    low: Union[pd.Series, np.ndarray],
                    close: Union[pd.Series, np.ndarray],
                    period: int = 14) -> np.ndarray:
        """Pandas实现的CCI"""
        if not isinstance(high, pd.Series):
            high = pd.Series(high)
            low = pd.Series(low)
            close = pd.Series(close)

        # 计算典型价格
        tp = (high + low + close) / 3

        # 计算SMA和平均绝对偏差
        sma = tp.rolling(window=period).mean()
        mad = tp.rolling(window=period).apply(lambda x: np.abs(x - x.mean()).mean())

        # 计算CCI
        cci = (tp - sma) / (0.015 * mad)
        return cci.values

    @staticmethod
    def get_available_functions() -> list:
        """获取可用的TA-Lib函数列表"""
        if not TALIB_AVAILABLE:
            return ['SMA', 'EMA', 'MACD', 'RSI', 'BBANDS', 'ATR', 'STOCH', 'ADX', 'OBV', 'CCI']

        functions = [
            'SMA', 'EMA', 'WMA', 'DEMA', 'TEMA',  # 移动平均
            'MACD', 'RSI', 'BBANDS',  # 基础指标
            'ATR', 'NATR',  # 波动率
            'STOCH', 'STOCHF', 'ADX', 'CCI', 'WILLR',  # 震荡指标
            'OBV', 'AD', 'ADOSC'  # 成交量指标
        ]
        available = []

        for func in functions:
            if hasattr(talib, func):
                try:
                    getattr(talib, func)
                    available.append(func)
                except:
                    pass

        return available

    @staticmethod
    def get_function_info(func_name: str) -> Dict[str, Any]:
        """获取TA-Lib函数信息"""
        if not TALIB_AVAILABLE:
            return {}

        try:
            info = talib.abstract.Function(func_name).info
            return {
                'name': info['name'],
                'group': info['group'],
                'display_name': info.get('display_name', ''),
                'function_flags': info.get('function_flags', []),
                'input_names': info.get('input_names', {}),
                'parameters': info.get('parameters', {}),
                'output_names': info.get('output_names', [])
            }
        except Exception as e:
            logger.warning(f"无法获取函数信息 {func_name}: {e}")
            return {}

# 全局适配器实例
talib_adapter = TalibAdapter()