#!/usr/bin/env python3
"""
常量使用最佳实践示例

本示例展示了如何在项目中正确使用全局常量，避免硬编码字符串，
提高代码的可维护性、类型安全性和一致性。

核心原则：
1. 总是从 utils.constants 导入常量
2. 使用 Timeframe 枚举而非字符串
3. 使用 OHLCV_COLUMNS 访问数据字段
4. 使用验证函数检查输入参数
5. 利用常量进行错误处理和文档化
"""

from datetime import datetime
from kline_data.sdk import KlineClient
from rich.console import Console
from rich.table import Table

# 导入全局常量
from kline_data.utils.constants import (
    # 时间周期枚举
    Timeframe,

    # 交易所和交易对常量
    DEFAULT_EXCHANGE,
    DEFAULT_SYMBOL,
    SUPPORTED_EXCHANGES,
    TEST_SYMBOLS,

    # 数据相关常量
    OHLCV_COLUMNS,
    DEFAULT_SOURCE_INTERVAL,
    COMMON_INTERVALS,

    # 验证和限制常量
    MIN_DATA_COMPLETENESS,
    MAX_DUPLICATE_RATE,
    DEFAULT_QUERY_LIMIT,

    # API和状态常量
    API_STATUS_HEALTHY,
    API_SUCCESS_MESSAGE,

    # 验证函数
    validate_timeframe,
    validate_exchange,
    validate_symbol,
    get_timeframe_seconds,
)

console = Console()


def demonstrate_constant_usage():
    """演示常量使用最佳实践"""

    console.print("[bold cyan]🔧 常量使用最佳实践演示[/bold cyan]")
    console.print("=" * 60)

    # 显示导入的常量
    console.print("\n📦 导入的常量:")
    console.print(f"  默认交易所: {DEFAULT_EXCHANGE}")
    console.print(f"  默认交易对: {DEFAULT_SYMBOL}")
    console.print(f"  支持的交易所: {SUPPORTED_EXCHANGES}")
    console.print(f"  测试交易对: {TEST_SYMBOLS}")
    console.print(f"  OHLCV字段: {OHLCV_COLUMNS}")
    console.print(f"  默认源周期: {DEFAULT_SOURCE_INTERVAL}")
    console.print(f"  常用周期: {COMMON_INTERVALS}")


def demonstrate_validation():
    """演示验证功能"""

    console.print("\n[bold green]✅ 验证功能演示[/bold green]")
    console.print("-" * 40)

    # 验证交易所
    try:
        validate_exchange(DEFAULT_EXCHANGE)
        console.print(f"✓ 交易所 '{DEFAULT_EXCHANGE}' 验证通过")
    except ValueError as e:
        console.print(f"✗ 交易所验证失败: {e}")

    # 验证交易对
    try:
        validate_symbol(DEFAULT_SYMBOL)
        console.print(f"✓ 交易对 '{DEFAULT_SYMBOL}' 验证通过")
    except ValueError as e:
        console.print(f"✗ 交易对验证失败: {e}")

    # 验证时间周期
    try:
        validate_timeframe(Timeframe.M1.value)
        console.print(f"✓ 时间周期 '{Timeframe.M1.value}' 验证通过")
    except ValueError as e:
        console.print(f"✗ 时间周期验证失败: {e}")

    # 验证无效时间周期
    try:
        validate_timeframe("invalid_timeframe")
        console.print("✗ 不应该到达这里")
    except ValueError as e:
        console.print(f"✓ 正确拒绝无效周期: {e}")


def demonstrate_timeframe_usage():
    """演示时间周期枚举使用"""

    console.print("\n[bold blue]⏰ 时间周期枚举使用演示[/bold blue]")
    console.print("-" * 40)

    # 创建表格显示时间周期信息
    table = Table(title="时间周期枚举信息")
    table.add_column("枚举名称", style="cyan")
    table.add_column("字符串值", style="green")
    table.add_column("秒数", justify="right", style="yellow")
    table.add_column("Pandas频率", style="magenta")

    # 显示常用时间周期
    timeframes = [Timeframe.M1, Timeframe.M5, Timeframe.M15, Timeframe.H1, Timeframe.H4, Timeframe.D1]

    for tf in timeframes:
        table.add_row(
            tf.name,
            tf.value,
            str(tf.seconds),
            tf.pandas_freq
        )

    console.print(table)

    # 演示从字符串创建枚举
    console.print("\n🔄 从字符串创建枚举:")
    test_intervals = ['1m', '5m', '1h', '1d']
    for interval in test_intervals:
        tf = Timeframe.from_string(interval)
        console.print(f"  '{interval}' -> {tf.name} ({tf.seconds}秒)")


def demonstrate_ohlcv_columns():
    """演示OHLCV字段常量使用"""

    console.print("\n[bold yellow]📊 OHLCV字段常量使用演示[/bold yellow]")
    console.print("-" * 40)

    console.print(f"OHLCV字段定义: {OHLCV_COLUMNS}")

    # 创建模拟数据帧演示字段访问
    import pandas as pd

    # 模拟K线数据
    sample_data = pd.DataFrame({
        OHLCV_COLUMNS[0]: [1640995200000, 1640995260000],  # timestamp
        OHLCV_COLUMNS[1]: [47000.0, 47100.0],               # open
        OHLCV_COLUMNS[2]: [47500.0, 47200.0],               # high
        OHLCV_COLUMNS[3]: [46800.0, 46900.0],               # low
        OHLCV_COLUMNS[4]: [47200.0, 47050.0],               # close
        OHLCV_COLUMNS[5]: [1250.5, 980.2],                  # volume
    })

    console.print("\n📈 模拟K线数据（使用常量访问字段）:")
    console.print(sample_data)

    # 演示安全字段访问
    console.print("\n🔍 安全字段访问示例:")
    for idx, row in sample_data.iterrows():
        timestamp = row[OHLCV_COLUMNS[0]]
        open_price = row[OHLCV_COLUMNS[1]]
        close_price = row[OHLCV_COLUMNS[4]]
        volume = row[OHLCV_COLUMNS[5]]

        console.print(f"  时间戳: {timestamp} | 开盘: {open_price} | 收盘: {close_price} | 成交量: {volume}")


def demonstrate_best_practices():
    """演示最佳实践对比"""

    console.print("\n[bold red]🚫 最佳实践对比[/bold red]")
    console.print("-" * 40)

    console.print("\n❌ 错误的用法（不推荐）:")
    console.print("  # 硬编码字符串，容易出错")
    console.print("  exchange = 'binance'")
    console.print("  symbol = 'BTC/USDT'")
    console.print("  interval = '1m'")
    console.print("  df['open'], df['high'], df['close']")

    console.print("\n✅ 正确的用法（推荐）:")
    console.print("  # 使用全局常量，类型安全")
    console.print("  from utils.constants import DEFAULT_EXCHANGE, DEFAULT_SYMBOL, Timeframe, OHLCV_COLUMNS")
    console.print("  exchange = DEFAULT_EXCHANGE")
    console.print("  symbol = DEFAULT_SYMBOL")
    console.print("  interval = Timeframe.M1.value")
    console.print("  df[OHLCV_COLUMNS[1]], df[OHLCV_COLUMNS[2]], df[OHLCV_COLUMNS[4]]")

    console.print("\n💡 优势:")
    console.print("  1. 类型安全 - 防止拼写错误")
    console.print("  2. IDE支持 - 自动补全和类型检查")
    console.print("  3. 集中管理 - 统一修改配置")
    console.print("  4. 文档化 - 常量即文档")
    console.print("  5. 验证功能 - 自动检查参数")


def demonstrate_practical_example():
    """演示实际使用示例"""

    console.print("\n[bold magenta]🛠️  实际使用示例[/bold magenta]")
    console.print("-" * 40)

    try:
        # 使用常量的实际数据获取示例
        console.print(f"🔍 尝试获取数据:")
        console.print(f"  交易所: {DEFAULT_EXCHANGE}")
        console.print(f"  交易对: {DEFAULT_SYMBOL}")
        console.print(f"  周期: {Timeframe.H1.value}")
        console.print(f"  限制: {DEFAULT_QUERY_LIMIT}")

        # 注意：这里只是演示，实际运行需要有效的数据源
        console.print("\n⚠️  注意：这只是常量使用演示，实际数据获取需要有效的数据源配置")

        console.print("\n📝 代码示例:")
        console.print("""
# 使用常量的完整示例
from kline_data.utils.constants import (
    DEFAULT_EXCHANGE, DEFAULT_SYMBOL, Timeframe,
    OHLCV_COLUMNS, validate_timeframe
)

# 验证输入
validate_timeframe(Timeframe.H1.value)

# 获取数据
with KlineClient() as client:
    df = client.get_klines_before(
        exchange=DEFAULT_EXCHANGE,
        symbol=DEFAULT_SYMBOL,
        interval=Timeframe.H1.value,
        limit=100
    )

    # 安全访问字段
    if not df.empty:
        latest_close = df[OHLCV_COLUMNS[4]].iloc[-1]
        latest_volume = df[OHLCV_COLUMNS[5]].iloc[-1]
        print(f"最新收盘价: {latest_close}")
        print(f"最新成交量: {latest_volume}")
        """)

    except Exception as e:
        console.print(f"\n💭 这是演示代码，实际运行需要配置数据源")


def main():
    """主函数"""

    console.print("[bold green]🌟 全局常量使用最佳实践完整演示[/bold green]")
    console.print("=" * 70)

    # 运行所有演示
    demonstrate_constant_usage()
    demonstrate_validation()
    demonstrate_timeframe_usage()
    demonstrate_ohlcv_columns()
    demonstrate_best_practices()
    demonstrate_practical_example()

    console.print("\n" + "=" * 70)
    console.print("[bold green]✅ 演示完成！请始终使用全局常量而非硬编码字符串。[/bold green]")
    console.print("\n📚 更多信息请参考:")
    console.print("  - utils/constants.py - 所有常量定义")
    console.print("  - docs/ - 项目文档")
    console.print("  - examples/ - 更多使用示例")


if __name__ == "__main__":
    main()