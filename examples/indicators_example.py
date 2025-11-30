"""指标层使用示例"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from kline_data.config import load_config
from kline_data.indicators import (
    # 移动平均
    calculate_ma,
    calculate_multiple_ma,
    
    # 布林带
    calculate_bollinger,
    calculate_keltner,
    calculate_donchian,
    
    # MACD
    calculate_macd,
    get_macd_signals,
    
    # 振荡指标
    calculate_rsi,
    calculate_stochastic,
    calculate_cci,
    calculate_williams_r,
    
    # 波动率
    calculate_atr,
    calculate_std,
    calculate_hv,
    
    # 成交量
    calculate_obv,
    calculate_vwap,
    calculate_mfi,
    
    # 管理器
    IndicatorManager,
    IndicatorLibrary,
    list_available_indicators,
)


def create_sample_data(days: int = 100) -> pd.DataFrame:
    """创建示例数据"""
    np.random.seed(42)
    
    start_date = datetime(2024, 1, 1)
    dates = pd.date_range(start_date, periods=days, freq='1D')
    
    # 生成模拟价格数据
    base_price = 100.0
    price_changes = np.random.randn(days) * 2
    prices = base_price + np.cumsum(price_changes)
    
    # 确保价格为正
    prices = np.maximum(prices, 50)
    
    df = pd.DataFrame({
        'timestamp': dates,
        'open': prices + np.random.randn(days) * 0.5,
        'high': prices + np.abs(np.random.randn(days) * 1.5),
        'low': prices - np.abs(np.random.randn(days) * 1.5),
        'close': prices,
        'volume': np.random.uniform(1000, 10000, days),
    })
    
    # 确保OHLC逻辑正确
    df['high'] = df[['open', 'high', 'close']].max(axis=1)
    df['low'] = df[['open', 'low', 'close']].min(axis=1)
    
    return df


def example_moving_averages():
    """示例1: 移动平均"""
    print("=" * 60)
    print("示例1: 移动平均指标")
    print("=" * 60)
    
    df = create_sample_data(100)
    
    # 计算不同类型的MA
    print("\n1. 计算SMA:")
    result = calculate_ma(df, period=20, ma_type='sma')
    print(f"  SMA_20: {result['sma_20'].iloc[-1]:.2f}")
    
    print("\n2. 计算EMA:")
    result = calculate_ma(result, period=20, ma_type='ema')
    print(f"  EMA_20: {result['ema_20'].iloc[-1]:.2f}")
    
    print("\n3. 批量计算多周期MA:")
    result = calculate_multiple_ma(df, periods=[5, 10, 20, 50], ma_type='sma')
    print(f"  SMA_5:  {result['sma_5'].iloc[-1]:.2f}")
    print(f"  SMA_10: {result['sma_10'].iloc[-1]:.2f}")
    print(f"  SMA_20: {result['sma_20'].iloc[-1]:.2f}")
    print(f"  SMA_50: {result['sma_50'].iloc[-1]:.2f}")
    
    print()


def example_bollinger_bands():
    """示例2: 布林带"""
    print("=" * 60)
    print("示例2: 布林带指标")
    print("=" * 60)
    
    df = create_sample_data(100)
    
    # 计算布林带
    result = calculate_bollinger(df, period=20, std_dev=2.0)
    
    last = result.iloc[-1]
    print(f"\n最新K线: {last['timestamp'].strftime('%Y-%m-%d')}")
    print(f"  收盘价: {last['close']:.2f}")
    print(f"  上轨:   {last['boll_upper']:.2f}")
    print(f"  中轨:   {last['boll_middle']:.2f}")
    print(f"  下轨:   {last['boll_lower']:.2f}")
    print(f"  带宽:   {last['boll_width']:.2f}")
    print(f"  %B:     {last['boll_pct_b']:.2f}")
    
    # 判断位置
    if last['boll_pct_b'] > 1:
        print("  状态: 价格在上轨上方（超买）")
    elif last['boll_pct_b'] < 0:
        print("  状态: 价格在下轨下方（超卖）")
    else:
        print(f"  状态: 价格在通道内（{last['boll_pct_b']*100:.0f}%）")
    
    print()


def example_macd():
    """示例3: MACD"""
    print("=" * 60)
    print("示例3: MACD指标")
    print("=" * 60)
    
    df = create_sample_data(100)
    
    # 计算MACD
    result = calculate_macd(df, fast_period=12, slow_period=26, signal_period=9)
    
    last = result.iloc[-1]
    print(f"\n最新K线: {last['timestamp'].strftime('%Y-%m-%d')}")
    print(f"  MACD:      {last['macd']:.4f}")
    print(f"  Signal:    {last['macd_signal']:.4f}")
    print(f"  Histogram: {last['macd_histogram']:.4f}")
    
    # 判断趋势
    if last['macd'] > 0:
        print("  趋势: 多头")
    else:
        print("  趋势: 空头")
    
    if last['macd'] > last['macd_signal']:
        print("  状态: MACD在信号线上方（看涨）")
    else:
        print("  状态: MACD在信号线下方（看跌）")
    
    # 获取交易信号
    print("\n获取MACD交易信号:")
    result = get_macd_signals(df)
    
    # 找到最近的金叉/死叉
    golden_cross = result[result['macd_golden_cross']].tail(1)
    death_cross = result[result['macd_death_cross']].tail(1)
    
    if not golden_cross.empty:
        print(f"  最近金叉: {golden_cross['timestamp'].iloc[0].strftime('%Y-%m-%d')}")
    
    if not death_cross.empty:
        print(f"  最近死叉: {death_cross['timestamp'].iloc[0].strftime('%Y-%m-%d')}")
    
    print()


def example_rsi():
    """示例4: RSI"""
    print("=" * 60)
    print("示例4: RSI指标")
    print("=" * 60)
    
    df = create_sample_data(100)
    
    # 计算RSI
    result = calculate_rsi(df, period=14)
    
    last = result.iloc[-1]
    print(f"\n最新K线: {last['timestamp'].strftime('%Y-%m-%d')}")
    print(f"  RSI(14): {last['rsi_14']:.2f}")
    
    # 判断超买超卖
    rsi = last['rsi_14']
    if rsi > 70:
        print("  状态: 超买区域（>70）")
    elif rsi < 30:
        print("  状态: 超卖区域（<30）")
    else:
        print(f"  状态: 正常区域（30-70）")
    
    # 统计RSI分布
    print("\nRSI统计:")
    print(f"  最大值: {result['rsi_14'].max():.2f}")
    print(f"  最小值: {result['rsi_14'].min():.2f}")
    print(f"  平均值: {result['rsi_14'].mean():.2f}")
    
    # 超买超卖次数
    overbought = (result['rsi_14'] > 70).sum()
    oversold = (result['rsi_14'] < 30).sum()
    print(f"  超买次数: {overbought}")
    print(f"  超卖次数: {oversold}")
    
    print()


def example_atr():
    """示例5: ATR"""
    print("=" * 60)
    print("示例5: ATR波动率指标")
    print("=" * 60)
    
    df = create_sample_data(100)
    
    # 计算ATR
    result = calculate_atr(df, period=14)
    
    last = result.iloc[-1]
    print(f"\n最新K线: {last['timestamp'].strftime('%Y-%m-%d')}")
    print(f"  收盘价: {last['close']:.2f}")
    print(f"  TR:     {last['tr']:.2f}")
    print(f"  ATR(14): {last['atr_14']:.2f}")
    print(f"  ATR%:   {last['atr_14']/last['close']*100:.2f}%")
    
    # ATR趋势
    atr_ma = result['atr_14'].rolling(20).mean().iloc[-1]
    print(f"\nATR 20日均值: {atr_ma:.2f}")
    
    if last['atr_14'] > atr_ma:
        print("  波动性增加")
    else:
        print("  波动性减小")
    
    print()


def example_volume_indicators():
    """示例6: 成交量指标"""
    print("=" * 60)
    print("示例6: 成交量指标")
    print("=" * 60)
    
    df = create_sample_data(100)
    
    # OBV
    result = calculate_obv(df)
    print(f"\n1. OBV (能量潮):")
    print(f"  当前OBV: {result['obv'].iloc[-1]:.0f}")
    
    # OBV趋势
    obv_ma = result['obv'].rolling(20).mean().iloc[-1]
    if result['obv'].iloc[-1] > obv_ma:
        print("  趋势: 上升（买盘强劲）")
    else:
        print("  趋势: 下降（卖盘强劲）")
    
    # VWAP
    result = calculate_vwap(result, period=20)
    last = result.iloc[-1]
    print(f"\n2. VWAP (成交量加权平均价):")
    print(f"  收盘价: {last['close']:.2f}")
    print(f"  VWAP:  {last['vwap']:.2f}")
    
    if last['close'] > last['vwap']:
        print("  状态: 价格在VWAP上方（强势）")
    else:
        print("  状态: 价格在VWAP下方（弱势）")
    
    # MFI
    result = calculate_mfi(result, period=14)
    print(f"\n3. MFI (资金流量指标):")
    print(f"  MFI(14): {result['mfi_14'].iloc[-1]:.2f}")
    
    mfi = result['mfi_14'].iloc[-1]
    if mfi > 80:
        print("  状态: 超买")
    elif mfi < 20:
        print("  状态: 超卖")
    else:
        print("  状态: 正常")
    
    print()


def example_indicator_manager():
    """示例7: 指标管理器"""
    print("=" * 60)
    print("示例7: 指标管理器")
    print("=" * 60)
    
    df = create_sample_data(100)
    
    # 列出所有可用指标
    print("\n1. 所有可用指标:")
    indicators = list_available_indicators()
    print(f"  共 {len(indicators)} 个指标")
    
    # 按类别分组
    ma_indicators = [i for i in indicators if i in ['sma', 'ema', 'wma', 'dema', 'tema', 'vwma', 'hma']]
    osc_indicators = [i for i in indicators if i in ['rsi', 'stoch', 'cci', 'williams_r', 'roc', 'momentum']]
    vol_indicators = [i for i in indicators if i in ['atr', 'natr', 'std', 'hv', 'ulcer', 'mass_index', 'choppiness']]
    
    print(f"\n  移动平均 ({len(ma_indicators)}): {', '.join(ma_indicators)}")
    print(f"  振荡指标 ({len(osc_indicators)}): {', '.join(osc_indicators)}")
    print(f"  波动率 ({len(vol_indicators)}): {', '.join(vol_indicators)}")
    
    # 使用指标管理器
    print("\n2. 使用指标管理器批量计算:")
    manager = IndicatorManager()
    
    indicators_config = {
        'sma': {'period': 20},
        'ema': {'period': 20},
        'rsi': {'period': 14},
        'macd': {'fast_period': 12, 'slow_period': 26, 'signal_period': 9},
        'boll': {'period': 20, 'std_dev': 2.0},
        'atr': {'period': 14},
    }
    
    result = manager.calculate_multiple(df, indicators_config)
    
    print(f"  计算完成，新增 {len(result.columns) - len(df.columns)} 列")
    print(f"  总列数: {len(result.columns)}")
    
    print()


def example_indicator_library():
    """示例8: 指标库（预设组合）"""
    print("=" * 60)
    print("示例8: 指标库（预设组合）")
    print("=" * 60)
    
    df = create_sample_data(100)
    
    print("\n1. 添加常用指标:")
    result = IndicatorLibrary.add_common_indicators(
        df,
        ma_periods=[5, 10, 20],
        include_macd=True,
        include_rsi=True,
        include_boll=True,
        include_volume=True
    )
    print(f"  原始列数: {len(df.columns)}")
    print(f"  新增列数: {len(result.columns) - len(df.columns)}")
    print(f"  总列数: {len(result.columns)}")
    
    print("\n2. 添加趋势指标:")
    result = IndicatorLibrary.add_trend_indicators(df, ma_periods=[20, 50])
    print(f"  新增列数: {len(result.columns) - len(df.columns)}")
    
    print("\n3. 添加动量指标:")
    result = IndicatorLibrary.add_momentum_indicators(df)
    print(f"  新增列数: {len(result.columns) - len(df.columns)}")
    
    print("\n4. 添加波动率指标:")
    result = IndicatorLibrary.add_volatility_indicators(df)
    print(f"  新增列数: {len(result.columns) - len(df.columns)}")
    
    print("\n5. 添加成交量指标:")
    result = IndicatorLibrary.add_volume_indicators(df)
    print(f"  新增列数: {len(result.columns) - len(df.columns)}")
    
    print()


def example_comprehensive_analysis():
    """示例9: 综合分析"""
    print("=" * 60)
    print("示例9: 综合技术分析")
    print("=" * 60)
    
    df = create_sample_data(100)
    
    # 计算所有主要指标
    result = IndicatorLibrary.add_common_indicators(df)
    
    # 最新数据
    last = result.iloc[-1]
    prev = result.iloc[-2]
    
    print(f"\n最新K线分析: {last['timestamp'].strftime('%Y-%m-%d')}")
    print(f"\n价格信息:")
    print(f"  收盘价: {last['close']:.2f}")
    print(f"  涨跌幅: {(last['close']/prev['close']-1)*100:+.2f}%")
    
    print(f"\n趋势判断:")
    # MA金叉死叉
    sma20 = last['sma_20']
    sma50 = last['sma_50']
    print(f"  SMA20: {sma20:.2f}")
    print(f"  SMA50: {sma50:.2f}")
    if sma20 > sma50:
        print("  → 短期均线在长期均线上方（多头排列）")
    else:
        print("  → 短期均线在长期均线下方（空头排列）")
    
    # MACD
    print(f"\n  MACD: {last['macd']:.4f}")
    if last['macd'] > 0 and last['macd_histogram'] > 0:
        print("  → MACD多头信号")
    elif last['macd'] < 0 and last['macd_histogram'] < 0:
        print("  → MACD空头信号")
    
    print(f"\n动量指标:")
    # RSI
    rsi = last['rsi_14']
    print(f"  RSI(14): {rsi:.2f}")
    if rsi > 70:
        print("  → 超买")
    elif rsi < 30:
        print("  → 超卖")
    else:
        print("  → 正常")
    
    print(f"\n波动率:")
    # 布林带
    pct_b = last['boll_pct_b']
    print(f"  布林带%B: {pct_b:.2f}")
    if pct_b > 1:
        print("  → 价格突破上轨")
    elif pct_b < 0:
        print("  → 价格突破下轨")
    else:
        print(f"  → 价格在通道内（{pct_b*100:.0f}%）")
    
    # ATR
    atr_pct = last['atr_14'] / last['close'] * 100
    print(f"  ATR%: {atr_pct:.2f}%")
    if atr_pct > 3:
        print("  → 高波动")
    elif atr_pct < 1:
        print("  → 低波动")
    else:
        print("  → 正常波动")
    
    print(f"\n成交量:")
    # OBV趋势
    obv_change = (last['obv'] - result['obv'].rolling(20).mean().iloc[-1]) / result['obv'].rolling(20).mean().iloc[-1]
    print(f"  OBV变化: {obv_change*100:+.2f}%")
    if obv_change > 0.1:
        print("  → 买盘强劲")
    elif obv_change < -0.1:
        print("  → 卖盘强劲")
    
    print()


def main():
    """运行所有示例"""
    try:
        example_moving_averages()
        example_bollinger_bands()
        example_macd()
        example_rsi()
        example_atr()
        example_volume_indicators()
        example_indicator_manager()
        example_indicator_library()
        example_comprehensive_analysis()
        
        print("=" * 60)
        print("✓ 所有示例运行完成")
        print("=" * 60)
        print("\n指标层特性:")
        print("✓ 7大类30+技术指标")
        print("✓ 移动平均: SMA, EMA, WMA, DEMA, TEMA, VWMA, HMA")
        print("✓ 布林带: BOLL, KC, DC")
        print("✓ MACD: MACD, PPO, APO")
        print("✓ 振荡指标: RSI, Stoch, CCI, Williams%R, ROC, MOM")
        print("✓ 波动率: ATR, NATR, STD, HV, UI, MI, CI")
        print("✓ 成交量: OBV, VWAP, MFI, A/D, CMF, EMV, FI")
        print("✓ 指标管理器支持批量计算")
        print("✓ 指标库提供预设组合")
        
    except Exception as e:
        print(f"\n✗ 错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
