#!/usr/bin/env python3
"""时间周期枚举使用示例

本示例展示如何使用全局的 Timeframe 枚举和相关常量。
"""

from datetime import datetime, timedelta
from kline_data.utils.constants import (
    Timeframe,
    TIMEFRAME_SECONDS,
    COMMON_INTERVALS,
    get_timeframe_seconds,
    validate_timeframe,
)


def example_basic_usage():
    """基本使用示例"""
    print("=" * 60)
    print("1. 基本使用")
    print("=" * 60)
    
    # 使用枚举值
    tf = Timeframe.M1
    print(f"枚举对象: {tf}")
    print(f"字符串值: {tf.value}")
    print(f"秒数: {tf.seconds}")
    print(f"Pandas频率: {tf.pandas_freq}")
    print()


def example_from_string():
    """从字符串创建枚举"""
    print("=" * 60)
    print("2. 从字符串创建枚举")
    print("=" * 60)
    
    intervals = ['1m', '5m', '15m', '1h', '4h', '1d']
    
    for interval_str in intervals:
        tf = Timeframe.from_string(interval_str)
        print(f"{interval_str:5s} -> {tf.name:5s} ({tf.seconds:6d} 秒)")
    print()


def example_list_all():
    """列出所有支持的时间周期"""
    print("=" * 60)
    print("3. 所有支持的时间周期")
    print("=" * 60)
    
    all_timeframes = Timeframe.list_all()
    print(f"支持的时间周期: {', '.join(all_timeframes)}")
    print(f"总计: {len(all_timeframes)} 个")
    print()



def example_constants_usage():
    """使用常量"""
    print("=" * 60)
    print("4. 使用预定义常量")
    print("=" * 60)
    
    print("常用周期 (COMMON_INTERVALS):")
    print(f"  {', '.join(COMMON_INTERVALS)}")
    print()
    
    print("所有周期直接由CCXT提供，无需本地重采样")
    print()
    
    print("时间周期秒数映射 (部分):")
    for interval in COMMON_INTERVALS:
        seconds = TIMEFRAME_SECONDS[interval]
        print(f"  {interval:4s}: {seconds:6d} 秒")
    print()


def example_time_calculations():
    """时间计算示例"""
    print("=" * 60)
    print("5. 时间计算")
    print("=" * 60)
    
    # 计算100根K线的时间跨度
    num_candles = 100
    
    for tf_name in ['M1', 'M5', 'H1', 'D1']:
        tf = getattr(Timeframe, tf_name)
        seconds = tf.seconds * num_candles
        time_span = timedelta(seconds=seconds)
        
        print(f"{num_candles:3d}根 {tf.value:4s} K线 = {time_span}")
    print()


def example_validation():
    """验证示例"""
    print("=" * 60)
    print("6. 验证功能")
    print("=" * 60)
    
    # 有效的时间周期
    valid_intervals = ['1m', '5m', '1h', '1d']
    print("验证有效周期:")
    for interval in valid_intervals:
        try:
            validate_timeframe(interval)
            print(f"  ✓ {interval} 有效")
        except ValueError as e:
            print(f"  ✗ {interval} 无效: {e}")
    print()
    
    # 无效的时间周期
    invalid_intervals = ['1x', '5y', 'invalid']
    print("验证无效周期:")
    for interval in invalid_intervals:
        try:
            validate_timeframe(interval)
            print(f"  ✓ {interval} 有效")
        except ValueError as e:
            print(f"  ✗ {interval} 无效 (预期)")
    print()


def example_practical_usage():
    """实际应用示例"""
    print("=" * 60)
    print("7. 实际应用场景")
    print("=" * 60)
    
    # 场景1: 批量处理多个周期
    print("场景1: 批量处理多个周期")
    for interval in COMMON_INTERVALS:
        tf = Timeframe.from_string(interval)
        print(f"  处理 {interval} 周期数据 (每根K线 {tf.seconds}秒)")
    print()
    
    # 场景2: 计算下载时间范围
    print("场景2: 计算需要下载的K线数量")
    start_time = datetime(2024, 1, 1)
    end_time = datetime(2024, 1, 31)
    time_diff = (end_time - start_time).total_seconds()
    
    for interval in ['1m', '1h', '1d']:
        seconds = get_timeframe_seconds(interval)
        num_candles = int(time_diff / seconds)
        print(f"  {interval:4s}: 约 {num_candles:6d} 根K线")
    print()
    
    # 场景3: 规划直接下载任务
    print("场景3: 规划直接下载任务（全部由CCXT提供）")
    target = Timeframe.H4  # 目标：4小时
    print(f"  目标周期: {target.value} (4小时)")
    print("  直接调用 KlineClient.get_kline(..., interval=target.value) 即可")
    print("  系统会在本地数据缺失时自动从交易所下载该周期")
    print()


def example_comparison():
    """新旧用法对比"""
    print("=" * 60)
    print("8. 新旧用法对比")
    print("=" * 60)
    
    print("❌ 旧的用法（不推荐）:")
    print("  interval = '1m'")
    print("  if interval in ['1m', '5m', '15m', '1h']:")
    print("      process(interval)")
    print()
    
    print("✅ 新的用法（推荐）:")
    print("  from utils.constants import Timeframe, COMMON_INTERVALS")
    print("  interval = Timeframe.M1.value")
    print("  for interval in COMMON_INTERVALS:")
    print("      process(interval)")
    print()


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("时间周期枚举 (Timeframe) 使用示例")
    print("=" * 60 + "\n")
    
    # 运行所有示例
    example_basic_usage()
    example_from_string()
    example_list_all()
    example_constants_usage()
    example_time_calculations()
    example_validation()
    example_practical_usage()
    example_comparison()
    
    print("=" * 60)
    print("示例完成！")
    print("=" * 60)
    print("\n更多信息请参考:")
    print("  - docs/timeframe_usage.md")
    print("  - utils/constants.py")
    print()


if __name__ == '__main__':
    main()
