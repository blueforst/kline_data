"""指标管理器"""

import pandas as pd
from typing import Dict, List, Optional, Any, Callable
import logging

from .base import BaseIndicator, IndicatorPipeline
from .moving_average import (
    SMA, EMA, WMA, DEMA, TEMA, VWMA, HMA,
    calculate_ma, calculate_multiple_ma
)
from .bollinger import (
    BollingerBands, KeltnerChannel, DonchianChannel,
    calculate_bollinger, calculate_keltner, calculate_donchian
)
from .macd import (
    MACD, PPO, APO,
    calculate_macd, calculate_ppo, get_macd_signals
)
from .oscillator import (
    RSI, StochasticOscillator, CCI, WilliamsR, ROC, MOM,
    calculate_rsi, calculate_stochastic, calculate_cci,
    calculate_williams_r, calculate_roc, calculate_momentum
)
from .volatility import (
    ATR, NormalizedATR, StandardDeviation, HistoricalVolatility,
    UlcerIndex, MassIndex, ChoppinessIndex,
    calculate_atr, calculate_natr, calculate_std, calculate_hv
)
from .volume import (
    OBV, VolumeMA, VWAP, MFI, AD, CMF, EMV, ForceIndex,
    calculate_obv, calculate_volume_ma, calculate_vwap,
    calculate_mfi, calculate_ad, calculate_cmf
)


logger = logging.getLogger(__name__)


class IndicatorManager:
    """
    指标管理器
    统一管理所有技术指标的计算
    """
    
    def __init__(self):
        """初始化指标管理器"""
        self.indicators: Dict[str, BaseIndicator] = {}
        self._register_default_indicators()
    
    def _register_default_indicators(self) -> None:
        """注册默认指标"""
        # 移动平均
        self.register('sma', SMA())
        self.register('ema', EMA())
        self.register('wma', WMA())
        self.register('dema', DEMA())
        self.register('tema', TEMA())
        self.register('vwma', VWMA())
        self.register('hma', HMA())
        
        # 布林带类
        self.register('boll', BollingerBands())
        self.register('kc', KeltnerChannel())
        self.register('dc', DonchianChannel())
        
        # MACD类
        self.register('macd', MACD())
        self.register('ppo', PPO())
        self.register('apo', APO())
        
        # 振荡指标
        self.register('rsi', RSI())
        self.register('stoch', StochasticOscillator())
        self.register('cci', CCI())
        self.register('williams_r', WilliamsR())
        self.register('roc', ROC())
        self.register('momentum', MOM())
        
        # 波动率指标
        self.register('atr', ATR())
        self.register('natr', NormalizedATR())
        self.register('std', StandardDeviation())
        self.register('hv', HistoricalVolatility())
        self.register('ulcer', UlcerIndex())
        self.register('mass_index', MassIndex())
        self.register('choppiness', ChoppinessIndex())
        
        # 成交量指标
        self.register('obv', OBV())
        self.register('volume_ma', VolumeMA())
        self.register('vwap', VWAP())
        self.register('mfi', MFI())
        self.register('ad', AD())
        self.register('cmf', CMF())
        self.register('emv', EMV())
        self.register('force_index', ForceIndex())
    
    def register(self, name: str, indicator: BaseIndicator) -> None:
        """
        注册指标
        
        Args:
            name: 指标名称
            indicator: 指标实例
        """
        self.indicators[name] = indicator
        logger.debug(f"Registered indicator: {name}")
    
    def get_indicator(self, name: str) -> Optional[BaseIndicator]:
        """
        获取指标
        
        Args:
            name: 指标名称
            
        Returns:
            BaseIndicator: 指标实例
        """
        return self.indicators.get(name)
    
    def list_indicators(self) -> List[str]:
        """
        列出所有可用指标
        
        Returns:
            List[str]: 指标名称列表
        """
        return list(self.indicators.keys())
    
    def calculate(
        self,
        df: pd.DataFrame,
        indicator_name: str,
        **kwargs
    ) -> pd.DataFrame:
        """
        计算单个指标
        
        Args:
            df: K线数据
            indicator_name: 指标名称
            **kwargs: 指标参数
            
        Returns:
            pd.DataFrame: 包含指标的数据
        """
        indicator = self.get_indicator(indicator_name)
        if indicator is None:
            raise ValueError(f"Unknown indicator: {indicator_name}")
        
        try:
            return indicator.calculate(df, **kwargs)
        except Exception as e:
            logger.error(f"Error calculating {indicator_name}: {e}")
            raise
    
    def calculate_multiple(
        self,
        df: pd.DataFrame,
        indicators: Dict[str, Dict[str, Any]]
    ) -> pd.DataFrame:
        """
        批量计算多个指标
        
        Args:
            df: K线数据
            indicators: 指标配置字典
                例: {
                    'sma': {'period': 20},
                    'ema': {'period': 50},
                    'rsi': {'period': 14}
                }
            
        Returns:
            pd.DataFrame: 包含所有指标的数据
        """
        result = df.copy()
        
        for name, params in indicators.items():
            try:
                result = self.calculate(result, name, **params)
            except Exception as e:
                logger.warning(f"Failed to calculate {name}: {e}")
                continue
        
        return result
    
    def create_pipeline(self, indicator_configs: List[tuple]) -> IndicatorPipeline:
        """
        创建指标计算流水线
        
        Args:
            indicator_configs: 指标配置列表
                例: [
                    ('sma', {'period': 20}),
                    ('rsi', {'period': 14})
                ]
            
        Returns:
            IndicatorPipeline: 指标流水线
        """
        pipeline = IndicatorPipeline()
        
        for name, params in indicator_configs:
            indicator = self.get_indicator(name)
            if indicator is not None:
                # 设置参数
                indicator.set_params(**params)
                pipeline.add_indicator(indicator)
        
        return pipeline


class IndicatorLibrary:
    """
    指标库
    提供便捷的指标计算函数
    """
    
    @staticmethod
    def add_common_indicators(
        df: pd.DataFrame,
        ma_periods: List[int] = [5, 10, 20, 50, 200],
        include_macd: bool = True,
        include_rsi: bool = True,
        include_boll: bool = True,
        include_atr: bool = True,
        include_volume: bool = True
    ) -> pd.DataFrame:
        """
        添加常用指标
        
        Args:
            df: K线数据
            ma_periods: MA周期列表
            include_macd: 是否包含MACD
            include_rsi: 是否包含RSI
            include_boll: 是否包含布林带
            include_volume: 是否包含成交量指标
            
        Returns:
            pd.DataFrame: 包含所有指标的数据
        """
        result = df.copy()
        
        # 添加移动平均
        for period in ma_periods:
            try:
                result = calculate_ma(result, period, 'sma')
                result = calculate_ma(result, period, 'ema')
            except Exception as e:
                logger.warning(f"Failed to calculate MA {period}: {e}")
        
        # 添加MACD
        if include_macd:
            try:
                result = calculate_macd(result)
            except Exception as e:
                logger.warning(f"Failed to calculate MACD: {e}")
        
        # 添加RSI
        if include_rsi:
            try:
                result = calculate_rsi(result, 14)
            except Exception as e:
                logger.warning(f"Failed to calculate RSI: {e}")
        
        # 添加布林带
        if include_boll:
            try:
                result = calculate_bollinger(result, 20)
            except Exception as e:
                logger.warning(f"Failed to calculate BOLL: {e}")
        
        # 添加ATR
        if include_atr:
            try:
                result = calculate_atr(result, 14)
            except Exception as e:
                logger.warning(f"Failed to calculate ATR: {e}")
        
        # 添加成交量指标
        if include_volume:
            try:
                result = calculate_obv(result)
                result = calculate_volume_ma(result, 20)
            except Exception as e:
                logger.warning(f"Failed to calculate volume indicators: {e}")
        
        return result
    
    @staticmethod
    def add_trend_indicators(
        df: pd.DataFrame,
        ma_periods: List[int] = [20, 50, 200],
        include_macd: bool = True,
        include_adx: bool = False
    ) -> pd.DataFrame:
        """
        添加趋势指标
        
        Args:
            df: K线数据
            ma_periods: MA周期列表
            include_macd: 是否包含MACD
            include_adx: 是否包含ADX
            
        Returns:
            pd.DataFrame: 包含趋势指标的数据
        """
        result = df.copy()
        
        # 移动平均
        result = calculate_multiple_ma(result, ma_periods, 'ema')
        
        # MACD
        if include_macd:
            result = calculate_macd(result)
        
        return result
    
    @staticmethod
    def add_momentum_indicators(
        df: pd.DataFrame,
        rsi_period: int = 14,
        stoch_period: int = 14,
        include_cci: bool = True,
        include_roc: bool = True
    ) -> pd.DataFrame:
        """
        添加动量指标
        
        Args:
            df: K线数据
            rsi_period: RSI周期
            stoch_period: 随机指标周期
            include_cci: 是否包含CCI
            include_roc: 是否包含ROC
            
        Returns:
            pd.DataFrame: 包含动量指标的数据
        """
        result = df.copy()
        
        # RSI
        result = calculate_rsi(result, rsi_period)
        
        # Stochastic
        result = calculate_stochastic(result, stoch_period)
        
        # CCI
        if include_cci:
            result = calculate_cci(result, 20)
        
        # ROC
        if include_roc:
            result = calculate_roc(result, 12)
        
        return result
    
    @staticmethod
    def add_volatility_indicators(
        df: pd.DataFrame,
        atr_period: int = 14,
        bb_period: int = 20,
        include_std: bool = True
    ) -> pd.DataFrame:
        """
        添加波动率指标
        
        Args:
            df: K线数据
            atr_period: ATR周期
            bb_period: 布林带周期
            include_std: 是否包含标准差
            
        Returns:
            pd.DataFrame: 包含波动率指标的数据
        """
        result = df.copy()
        
        # ATR
        result = calculate_atr(result, atr_period)
        
        # 布林带
        result = calculate_bollinger(result, bb_period)
        
        # 标准差
        if include_std:
            result = calculate_std(result, bb_period)
        
        return result
    
    @staticmethod
    def add_volume_indicators(
        df: pd.DataFrame,
        obv: bool = True,
        vwap: bool = True,
        mfi_period: int = 14
    ) -> pd.DataFrame:
        """
        添加成交量指标
        
        Args:
            df: K线数据
            obv: 是否包含OBV
            vwap: 是否包含VWAP
            mfi_period: MFI周期
            
        Returns:
            pd.DataFrame: 包含成交量指标的数据
        """
        result = df.copy()
        
        # OBV
        if obv:
            result = calculate_obv(result)
        
        # VWAP
        if vwap:
            result = calculate_vwap(result, 20)
        
        # MFI
        result = calculate_mfi(result, mfi_period)
        
        return result


# 全局指标管理器实例
_global_manager = IndicatorManager()


def get_indicator_manager() -> IndicatorManager:
    """获取全局指标管理器"""
    return _global_manager


def calculate_indicator(
    df: pd.DataFrame,
    indicator_name: str,
    **kwargs
) -> pd.DataFrame:
    """
    计算指标（便捷函数）
    
    Args:
        df: K线数据
        indicator_name: 指标名称
        **kwargs: 指标参数
        
    Returns:
        pd.DataFrame: 包含指标的数据
    """
    return _global_manager.calculate(df, indicator_name, **kwargs)


def list_available_indicators() -> List[str]:
    """列出所有可用指标"""
    return _global_manager.list_indicators()
