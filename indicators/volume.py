"""成交量指标"""

import pandas as pd
import numpy as np
from typing import Optional

from .base import VolumeBase


class OBV(VolumeBase):
    """
    OBV (On Balance Volume)
    能量潮指标
    
    如果今日收盘价 > 昨日收盘价: OBV = OBV_prev + Volume
    如果今日收盘价 < 昨日收盘价: OBV = OBV_prev - Volume
    如果今日收盘价 = 昨日收盘价: OBV = OBV_prev
    """
    
    def __init__(self):
        super().__init__('OBV')
    
    def calculate(
        self,
        df: pd.DataFrame,
        column: str = 'close'
    ) -> pd.DataFrame:
        """
        计算OBV
        
        Args:
            df: K线数据
            column: 价格列
            
        Returns:
            pd.DataFrame: 包含OBV的数据
        """
        self.validate_data(df, [column, 'volume'])
        self._validate_volume(df)
        
        result = df.copy()
        
        # 计算价格变化方向
        price_change = result[column].diff()
        
        # 计算OBV
        obv = (np.sign(price_change) * result['volume']).fillna(0).cumsum()
        
        result['obv'] = obv
        
        return result


class VolumeMA(VolumeBase):
    """
    成交量移动平均
    """
    
    def __init__(self):
        super().__init__('VolumeMA')
    
    def calculate(
        self,
        df: pd.DataFrame,
        period: int = 20
    ) -> pd.DataFrame:
        """
        计算成交量移动平均
        
        Args:
            df: K线数据
            period: 周期
            
        Returns:
            pd.DataFrame: 包含成交量MA的数据
        """
        self.validate_data(df, ['volume'])
        self._validate_volume(df)
        
        result = df.copy()
        
        # 计算成交量MA
        result[f'volume_ma_{period}'] = result['volume'].rolling(window=period).mean()
        
        return result


class VWAP(VolumeBase):
    """
    VWAP (Volume Weighted Average Price)
    成交量加权平均价
    
    VWAP = sum(Price * Volume) / sum(Volume)
    """
    
    def __init__(self):
        super().__init__('VWAP')
    
    def calculate(
        self,
        df: pd.DataFrame,
        period: Optional[int] = None
    ) -> pd.DataFrame:
        """
        计算VWAP
        
        Args:
            df: K线数据
            period: 周期（None表示累计）
            
        Returns:
            pd.DataFrame: 包含VWAP的数据
        """
        self.validate_data(df, ['high', 'low', 'close', 'volume'])
        self._validate_volume(df)
        
        result = df.copy()
        
        # 计算典型价格
        typical_price = (result['high'] + result['low'] + result['close']) / 3
        
        # 计算价格*成交量
        pv = typical_price * result['volume']
        
        if period is None:
            # 累计VWAP
            vwap = pv.cumsum() / result['volume'].cumsum()
        else:
            # 周期VWAP
            vwap = pv.rolling(window=period).sum() / result['volume'].rolling(window=period).sum()
        
        result['vwap'] = vwap
        
        return result


class MFI(VolumeBase):
    """
    MFI (Money Flow Index)
    资金流量指标
    
    类似RSI，但考虑了成交量
    MFI = 100 - 100 / (1 + Money Flow Ratio)
    """
    
    def __init__(self):
        super().__init__('MFI')
    
    def calculate(
        self,
        df: pd.DataFrame,
        period: int = 14
    ) -> pd.DataFrame:
        """
        计算MFI
        
        Args:
            df: K线数据
            period: 周期
            
        Returns:
            pd.DataFrame: 包含MFI的数据
        """
        self.validate_data(df, ['high', 'low', 'close', 'volume'])
        self._validate_volume(df)
        
        result = df.copy()
        
        # 计算典型价格
        typical_price = (result['high'] + result['low'] + result['close']) / 3
        
        # 计算资金流量
        money_flow = typical_price * result['volume']
        
        # 分离正负资金流量
        positive_flow = money_flow.where(typical_price > typical_price.shift(1), 0)
        negative_flow = money_flow.where(typical_price < typical_price.shift(1), 0)
        
        # 计算周期内正负资金流量
        positive_mf = positive_flow.rolling(window=period).sum()
        negative_mf = negative_flow.rolling(window=period).sum()
        
        # 计算资金流量比率
        mfr = positive_mf / negative_mf
        
        # 计算MFI
        mfi = 100 - (100 / (1 + mfr))
        
        result[f'mfi_{period}'] = mfi
        
        return result


class AD(VolumeBase):
    """
    A/D (Accumulation/Distribution)
    累积/派发指标
    
    AD = ((Close - Low) - (High - Close)) / (High - Low) * Volume
    """
    
    def __init__(self):
        super().__init__('AD')
    
    def calculate(
        self,
        df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        计算A/D
        
        Args:
            df: K线数据
            
        Returns:
            pd.DataFrame: 包含A/D的数据
        """
        self.validate_data(df, ['high', 'low', 'close', 'volume'])
        self._validate_volume(df)
        
        result = df.copy()
        
        # 计算资金流量乘数
        clv = ((result['close'] - result['low']) - (result['high'] - result['close'])) / (result['high'] - result['low'])
        clv = clv.fillna(0)  # 处理分母为0的情况
        
        # 计算A/D
        ad = (clv * result['volume']).cumsum()
        
        result['ad'] = ad
        
        return result


class CMF(VolumeBase):
    """
    CMF (Chaikin Money Flow)
    蔡金资金流量
    
    CMF = sum(Money Flow Volume) / sum(Volume)
    Money Flow Volume = ((Close - Low) - (High - Close)) / (High - Low) * Volume
    """
    
    def __init__(self):
        super().__init__('CMF')
    
    def calculate(
        self,
        df: pd.DataFrame,
        period: int = 20
    ) -> pd.DataFrame:
        """
        计算CMF
        
        Args:
            df: K线数据
            period: 周期
            
        Returns:
            pd.DataFrame: 包含CMF的数据
        """
        self.validate_data(df, ['high', 'low', 'close', 'volume'])
        self._validate_volume(df)
        
        result = df.copy()
        
        # 计算资金流量乘数
        clv = ((result['close'] - result['low']) - (result['high'] - result['close'])) / (result['high'] - result['low'])
        clv = clv.fillna(0)
        
        # 计算资金流量成交量
        mf_volume = clv * result['volume']
        
        # 计算CMF
        cmf = mf_volume.rolling(window=period).sum() / result['volume'].rolling(window=period).sum()
        
        result[f'cmf_{period}'] = cmf
        
        return result


class EMV(VolumeBase):
    """
    EMV (Ease of Movement)
    简易波动指标
    
    Distance = (High + Low) / 2 - (High_prev + Low_prev) / 2
    Box Ratio = Volume / (High - Low)
    EMV = Distance / Box Ratio
    """
    
    def __init__(self):
        super().__init__('EMV')
    
    def calculate(
        self,
        df: pd.DataFrame,
        period: int = 14
    ) -> pd.DataFrame:
        """
        计算EMV
        
        Args:
            df: K线数据
            period: 周期
            
        Returns:
            pd.DataFrame: 包含EMV的数据
        """
        self.validate_data(df, ['high', 'low', 'volume'])
        self._validate_volume(df)
        
        result = df.copy()
        
        # 计算中点移动距离
        mid_point = (result['high'] + result['low']) / 2
        distance = mid_point - mid_point.shift(1)
        
        # 计算Box Ratio
        box_ratio = result['volume'] / (result['high'] - result['low'])
        box_ratio = box_ratio.replace([np.inf, -np.inf], np.nan)
        
        # 计算EMV
        emv = distance / box_ratio
        
        # 计算EMV的移动平均
        emv_ma = emv.rolling(window=period).mean()
        
        result['emv'] = emv
        result[f'emv_ma_{period}'] = emv_ma
        
        return result


class ForceIndex(VolumeBase):
    """
    Force Index
    强力指数
    
    FI = (Close - Close_prev) * Volume
    """
    
    def __init__(self):
        super().__init__('ForceIndex')
    
    def calculate(
        self,
        df: pd.DataFrame,
        period: int = 13
    ) -> pd.DataFrame:
        """
        计算强力指数
        
        Args:
            df: K线数据
            period: EMA周期
            
        Returns:
            pd.DataFrame: 包含强力指数的数据
        """
        self.validate_data(df, ['close', 'volume'])
        self._validate_volume(df)
        
        result = df.copy()
        
        # 计算原始强力指数
        fi = (result['close'] - result['close'].shift(1)) * result['volume']
        
        # 计算EMA
        fi_ema = fi.ewm(span=period, adjust=False).mean()
        
        result['force_index'] = fi
        result[f'force_index_ema_{period}'] = fi_ema
        
        return result


# 便捷函数

def calculate_obv(df: pd.DataFrame, column: str = 'close') -> pd.DataFrame:
    """计算OBV"""
    obv = OBV()
    return obv.calculate(df, column)


def calculate_volume_ma(df: pd.DataFrame, period: int = 20) -> pd.DataFrame:
    """计算成交量MA"""
    vma = VolumeMA()
    return vma.calculate(df, period)


def calculate_vwap(df: pd.DataFrame, period: Optional[int] = None) -> pd.DataFrame:
    """计算VWAP"""
    vwap = VWAP()
    return vwap.calculate(df, period)


def calculate_mfi(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """计算MFI"""
    mfi = MFI()
    return mfi.calculate(df, period)


def calculate_ad(df: pd.DataFrame) -> pd.DataFrame:
    """计算A/D"""
    ad = AD()
    return ad.calculate(df)


def calculate_cmf(df: pd.DataFrame, period: int = 20) -> pd.DataFrame:
    """计算CMF"""
    cmf = CMF()
    return cmf.calculate(df, period)
