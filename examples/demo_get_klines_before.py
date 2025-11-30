"""简单演示：get_klines_before接口

本示例展示如何使用全局常量来替换硬编码字符串，提高代码的可维护性和类型安全性。
"""

from datetime import datetime
from kline_data.sdk import KlineClient
from kline_data.utils.timezone import to_utc, format_datetime, timestamp_to_datetime

# 导入全局常量
from kline_data.utils.constants import (
    Timeframe,
    DEFAULT_EXCHANGE,
    DEFAULT_SYMBOL,
    OHLCV_COLUMNS,
    get_timeframe_seconds,
    validate_timeframe,
    validate_exchange,
    validate_symbol,
)

def demo():
    """演示get_klines_before接口的基本使用（使用全局常量）"""

    print("=" * 70)
    print("get_klines_before 接口演示（使用全局常量）")
    print("=" * 70)

    # 验证常量
    validate_exchange(DEFAULT_EXCHANGE)
    validate_symbol(DEFAULT_SYMBOL)
    validate_timeframe(Timeframe.D1.value)

    print(f"使用的常量:")
    print(f"  交易所: {DEFAULT_EXCHANGE}")
    print(f"  交易对: {DEFAULT_SYMBOL}")
    print(f"  OHLCV字段: {OHLCV_COLUMNS}")
    print()

    # 创建客户端
    client = KlineClient()

    # 示例1：获取指定日期前的K线（使用常量）
    print("\n[示例1] 获取2024年1月1日前10条日线")
    print("-" * 70)

    before_time = datetime(2024, 1, 1)
    df = client.get_klines_before(
        exchange=DEFAULT_EXCHANGE,  # 使用常量而非硬编码
        symbol=DEFAULT_SYMBOL,       # 使用常量而非硬编码
        before_time=before_time,
        interval=Timeframe.D1.value,  # 使用枚举值
        limit=10
    )

    if not df.empty:
        print(f"✓ 成功获取 {len(df)} 条K线数据")
        print(f"  时间范围: {df[OHLCV_COLUMNS[0]].min()} 至 {df[OHLCV_COLUMNS[0]].max()}")
        print(f"\n  最后3条数据:")
        for idx, row in df.tail(3).iterrows():
            dt = timestamp_to_datetime(row[OHLCV_COLUMNS[0]])
            print(f"    {format_datetime(dt, for_display=True)} | "
                  f"开:{row[OHLCV_COLUMNS[1]]:.2f} 高:{row[OHLCV_COLUMNS[2]]:.2f} "
                  f"低:{row[OHLCV_COLUMNS[3]]:.2f} 收:{row[OHLCV_COLUMNS[4]]:.2f}")
    else:
        print("✗ 未获取到数据")
    
    # 示例2：使用UTC时间获取小时线（使用常量）
    print("\n[示例2] 使用UTC时间获取2024年6月15日12:00前的5条小时线")
    print("-" * 70)

    before_time_utc = to_utc(datetime(2024, 6, 15, 12, 0, 0))
    print(f"截止时间(UTC): {format_datetime(before_time_utc, for_display=True)}")

    # 验证时间周期
    hourly_tf = Timeframe.H1
    print(f"时间周期: {hourly_tf.value} ({hourly_tf.seconds}秒/根K线)")

    df2 = client.get_klines_before(
        exchange=DEFAULT_EXCHANGE,    # 使用常量
        symbol=DEFAULT_SYMBOL,         # 使用常量
        before_time=before_time_utc,
        interval=hourly_tf.value,      # 使用枚举值
        limit=5
    )

    if not df2.empty:
        print(f"✓ 成功获取 {len(df2)} 条K线数据")
        print(f"\n  数据列表:")
        for idx, row in df2.iterrows():
            dt = timestamp_to_datetime(row[OHLCV_COLUMNS[0]])
            print(f"    {format_datetime(dt, for_display=True)} | 收盘:{row[OHLCV_COLUMNS[4]]:.2f}")
    else:
        print("✗ 未获取到数据")
    
    # 示例3：获取数据并计算指标（使用常量）
    print("\n[示例3] 获取数据并计算技术指标")
    print("-" * 70)

    df3 = client.get_klines_before(
        exchange=DEFAULT_EXCHANGE,      # 使用常量
        symbol=DEFAULT_SYMBOL,           # 使用常量
        before_time=datetime(2024, 3, 1),
        interval=Timeframe.D1.value,     # 使用枚举值
        limit=30,
        with_indicators=['MA_20', 'RSI_14']
    )

    if not df3.empty:
        print(f"✓ 成功获取 {len(df3)} 条K线数据，已计算指标")
        print(f"  数据列: {', '.join(df3.columns.tolist())}")

        # 显示最后5条数据的指标
        print(f"\n  最后5条数据的指标:")
        for idx, row in df3.tail(5).iterrows():
            dt = timestamp_to_datetime(row[OHLCV_COLUMNS[0]])
            ma_val = f"{row['MA_20']:.2f}" if not pd.isna(row['MA_20']) else "N/A"
            rsi_val = f"{row['RSI_14']:.2f}" if not pd.isna(row['RSI_14']) else "N/A"
            print(f"    {format_datetime(dt, for_display=True)[:10]} | "
                  f"收盘:{row[OHLCV_COLUMNS[4]]:.2f} MA20:{ma_val} RSI:{rsi_val}")
    else:
        print("✗ 未获取到数据")

    # 示例4：展示常量的优势和验证功能
    print("\n[示例4] 常量验证和错误处理")
    print("-" * 70)

    print("✅ 常量使用的优势:")
    print("  1. 类型安全 - 防止拼写错误")
    print("  2. 自动补全 - IDE支持和更好的开发体验")
    print("  3. 集中管理 - 统一修改配置")
    print("  4. 验证功能 - 自动检查参数有效性")

    print("\n📊 时间周期秒数映射:")
    common_intervals = ['1m', '5m', '15m', '1h', '1d']
    for interval in common_intervals:
        seconds = get_timeframe_seconds(interval)
        print(f"  {interval}: {seconds}秒")

    print("\n" + "=" * 70)
    print("演示完成！现在您应该使用全局常量而非硬编码字符串。")
    print("=" * 70)
    print("\n💡 使用提示:")
    print("  - 总是从 utils.constants 导入常量")
    print("  - 使用 Timeframe 枚举而非字符串")
    print("  - 使用 OHLCV_COLUMNS 访问字段名")
    print("  - 使用验证函数检查输入")


if __name__ == '__main__':
    # 需要导入pandas用于isna检查
    import pandas as pd
    
    demo()
