#!/usr/bin/env python
"""
数据完整性验证示例

演示如何使用SDK验证和检查K线数据的完整性、质量（使用全局常量）
"""
from kline_data.sdk import KlineClient
from kline_data.storage.validator import DataValidator
from kline_data.storage.metadata_manager import MetadataManager
from kline_data.config import get_config
from rich.console import Console
from rich.table import Table

# 导入全局常量
from kline_data.utils.constants import (
    Timeframe,
    DEFAULT_EXCHANGE,
    DEFAULT_SYMBOL,
    SUPPORTED_EXCHANGES,
    OHLCV_COLUMNS,
    DEFAULT_SOURCE_INTERVAL,
    MIN_DATA_COMPLETENESS,
    MAX_DUPLICATE_RATE,
    VALIDATION_METHODS,
    VALIDATION_STATUS,
    validate_timeframe,
    validate_exchange,
    validate_symbol,
)

console = Console()


def example_1_check_completeness():
    """示例1: 检查数据完整性（使用全局常量）"""
    console.print("\n[bold cyan]示例1: 检查数据完整性（使用常量）[/bold cyan]")

    # 使用全局常量
    symbol = DEFAULT_SYMBOL
    timeframe = DEFAULT_SOURCE_INTERVAL  # 使用默认源周期

    # 验证常量
    validate_exchange(DEFAULT_EXCHANGE)
    validate_symbol(symbol)
    validate_timeframe(timeframe)

    console.print(f"🔍 验证配置:")
    console.print(f"  交易所: {DEFAULT_EXCHANGE}")
    console.print(f"  交易对: {symbol}")
    console.print(f"  周期: {timeframe}")
    console.print(f"  OHLCV字段: {OHLCV_COLUMNS}")
    console.print(f"  完整性阈值: {MIN_DATA_COMPLETENESS*100:.1f}%")

    with KlineClient() as client:
        console.print(f"\n📊 读取 {symbol} 的 {timeframe} 数据...")
        df = client.get_kline(
            symbol=symbol,
            exchange=DEFAULT_EXCHANGE,  # 使用常量
            timeframe=timeframe,
        )

        if df.empty:
            console.print("[yellow]未找到数据[/yellow]")
            return

        # 检查完整性
        completeness, missing_ranges = DataValidator.check_completeness(df, timeframe)

        console.print(f"\n📈 数据量: [bold]{len(df):,}[/bold] 条")
        console.print(f"✅ 完整性: [bold]{completeness*100:.2f}%[/bold]")
        if completeness >= MIN_DATA_COMPLETENESS:
            console.print(f"[green]✓ 通过完整性检查 (≥{MIN_DATA_COMPLETENESS*100:.1f}%)[/green]")
        else:
            console.print(f"[red]✗ 未通过完整性检查 (<{MIN_DATA_COMPLETENESS*100:.1f}%)[/red]")

        console.print(f"⚠️  缺失段数: [bold]{len(missing_ranges)}[/bold] 个")

        # 显示前5个缺失段
        if missing_ranges:
            console.print("\n[yellow]前5个缺失数据段:[/yellow]")
            table = Table()
            table.add_column("#", style="dim")
            table.add_column("起始时间", style="cyan")
            table.add_column("结束时间", style="cyan")
            table.add_column("间隔", style="red")

            for idx, gap in enumerate(missing_ranges[:5], 1):
                table.add_row(
                    str(idx),
                    str(gap.start),
                    str(gap.end),
                    str(gap.gap)
                )

            console.print(table)


def example_2_check_quality():
    """示例2: 检查数据质量"""
    console.print("\n[bold cyan]示例2: 检查数据质量[/bold cyan]")
    
    with KlineClient() as client:
        symbol = "BTC/USDT"
        
        console.print(f"读取 {symbol} 数据...")
        df = client.get_kline(
            symbol=symbol,
            exchange="binance",
            timeframe="1s",
        )
        
        if df.empty:
            console.print("[yellow]未找到数据[/yellow]")
            return
        
        # 检查数据质量
        quality = DataValidator.check_data_quality(df, "1s")
        
        # 检测异常值
        df_with_anomalies = DataValidator.detect_anomalies(df)
        
        # 计算异常统计
        price_anomalies = df_with_anomalies.get('price_change_anomaly', [False]).sum()
        volume_anomalies = df_with_anomalies.get('volume_anomaly', [False]).sum()
        
        # 显示质量报告
        table = Table(title="数据质量报告")
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


def example_3_batch_validate():
    """示例3: 批量验证多个交易对"""
    console.print("\n[bold cyan]示例3: 批量验证多个交易对[/bold cyan]")
    
    cfg = get_config()
    metadata_mgr = MetadataManager(cfg.storage.metadata_path)
    
    # 获取所有交易对
    all_metadata = metadata_mgr.list_all()
    
    console.print(f"找到 {len(all_metadata)} 个交易对\n")
    
    # 准备结果表格
    table = Table(title="批量验证报告")
    table.add_column("交易对", style="cyan")
    table.add_column("交易所", style="green")
    table.add_column("数据量", style="yellow", justify="right")
    table.add_column("完整性", style="blue", justify="right")
    table.add_column("状态", style="bold")
    
    with KlineClient() as client:
        for meta in all_metadata[:5]:  # 只验证前5个作为示例
            try:
                df = client.get_kline(
                    symbol=meta.symbol,
                    exchange=meta.exchange,
                    timeframe="1s",
                )
                
                if df.empty:
                    table.add_row(meta.symbol, meta.exchange, "0", "0%", "[red]无数据[/red]")
                    continue
                
                # 检查完整性
                completeness, _ = DataValidator.check_completeness(df, "1s")
                
                # 判断状态
                if completeness >= 0.99:
                    status = "[green]✓ 优秀[/green]"
                elif completeness >= 0.95:
                    status = "[yellow]• 良好[/yellow]"
                else:
                    status = "[red]✗ 需修复[/red]"
                
                table.add_row(
                    meta.symbol,
                    meta.exchange,
                    f"{len(df):,}",
                    f"{completeness*100:.2f}%",
                    status
                )
                
            except Exception as e:
                console.print(f"[red]验证 {meta.symbol} 时出错: {e}[/red]")
    
    console.print(table)


def example_4_export_validation_report():
    """示例4: 导出验证报告"""
    console.print("\n[bold cyan]示例4: 导出验证报告[/bold cyan]")
    
    import pandas as pd
    from datetime import datetime
    
    cfg = get_config()
    metadata_mgr = MetadataManager(cfg.storage.metadata_path)
    all_metadata = metadata_mgr.list_all()
    
    validation_results = []
    
    with KlineClient() as client:
        for meta in all_metadata[:3]:  # 只验证前3个作为示例
            try:
                df = client.get_kline(
                    symbol=meta.symbol,
                    exchange=meta.exchange,
                    timeframe="1s",
                )
                
                if df.empty:
                    continue
                
                # 检查完整性
                completeness, missing_ranges = DataValidator.check_completeness(df, "1s")
                
                # 检查质量
                quality = DataValidator.check_data_quality(df, "1s")
                
                validation_results.append({
                    "交易对": meta.symbol,
                    "交易所": meta.exchange,
                    "数据量": len(df),
                    "完整性": f"{completeness*100:.2f}%",
                    "重复率": f"{quality.duplicate_rate*100:.2f}%",
                    "缺失段数": len(missing_ranges),
                    "验证时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
                
            except Exception as e:
                console.print(f"[red]验证 {meta.symbol} 时出错: {e}[/red]")
    
    if validation_results:
        # 导出到CSV
        report_df = pd.DataFrame(validation_results)
        output_file = f"validation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        report_df.to_csv(output_file, index=False, encoding='utf-8-sig')
        console.print(f"\n[green]✓ 验证报告已导出到: {output_file}[/green]")
        console.print("\n报告预览:")
        console.print(report_df.to_string(index=False))


def main():
    """主函数"""
    console.print("[bold green]K线数据完整性验证示例[/bold green]")
    console.print("=" * 60)
    
    try:
        # 运行所有示例
        example_1_check_completeness()
        example_2_check_quality()
        example_3_batch_validate()
        example_4_export_validation_report()
        
        console.print("\n[bold green]✓ 所有示例运行完成！[/bold green]")
        
    except Exception as e:
        console.print(f"\n[red]✗ 错误: {e}[/red]")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
