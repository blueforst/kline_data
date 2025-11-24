"""振荡指标"""

import pandas as pd
import numpy as np
from typing import Optional

from .base import OscillatorBase


class RSI(OscillatorBase):
    """
    RSI (Relative Strength Index)
    相对强弱指标
    
    RSI = 100 - 100 / (1 + RS)
    RS = 平均涨幅 / 平均跌幅
    """
    
    def __init__(self):
        super().__init__('RSI')
    
    def calculate(
        self,
        df: pd.DataFrame,
        period: int = 14,
        column: str = 'close'
    ) -> pd.DataFrame:
        """
        计算RSI
        
        Args:
            df: K线数据
            period: 周期
            column: 计算列
            
        Returns:
            pd.DataFrame: 包含RSI的数据
        """
        self.validate_data(df, [column])
        
        result = df.copy()
        
        # 计算价格变化
        delta = result[column].diff()
        
        # 分离涨跌
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        
        # 计算平均涨跌幅（使用EMA）
        avg_gain = gain.ewm(span=period, adjust=False).mean()
        avg_loss = loss.ewm(span=period, adjust=False).mean()
        
        # 计算RS和RSI
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        result[f'rsi_{period}'] = rsi
        
        return result
    
    def get_signals(
        self,
        df: pd.DataFrame,
        period: int = 14,
        oversold: float = 30,
        overbought: float = 70,
        column: str = 'close'
    ) -> pd.DataFrame:
        """
        生成RSI交易信号
        
        Args:
            df: K线数据
            period: 周期
            oversold: 超卖阈值
            overbought: 超买阈值
            column: 计算列
            
        Returns:
            pd.DataFrame: 包含信号的数据
        """
        result = self.calculate(df, period, column)
        rsi_col = f'rsi_{period}'
        
        # 超卖信号
        result['rsi_oversold'] = result[rsi_col] < oversold
        
        # 超买信号
        result['rsi_overbought'] = result[rsi_col] > overbought
        
        # RSI上穿超卖线
        result['rsi_cross_up_oversold'] = (
            (result[rsi_col].shift(1) < oversold) &
            (result[rsi_col] >= oversold)
        )
        
        # RSI下穿超买线
        result['rsi_cross_down_overbought'] = (
            (result[rsi_col].shift(1) > overbought) &
            (result[rsi_col] <= overbought)
        )
        
        return result


class StochasticOscillator(OscillatorBase):
    """
    随机振荡器 (Stochastic Oscillator)
    
    %K = (收盘价 - 最低价) / (最高价 - 最低价) * 100
    %D = %K的移动平均
    """
    
    def __init__(self):
        super().__init__('Stochastic')
    
    def calculate(
        self,
        df: pd.DataFrame,
        k_period: int = 14,
        d_period: int = 3,
        smooth_k: int = 3
    ) -> pd.DataFrame:
        """
        计算随机振荡器
        
        Args:
            df: K线数据
            k_period: %K周期
            d_period: %D周期（%K的平滑周期）
            smooth_k: %K的平滑周期
            
        Returns:
            pd.DataFrame: 包含随机振荡器的数据
        """
        self.validate_data(df, ['high', 'low', 'close'])
        
        result = df.copy()
        
        # 计算最高价和最低价
        highest_high = result['high'].rolling(window=k_period).max()
        lowest_low = result['low'].rolling(window=k_period).min()
        
        # 计算%K
        k = (result['close'] - lowest_low) / (highest_high - lowest_low) * 100
        
        # 平滑%K
        if smooth_k > 1:
            k = k.rolling(window=smooth_k).mean()
        
        # 计算%D
        d = k.rolling(window=d_period).mean()
        
        result['stoch_k'] = k
        result['stoch_d'] = d
        
        return result
    
    def get_signals(
        self,
        df: pd.DataFrame,
        k_period: int = 14,
        d_period: int = 3,
        smooth_k: int = 3,
        oversold: float = 20,
        overbought: float = 80
    ) -> pd.DataFrame:
        """
        生成随机振荡器交易信号
        
        Args:
            df: K线数据
            k_period: %K周期
            d_period: %D周期
            smooth_k: %K的平滑周期
            oversold: 超卖阈值
            overbought: 超买阈值
            
        Returns:
            pd.DataFrame: 包含信号的数据
        """
        result = self.calculate(df, k_period, d_period, smooth_k)
        
        # 金叉: %K上穿%D
        result['stoch_golden_cross'] = (
            (result['stoch_k'].shift(1) <= result['stoch_d'].shift(1)) &
            (result['stoch_k'] > result['stoch_d'])
        )
        
        # 死叉: %K下穿%D
        result['stoch_death_cross'] = (
            (result['stoch_k'].shift(1) >= result['stoch_d'].shift(1)) &
            (result['stoch_k'] < result['stoch_d'])
        )
        
        # 超卖区金叉
        result['stoch_oversold_cross'] = (
            result['stoch_golden_cross'] &
            (result['stoch_k'] < oversold)
        )
        
        # 超买区死叉
        result['stoch_overbought_cross'] = (
            result['stoch_death_cross'] &
            (result['stoch_k'] > overbought)
        )
        
        return result


class CCI(OscillatorBase):
    """
    CCI (Commodity Channel Index)
    顺势指标
    
    CCI = (TP - MA) / (0.015 * MD)
    TP = (High + Low + Close) / 3
    MA = TP的移动平均
    MD = 平均绝对偏差
    """
    
    def __init__(self):
        super().__init__('CCI')
    
    def calculate(
        self,
        df: pd.DataFrame,
        period: int = 20,
        constant: float = 0.015
    ) -> pd.DataFrame:
        """
        计算CCI
        
        Args:
            df: K线数据
            period: 周期
            constant: 常数（通常为0.015）
            
        Returns:
            pd.DataFrame: 包含CCI的数据
        """
        self.validate_data(df, ['high', 'low', 'close'])
        
        result = df.copy()
        
        # 计算典型价格
        tp = (result['high'] + result['low'] + result['close']) / 3
        
        # 计算TP的移动平均
        ma = tp.rolling(window=period).mean()
        
        # 计算平均绝对偏差
        md = tp.rolling(window=period).apply(lambda x: np.abs(x - x.mean()).mean())
        
        # 计算CCI
        cci = (tp - ma) / (constant * md)
        
        result[f'cci_{period}'] = cci
        
        return result


class WilliamsR(OscillatorBase):
    """
    Williams %R
    威廉指标
    
    %R = (最高价 - 收盘价) / (最高价 - 最低价) * -100
    """
    
    def __init__(self):
        super().__init__('WilliamsR')
    
    def calculate(
        self,
        df: pd.DataFrame,
        period: int = 14
    ) -> pd.DataFrame:
        """
        计算Williams %R
        
        Args:
            df: K线数据
            period: 周期
            
        Returns:
            pd.DataFrame: 包含Williams %R的数据
        """
        self.validate_data(df, ['high', 'low', 'close'])
        
        result = df.copy()
        
        # 计算最高价和最低价
        highest_high = result['high'].rolling(window=period).max()
        lowest_low = result['low'].rolling(window=period).min()
        
        # 计算%R
        wr = (highest_high - result['close']) / (highest_high - lowest_low) * -100
        
        result[f'williams_r_{period}'] = wr
        
        return result


class ROC(OscillatorBase):
    """
    ROC (Rate of Change)
    变化率指标
    
    ROC = (Close - Close_n) / Close_n * 100
    """
    
    def __init__(self):
        super().__init__('ROC')
    
    def calculate(
        self,
        df: pd.DataFrame,
        period: int = 12,
        column: str = 'close'
    ) -> pd.DataFrame:
        """
        计算ROC
        
        Args:
            df: K线数据
            period: 周期
            column: 计算列
            
        Returns:
            pd.DataFrame: 包含ROC的数据
        """
        self.validate_data(df, [column])
        
        result = df.copy()
        
        # 计算ROC
        roc = (result[column] - result[column].shift(period)) / result[column].shift(period) * 100
        
        result[f'roc_{period}'] = roc
        
        return result


class MOM(OscillatorBase):
    """
    Momentum
    动量指标
    
    MOM = Close - Close_n
    """
    
    def __init__(self):
        super().__init__('Momentum')
    
    def calculate(
        self,
        df: pd.DataFrame,
        period: int = 10,
        column: str = 'close'
    ) -> pd.DataFrame:
        """
        计算动量
        
        Args:
            df: K线数据
            period: 周期
            column: 计算列
            
        Returns:
            pd.DataFrame: 包含动量的数据
        """
        self.validate_data(df, [column])
        
        result = df.copy()
        
        # 计算动量
        mom = result[column] - result[column].shift(period)
        
        result[f'mom_{period}'] = mom
        
        return result


# 便捷函数

def calculate_rsi(df: pd.DataFrame, period: int = 14, column: str = 'close') -> pd.DataFrame:
    """计算RSI"""
    rsi = RSI()
    return rsi.calculate(df, period, column)


def calculate_stochastic(
    df: pd.DataFrame,
    k_period: int = 14,
    d_period: int = 3,
    smooth_k: int = 3
) -> pd.DataFrame:
    """计算随机振荡器"""
    stoch = StochasticOscillator()
    return stoch.calculate(df, k_period, d_period, smooth_k)


def calculate_cci(df: pd.DataFrame, period: int = 20) -> pd.DataFrame:
    """计算CCI"""
    cci = CCI()
    return cci.calculate(df, period)


def calculate_williams_r(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """计算Williams %R"""
    wr = WilliamsR()
    return wr.calculate(df, period)


def calculate_roc(df: pd.DataFrame, period: int = 12, column: str = 'close') -> pd.DataFrame:
    """计算ROC"""
    roc = ROC()
    return roc.calculate(df, period, column)


def calculate_momentum(df: pd.DataFrame, period: int = 10, column: str = 'close') -> pd.DataFrame:
    """计算动量"""
    mom = MOM()
    return mom.calculate(df, period, column)
