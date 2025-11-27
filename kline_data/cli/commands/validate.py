"""
数据验证命令模块
"""
import typer
from typing import Optional
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.progress import track
import pandas as pd

from ...sdk import KlineClient
from ...storage.validator import DataValidator
from ...storage.metadata_manager import MetadataManager
from ...config import get_config

app = typer.Typer(help="数据完整性验证命令")
console = Console()


@app.command("check")
def validate_data(
    symbol: Optional[str] = typer.Option(None, "--symbol", "-s", help="交易对符号，不指定则检查所有"),
    exchange: Optional[str] = typer.Option(None, "--exchange", "-e", help="交易所名称"),
    interval: str = typer.Option("1s", "--interval", "-i", help="检查的时间间隔"),
    show_gaps: bool = typer.Option(False, "--show-gaps", "-g", help="显示缺失数据的详细范围"),
    export: Optional[Path] = typer.Option(None, "--export", "-o", help="导出报告到CSV文件"),
    auto_repair: bool = typer.Option(False, "--auto-repair", "-r", help="自动修复发现的缺失数据"),
    max_check: bool = typer.Option(False, "--max", help="完整校验：对比实际数据与元数据，修复不一致问题"),
):
    """
    检查K线数据完整性
    
    示例:
        kline validate check --symbol BTC/USDT
        kline validate check --symbol BTC/USDT --show-gaps
        kline validate check --exchange binance
        kline validate check --export validation_report.csv
        kline validate check --symbol BTC/USDT --auto-repair  # 自动修复缺失数据
        kline validate check --symbol BTC/USDT --max  # 完整校验并修复元数据
    """
    try:
        cfg = get_config()
        metadata_mgr = MetadataManager(cfg)
        
        # 如果启用 --max 完整校验模式
        if max_check:
            _perform_max_check(metadata_mgr, symbol, exchange, interval)
            return
        
        # 获取要检查的交易对
        all_exchanges = metadata_mgr.list_exchanges()
        
        symbols_to_check = []
        for exch in all_exchanges:
            if exchange and exch != exchange:
                continue
            for sym in metadata_mgr.list_symbols(exch):
                if symbol and sym != symbol:
                    continue
                symbols_to_check.append((exch, sym))
        
        if not symbols_to_check:
            console.print("[yellow]未找到匹配的交易对数据[/yellow]")
            return
        
        console.print(f"[cyan]开始验证 {len(symbols_to_check)} 个交易对的数据完整性...[/cyan]\n")
        
        # 准备结果表格
        table = Table(title="数据完整性验证报告")
        table.add_column("交易对", style="cyan")
        table.add_column("交易所", style="green")
        table.add_column("数据量", style="yellow", justify="right")
        table.add_column("完整性", style="blue", justify="right")
        table.add_column("缺失段数", style="magenta", justify="right")
        table.add_column("状态", style="bold")
        
        validation_results = []
        
        # 遍历检查每个交易对
        with KlineClient() as client:
            for exch, sym in track(symbols_to_check, description="验证中..."):
                try:
                    # 读取原始数据
                    df = client.get_kline(
                        symbol=sym,
                        exchange=exch,
                        timeframe=interval,
                    )
                    
                    if df.empty:
                        table.add_row(sym, exch, "0", "0%", "0", "[red]无数据[/red]")
                        continue
                    
                    # 检查完整性
                    completeness, missing_ranges = DataValidator.check_completeness(df, interval)
                    
                    # 判断状态
                    if completeness >= 0.99:
                        status = "[green]✓ 优秀[/green]"
                    elif completeness >= 0.95:
                        status = "[yellow]• 良好[/yellow]"
                    else:
                        status = "[red]✗ 需修复[/red]"
                    
                    table.add_row(
                        sym,
                        exch,
                        f"{len(df):,}",
                        f"{completeness*100:.2f}%",
                        str(len(missing_ranges)),
                        status
                    )
                    
                    # 记录结果
                    validation_results.append({
                        "symbol": sym,
                        "exchange": exch,
                        "count": len(df),
                        "completeness": completeness,
                        "gaps": len(missing_ranges),
                        "missing_ranges": missing_ranges if show_gaps else None
                    })
                    
                    # 显示缺失范围详情
                    if show_gaps and missing_ranges:
                        console.print(f"\n[yellow]缺失数据详情 - {sym}:[/yellow]")
                        gap_table = Table(show_header=True)
                        gap_table.add_column("#", style="dim")
                        gap_table.add_column("起始时间", style="cyan")
                        gap_table.add_column("结束时间", style="cyan")
                        gap_table.add_column("间隔", style="red")
                        
                        for idx, gap in enumerate(missing_ranges[:10], 1):  # 只显示前10个
                            gap_table.add_row(
                                str(idx),
                                gap.start,
                                gap.end,
                                gap.gap
                            )
                        
                        console.print(gap_table)
                        if len(missing_ranges) > 10:
                            console.print(f"[dim]... 还有 {len(missing_ranges) - 10} 个缺失段[/dim]\n")
                    
                except Exception as e:
                    console.print(f"[red]验证 {sym} 时出错: {e}[/red]")
                    table.add_row(sym, exch, "N/A", "N/A", "N/A", "[red]✗ 错误[/red]")
        
        # 显示结果表格
        console.print("\n")
        console.print(table)
        
        # 统计摘要
        if validation_results:
            total_checked = len(validation_results)
            avg_completeness = sum(r['completeness'] for r in validation_results) / total_checked
            total_gaps = sum(r['gaps'] for r in validation_results)
            
            console.print(f"\n[bold cyan]验证摘要:[/bold cyan]")
            console.print(f"检查交易对: [bold]{total_checked}[/bold] 个")
            console.print(f"平均完整性: [bold]{avg_completeness*100:.2f}%[/bold]")
            console.print(f"总缺失段数: [bold]{total_gaps}[/bold] 个")
        
        # 导出报告
        if export and validation_results:
            import pandas as pd
            report_df = pd.DataFrame([
                {
                    "交易对": r["symbol"],
                    "交易所": r["exchange"],
                    "数据量": r["count"],
                    "完整性": f"{r['completeness']*100:.2f}%",
                    "缺失段数": r["gaps"]
                }
                for r in validation_results
            ])
            report_df.to_csv(export, index=False, encoding='utf-8-sig')
            console.print(f"\n[green]✓[/green] 报告已导出到: {export}")
        
        # 自动修复功能
        if auto_repair and validation_results:
            from datetime import datetime
            from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
            
            # 筛选需要修复的交易对
            symbols_to_repair = [
                (r['symbol'], r['exchange'], r['missing_ranges'])
                for r in validation_results
                if r['completeness'] < 0.99 and r['missing_ranges']
            ]
            
            if not symbols_to_repair:
                console.print("\n[green]✓ 所有数据完整性良好，无需修复[/green]")
            else:
                console.print(f"\n[cyan]开始自动修复 {len(symbols_to_repair)} 个交易对的缺失数据...[/cyan]\n")
                
                for sym, exch, missing_ranges in symbols_to_repair:
                    console.print(f"\n[yellow]修复交易对: {sym} ({exch})[/yellow]")
                    console.print(f"发现 {len(missing_ranges)} 个缺失段")
                    
                    repaired_count = 0
                    failed_count = 0
                    
                    with Progress(
                        SpinnerColumn(),
                        TextColumn("[progress.description]{task.description}"),
                        BarColumn(),
                        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                        console=console,
                    ) as progress:
                        task_id = progress.add_task(
                            f"修复中... (0/{len(missing_ranges)})",
                            total=len(missing_ranges)
                        )
                        
                        for idx, gap in enumerate(missing_ranges, 1):
                            try:
                                # 解析缺失时间范围
                                from utils.timezone import parse_datetime
                                gap_start = parse_datetime(gap.start)
                                gap_end = parse_datetime(gap.end)
                                
                                progress.update(
                                    task_id,
                                    description=f"修复中... ({idx}/{len(missing_ranges)})",
                                )
                                
                                # 使用SDK客户端下载缺失段
                                download_result = client.download(
                                    exchange=exch,
                                    symbol=sym,
                                    start_time=gap_start,
                                    end_time=gap_end,
                                    interval=interval,
                                    force=False,
                                )
                                
                                repaired_count += 1
                                progress.update(task_id, advance=1)
                                
                            except Exception as e:
                                console.print(f"[red]修复缺失段 {idx} 失败: {e}[/red]")
                                failed_count += 1
                                progress.update(task_id, advance=1)
                                continue
                    
                    console.print(f"  成功修复: [bold green]{repaired_count}[/bold green] 段")
                    if failed_count > 0:
                        console.print(f"  修复失败: [bold red]{failed_count}[/bold red] 段")
                
                console.print("\n[bold cyan]自动修复完成！[/bold cyan]")
            
    except Exception as e:
        console.print(f"[red]✗ 错误:[/red] {e}")
        raise typer.Exit(1)


def _perform_max_check(
    metadata_mgr: MetadataManager,
    symbol: Optional[str],
    exchange: Optional[str],
    interval: str
):
    """
    执行完整校验：对比实际数据与元数据，修复不一致问题
    
    Args:
        metadata_mgr: 元数据管理器
        symbol: 交易对符号
        exchange: 交易所名称
        interval: 时间周期
    """
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
    from storage.writer import ParquetWriter
    
    console.print("[bold cyan]===== 完整校验模式 (--max) =====[/bold cyan]\n")
    console.print("[yellow]说明: 此模式会完整扫描所有实际数据文件，对比元数据，并修复不一致问题[/yellow]\n")
    
    # 获取要检查的交易对
    all_exchanges = metadata_mgr.list_exchanges()
    
    symbols_to_check = []
    for exch in all_exchanges:
        if exchange and exch != exchange:
            continue
        for sym in metadata_mgr.list_symbols(exch):
            if symbol and sym != symbol:
                continue
            symbols_to_check.append((exch, sym))
    
    if not symbols_to_check:
        console.print("[yellow]未找到匹配的交易对数据[/yellow]")
        return
    
    console.print(f"[cyan]开始校验 {len(symbols_to_check)} 个交易对...[/cyan]\n")
    
    # 校验结果统计
    total_checked = 0
    total_fixed = 0
    total_errors = 0
    
    # 逐个交易对校验
    with KlineClient() as client:
        for exch, sym in symbols_to_check:
            total_checked += 1
            console.print(f"\n[bold cyan]>>> 校验交易对: {sym} ({exch})[/bold cyan]")
            
            try:
                # 1. 读取实际数据
                console.print(f"  [dim]正在读取实际数据...[/dim]")
                df = client.get_kline(
                    symbol=sym,
                    exchange=exch,
                    timeframe=interval,
                )
                
                if df.empty:
                    console.print(f"  [yellow]⚠ 无实际数据[/yellow]")
                    continue
                
                # 2. 获取元数据
                metadata = metadata_mgr.get_symbol_metadata(exch, sym)
                
                # 3. 对比实际数据范围与元数据
                actual_start_ts = int(df['timestamp'].min().timestamp() * 1000)
                actual_end_ts = int(df['timestamp'].max().timestamp() * 1000)
                actual_count = len(df)
                
                console.print(f"  [dim]实际数据: {actual_count:,} 条[/dim]")
                
                # 转换为本地时区显示
                min_ts = df['timestamp'].min()
                max_ts = df['timestamp'].max()
                if hasattr(min_ts, 'tz_localize'):
                    if min_ts.tz is None:
                        min_ts = min_ts.tz_localize('UTC')
                    min_ts = min_ts.astimezone()
                if hasattr(max_ts, 'tz_localize'):
                    if max_ts.tz is None:
                        max_ts = max_ts.tz_localize('UTC')
                    max_ts = max_ts.astimezone()
                
                console.print(f"  [dim]时间范围: {min_ts} ~ {max_ts}[/dim]")
                
                # 4. 检查元数据中的 interval ranges
                interval_data = metadata.intervals.get(interval)
                meta_needs_fix = False
                
                if not interval_data:
                    console.print(f"  [red]✗ 元数据缺失 interval '{interval}' 信息[/red]")
                    meta_needs_fix = True
                else:
                    meta_start = interval_data.start_timestamp
                    meta_end = interval_data.end_timestamp
                    
                    # 允许一定的时间误差（1个周期的步长）
                    from resampler.timeframe import get_timeframe_seconds
                    tolerance_ms = get_timeframe_seconds(interval) * 1000
                    
                    if abs(actual_start_ts - meta_start) > tolerance_ms or abs(actual_end_ts - meta_end) > tolerance_ms:
                        console.print(f"  [red]✗ 元数据时间范围不一致[/red]")
                        console.print(f"    元数据: {meta_start} ~ {meta_end}")
                        console.print(f"    实际值: {actual_start_ts} ~ {actual_end_ts}")
                        meta_needs_fix = True
                    else:
                        console.print(f"  [green]✓ 元数据时间范围一致[/green]")
                
                # 5. 检查 data_range
                if metadata.data_range:
                    if (abs(actual_start_ts - metadata.data_range.start_timestamp) > tolerance_ms or 
                        abs(actual_end_ts - metadata.data_range.end_timestamp) > tolerance_ms):
                        console.print(f"  [red]✗ 元数据 data_range 不一致[/red]")
                        meta_needs_fix = True
                    else:
                        console.print(f"  [green]✓ 元数据 data_range 一致[/green]")
                else:
                    console.print(f"  [red]✗ 元数据缺失 data_range[/red]")
                    meta_needs_fix = True
                
                # 6. 如果需要修复，重建元数据
                if meta_needs_fix:
                    console.print(f"  [yellow]>>> 开始修复元数据...[/yellow]")
                    
                    # 清空该周期的 interval ranges
                    if interval in metadata.intervals:
                        del metadata.intervals[interval]
                    
                    # 重新添加完整的时间范围
                    metadata_mgr.add_interval_range(
                        exchange=exch,
                        symbol=sym,
                        interval=interval,
                        start_timestamp=actual_start_ts,
                        end_timestamp=actual_end_ts
                    )
                    
                    # 更新 data_range
                    metadata_mgr.update_data_range(
                        exchange=exch,
                        symbol=sym,
                        start_timestamp=actual_start_ts,
                        end_timestamp=actual_end_ts
                    )
                    
                    # 检查数据完整性并更新统计信息
                    completeness, missing_ranges = DataValidator.check_completeness(df, interval)
                    data_quality = DataValidator.check_data_quality(df, interval)
                    
                    # 计算数据大小
                    writer = ParquetWriter(metadata_mgr.config)
                    data_size = 0
                    for year_month in df['timestamp'].dt.to_period('M').unique():
                        year = year_month.year
                        month = year_month.month
                        file_path = writer._get_partition_path(exch, sym, year, month, interval)
                        if file_path.exists():
                            data_size += file_path.stat().st_size
                    
                    metadata_mgr.update_statistics(
                        exchange=exch,
                        symbol=sym,
                        total_records=actual_count,
                        total_size_bytes=data_size,
                        missing_ranges=missing_ranges,
                        data_quality=data_quality
                    )
                    
                    console.print(f"  [green]✓ 元数据已修复[/green]")
                    console.print(f"    更新时间范围: {actual_start_ts} ~ {actual_end_ts}")
                    console.print(f"    更新记录数: {actual_count:,} 条")
                    console.print(f"    数据完整性: {completeness*100:.2f}%")
                    
                    total_fixed += 1
                else:
                    console.print(f"  [green]✓ 元数据正常，无需修复[/green]")
                
            except Exception as e:
                console.print(f"  [red]✗ 校验失败: {e}[/red]")
                import traceback
                console.print(f"  [dim]{traceback.format_exc()}[/dim]")
                total_errors += 1
    
    # 显示校验摘要
    console.print("\n" + "="*60)
    console.print("[bold cyan]完整校验摘要[/bold cyan]\n")
    
    summary_table = Table(show_header=False)
    summary_table.add_column("项目", style="cyan")
    summary_table.add_column("数量", style="green", justify="right")
    
    summary_table.add_row("检查交易对", f"{total_checked}")
    summary_table.add_row("修复交易对", f"[yellow]{total_fixed}[/yellow]" if total_fixed > 0 else "0")
    summary_table.add_row("错误数量", f"[red]{total_errors}[/red]" if total_errors > 0 else "0")
    
    console.print(summary_table)
    
    if total_fixed > 0:
        console.print(f"\n[bold green]✓ 完整校验完成！已修复 {total_fixed} 个交易对的元数据[/bold green]")
    else:
        console.print(f"\n[bold green]✓ 完整校验完成！所有元数据正常[/bold green]")
    
    if total_errors > 0:
        console.print(f"[yellow]⚠ 有 {total_errors} 个交易对校验出错，请检查日志[/yellow]")


@app.command("quality")
def check_quality(
    symbol: str = typer.Option(..., "--symbol", "-s", help="交易对符号"),
    exchange: str = typer.Option("binance", "--exchange", "-e", help="交易所名称"),
    interval: str = typer.Option("1s", "--interval", "-i", help="时间间隔"),
):
    """
    检查数据质量（完整性、重复率、异常值等）
    
    示例:
        kline validate quality --symbol BTC/USDT
        kline validate quality -s ETH/USDT -e binance
    """
    try:
        console.print(f"[cyan]检查数据质量...[/cyan]")
        console.print(f"交易对: [bold]{symbol}[/bold]")
        console.print(f"交易所: [bold]{exchange}[/bold]\n")
        
        with KlineClient() as client:
            # 读取数据
            df = client.get_kline(
                symbol=symbol,
                exchange=exchange,
                timeframe=interval,
            )
            
            if df.empty:
                console.print("[yellow]未找到数据[/yellow]")
                return
            
            # 检查数据质量
            quality = DataValidator.check_data_quality(df, interval)
            
            # 检测异常值
            df_with_anomalies = DataValidator.detect_anomalies(df)
            
            # 计算异常统计
            price_anomalies = df_with_anomalies.get('price_change_anomaly', pd.Series([False])).sum()
            volume_anomalies = df_with_anomalies.get('volume_anomaly', pd.Series([False])).sum()
            
            # 显示质量报告
            console.print("[bold cyan]数据质量报告[/bold cyan]\n")
            
            table = Table(show_header=False)
            table.add_column("指标", style="cyan")
            table.add_column("值", style="green")
            table.add_column("评级", style="bold")
            
            # 完整性
            comp_rating = "优秀" if quality.completeness >= 0.99 else "良好" if quality.completeness >= 0.95 else "需改进"
            comp_color = "green" if quality.completeness >= 0.99 else "yellow" if quality.completeness >= 0.95 else "red"
            table.add_row(
                "完整性",
                f"{quality.completeness*100:.2f}%",
                f"[{comp_color}]{comp_rating}[/{comp_color}]"
            )
            
            # 重复率
            dup_rating = "优秀" if quality.duplicate_rate < 0.01 else "良好" if quality.duplicate_rate < 0.05 else "需改进"
            dup_color = "green" if quality.duplicate_rate < 0.01 else "yellow" if quality.duplicate_rate < 0.05 else "red"
            table.add_row(
                "重复率",
                f"{quality.duplicate_rate*100:.2f}%",
                f"[{dup_color}]{dup_rating}[/{dup_color}]"
            )
            
            # 数据量
            table.add_row("总数据量", f"{len(df):,} 条", "")
            
            # 异常值
            anomaly_rate = (price_anomalies + volume_anomalies) / len(df) if len(df) > 0 else 0
            anom_rating = "正常" if anomaly_rate < 0.01 else "注意" if anomaly_rate < 0.05 else "异常"
            anom_color = "green" if anomaly_rate < 0.01 else "yellow" if anomaly_rate < 0.05 else "red"
            table.add_row(
                "异常数据",
                f"{price_anomalies + volume_anomalies} 条 ({anomaly_rate*100:.2f}%)",
                f"[{anom_color}]{anom_rating}[/{anom_color}]"
            )
            
            console.print(table)
            
            # 详细异常信息
            if price_anomalies > 0 or volume_anomalies > 0:
                console.print(f"\n[yellow]异常详情:[/yellow]")
                console.print(f"  价格异常: {price_anomalies} 条")
                console.print(f"  成交量异常: {volume_anomalies} 条")
            
    except Exception as e:
        console.print(f"[red]✗ 错误:[/red] {e}")
        raise typer.Exit(1)


@app.command("repair")
def repair_data(
    symbol: str = typer.Option(..., "--symbol", "-s", help="交易对符号"),
    exchange: str = typer.Option("binance", "--exchange", "-e", help="交易所名称"),
    auto: bool = typer.Option(False, "--auto", "-a", help="自动修复（重新下载缺失数据）"),
    dry_run: bool = typer.Option(False, "--dry-run", help="仅显示需要修复的内容，不执行"),
):
    """
    修复数据缺失和异常
    
    示例:
        kline validate repair --symbol BTC/USDT --dry-run
        kline validate repair --symbol BTC/USDT --auto
    """
    try:
        console.print(f"[cyan]检查并修复数据...[/cyan]")
        console.print(f"交易对: [bold]{symbol}[/bold]")
        console.print(f"交易所: [bold]{exchange}[/bold]\n")
        
        with KlineClient() as client:
            # 读取数据
            df = client.get_kline(
                symbol=symbol,
                exchange=exchange,
                timeframe="1s",
            )
            
            if df.empty:
                console.print("[yellow]未找到数据[/yellow]")
                return
            
            # 检查完整性
            completeness, missing_ranges = DataValidator.check_completeness(df, "1s")
            
            console.print(f"当前完整性: [bold]{completeness*100:.2f}%[/bold]")
            console.print(f"发现 [bold]{len(missing_ranges)}[/bold] 个缺失段\n")
            
            if not missing_ranges:
                console.print("[green]✓ 数据完整，无需修复[/green]")
                return
            
            if dry_run:
                console.print("[yellow]预览模式 - 需要修复的缺失段:[/yellow]\n")
                
                table = Table()
                table.add_column("#", style="dim")
                table.add_column("起始时间", style="cyan")
                table.add_column("结束时间", style="cyan")
                table.add_column("间隔", style="red")
                
                for idx, gap in enumerate(missing_ranges[:20], 1):
                    table.add_row(str(idx), gap.start, gap.end, gap.gap)
                
                console.print(table)
                
                if len(missing_ranges) > 20:
                    console.print(f"\n[dim]... 还有 {len(missing_ranges) - 20} 个缺失段[/dim]")
                
                console.print("\n[yellow]提示: 使用 --auto 参数执行自动修复[/yellow]")
                return
            
            if auto:
                console.print("\n[cyan]开始自动修复数据缺失...[/cyan]\n")
                
                from datetime import datetime
                from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
                
                # 统计总共需要下载的段数
                total_gaps = len(missing_ranges)
                repaired_count = 0
                failed_count = 0
                
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    BarColumn(),
                    TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                    console=console,
                ) as progress:
                    task_id = progress.add_task(
                        f"修复中... (0/{total_gaps})",
                        total=total_gaps
                    )
                    
                    for idx, gap in enumerate(missing_ranges, 1):
                        try:
                            # 解析缺失时间范围
                            from utils.timezone import parse_datetime
                            gap_start = parse_datetime(gap.start)
                            gap_end = parse_datetime(gap.end)
                            
                            progress.update(
                                task_id,
                                description=f"修复中... ({idx}/{total_gaps}) - {gap.start[:19]} ~ {gap.end[:19]}",
                            )
                            
                            # 使用SDK客户端下载缺失段
                            download_result = client.download(
                                exchange=exchange,
                                symbol=symbol,
                                start_time=gap_start,
                                end_time=gap_end,
                                interval="1s",
                                force=False,
                            )
                            
                            repaired_count += 1
                            progress.update(task_id, advance=1)
                            
                        except Exception as e:
                            console.print(f"[red]修复缺失段 {idx} 失败: {e}[/red]")
                            failed_count += 1
                            progress.update(task_id, advance=1)
                            continue
                
                # 显示修复结果
                console.print("\n[bold cyan]修复完成！[/bold cyan]\n")
                console.print(f"总缺失段数: [bold]{total_gaps}[/bold]")
                console.print(f"成功修复: [bold green]{repaired_count}[/bold green]")
                if failed_count > 0:
                    console.print(f"修复失败: [bold red]{failed_count}[/bold red]")
                
                # 重新检查完整性
                df_new = client.get_kline(
                    symbol=symbol,
                    exchange=exchange,
                    timeframe="1s",
                )
                
                if not df_new.empty:
                    new_completeness, new_missing = DataValidator.check_completeness(df_new, "1s")
                    console.print(f"\n修复后完整性: [bold green]{new_completeness*100:.2f}%[/bold green]")
                    console.print(f"剩余缺失段: [bold]{len(new_missing)}[/bold]")
            else:
                console.print("[yellow]请使用 --auto 参数启用自动修复，或 --dry-run 预览[/yellow]")
            
    except Exception as e:
        console.print(f"[red]✗ 错误:[/red] {e}")
        raise typer.Exit(1)
