#!/usr/bin/env python
"""
下载进度显示示例

演示如何使用进度回调功能监控下载进度
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

console = Console()


def example_basic_progress():
    """基础进度显示示例"""
    
    console.print("\n[bold cyan]示例1: 基础进度显示[/bold cyan]\n")
    
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
                symbol="BTC/USDT",
                exchange="binance",
                start_time=datetime(2024, 1, 1),
                end_time=datetime(2024, 1, 2),
                progress_callback=update_progress,
            )
        
        console.print(f"[green]✓[/green] 完成: {result.get('count', 0):,} 条数据")


def example_detailed_progress():
    """详细进度显示示例（含数据量和时间估算）"""
    
    console.print("\n[bold cyan]示例2: 详细进度显示[/bold cyan]\n")
    
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
                symbol="ETH/USDT",
                exchange="binance",
                start_time=datetime(2024, 1, 1),
                end_time=datetime(2024, 1, 3),
                progress_callback=update_progress,
            )
        
        console.print(f"[green]✓[/green] 完成: {result.get('count', 0):,} 条数据")


def example_multiple_downloads():
    """多个下载任务并发显示"""
    
    console.print("\n[bold cyan]示例3: 多任务进度显示[/bold cyan]\n")
    
    symbols = ["BTC/USDT", "ETH/USDT", "BNB/USDT"]
    
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
                    symbol=symbol,
                    exchange="binance",
                    start_time=datetime(2024, 1, 1),
                    end_time=datetime(2024, 1, 2),
                    progress_callback=make_callback(task_id),
                )
    
    console.print(f"[green]✓[/green] 所有下载任务完成")


def example_custom_callback():
    """自定义进度回调处理"""
    
    console.print("\n[bold cyan]示例4: 自定义进度回调[/bold cyan]\n")
    
    # 记录进度信息
    progress_log = []
    
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
            symbol="BTC/USDT",
            exchange="binance",
            start_time=datetime(2024, 1, 1),
            end_time=datetime(2024, 1, 2),
            progress_callback=custom_callback,
        )
    
    console.print(f"\n[green]✓[/green] 完成")
    console.print(f"总数据量: {result.get('count', 0):,} 条")
    console.print(f"进度更新次数: {len(progress_log)} 次")


if __name__ == "__main__":
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
        console.print("[bold]可用示例:[/bold]")
        console.print("  python download_with_progress.py 1  - 基础进度显示")
        console.print("  python download_with_progress.py 2  - 详细进度显示")
        console.print("  python download_with_progress.py 3  - 多任务进度显示")
        console.print("  python download_with_progress.py 4  - 自定义进度回调")
        console.print("\n[yellow]默认运行示例2...[/yellow]")
        example_detailed_progress()
