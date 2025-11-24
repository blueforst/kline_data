"""重采样层使用示例

此示例已更新为使用统一的全局常量定义。
"""

import sys
from pathlib import Path
from datetime import datetime

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config import load_config

# 导入更新后的resampler模块（现在使用utils.constants）
from resampler import (
    Timeframe,
    TimeframeConverter,
    get_timeframe_seconds,
    can_resample,
    KlineResampler,
    SmartResampler,
    OHLCV_AGGREGATION_RULES,
    OHLCV_COLUMNS,
)

# 从常量模块导入验证函数（推荐使用方式）
from utils.constants import (
    SUPPORTED_EXCHANGES,
    DEMO_SYMBOL,
    DEFAULT_EXCHANGE,
    validate_exchange,
    validate_symbol,
)

import pandas as pd


def example_timeframe():
    """示例1: 时间周期"""
    print("=" * 60)
    print("示例1: 时间周期")
    print("=" * 60)
    
    # 使用枚举
    print("时间周期枚举:")
    print(f"  1秒: {Timeframe.S1.value} = {Timeframe.S1.seconds}秒")
    print(f"  1分: {Timeframe.M1.value} = {Timeframe.M1.seconds}秒")
    print(f"  1时: {Timeframe.H1.value} = {Timeframe.H1.seconds}秒")
    print(f"  1天: {Timeframe.D1.value} = {Timeframe.D1.seconds}秒")
    
    # pandas频率
    print("\nPandas频率:")
    print(f"  1秒: {Timeframe.S1.value} -> {Timeframe.S1.pandas_freq}")
    print(f"  1分: {Timeframe.M1.value} -> {Timeframe.M1.pandas_freq}")
    print(f"  1时: {Timeframe.H1.value} -> {Timeframe.H1.pandas_freq}")
    
    # 从字符串创建
    tf = Timeframe.from_string('5m')
    print(f"\n从字符串创建: '5m' -> {tf.value}")
    print()


def example_timeframe_converter():
    """示例2: 时间周期转换"""
    print("=" * 60)
    print("示例2: 时间周期转换")
    print("=" * 60)
    
    # 转换为秒
    print("转换为秒:")
    print(f"  1m = {TimeframeConverter.to_seconds('1m')} 秒")
    print(f"  5m = {TimeframeConverter.to_seconds('5m')} 秒")
    print(f"  1h = {TimeframeConverter.to_seconds('1h')} 秒")
    
    # 比较
    print("\n比较时间周期:")
    result = TimeframeConverter.compare('1m', '1h')
    print(f"  1m vs 1h: {result} (负数表示1m < 1h)")
    
    # 获取较小/较大
    print(f"  较小: {TimeframeConverter.get_smaller('1m', '1h')}")
    print(f"  较大: {TimeframeConverter.get_larger('1m', '1h')}")
    print()


def example_can_resample():
    """示例3: 重采样有效性检查"""
    print("=" * 60)
    print("示例3: 重采样有效性检查")
    print("=" * 60)
    
    # 测试各种组合
    tests = [
        ('1s', '1m'),
        ('1s', '1h'),
        ('1m', '5m'),
        ('1m', '15m'),
        ('1m', '1s'),  # 无效
        ('1h', '1m'),  # 无效
    ]
    
    print("重采样有效性:")
    for source, target in tests:
        valid = can_resample(source, target)
        status = "✓" if valid else "✗"
        print(f"  {status} {source} -> {target}: {valid}")
    print()


def example_basic_resample():
    """示例4: 基本重采样"""
    print("=" * 60)
    print("示例4: 基本重采样")
    print("=" * 60)
    
    # 创建1秒数据
    start_date = datetime(2024, 1, 1)
    dates = pd.date_range(start_date, periods=300, freq='1s')  # 5分钟
    
    df = pd.DataFrame({
        'timestamp': dates,
        'open': 100.0,
        'high': 105.0,
        'low': 95.0,
        'close': 102.0,
        'volume': 10.0,
    })
    
    print(f"原始数据 (1s): {len(df)} 行")
    print(f"  时间范围: {df['timestamp'].min()} 到 {df['timestamp'].max()}")
    
    # 重采样到1分钟
    config = load_config('config/config.yaml')
    resampler = KlineResampler(config)
    
    resampled_1m = resampler.resample(df, '1s', '1m')
    print(f"\n重采样到1m: {len(resampled_1m)} 行")
    print(f"  成交量: {resampled_1m['volume'].iloc[0]} (原来的60倍)")
    
    # 重采样到5分钟
    resampled_5m = resampler.resample(df, '1s', '5m')
    print(f"\n重采样到5m: {len(resampled_5m)} 行")
    print(f"  成交量: {resampled_5m['volume'].iloc[0]} (原来的300倍)")
    
    print("\n前3行 (1m):")
    print(resampled_1m.head(3))
    print()


def example_ohlc_resample():
    """示例5: OHLC重采样"""
    print("=" * 60)
    print("示例5: OHLC重采样逻辑")
    print("=" * 60)
    
    # 创建有变化的价格数据
    start_date = datetime(2024, 1, 1)
    dates = pd.date_range(start_date, periods=60, freq='1s')
    
    # 模拟价格波动
    import numpy as np
    np.random.seed(42)
    
    base_price = 100.0
    prices = base_price + np.cumsum(np.random.randn(60) * 0.5)
    
    df = pd.DataFrame({
        'timestamp': dates,
        'open': prices,
        'high': prices + np.abs(np.random.randn(60) * 0.2),
        'low': prices - np.abs(np.random.randn(60) * 0.2),
        'close': prices + np.random.randn(60) * 0.1,
        'volume': np.random.uniform(10, 20, 60),
    })
    
    config = load_config('config/config.yaml')
    resampler = KlineResampler(config)
    
    # 重采样到1分钟
    resampled = resampler.resample(df, '1s', '1m')
    
    print(f"原始数据 (1s): {len(df)} 行")
    print(f"重采样后 (1m): {len(resampled)} 行")
    
    print("\nOHLC逻辑验证:")
    row = resampled.iloc[0]
    print(f"  Open:  {row['open']:.2f} (第一个价格)")
    print(f"  High:  {row['high']:.2f} (最高价格)")
    print(f"  Low:   {row['low']:.2f} (最低价格)")
    print(f"  Close: {row['close']:.2f} (最后价格)")
    print(f"  Volume: {row['volume']:.2f} (总成交量)")
    
    # 验证
    assert row['high'] >= row['open'], "High应该 >= Open"
    assert row['high'] >= row['close'], "High应该 >= Close"
    assert row['low'] <= row['open'], "Low应该 <= Open"
    assert row['low'] <= row['close'], "Low应该 <= Close"
    print("\n✓ OHLC逻辑验证通过")
    print()


def example_batch_resample():
    """示例6: 批量重采样"""
    print("=" * 60)
    print("示例6: 批量重采样")
    print("=" * 60)
    
    # 创建测试数据
    start_date = datetime(2024, 1, 1)
    dates = pd.date_range(start_date, periods=3600, freq='1s')  # 1小时
    
    df = pd.DataFrame({
        'timestamp': dates,
        'open': 100.0,
        'high': 105.0,
        'low': 95.0,
        'close': 102.0,
        'volume': 10.0,
    })
    
    print(f"原始数据 (1s): {len(df)} 行")
    
    config = load_config('config/config.yaml')
    resampler = KlineResampler(config)
    
    # 批量重采样到多个周期
    print("\n批量重采样到多个周期:")
    target_timeframes = ['1m', '5m', '15m', '30m', '1h']
    
    for tf in target_timeframes:
        resampled = resampler.resample(df, '1s', tf)
        print(f"  {tf:>4s}: {len(resampled):>3d} 行")
    print()


def example_verify_resample():
    """示例7: 验证重采样结果"""
    print("=" * 60)
    print("示例7: 验证重采样结果")
    print("=" * 60)
    
    # 创建测试数据
    start_date = datetime(2024, 1, 1)
    dates = pd.date_range(start_date, periods=300, freq='1s')
    
    df = pd.DataFrame({
        'timestamp': dates,
        'open': 100.0,
        'high': 105.0,
        'low': 95.0,
        'close': 102.0,
        'volume': 10.0,
    })
    
    config = load_config('config/config.yaml')
    resampler = KlineResampler(config)
    
    # 重采样
    resampled = resampler.resample(df, '1s', '1m')
    
    # 验证
    result = resampler.verify_resample(df, resampled, '1s', '1m')
    
    print("验证结果:")
    print(f"  有效: {result['valid']}")
    print(f"  错误: {len(result['errors'])} 个")
    print(f"  警告: {len(result['warnings'])} 个")
    
    if result['errors']:
        print("\n错误:")
        for error in result['errors']:
            print(f"    - {error}")
    
    if result['warnings']:
        print("\n警告:")
        for warning in result['warnings']:
            print(f"    - {warning}")
    
    if result['valid'] and not result['errors']:
        print("\n✓ 重采样结果验证通过")
    print()


def example_real_resample():
    """示例8: 实际数据重采样（需要有数据）"""
    print("=" * 60)
    print("示例8: 实际数据重采样")
    print("=" * 60)
    
    config = load_config('config/config.yaml')
    resampler = KlineResampler(config)
    
    start = datetime(2024, 1, 1)
    end = datetime(2024, 1, 1, 1, 0)
    
    print("尝试重采样实际数据...")
    print(f"  交易所: binance")
    print(f"  交易对: BTC/USDT")
    print(f"  时间: {start} 到 {end}")
    print(f"  源周期: 1s")
    print(f"  目标周期: 1m, 5m, 15m")
    
    try:
        # 尝试重采样
        df = resampler.resample_range(
            'binance',
            'BTC/USDT',
            start,
            end,
            '1s',
            '1m',
            save=False
        )
        
        if not df.empty:
            print(f"\n✓ 重采样成功: {len(df)} 行")
            print("\n前5行:")
            print(df.head())
        else:
            print("\n⚠ 没有数据（需要先下载数据）")
    except Exception as e:
        print(f"\n⚠ 重采样失败: {e}")
        print("  提示: 请先使用storage层下载1s数据")
    print()


def main():
    """运行所有示例"""
    try:
        example_timeframe()
        example_timeframe_converter()
        example_can_resample()
        example_basic_resample()
        example_ohlc_resample()
        example_batch_resample()
        example_verify_resample()
        example_real_resample()
        
        print("=" * 60)
        print("✓ 所有示例运行完成")
        print("=" * 60)
        print("\n使用提示:")
        print("1. 重采样只能从小周期到大周期（1s->1m, 1m->1h）")
        print("2. 目标周期必须是源周期的整数倍")
        print("3. 使用batch_resample可以一次性生成多个周期")
        print("4. SmartResampler可以自动选择最优的重采样路径")
        
    except Exception as e:
        print(f"\n✗ 错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
