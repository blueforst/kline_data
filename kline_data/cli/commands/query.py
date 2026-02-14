"""
数据查询命令模块
"""
import typer
from datetime import datetime
from typing import Optional
from pathlib import Path
from rich.console import Console
from rich.table import Table
import pandas as pd

from ...sdk import KlineClient
from ...utils.constants import Timeframe, get_default_exchange
from ...utils.timezone import format_time_for_display, format_time_for_display, now_utc

app = typer.Typer(help="数据查询命令")
console = Console()


@app.command("kline")
def query_kline(
    symbol: str = typer.Option(..., "--symbol", "-s", help="交易对符号"),
    exchange: Optional[str] = typer.Option(None, "--exchange", "-e", help="交易所名称"),
    timeframe: str = typer.Option("1m", "--timeframe", "-t", help="时间周期 (1s/1m/5m/15m/1h/4h/1d等)"),
    start: Optional[str] = typer.Option(None, "--start", help="开始时间 (YYYY-MM-DD HH:MM:SS)"),
    end: Optional[str] = typer.Option(None, "--end", help="结束时间 (YYYY-MM-DD HH:MM:SS)"),
    limit: int = typer.Option(100, "--limit", "-l", help="返回数量限制"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="输出到CSV文件"),
    indicators: Optional[str] = typer.Option(None, "--indicators", "-i", help="添加指标，逗号分隔 (如: sma_20,ema_50)"),
):
    """
    查询K线数据
    
    示例:
        kline query kline --symbol BTC/USDT --timeframe 1m --limit 10
        kline query kline -s ETH/USDT -t 5m --start "2024-01-01" --end "2024-01-02"
        kline query kline -s BTC/USDT -t 1h -i sma_20,ema_50 -o output.csv
    """
    try:
        exchange = exchange or get_default_exchange()
        # 解析时间
        start_time = None
        end_time = None
        if start:
            start_time = pd.to_datetime(start)
        if end:
            end_time = pd.to_datetime(end)
        
        console.print(f"[cyan]查询K线数据...[/cyan]")
        console.print(f"交易对: [bold]{symbol}[/bold]")
        console.print(f"周期: [bold]{timeframe}[/bold]")
        
        with KlineClient() as client:
            # 获取K线数据
            df = client.get_kline(
                symbol=symbol,
                exchange=exchange,
                timeframe=timeframe,
                start_time=start_time,
                end_time=end_time,
                limit=limit,
            )
            
            # 添加指标
            if indicators:
                indicator_list = [ind.strip() for ind in indicators.split(",")]
                df = client.add_indicators(df, indicator_list)
            
            # 输出到文件
            if output:
                df.to_csv(output, index=False)
                console.print(f"[green]✓[/green] 已保存到: {output}")
            else:
                # 显示在终端
                _display_dataframe(df, limit=20)
            
            console.print(f"\n总数据量: [bold]{len(df):,}[/bold] 条")
            
    except Exception as e:
        console.print(f"[red]✗ 错误:[/red] {e}")
        raise typer.Exit(1)


@app.command("latest")
def query_latest(
    symbol: str = typer.Option(..., "--symbol", "-s", help="交易对符号"),
    exchange: Optional[str] = typer.Option(None, "--exchange", "-e", help="交易所名称"),
    timeframe: str = typer.Option("1m", "--timeframe", "-t", help="时间周期"),
    count: int = typer.Option(10, "--count", "-n", help="返回数量"),
):
    """
    查询最新K线数据
    
    示例:
        kline query latest --symbol BTC/USDT --timeframe 1m --count 5
    """
    try:
        exchange = exchange or get_default_exchange()
        console.print(f"[cyan]查询最新数据...[/cyan]")
        
        with KlineClient() as client:
            df = client.get_kline(
                symbol=symbol,
                exchange=exchange,
                timeframe=timeframe,
                limit=count,
            )
            
            # 取最后N条
            df = df.tail(count)
            
            _display_dataframe(df)
            
    except Exception as e:
        console.print(f"[red]✗ 错误:[/red] {e}")
        raise typer.Exit(1)


@app.command("range")
def query_range(
    symbol: str = typer.Option(..., "--symbol", "-s", help="交易对符号"),
    exchange: Optional[str] = typer.Option(None, "--exchange", "-e", help="交易所名称"),
):
    """
    查询数据范围
    
    示例:
        kline query range --symbol BTC/USDT
    """
    try:
        exchange = exchange or get_default_exchange()
        with KlineClient() as client:
            metadata = client.get_metadata(symbol=symbol, exchange=exchange)
            
            if not metadata:
                console.print(f"[yellow]未找到数据: {symbol}[/yellow]")
                return
            
            console.print(f"\n[bold cyan]数据范围: {symbol}[/bold cyan]\n")
            
            # 使用统一的时区转换函数
            start_time_str = format_time_for_display(metadata.get('start_time'))
            end_time_str = format_time_for_display(metadata.get('end_time'))
            total_records = metadata.get('total_records', metadata.get('count', 0))
            duration = None
            if metadata.get('start_time') and metadata.get('end_time'):
                duration = metadata.get('end_time') - metadata.get('start_time')
            
            console.print(f"起始时间: [bold]{start_time_str}[/bold]")
            console.print(f"结束时间: [bold]{end_time_str}[/bold]")
            console.print(f"数据量: [bold]{total_records:,}[/bold] 条")
            if duration:
                console.print(f"时间跨度: [bold]{duration}[/bold]")
            
    except Exception as e:
        console.print(f"[red]✗ 错误:[/red] {e}")
        raise typer.Exit(1)


@app.command("symbols")
def list_symbols(
    exchange: Optional[str] = typer.Option(None, "--exchange", "-e", help="筛选交易所"),
):
    """
    列出所有可用交易对
    
    示例:
        kline query symbols
        kline query symbols --exchange binance
    """
    try:
        with KlineClient() as client:
            metadata = client.get_metadata()
            
            table = Table(title="可用交易对")
            table.add_column("交易对", style="cyan")
            table.add_column("交易所", style="green")
            table.add_column("数据量", style="yellow", justify="right")
            table.add_column("最新时间", style="blue")
            
            for symbol, info in metadata.items():
                if exchange and info.get("exchange") != exchange:
                    continue
                
                # 使用统一的时区转换函数
                end_time_str = format_time_for_display(info.get("end_time"))
                total_records = info.get("total_records", info.get("count", 0))
                
                table.add_row(
                    symbol,
                    info.get("exchange", "N/A"),
                    f"{total_records:,}",
                    end_time_str,
                )
            
            console.print(table)
            console.print(f"\n总计: [bold]{len(metadata)}[/bold] 个交易对")
            
    except Exception as e:
        console.print(f"[red]✗ 错误:[/red] {e}")
        raise typer.Exit(1)


@app.command("stats")
def query_stats(
    symbol: str = typer.Option(..., "--symbol", "-s", help="交易对符号"),
    exchange: Optional[str] = typer.Option(None, "--exchange", "-e", help="交易所名称"),
    timeframe: str = typer.Option("1d", "--timeframe", "-t", help="时间周期"),
    period: int = typer.Option(30, "--period", "-p", help="统计周期（天）"),
):
    """
    查询统计信息
    
    示例:
        kline query stats --symbol BTC/USDT --period 30
    """
    try:
        exchange = exchange or get_default_exchange()
        console.print(f"[cyan]查询统计信息...[/cyan]")
        
        with KlineClient() as client:
            # 获取最近N天的数据 (使用UTC时间)
            end_time = now_utc().replace(tzinfo=None)  # SDK expects naive datetime
            start_time = end_time - pd.Timedelta(days=period)
            
            df = client.get_kline(
                symbol=symbol,
                exchange=exchange,
                timeframe=timeframe,
                start_time=start_time,
                end_time=end_time,
            )
            
            if df.empty:
                console.print(f"[yellow]未找到数据[/yellow]")
                return
            
            # 计算统计信息
            stats = {
                "最高价": df["high"].max(),
                "最低价": df["low"].min(),
                "平均价": df["close"].mean(),
                "价格变化": ((df["close"].iloc[-1] - df["close"].iloc[0]) / df["close"].iloc[0] * 100),
                "总成交量": df["volume"].sum(),
                "平均成交量": df["volume"].mean(),
                "波动率": df["close"].pct_change().std() * 100,
            }
            
            console.print(f"\n[bold cyan]统计信息 (最近{period}天)[/bold cyan]\n")
            
            table = Table(show_header=False)
            table.add_column("指标", style="cyan")
            table.add_column("值", style="green")
            
            table.add_row("最高价", f"{stats['最高价']:.2f}")
            table.add_row("最低价", f"{stats['最低价']:.2f}")
            table.add_row("平均价", f"{stats['平均价']:.2f}")
            table.add_row("价格变化", f"{stats['价格变化']:.2f}%")
            table.add_row("总成交量", f"{stats['总成交量']:.2f}")
            table.add_row("平均成交量", f"{stats['平均成交量']:.2f}")
            table.add_row("波动率", f"{stats['波动率']:.2f}%")
            
            console.print(table)
            
    except Exception as e:
        console.print(f"[red]✗ 错误:[/red] {e}")
        raise typer.Exit(1)


def _display_dataframe(df: pd.DataFrame, limit: int = 20):
    """在终端显示DataFrame"""
    table = Table(title="K线数据 (时间为本地时区)")
    
    # 添加列
    for col in df.columns:
        table.add_column(col, style="cyan" if col == "timestamp" else "green")
    
    # 添加行
    display_df = df.head(limit) if len(df) > limit else df
    
    # 转换 timestamp 列为本地时区
    for _, row in display_df.iterrows():
        row_values = []
        for col, val in row.items():
            if col == "timestamp" and pd.notna(val):
                # 转换 timestamp 为本地时区
                if hasattr(val, 'tz_localize'):
                    # 如果是 naive datetime，先设为 UTC
                    if val.tz is None:
                        val = val.tz_localize('UTC')
                    # 转换为本地时区
                    val = val.tz_convert(None).tz_localize('UTC').astimezone()
                    row_values.append(str(val))
                else:
                    row_values.append(str(val))
            else:
                row_values.append(str(val))
        table.add_row(*row_values)
    
    console.print(table)
    
    if len(df) > limit:
        console.print(f"\n[yellow]仅显示前{limit}条，共{len(df)}条数据[/yellow]")
