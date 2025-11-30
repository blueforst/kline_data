"""测试SDK获取4h K线数据（2020年1月）"""

import sys
from pathlib import Path
from datetime import datetime

# 添加项目根目录到sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from kline_data.sdk import KlineClient
from kline_data.utils.constants import DEFAULT_EXCHANGE, DEFAULT_SYMBOL
from rich.console import Console
from rich.table import Table

console = Console()


def test_get_4h_kline():
    """
    测试获取2020年1月份的4h K线数据
    
    预期行为：
    1. 如果本地有4h数据 -> 直接读取
    2. 如果本地有1s/1m等更小周期 -> 自动重采样
    3. 如果本地没有 -> 从交易所下载4h数据
    """
    console.print("\n" + "="*60, style="bold cyan")
    console.print("测试：SDK获取2020年1月份的4h K线数据", style="bold cyan")
    console.print("="*60 + "\n", style="bold cyan")
    
    # 初始化客户端
    client = KlineClient()
    
    # 设置时间范围
    start_time = datetime(2020, 1, 1)
    end_time = datetime(2020, 2, 1)
    interval = '4h'
    
    # 步骤1: 查看策略决策
    console.print("[bold yellow]步骤1: 查看智能策略决策[/bold yellow]\n")
    strategy_explanation = client.explain_strategy(
        exchange=DEFAULT_EXCHANGE,
        symbol=DEFAULT_SYMBOL,
        start_time=start_time,
        end_time=end_time,
        interval=interval
    )
    console.print(strategy_explanation)
    console.print()
    
    # 步骤2: 获取数据（使用智能策略）
    console.print("[bold yellow]步骤2: 使用智能策略获取数据[/bold yellow]\n")
    
    try:
        df = client.get_kline(
            exchange=DEFAULT_EXCHANGE,
            symbol=DEFAULT_SYMBOL,
            start_time=start_time,
            end_time=end_time,
            interval=interval,
            auto_strategy=True  # 启用智能策略
        )
        
        if df.empty:
            console.print("[bold red]❌ 获取失败：返回空数据[/bold red]")
            return False
        
        # 显示结果
        console.print(f"[bold green]✓ 成功获取 {len(df)} 条4h K线数据[/bold green]\n")
        
        # 数据统计
        table = Table(title="数据统计", show_header=True, header_style="bold magenta")
        table.add_column("指标", style="cyan", width=20)
        table.add_column("数值", style="green")
        
        table.add_row("记录数量", f"{len(df):,}")
        table.add_row("开始时间", str(df['timestamp'].min()))
        table.add_row("结束时间", str(df['timestamp'].max()))
        table.add_row("时间跨度", f"{(df['timestamp'].max() - df['timestamp'].min()).days} 天")
        
        # 价格统计
        table.add_row("最高价", f"${df['high'].max():,.2f}")
        table.add_row("最低价", f"${df['low'].min():,.2f}")
        table.add_row("平均收盘价", f"${df['close'].mean():,.2f}")
        table.add_row("总成交量", f"{df['volume'].sum():,.2f}")
        
        console.print(table)
        console.print()
        
        # 显示前5条数据
        console.print("[bold yellow]前5条数据样本：[/bold yellow]")
        display_table = Table(show_header=True, header_style="bold magenta")
        display_table.add_column("时间", style="cyan")
        display_table.add_column("开盘", style="yellow")
        display_table.add_column("最高", style="green")
        display_table.add_column("最低", style="red")
        display_table.add_column("收盘", style="blue")
        display_table.add_column("成交量", style="magenta")
        
        for _, row in df.head(5).iterrows():
            display_table.add_row(
                str(row['timestamp']),
                f"${row['open']:,.2f}",
                f"${row['high']:,.2f}",
                f"${row['low']:,.2f}",
                f"${row['close']:,.2f}",
                f"{row['volume']:,.2f}"
            )
        
        console.print(display_table)
        console.print()
        
        # 显示最后5条数据
        console.print("[bold yellow]最后5条数据样本：[/bold yellow]")
        display_table_end = Table(show_header=True, header_style="bold magenta")
        display_table_end.add_column("时间", style="cyan")
        display_table_end.add_column("开盘", style="yellow")
        display_table_end.add_column("最高", style="green")
        display_table_end.add_column("最低", style="red")
        display_table_end.add_column("收盘", style="blue")
        display_table_end.add_column("成交量", style="magenta")
        
        for _, row in df.tail(5).iterrows():
            display_table_end.add_row(
                str(row['timestamp']),
                f"${row['open']:,.2f}",
                f"${row['high']:,.2f}",
                f"${row['low']:,.2f}",
                f"${row['close']:,.2f}",
                f"{row['volume']:,.2f}"
            )
        
        console.print(display_table_end)
        console.print()
        
        # 验证数据完整性
        console.print("[bold yellow]步骤3: 验证数据完整性[/bold yellow]\n")
        
        # 计算预期的K线数量
        # 2020年1月有31天，每天6根4h K线（24/4=6）
        expected_bars = 31 * 6
        actual_bars = len(df)
        completeness = (actual_bars / expected_bars) * 100
        
        console.print(f"预期K线数量: {expected_bars}")
        console.print(f"实际K线数量: {actual_bars}")
        console.print(f"数据完整度: {completeness:.2f}%")
        
        if completeness >= 95:
            console.print(f"[bold green]✓ 数据完整性良好 (>= 95%)[/bold green]")
        elif completeness >= 80:
            console.print(f"[bold yellow]⚠ 数据基本完整 (>= 80%)[/bold yellow]")
        else:
            console.print(f"[bold red]❌ 数据不完整 (< 80%)[/bold red]")
        
        console.print()
        
        # 测试不同策略
        console.print("[bold yellow]步骤4: 测试不同获取策略[/bold yellow]\n")
        
        # 策略A: 强制从本地读取
        console.print("[cyan]策略A: 强制从本地读取（force_strategy='local'）[/cyan]")
        try:
            df_local = client.get_kline(
                exchange=DEFAULT_EXCHANGE,
                symbol=DEFAULT_SYMBOL,
                start_time=start_time,
                end_time=end_time,
                interval=interval,
                force_strategy='local'
            )
            console.print(f"  结果: 获取到 {len(df_local)} 条数据")
        except Exception as e:
            console.print(f"  结果: 失败 - {e}")
        console.print()
        
        # 策略B: 强制从交易所下载
        console.print("[cyan]策略B: 强制从交易所下载（force_strategy='ccxt'）[/cyan]")
        console.print("  [yellow]跳过此测试（避免重复下载）[/yellow]")
        console.print()
        
        # 总结
        console.print("="*60, style="bold green")
        console.print("测试完成！", style="bold green")
        console.print("="*60, style="bold green")
        
        return True
        
    except Exception as e:
        console.print(f"[bold red]❌ 测试失败: {e}[/bold red]")
        import traceback
        console.print(traceback.format_exc())
        return False


if __name__ == "__main__":
    success = test_get_4h_kline()
    sys.exit(0 if success else 1)
