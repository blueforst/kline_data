"""相对强弱指数（RSI）技术指标"""

import pandas as pd
import numpy as np
from typing import Optional, Dict, Any

from .base import BaseIndicator


class RSI(BaseIndicator):
    """
    相对强弱指数（Relative Strength Index，RSI）

    RSI是一种技术动量振荡器，用于比较最近收益的平均幅度与最近损失的平均幅度。
    RSI值的范围为0到100，高于70通常被认为是超买状态，低于30被认为是超卖状态。

    计算公式：
    RSI = 100 - (100 / (1 + RS))

    其中 RS = (平均收益) / (平均损失)
    """

    def __init__(self, period: int = 14):
        """
        初始化RSI指标

        Args:
            period: 计算周期，默认为14
        """
        super().__init__("RSI")
        self.period = period
        self._params = {
            'period': period
        }

    def calculate(self, df: pd.DataFrame, price_column: str = 'close', **kwargs) -> pd.DataFrame:
        """
        计算RSI指标

        Args:
            df: K线数据，必须包含收盘价
            price_column: 价格列名，默认为'close'
            **kwargs: 其他参数（未使用）

        Returns:
            pd.DataFrame: 添加了RSI列的数据框
        """
        # 验证输入数据
        self.validate_data(df, [price_column])

        if len(df) < self.period + 1:
            raise ValueError(f"数据长度不足，需要至少 {self.period + 1} 条数据")

        result_df = df.copy()

        # 计算价格变化
        price_changes = result_df[price_column].diff()

        # 分离收益和损失
        gains = price_changes.where(price_changes > 0, 0)
        losses = -price_changes.where(price_changes < 0, 0)

        # 计算平均收益和平均损失（使用指数移动平均）
        avg_gains = gains.ewm(alpha=1/self.period, adjust=False).mean()
        avg_losses = losses.ewm(alpha=1/self.period, adjust=False).mean()

        # 计算相对强度
        rs = avg_gains / avg_losses

        # 计算RSI
        rsi = 100 - (100 / (1 + rs))

        # 添加RSI列
        rsi_column_name = f'RSI_{self.period}'
        result_df[rsi_column_name] = rsi

        return result_df

    def get_signal_lines(self) -> Dict[str, float]:
        """
        获取RSI的信号线

        Returns:
            Dict[str, float]: 包含超买和超卖线的字典
        """
        return {
            'overbought': 70.0,
            'oversold': 30.0,
            'middle': 50.0
        }

    def interpret_signal(self, rsi_value: float) -> str:
        """
        解释RSI信号

        Args:
            rsi_value: RSI值

        Returns:
            str: 信号解释
        """
        signal_lines = self.get_signal_lines()

        if rsi_value > signal_lines['overbought']:
            return "超买状态，可能存在回调风险"
        elif rsi_value < signal_lines['oversold']:
            return "超卖状态，可能存在反弹机会"
        elif rsi_value > signal_lines['middle']:
            return "多头强势区域"
        else:
            return "空头强势区域"

    def calculate_divergence(self, df: pd.DataFrame, rsi_column: str,
                           price_column: str = 'close') -> Dict[str, Any]:
        """
        计算RSI背离

        Args:
            df: 包含价格和RSI的数据
            rsi_column: RSI列名
            price_column: 价格列名

        Returns:
            Dict[str, Any]: 背离分析结果
        """
        if len(df) < 10:  # 需要足够的数据来识别背离
            return {'bullish_divergence': False, 'bearish_divergence': False}

        # 取最近的数据点来分析背离
        recent_data = df.tail(10)

        # 寻找价格高点和RSI高点
        price_highs = recent_data[price_column].rolling(window=3, center=True).max()
        rsi_highs = recent_data[rsi_column].rolling(window=3, center=True).max()

        # 寻找价格低点和RSI低点
        price_lows = recent_data[price_column].rolling(window=3, center=True).min()
        rsi_lows = recent_data[rsi_column].rolling(window=3, center=True).min()

        # 简化的背离检测逻辑
        bearish_divergence = False
        bullish_divergence = False

        # 检查看跌背离（价格创新高但RSI没有）
        if (len(price_highs) >= 2 and len(rsi_highs) >= 2):
            if price_highs.iloc[-1] > price_highs.iloc[-2] and rsi_highs.iloc[-1] < rsi_highs.iloc[-2]:
                bearish_divergence = True

        # 检查看涨背离（价格创新低但RSI没有）
        if (len(price_lows) >= 2 and len(rsi_lows) >= 2):
            if price_lows.iloc[-1] < price_lows.iloc[-2] and rsi_lows.iloc[-1] > rsi_lows.iloc[-2]:
                bullish_divergence = True

        return {
            'bullish_divergence': bullish_divergence,
            'bearish_divergence': bearish_divergence,
            'signal': 'bullish' if bullish_divergence else 'bearish' if bearish_divergence else 'neutral'
        }