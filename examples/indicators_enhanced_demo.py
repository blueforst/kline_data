"""
指标模块增强功能演示
展示重构后的TA-Lib和Pandas兼容性改进
"""

import pandas as pd
import numpy as np
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

# 导入指标模块
from indicators import (
    IndicatorManager,
    talib_adapter,
    TALIB_AVAILABLE,
    ensure_dataframe,
    normalize_ohlcv_columns,
    validate_price_data,
    calculate_returns,
    crossover,
    crossunder,
    smooth_series,
    list_available_indicators
)

console = Console()


def demo_basic_usage():
    """演示基本用法"""
    console.print("\n[bold cyan]1. 基本用法演示[/bold cyan]")
    
    # 创建示例数据
    np.random.seed(42)
    dates = pd.date_range('2024-01-01', periods=100, freq='1D')
    base_price = 100
    
    df = pd.DataFrame({
        'timestamp': dates,
        'open': base_price + np.cumsum(np.random.randn(100) * 2),
        'high': base_price + np.cumsum(np.random.randn(100) * 2) + 2,
        'low': base_price + np.cumsum(np.random.randn(100) * 2) - 2,
        'close': base_price + np.cumsum(np.random.randn(100) * 2),
        'volume': np.random.randint(1000, 5000, 100)
    })
    
    # 确保价格一致性
    df['high'] = df[['open', 'close', 'high']].max(axis=1) + 1
    df['low'] = df[['open', 'close', 'low']].min(axis=1) - 1
    
    console.print(f"✓ 创建了 {len(df)} 行示例数据")
    console.print(df.head())
    
    # 验证数据
    is_valid, errors = validate_price_data(df)
    if is_valid:
        console.print("✓ 数据验证通过", style="green")
    else:
        console.print(f"✗ 数据验证失败: {errors}", style="red")
    
    return df


def demo_talib_compatibility():
    """演示TA-Lib兼容性"""
    console.print("\n[bold cyan]2. TA-Lib兼容性演示[/bold cyan]")
    
    console.print(f"TA-Lib可用: [bold]{'是' if TALIB_AVAILABLE else '否'}[/bold]")
    
    # 获取可用函数
    available_funcs = talib_adapter.get_available_functions()
    console.print(f"可用TA-Lib函数数量: [bold]{len(available_funcs)}[/bold]")
    console.print(f"函数列表: {', '.join(available_funcs[:10])}...")
    
    # 测试数据
    close = np.array([100, 102, 101, 103, 105, 104, 106, 108, 107, 110])
    
    # SMA测试
    sma_result = talib_adapter.sma(close, period=5)
    console.print(f"\nSMA(5)计算结果: {sma_result[-3:]}")
    
    # EMA测试
    ema_result = talib_adapter.ema(close, period=5)
    console.print(f"EMA(5)计算结果: {ema_result[-3:]}")
    
    # RSI测试
    rsi_result = talib_adapter.rsi(close, period=5)
    console.print(f"RSI(5)计算结果: {rsi_result[-3:]}")


def demo_indicator_manager(df: pd.DataFrame):
    """演示指标管理器"""
    console.print("\n[bold cyan]3. 指标管理器演示[/bold cyan]")
    
    manager = IndicatorManager()
    
    # 列出所有可用指标
    indicators = list_available_indicators()
    console.print(f"可用指标数量: [bold]{len(indicators)}[/bold]")
    
    # 计算单个指标
    console.print("\n计算SMA指标...")
    result = manager.calculate(df, 'sma', period=10)
    console.print(f"✓ 添加了列: sma_10")
    console.print(result[['close', 'sma_10']].tail())
    
    # 批量计算指标
    console.print("\n批量计算多个指标...")
    indicators_config = {
        'sma': {'period': 20},
        'ema': {'period': 20},
        'rsi': {'period': 14},
        'macd': {}
    }
    
    result = manager.calculate_multiple(df, indicators_config)
    console.print(f"✓ 计算完成，新增 {len(result.columns) - len(df.columns)} 个指标列")
    console.print(f"列名: {list(result.columns)}")


def demo_utility_functions(df: pd.DataFrame):
    """演示工具函数"""
    console.print("\n[bold cyan]4. 工具函数演示[/bold cyan]")
    
    # 计算收益率
    console.print("\n计算收益率...")
    simple_returns = calculate_returns(df, column='close', method='simple')
    log_returns = calculate_returns(df, column='close', method='log')
    
    console.print(f"简单收益率均值: {simple_returns.mean():.4f}")
    console.print(f"对数收益率均值: {log_returns.mean():.4f}")
    
    # 检测交叉信号
    console.print("\n检测均线交叉...")
    df['sma_5'] = df['close'].rolling(5).mean()
    df['sma_20'] = df['close'].rolling(20).mean()
    
    cross_up = crossover(df['sma_5'], df['sma_20'])
    cross_down = crossunder(df['sma_5'], df['sma_20'])
    
    console.print(f"上穿信号数量: {cross_up.sum()}")
    console.print(f"下穿信号数量: {cross_down.sum()}")
    
    if cross_up.sum() > 0:
        up_dates = df.loc[cross_up, 'timestamp'].values
        console.print(f"上穿日期: {up_dates[:3]}")
    
    # 平滑数据
    console.print("\n数据平滑...")
    smoothed_sma = smooth_series(df['close'], method='sma', window=5)
    smoothed_ema = smooth_series(df['close'], method='ema', window=5)
    
    console.print(f"原始数据标准差: {df['close'].std():.2f}")
    console.print(f"SMA平滑后标准差: {smoothed_sma.std():.2f}")
    console.print(f"EMA平滑后标准差: {smoothed_ema.std():.2f}")


def demo_advanced_features(df: pd.DataFrame):
    """演示高级特性"""
    console.print("\n[bold cyan]5. 高级特性演示[/bold cyan]")
    
    # 测试ATR
    console.print("\n计算ATR（平均真实范围）...")
    high = df['high'].values
    low = df['low'].values
    close = df['close'].values
    
    atr = talib_adapter.atr(high, low, close, period=14)
    console.print(f"ATR最新值: {atr[-1]:.2f}")
    console.print(f"ATR均值: {np.nanmean(atr):.2f}")
    
    # 测试随机指标
    console.print("\n计算随机指标...")
    stoch_k, stoch_d = talib_adapter.stoch(high, low, close)
    console.print(f"Stoch %K最新值: {stoch_k[-1]:.2f}")
    console.print(f"Stoch %D最新值: {stoch_d[-1]:.2f}")
    
    # 测试OBV
    console.print("\n计算OBV（能量潮）...")
    volume = df['volume'].values
    obv = talib_adapter.obv(close, volume)
    console.print(f"OBV最新值: {obv[-1]:.0f}")
    
    # 测试CCI
    console.print("\n计算CCI（商品通道指数）...")
    cci = talib_adapter.cci(high, low, close, period=14)
    console.print(f"CCI最新值: {cci[-1]:.2f}")


def demo_data_validation():
    """演示数据验证"""
    console.print("\n[bold cyan]6. 数据验证演示[/bold cyan]")
    
    # 测试正常数据
    console.print("\n测试正常数据...")
    normal_df = pd.DataFrame({
        'open': [100, 102, 101],
        'high': [103, 104, 103],
        'low': [99, 101, 100],
        'close': [102, 103, 101]
    })
    
    is_valid, errors = validate_price_data(normal_df)
    console.print(f"正常数据验证: {'✓ 通过' if is_valid else '✗ 失败'}", 
                 style="green" if is_valid else "red")
    
    # 测试异常数据
    console.print("\n测试异常数据（高价低于低价）...")
    bad_df = pd.DataFrame({
        'open': [100, 102, 101],
        'high': [98, 99, 100],  # 错误：高价低于低价
        'low': [99, 101, 100],
        'close': [102, 103, 101]
    })
    
    is_valid, errors = validate_price_data(bad_df, check_consistency=True)
    console.print(f"异常数据验证: {'✓ 通过' if is_valid else '✗ 失败'}", 
                 style="green" if is_valid else "red")
    if not is_valid:
        for error in errors:
            console.print(f"  - {error}", style="yellow")


def demo_performance_comparison():
    """演示性能对比"""
    console.print("\n[bold cyan]7. 性能对比[/bold cyan]")
    
    import time
    
    # 创建大数据集
    n = 10000
    np.random.seed(42)
    data = 100 + np.cumsum(np.random.randn(n) * 0.1)
    
    console.print(f"测试数据量: {n} 行")
    
    # 测试SMA
    console.print("\nSMA性能测试...")
    
    start = time.time()
    sma_result = talib_adapter.sma(data, period=20)
    talib_time = time.time() - start
    console.print(f"TA-Lib SMA: {talib_time*1000:.2f}ms")
    
    start = time.time()
    pandas_result = pd.Series(data).rolling(20).mean().values
    pandas_time = time.time() - start
    console.print(f"Pandas SMA: {pandas_time*1000:.2f}ms")
    
    # 验证结果一致性
    diff = np.nanmean(np.abs(sma_result - pandas_result))
    console.print(f"结果差异: {diff:.10f}")
    
    if diff < 1e-10:
        console.print("✓ 结果完全一致", style="green")
    else:
        console.print("⚠ 存在微小差异", style="yellow")


def create_summary_table():
    """创建功能总结表"""
    table = Table(title="指标模块重构功能总结", show_header=True, header_style="bold magenta")
    
    table.add_column("类别", style="cyan", width=20)
    table.add_column("功能", style="green", width=30)
    table.add_column("状态", style="yellow", width=10)
    
    features = [
        ("基类", "VolatilityBase", "✓"),
        ("基类", "VolumeBase", "✓"),
        ("基类", "IndicatorPipeline", "✓"),
        ("基类", "validate_ohlcv", "✓"),
        ("适配器", "ATR计算", "✓"),
        ("适配器", "Stochastic计算", "✓"),
        ("适配器", "ADX计算", "✓"),
        ("适配器", "OBV计算", "✓"),
        ("适配器", "CCI计算", "✓"),
        ("工具", "数据格式转换", "✓"),
        ("工具", "数据验证", "✓"),
        ("工具", "收益率计算", "✓"),
        ("工具", "交叉信号检测", "✓"),
        ("工具", "数据平滑", "✓"),
    ]
    
    for category, feature, status in features:
        table.add_row(category, feature, status)
    
    return table


def main():
    """主函数"""
    console.print(Panel.fit(
        "[bold green]指标模块增强功能演示[/bold green]\n"
        "展示TA-Lib和Pandas兼容性改进",
        border_style="green"
    ))
    
    # 1. 基本用法
    df = demo_basic_usage()
    
    # 2. TA-Lib兼容性
    demo_talib_compatibility()
    
    # 3. 指标管理器
    demo_indicator_manager(df)
    
    # 4. 工具函数
    demo_utility_functions(df)
    
    # 5. 高级特性
    demo_advanced_features(df)
    
    # 6. 数据验证
    demo_data_validation()
    
    # 7. 性能对比
    demo_performance_comparison()
    
    # 显示功能总结
    console.print("\n")
    console.print(create_summary_table())
    
    console.print("\n[bold green]✓ 所有演示完成！[/bold green]")


if __name__ == '__main__':
    main()
