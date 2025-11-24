"""示例：使用get_klines_before获取指定时间前的K线数据

本示例展示了如何使用全局常量来替换硬编码字符串，提高代码的维护性和类型安全性。
"""

from datetime import datetime
from sdk import KlineClient
from utils.timezone import to_utc, format_datetime
from rich.console import Console
from rich.table import Table

# 导入全局常量
from utils.constants import (
    Timeframe,
    DEFAULT_EXCHANGE,
    DEFAULT_SYMBOL,
    OHLCV_COLUMNS,
    COMMON_INTERVALS,
    get_timeframe_seconds,
    validate_timeframe,
    validate_exchange,
    validate_symbol,
)

console = Console()


def example_basic_usage():
    """基本用法：获取指定日期前的K线（使用全局常量）"""
    console.print("\n[bold blue]示例1: 获取2024年1月1日前100条日线（使用常量）[/bold blue]")

    # 验证常量
    validate_exchange(DEFAULT_EXCHANGE)
    validate_symbol(DEFAULT_SYMBOL)
    validate_timeframe(Timeframe.D1.value)

    console.print(f"📊 使用常量: {DEFAULT_EXCHANGE} | {DEFAULT_SYMBOL} | {Timeframe.D1.value}")

    with KlineClient() as client:
        # 获取2024年1月1日前100条日线数据
        df = client.get_klines_before(
            exchange=DEFAULT_EXCHANGE,    # 使用常量而非硬编码
            symbol=DEFAULT_SYMBOL,         # 使用常量而非硬编码
            before_time=datetime(2024, 1, 1),
            interval=Timeframe.D1.value,   # 使用枚举值
            limit=100
        )

        if not df.empty:
            console.print(f"✅ 获取到 {len(df)} 条K线数据")
            console.print(f"时间范围: {df[OHLCV_COLUMNS[0]].min()} 到 {df[OHLCV_COLUMNS[0]].max()}")
            console.print("\n前5条数据:")
            console.print(df.head())
            console.print("\n后5条数据:")
            console.print(df.tail())
        else:
            console.print("[yellow]未获取到数据[/yellow]")


def example_with_timezone():
    """使用timezone处理UTC时间（使用全局常量）"""
    console.print("\n[bold blue]示例2: 使用UTC时间获取小时线（使用常量）[/bold blue]")

    with KlineClient() as client:
        # 指定UTC时间：2024年6月15日 12:00:00 UTC
        before_time = to_utc(datetime(2024, 6, 15, 12, 0, 0))

        hourly_tf = Timeframe.H1
        console.print(f"🕐 截止时间: {format_datetime(before_time, for_display=True)}")
        console.print(f"📈 时间周期: {hourly_tf.value} ({hourly_tf.seconds}秒)")

        # 获取前50条小时线
        df = client.get_klines_before(
            exchange=DEFAULT_EXCHANGE,    # 使用常量
            symbol=DEFAULT_SYMBOL,         # 使用常量
            before_time=before_time,
            interval=hourly_tf.value,      # 使用枚举值
            limit=50
        )

        if not df.empty:
            console.print(f"✅ 获取到 {len(df)} 条K线数据")

            # 显示时间范围
            from utils.timezone import timestamp_to_datetime
            start_dt = timestamp_to_datetime(df[OHLCV_COLUMNS[0]].min())
            end_dt = timestamp_to_datetime(df[OHLCV_COLUMNS[0]].max())

            console.print(f"开始时间: {format_datetime(start_dt, for_display=True)}")
            console.print(f"结束时间: {format_datetime(end_dt, for_display=True)}")

            # 创建展示表格（使用常量访问字段）
            table = Table(title="最后10条K线数据")
            table.add_column("时间", style="cyan")
            table.add_column("开盘", justify="right", style="green")
            table.add_column("最高", justify="right", style="green")
            table.add_column("最低", justify="right", style="red")
            table.add_column("收盘", justify="right", style="yellow")
            table.add_column("成交量", justify="right", style="magenta")

            for _, row in df.tail(10).iterrows():
                dt = timestamp_to_datetime(row[OHLCV_COLUMNS[0]])
                table.add_row(
                    format_datetime(dt, for_display=True),
                    f"{row[OHLCV_COLUMNS[1]]:.2f}",
                    f"{row[OHLCV_COLUMNS[2]]:.2f}",
                    f"{row[OHLCV_COLUMNS[3]]:.2f}",
                    f"{row[OHLCV_COLUMNS[4]]:.2f}",
                    f"{row[OHLCV_COLUMNS[5]]:.2f}"
                )

            console.print(table)
        else:
            console.print("[yellow]未获取到数据[/yellow]")


def example_with_indicators():
    """获取数据并计算技术指标"""
    console.print("\n[bold blue]示例3: 获取数据并计算技术指标[/bold blue]")
    
    with KlineClient() as client:
        # 获取数据并计算MA、EMA、RSI指标
        df = client.get_klines_before(
            exchange='binance',
            symbol='BTC/USDT',
            before_time=datetime(2024, 3, 1),
            interval='1d',
            limit=50,
            with_indicators=['MA_20', 'EMA_12', 'RSI_14']
        )
        
        if not df.empty:
            console.print(f"获取到 {len(df)} 条K线数据，已计算指标")
            console.print(f"数据列: {list(df.columns)}")
            
            # 显示最后5条数据的指标
            console.print("\n最后5条数据的指标:")
            indicators_df = df[['timestamp', 'close', 'MA_20', 'EMA_12', 'RSI_14']].tail()
            console.print(indicators_df)
        else:
            console.print("[yellow]未获取到数据[/yellow]")


def example_multiple_intervals():
    """获取不同周期的数据（使用全局常量）"""
    console.print("\n[bold blue]示例4: 获取不同周期的数据（使用常量）[/bold blue]")

    with KlineClient() as client:
        before_time = datetime(2024, 2, 1)

        console.print(f"📊 使用常用周期常量: {COMMON_INTERVALS}")

        for interval_str in COMMON_INTERVALS:
            try:
                tf = Timeframe.from_string(interval_str)
                console.print(f"⏱️  处理 {interval_str} ({tf.seconds}秒)...")

                df = client.get_klines_before(
                    exchange=DEFAULT_EXCHANGE,    # 使用常量
                    symbol=DEFAULT_SYMBOL,         # 使用常量
                    before_time=before_time,
                    interval=tf.value,             # 使用枚举值
                    limit=20
                )

                if not df.empty:
                    console.print(f"[green]✓[/green] {tf.value:4s} - 获取 {len(df):3d} 条数据")
                else:
                    console.print(f"[red]✗[/red] {tf.value:4s} - 无数据")

            except ValueError as e:
                console.print(f"[yellow]⚠️  无效周期: {interval_str} - {e}[/yellow]")


def example_recent_data():
    """获取最近的数据（相对于当前时间，使用全局常量）"""
    console.print("\n[bold blue]示例5: 获取当前时间前的最近数据（使用常量）[/bold blue]")

    from utils.timezone import now_utc

    with KlineClient() as client:
        # 获取当前时间前的100条分钟线
        current_time = now_utc()
        console.print(f"当前时间: {format_datetime(current_time, for_display=True)}")

        # 使用分钟级时间周期
        minute_tf = Timeframe.M1
        console.print(f"时间周期: {minute_tf.value} ({minute_tf.seconds}秒)")

        df = client.get_klines_before(
            exchange=DEFAULT_EXCHANGE,    # 使用常量
            symbol=DEFAULT_SYMBOL,         # 使用常量
            before_time=current_time,
            interval=minute_tf.value,      # 使用枚举值
            limit=100
        )

        if not df.empty:
            console.print(f"✅ 获取到 {len(df)} 条K线数据")

            from utils.timezone import timestamp_to_datetime
            latest_dt = timestamp_to_datetime(df[OHLCV_COLUMNS[0]].max())
            console.print(f"最新K线时间: {format_datetime(latest_dt, for_display=True)}")

            # 显示最近的价格变化（使用常量访问字段）
            recent = df.tail(10)
            console.print("\n最近10根K线:")
            for _, row in recent.iterrows():
                dt = timestamp_to_datetime(row[OHLCV_COLUMNS[0]])
                time_str = format_datetime(dt, for_display=True)
                console.print(
                    f"  {time_str} - "
                    f"O:{row[OHLCV_COLUMNS[1]]:.2f} H:{row[OHLCV_COLUMNS[2]]:.2f} "
                    f"L:{row[OHLCV_COLUMNS[3]]:.2f} C:{row[OHLCV_COLUMNS[4]]:.2f}"
                )
        else:
            console.print("[yellow]未获取到数据[/yellow]")


if __name__ == '__main__':
    console.print("[bold cyan]get_klines_before 接口使用示例（使用全局常量）[/bold cyan]")
    console.print("=" * 60)

    # 显示使用的常量
    console.print("\n🔧 使用全局常量:")
    console.print(f"  默认交易所: {DEFAULT_EXCHANGE}")
    console.print(f"  默认交易对: {DEFAULT_SYMBOL}")
    console.print(f"  OHLCV字段: {OHLCV_COLUMNS}")
    console.print(f"  常用周期: {COMMON_INTERVALS}")

    # 运行所有示例
    example_basic_usage()
    example_with_timezone()
    example_with_indicators()
    example_multiple_intervals()
    example_recent_data()

    console.print("\n[bold green]✅ 所有示例运行完成！[/bold green]")
    console.print("\n💡 提示:")
    console.print("  - 使用全局常量可以避免硬编码错误")
    console.print("  - Timeframe枚举提供类型安全")
    console.print("  - OHLCV_COLUMNS确保字段名一致性")
    console.print("  - 验证函数帮助检查参数有效性")
