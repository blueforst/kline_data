"""指标客户端 - 技术指标计算"""

import pandas as pd
from typing import List
from rich.console import Console

from ...config import Config
from ...indicators import IndicatorManager
from ...utils.constants import OHLCV_COLUMNS

console = Console()


class IndicatorClient:
    """
    技术指标计算客户端
    
    提供常用技术指标计算功能，包括：
    1. 移动平均线（MA, EMA）
    2. 相对强弱指标（RSI）
    3. 布林带（BOLL）
    4. MACD
    """
    
    def __init__(self, config: Config = None):
        """
        初始化指标客户端
        
        Args:
            config: 配置对象（目前未使用，为未来扩展预留）
        """
        self.config = config
        self.indicator_calc = IndicatorManager()
    
    def calculate(
        self,
        df: pd.DataFrame,
        indicators: List[str]
    ) -> pd.DataFrame:
        """
        计算技术指标

        Args:
            df: K线数据
            indicators: 指标列表（如 ['MA_20', 'EMA_12', 'RSI_14', 'BOLL_20']）

        Returns:
            pd.DataFrame: 带指标的数据
        """
        # 验证DataFrame包含必要的OHLCV列
        required_columns = OHLCV_COLUMNS[:6]  # timestamp, open, high, low, close, volume
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise ValueError(f"DataFrame missing required OHLCV columns: {missing_columns}")

        # 创建副本避免修改原数据
        df = df.copy()

        for indicator in indicators:
            try:
                # 解析指标名称和参数
                parts = indicator.split('_')
                indicator_name = parts[0].lower()
                
                # 获取参数
                params = {}
                if len(parts) > 1:
                    if indicator_name in ['ma', 'sma', 'ema', 'wma']:
                        params['period'] = int(parts[1])
                    elif indicator_name == 'rsi':
                        params['period'] = int(parts[1])
                    elif indicator_name in ['boll', 'bollinger']:
                        params['period'] = int(parts[1])
                
                # 使用IndicatorManager计算
                if indicator_name in ['ma', 'sma']:
                    df = self.indicator_calc.calculate(df, 'sma', **params)
                    # 重命名列
                    period = params.get('period', 20)
                    df = df.rename(columns={f'sma_{period}': indicator})
                
                elif indicator_name == 'ema':
                    df = self.indicator_calc.calculate(df, 'ema', **params)
                    period = params.get('period', 12)
                    df = df.rename(columns={f'ema_{period}': indicator})
                
                elif indicator_name == 'rsi':
                    df = self.indicator_calc.calculate(df, 'rsi', **params)
                    period = params.get('period', 14)
                    df = df.rename(columns={f'rsi_{period}': indicator})
                
                elif indicator_name in ['boll', 'bollinger']:
                    df = self.indicator_calc.calculate(df, 'boll', **params)
                    period = params.get('period', 20)
                    # 布林带会生成三列，保持原样或重命名
                    if f'boll_upper_{period}' in df.columns:
                        df = df.rename(columns={
                            f'boll_upper_{period}': f'{indicator}_upper',
                            f'boll_middle_{period}': f'{indicator}_middle',
                            f'boll_lower_{period}': f'{indicator}_lower'
                        })
                
                elif indicator_name == 'macd':
                    df = self.indicator_calc.calculate(df, 'macd')
                    # MACD会生成多列，保持原列名
                
                else:
                    console.print(f"[yellow]Unknown indicator: {indicator}[/yellow]")

            except Exception as e:
                console.print(f"[red]Error calculating {indicator}: {e}[/red]")

        return df
