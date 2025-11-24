#!/usr/bin/env python
"""
下载进度显示示例

演示如何使用进度回调功能监控下载进度（使用全局常量）
"""

from datetime import datetime
from rich.console import Console
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
    TimeRemainingColumn,
    TimeElapsedColumn
)

from sdk import KlineClient

# 导入全局常量
from utils.constants import (
    Timeframe,
    DEFAULT_EXCHANGE,
    DEFAULT_SYMBOL,
    TEST_SYMBOLS,
    OHLCV_COLUMNS,
    validate_exchange,
    validate_symbol,
    validate_timeframe,
)

console = Console()


def example_basic_progress():
    """基础进度显示示例（使用全局常量）"""

    console.print("\n[bold cyan]示例1: 基础进度显示（使用常量）[/bold cyan]\n")

    # 验证常量
    validate_exchange(DEFAULT_EXCHANGE)
    validate_symbol(DEFAULT_SYMBOL)

    console.print(f"📊 下载配置:")
    console.print(f"  交易所: {DEFAULT_EXCHANGE}")
    console.print(f"  交易对: {DEFAULT_SYMBOL}")
    console.print(f"  时间: 2024-01-01 到 2024-01-02")

    with KlineClient() as client:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
        ) as progress:
            task_id = progress.add_task("下载中...", total=100)

            def update_progress(percentage: float, downloaded_records: int, total_records: int):
                progress.update(task_id, completed=percentage)

            result = client.download(
                symbol=DEFAULT_SYMBOL,      # 使用常量
                exchange=DEFAULT_EXCHANGE,  # 使用常量
                start_time=datetime(2024, 1, 1),
                end_time=datetime(2024, 1, 2),
                progress_callback=update_progress,
            )

        console.print(f"[green]✓[/green] 完成: {result.get('count', 0):,} 条数据")


def example_detailed_progress():
    """详细进度显示示例（含数据量和时间估算，使用全局常量）"""

    console.print("\n[bold cyan]示例2: 详细进度显示（使用常量）[/bold cyan]\n")

    # 使用测试交易对
    test_symbol = TEST_SYMBOLS[1]  # ETH/USDT
    validate_symbol(test_symbol)

    console.print(f"📈 详细下载配置:")
    console.print(f"  交易所: {DEFAULT_EXCHANGE}")
    console.print(f"  交易对: {test_symbol}")
    console.print(f"  时间: 2024-01-01 到 2024-01-03 (3天)")
    console.print(f"  OHLCV字段: {OHLCV_COLUMNS}")

    with KlineClient() as client:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TextColumn("•"),
            TextColumn("[cyan]{task.fields[records]:,}[/cyan] 条"),
            TextColumn("•"),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            task_id = progress.add_task("下载中...", total=100, records=0)

            def update_progress(percentage: float, downloaded_records: int, total_records: int):
                progress.update(task_id, completed=percentage, records=downloaded_records)

            result = client.download(
                symbol=test_symbol,          # 使用测试常量
                exchange=DEFAULT_EXCHANGE,   # 使用常量
                start_time=datetime(2024, 1, 1),
                end_time=datetime(2024, 1, 3),
                progress_callback=update_progress,
            )

        console.print(f"[green]✓[/green] 完成: {result.get('count', 0):,} 条数据")


def example_multiple_downloads():
    """多个下载任务并发显示（使用全局常量）"""

    console.print("\n[bold cyan]示例3: 多任务进度显示（使用常量）[/bold cyan]\n")

    # 使用测试交易对常量
    symbols = TEST_SYMBOLS[:3]  # 使用前3个测试交易对
    console.print(f"🚀 批量下载配置:")
    console.print(f"  交易所: {DEFAULT_EXCHANGE}")
    console.print(f"  交易对: {symbols}")
    console.print(f"  时间: 2024-01-01 到 2024-01-02")

    # 验证所有交易对
    for symbol in symbols:
        validate_symbol(symbol)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TextColumn("[cyan]{task.fields[records]:,}[/cyan] 条"),
        console=console,
    ) as progress:

        for symbol in symbols:
            with KlineClient() as client:
                task_id = progress.add_task(f"下载 {symbol}", total=100, records=0)

                def make_callback(tid):
                    def update_progress(percentage: float, downloaded_records: int, total_records: int):
                        progress.update(tid, completed=percentage, records=downloaded_records)
                    return update_progress

                result = client.download(
                    symbol=symbol,               # 使用常量
                    exchange=DEFAULT_EXCHANGE,   # 使用常量
                    start_time=datetime(2024, 1, 1),
                    end_time=datetime(2024, 1, 2),
                    progress_callback=make_callback(task_id),
                )

    console.print(f"[green]✓[/green] 所有下载任务完成")


def example_custom_callback():
    """自定义进度回调处理（使用全局常量）"""

    console.print("\n[bold cyan]示例4: 自定义进度回调（使用常量）[/bold cyan]\n")

    # 记录进度信息
    progress_log = []

    console.print(f"🎯 自定义回调配置:")
    console.print(f"  交易所: {DEFAULT_EXCHANGE}")
    console.print(f"  交易对: {DEFAULT_SYMBOL}")
    console.print(f"  时间: 2024-01-01 到 2024-01-02")
    console.print(f"  回调检查点: 每10%")

    def custom_callback(percentage: float, downloaded_records: int, total_records: int):
        progress_log.append({
            'percentage': percentage,
            'records': downloaded_records,
            'total': total_records,
            'timestamp': datetime.now()
        })

        # 每10%输出一次
        if int(percentage) % 10 == 0 and percentage > 0:
            console.print(
                f"[yellow]进度检查点:[/yellow] "
                f"{percentage:.1f}% - "
                f"{downloaded_records:,}/{total_records:,} 条记录"
            )

    with KlineClient() as client:
        result = client.download(
            symbol=DEFAULT_SYMBOL,      # 使用常量
            exchange=DEFAULT_EXCHANGE,  # 使用常量
            start_time=datetime(2024, 1, 1),
            end_time=datetime(2024, 1, 2),
            progress_callback=custom_callback,
        )

    console.print(f"\n[green]✓[/green] 完成")
    console.print(f"总数据量: {result.get('count', 0):,} 条")
    console.print(f"进度更新次数: {len(progress_log)} 次")


if __name__ == "__main__":
    # 显示常量信息
    console.print("\n🔧 下载进度示例使用的全局常量:")
    console.print(f"  默认交易所: {DEFAULT_EXCHANGE}")
    console.print(f"  默认交易对: {DEFAULT_SYMBOL}")
    console.print(f"  测试交易对: {TEST_SYMBOLS}")
    console.print(f"  OHLCV字段: {OHLCV_COLUMNS}")
    console.print()

    # 选择要运行的示例
    import sys

    examples = {
        '1': example_basic_progress,
        '2': example_detailed_progress,
        '3': example_multiple_downloads,
        '4': example_custom_callback,
    }

    if len(sys.argv) > 1 and sys.argv[1] in examples:
        examples[sys.argv[1]]()
    else:
        console.print("[bold]可用示例（使用全局常量）:[/bold]")
        console.print("  python download_with_progress.py 1  - 基础进度显示")
        console.print("  python download_with_progress.py 2  - 详细进度显示")
        console.print("  python download_with_progress.py 3  - 多任务进度显示")
        console.print("  python download_with_progress.py 4  - 自定义进度回调")
        console.print("\n[yellow]默认运行示例2...[/yellow]")
        example_detailed_progress()
