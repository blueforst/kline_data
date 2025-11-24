"""
数据下载命令模块
"""
import typer
from datetime import datetime
from typing import Optional
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeRemainingColumn
from rich.table import Table

from sdk import KlineClient
from config import get_config
from utils.timezone import format_time_for_display, format_time_for_display, now_utc

app = typer.Typer(help="数据下载和更新命令")
console = Console()


@app.command("start")
def download_data(
    symbol: str = typer.Option(..., "--symbol", "-s", help="交易对符号，如 BTC/USDT"),
    exchange: str = typer.Option("binance", "--exchange", "-e", help="交易所名称"),
    start: str = typer.Option(..., "--start", help="开始时间 (YYYY-MM-DD 或 'all' 表示从交易所最早可用时间开始)"),
    end: Optional[str] = typer.Option(None, "--end", help="结束时间 (YYYY-MM-DD)，不指定则到当前"),
    force: bool = typer.Option(False, "--force", "-f", help="强制重新下载（删除指定时间范围的现有数据）"),
):
    """
    下载K线数据
    
    示例:
        kline download start --symbol BTC/USDT --start 2024-01-01
        kline download start -s ETH/USDT -e binance --start 2024-01-01 --end 2024-01-31
        kline download start --symbol BTC/USDT --start 2024-01-01 --force  # 强制重新下载
        kline download start -s BTC/USDT --start all  # 从交易所最早可用时间开始下载
    """
    try:
        # 解析开始时间
        if start.lower() == 'all':
            # 自动查找交易所的最早数据时间
            console.print(f"[cyan]正在查询交易所 [bold]{exchange}[/bold] 的最早可用数据时间...[/cyan]")
            
            from storage.downloader import DataDownloader
            config = get_config()
            
            # 创建临时下载器实例来查询最早时间
            temp_downloader = DataDownloader(exchange, symbol, config, interval='1s')
            earliest_timestamp = temp_downloader.get_earliest_timestamp()
            
            if earliest_timestamp is None:
                console.print(f"[red]✗ 错误:[/red] 无法获取交易所最早可用时间")
                raise typer.Exit(1)
            
            start_time = datetime.fromtimestamp(earliest_timestamp / 1000)
            console.print(f"[green]✓[/green] 找到最早可用时间: [bold]{start_time.date()}[/bold]")
        else:
            start_time = datetime.strptime(start, "%Y-%m-%d")
        
        end_time = datetime.strptime(end, "%Y-%m-%d") if end else now_utc().replace(tzinfo=None)
        
        console.print(f"[cyan]开始下载数据...[/cyan]")
        console.print(f"交易对: [bold]{symbol}[/bold]")
        console.print(f"交易所: [bold]{exchange}[/bold]")
        console.print(f"时间范围: [bold]{start_time.date()}[/bold] 到 [bold]{end_time.date()}[/bold]\n")
        
        # 创建客户端
        with KlineClient() as client:
            # 创建进度条（初始隐藏，等检测到缺失范围后才显示）
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>4.1f}%"),
                TextColumn("•"),
                TextColumn("[cyan]{task.fields[downloaded]:,}/{task.fields[total_records]:,}[/cyan] 条"),
                console=console,
            ) as progress:
                task_id = progress.add_task("下载中...", total=100, downloaded=0, total_records=0, visible=False)
                progress_stopped = False
                
                # 定义进度回调
                def update_progress(percentage: float, downloaded_records: int, total_records: int):
                    # 如果进度已停止，不再更新
                    if progress_stopped:
                        return
                    # 首次调用时显示进度条
                    if not progress.tasks[task_id].visible:
                        progress.update(task_id, visible=True)
                    progress.update(task_id, completed=percentage, downloaded=downloaded_records, total_records=total_records)
                
                try:
                    # 下载数据
                    result = client.download(
                        symbol=symbol,
                        exchange=exchange,
                        start_time=start_time,
                        end_time=end_time,
                        force=force,
                        progress_callback=update_progress,
                    )
                except KeyboardInterrupt:
                    # 用户中断时立即停止进度更新
                    progress_stopped = True
                    progress.stop()
                    raise
            
            # 显示结果
            console.print(f"\n[green]✓[/green] 下载完成!")
            console.print(f"数据量: [bold]{result.get('count', 0):,}[/bold] 条")
            console.print(f"时间范围: {result.get('start')} 到 {result.get('end')}")
            
    except KeyboardInterrupt:
        # KeyboardInterrupt 特殊处理，避免显示为错误
        console.print(f"\n已取消")
        raise typer.Exit(0)
    except Exception as e:
        console.print(f"[red]✗ 错误:[/red] {e}")
        raise typer.Exit(1)


@app.command("update")
def update_data(
    symbol: str = typer.Option(..., "--symbol", "-s", help="交易对符号"),
    exchange: str = typer.Option("binance", "--exchange", "-e", help="交易所名称"),
):
    """
    更新K线数据（增量下载）
    
    示例:
        kline download update --symbol BTC/USDT
        kline download update -s ETH/USDT -e binance
    """
    try:
        console.print(f"[cyan]更新数据...[/cyan]")
        console.print(f"交易对: [bold]{symbol}[/bold]")
        console.print(f"交易所: [bold]{exchange}[/bold]")
        
        with KlineClient() as client:
            result = client.update(symbol=symbol, exchange=exchange)
            
            if result.get("updated", False):
                console.print(f"[green]✓[/green] 更新完成!")
                console.print(f"新增数据: [bold]{result.get('count', 0):,}[/bold] 条")
                console.print(f"最新时间: {result.get('latest')}")
            else:
                console.print(f"[yellow]•[/yellow] 数据已是最新")
                
    except Exception as e:
        console.print(f"[red]✗ 错误:[/red] {e}")
        raise typer.Exit(1)


@app.command("list")
def list_downloads(
    exchange: Optional[str] = typer.Option(None, "--exchange", "-e", help="筛选交易所"),
    status: Optional[str] = typer.Option(None, "--status", help="筛选状态 (pending/running/completed/failed)"),
):
    """
    列出下载任务
    
    示例:
        kline download list
        kline download list --exchange binance
        kline download list --status completed
    """
    try:
        with KlineClient() as client:
            # 获取元数据
            metadata = client.get_metadata()
            
            table = Table(title="下载任务列表")
            table.add_column("交易对", style="cyan")
            table.add_column("交易所", style="green")
            table.add_column("数据量", style="yellow", justify="right")
            table.add_column("起始时间", style="blue")
            table.add_column("结束时间", style="blue")
            table.add_column("最后更新", style="magenta")
            
            for symbol, info in metadata.items():
                # 筛选
                if exchange and info.get("exchange") != exchange:
                    continue
                
                # 使用统一的时区转换函数
                table.add_row(
                    symbol,
                    info.get("exchange", "N/A"),
                    f"{info.get('count', 0):,}",
                    format_time_for_display(info.get("start_time")),
                    format_time_for_display(info.get("end_time")),
                    format_time_for_display(info.get("last_update")),
                )
            
            console.print(table)
            
    except Exception as e:
        console.print(f"[red]✗ 错误:[/red] {e}")
        raise typer.Exit(1)


@app.command("status")
def check_status(
    symbol: str = typer.Option(..., "--symbol", "-s", help="交易对符号"),
    exchange: str = typer.Option("binance", "--exchange", "-e", help="交易所名称"),
):
    """
    检查数据状态
    
    示例:
        kline download status --symbol BTC/USDT
    """
    try:
        with KlineClient() as client:
            metadata = client.get_metadata(symbol=symbol, exchange=exchange)
            
            if not metadata:
                console.print(f"[yellow]未找到数据: {symbol}[/yellow]")
                return
            
            console.print(f"\n[bold cyan]数据状态: {symbol}[/bold cyan]\n")
            
            table = Table(show_header=False)
            table.add_column("属性", style="cyan")
            table.add_column("值", style="green")
            
            # 使用统一的时区转换函数
            table.add_row("交易所", metadata.get("exchange", "N/A"))
            table.add_row("数据量", f"{metadata.get('count', 0):,} 条")
            table.add_row("起始时间", format_time_for_display(metadata.get("start_time")))
            table.add_row("结束时间", format_time_for_display(metadata.get("end_time")))
            table.add_row("最后更新", format_time_for_display(metadata.get("last_update")))
            table.add_row("文件大小", metadata.get("file_size", "N/A"))
            table.add_row("完整性", metadata.get("integrity", "N/A"))
            
            console.print(table)
            
    except Exception as e:
        console.print(f"[red]✗ 错误:[/red] {e}")
        raise typer.Exit(1)
