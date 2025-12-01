"""
数据下载命令模块
"""
import typer
from datetime import datetime
from typing import Optional, List
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeRemainingColumn
from rich.table import Table

from ...sdk import KlineClient
from ...utils.constants import Timeframe
from ...utils.timezone import format_time_for_display, now_utc

app = typer.Typer(help="数据下载和更新命令")
console = Console()


def _is_all(value: str) -> bool:
    return value.lower() == "all"


def _resolve_intervals(interval_option: str) -> List[str]:
    if _is_all(interval_option):
        return Timeframe.list_all()
    return [interval_option]


def _resolve_start_time_for_interval(
    client: KlineClient,
    exchange: str,
    symbol: str,
    interval: str,
    start_option: str,
    parsed_start_time: Optional[datetime],
) -> Optional[datetime]:
    if not _is_all(start_option):
        return parsed_start_time

    console.print(
        f"[cyan]正在查询交易所 [bold]{exchange}[/bold] {interval} 周期的最早可用数据时间...[/cyan]"
    )
    try:
        earliest = client.get_earliest_available_time(exchange, symbol, interval)
    except Exception as exc:
        console.print(f"[red]✗ 错误:[/red] 获取 {interval} 最早时间失败: {exc}")
        return None

    if earliest is None:
        console.print(f"[yellow]未能获取 {interval} 周期的最早时间[/yellow]")
        return None

    console.print(
        f"[green]✓[/green] {interval} 周期最早可用时间: [bold]{earliest.date()}[/bold]"
    )
    return earliest


def _run_download_with_progress(
    client: KlineClient,
    symbol: str,
    exchange: str,
    interval: str,
    start_time: datetime,
    end_time: datetime,
    force: bool,
) -> dict:
    console.print(f"\n[bold cyan]=== 下载 {interval} 数据 ===[/bold cyan]")
    console.print(f"交易对: [bold]{symbol}[/bold]")
    console.print(f"交易所: [bold]{exchange}[/bold]")
    console.print(f"时间周期: [bold]{interval}[/bold]")
    console.print(
        f"时间范围: [bold]{start_time.date()}[/bold] 到 [bold]{end_time.date()}[/bold]\n"
    )

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>4.1f}%"),
        TextColumn("•"),
        TextColumn("[cyan]{task.fields[downloaded]:,}/{task.fields[total_records]:,}[/cyan] 条"),
        console=console,
    ) as progress:
        task_id = progress.add_task(
            "下载中...", total=100, downloaded=0, total_records=0, visible=False
        )
        progress_stopped = False

        def stop_progress():
            nonlocal progress_stopped
            if progress_stopped:
                return
            progress_stopped = True
            progress.update(task_id, visible=False)
            progress.stop()

        def update_progress(percentage: float, downloaded_records: int, total_records: int):
            if progress_stopped:
                return
            if not progress.tasks[task_id].visible:
                progress.update(task_id, visible=True)
            progress.update(
                task_id,
                completed=percentage,
                downloaded=downloaded_records,
                total_records=total_records,
            )

        try:
            result = client.download(
                symbol=symbol,
                exchange=exchange,
                start_time=start_time,
                end_time=end_time,
                interval=interval,
                force=force,
                progress_callback=update_progress,
                interrupt_handler=stop_progress,
            )
        except KeyboardInterrupt:
            stop_progress()
            raise

    console.print(f"\n[green]✓[/green] {interval} 下载完成!")
    console.print(f"数据量: [bold]{result.get('count', 0):,}[/bold] 条")
    console.print(f"时间范围: {result.get('start')} 到 {result.get('end')}")
    result["interval"] = interval
    return result


def _print_summary(results: List[dict]) -> None:
    if not results:
        return

    table = Table(title="下载结果汇总")
    table.add_column("周期", style="cyan")
    table.add_column("数据量", style="green", justify="right")
    table.add_column("起始时间", style="yellow")
    table.add_column("结束时间", style="yellow")

    for res in results:
        table.add_row(
            res.get("interval", "-"),
            f"{res.get('count', 0):,}",
            format_time_for_display(res.get("start")),
            format_time_for_display(res.get("end")),
        )

    console.print("\n")
    console.print(table)


@app.command("start")
def download_data(
    symbol: str = typer.Option(..., "--symbol", "-s", help="交易对符号，如 BTC/USDT"),
    exchange: str = typer.Option("binance", "--exchange", "-e", help="交易所名称"),
    start: str = typer.Option(..., "--start", help="开始时间 (YYYY-MM-DD 或 'all' 表示从交易所最早可用时间开始)"),
    end: Optional[str] = typer.Option(None, "--end", help="结束时间 (YYYY-MM-DD)，不指定则到当前"),
    interval: str = typer.Option("1s", "--interval", "-i", help="时间周期 (1s, 1m, 5m, 15m, 30m, 1h, 4h, 1d等，或'all'表示下载所有周期)"),
    force: bool = typer.Option(False, "--force", "-f", help="强制重新下载（删除指定时间范围的现有数据）"),
):
    """
    下载K线数据（支持多种时间周期或一次性下载所有周期）
    
    示例:
        kline download start --symbol BTC/USDT --start 2024-01-01
        kline download start -s ETH/USDT -e binance --start 2024-01-01 --end 2024-01-31
        kline download start --symbol BTC/USDT --start 2024-01-01 --interval 1h  # 下载1小时数据
        kline download start -s BTC/USDT --start 2024-01-01 -i 4h  # 下载4小时数据
        kline download start --symbol BTC/USDT --start 2024-01-01 --force  # 强制重新下载
        kline download start -s BTC/USDT --start all  # 从交易所最早可用时间开始下载
        kline download start -s BTC/USDT --start all -i all  # 下载所有可用时间和周期
    """
    try:
        start_option = start.strip()
        interval_option = interval.strip()
        intervals = _resolve_intervals(interval_option)

        parsed_start_time: Optional[datetime] = None
        if not _is_all(start_option):
            try:
                parsed_start_time = datetime.strptime(start_option, "%Y-%m-%d")
            except ValueError:
                raise ValueError("开始时间格式无效，请使用 YYYY-MM-DD 或 'all'")
        
        try:
            end_time = (
                datetime.strptime(end, "%Y-%m-%d")
                if end
                else now_utc().replace(tzinfo=None)
            )
        except ValueError:
            raise ValueError("结束时间格式无效，请使用 YYYY-MM-DD")

        if len(intervals) > 1:
            console.print(f"[cyan]开始下载 {len(intervals)} 个周期的数据...[/cyan]")
        else:
            console.print("[cyan]开始下载数据...[/cyan]")

        results: List[dict] = []
        failures = []

        with KlineClient() as client:
            for current_interval in intervals:
                start_time = _resolve_start_time_for_interval(
                    client,
                    exchange,
                    symbol,
                    current_interval,
                    start_option,
                    parsed_start_time,
                )

                if start_time is None:
                    failures.append((current_interval, "未找到可用的开始时间"))
                    continue

                try:
                    result = _run_download_with_progress(
                        client,
                        symbol,
                        exchange,
                        current_interval,
                        start_time,
                        end_time,
                        force,
                    )
                    results.append(result)
                except KeyboardInterrupt:
                    raise
                except Exception as exc:
                    console.print(f"[red]✗[/red] 下载 {current_interval} 数据失败: {exc}")
                    failures.append((current_interval, str(exc)))

        if not results:
            if failures:
                console.print("[red]✗[/red] 所有周期下载失败")
            raise typer.Exit(1)

        if len(results) > 1:
            _print_summary(results)

        if failures:
            console.print("\n[yellow]⚠ 部分周期下载失败，请检查日志后重试:[/yellow]")
            for iv, reason in failures:
                console.print(f"  • {iv}: {reason}")

    except KeyboardInterrupt:
        console.print("\n已取消")
        raise typer.Exit(0)
    except ValueError as exc:
        console.print(f"[red]✗ 错误:[/red] {exc}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]✗ 错误:[/red] {e}")
        raise typer.Exit(1)


@app.command("update")
def update_data(
    symbol: str = typer.Option(..., "--symbol", "-s", help="交易对符号"),
    exchange: str = typer.Option("binance", "--exchange", "-e", help="交易所名称"),
    interval: str = typer.Option("1s", "--interval", "-i", help="时间周期 (1s, 1m, 5m, 15m, 30m, 1h, 4h, 1d等)"),
):
    """
    更新K线数据（增量下载）
    
    示例:
        kline download update --symbol BTC/USDT
        kline download update -s ETH/USDT -e binance --interval 1h
        kline download update -s BTC/USDT -i 4h
    """
    try:
        console.print(f"[cyan]更新数据...[/cyan]")
        console.print(f"交易对: [bold]{symbol}[/bold]")
        console.print(f"交易所: [bold]{exchange}[/bold]")
        console.print(f"时间周期: [bold]{interval}[/bold]")
        
        with KlineClient() as client:
            result = client.update(symbol=symbol, exchange=exchange, interval=interval)
            
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
                total_records = info.get("total_records", info.get("count", 0))
                table.add_row(
                    symbol,
                    info.get("exchange", "N/A"),
                    f"{total_records:,}",
                    format_time_for_display(info.get("start_time")),
                    format_time_for_display(info.get("end_time")),
                    format_time_for_display(info.get("last_update")),
                )
            
            console.print(table)
            
    except Exception as e:
        console.print(f"[red]✗ 错误:[/red] {e}")
        raise typer.Exit(1)


from . import task as task_commands

app.add_typer(task_commands.app, name="task", help="下载任务管理")


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
            total_records = metadata.get("total_records", metadata.get("count", 0))
            total_size = metadata.get("total_size_bytes", metadata.get("file_size"))

            table.add_row("交易所", metadata.get("exchange", "N/A"))
            table.add_row("数据量", f"{total_records:,} 条")
            table.add_row("起始时间", format_time_for_display(metadata.get("start_time")))
            table.add_row("结束时间", format_time_for_display(metadata.get("end_time")))
            table.add_row("最后更新", format_time_for_display(metadata.get("last_update")))
            if total_size is not None:
                table.add_row("总大小", f"{total_size} bytes")
            
            console.print(table)

            # 展示各周期覆盖情况
            intervals = metadata.get("intervals", {})
            if intervals:
                interval_table = Table(title="周期覆盖情况")
                interval_table.add_column("周期", style="cyan")
                interval_table.add_column("记录数", justify="right")
                interval_table.add_column("大小(bytes)", justify="right")
                interval_table.add_column("完整性", justify="right")
                interval_table.add_column("范围", style="green")

                for iv, info in intervals.items():
                    interval_table.add_row(
                        iv,
                        f"{info.get('records', 0):,}",
                        f"{info.get('size_bytes', 0):,}",
                        f"{info.get('completeness', 0):.2f}",
                        f"{format_time_for_display(info.get('start_time'))} - {format_time_for_display(info.get('end_time'))}",
                    )

                console.print(interval_table)
            
    except Exception as e:
        console.print(f"[red]✗ 错误:[/red] {e}")
        raise typer.Exit(1)
