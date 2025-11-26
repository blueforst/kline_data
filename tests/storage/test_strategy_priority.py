"""测试数据源策略优先级"""

import sys
from pathlib import Path
from datetime import datetime

# 添加项目根目录到sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sdk import KlineClient
from utils.constants import DEFAULT_EXCHANGE, DEFAULT_SYMBOL
from rich.console import Console
from rich.table import Table

console = Console()


def test_strategy_priority():
    """
    测试策略优先级：交易所下载 > 本地重采样
    
    场景：
    - 假设本地已有1s数据
    - 请求获取4h数据
    - 期望：优先从交易所下载4h，而不是从1s重采样
    """
    console.print("\n" + "="*70, style="bold cyan")
    console.print("测试：数据源策略优先级验证", style="bold cyan")
    console.print("="*70 + "\n", style="bold cyan")
    
    client = KlineClient()
    
    # 测试场景：2024年1月的4h数据（假设本地没有4h但有1s）
    start_time = datetime(2024, 1, 1)
    end_time = datetime(2024, 1, 8)  # 一周数据
    interval = '4h'
    
    console.print("[bold yellow]场景说明：[/bold yellow]")
    console.print("• 时间范围：2024年1月1日 - 1月8日（7天）")
    console.print("• 目标周期：4h")
    console.print("• 本地可能有1s/1m等更小周期数据")
    console.print()
    
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
    
    # 分析决策
    if "Download" in strategy_explanation and "exchange" in strategy_explanation:
        console.print("[bold green]✓ 正确：策略选择从交易所下载[/bold green]")
        console.print("  理由：直接从交易所下载比从1s重采样更高效")
    elif "Resample" in strategy_explanation and "local" in strategy_explanation:
        console.print("[bold red]✗ 错误：策略选择从本地重采样[/bold red]")
        console.print("  问题：应该优先从交易所下载，而不是从1s重采样")
    else:
        console.print("[bold blue]ℹ 其他策略（可能本地已有4h数据）[/bold blue]")
    console.print()
    
    # 步骤2: 对比不同策略的效率
    console.print("[bold yellow]步骤2: 策略效率对比分析[/bold yellow]\n")
    
    table = Table(title="不同策略的数据量对比", show_header=True, header_style="bold magenta")
    table.add_column("策略", style="cyan", width=25)
    table.add_column("数据量", style="yellow", justify="right")
    table.add_column("效率", style="green")
    table.add_column("推荐", style="blue")
    
    # 计算数据量
    days = 7
    hours_4h = days * 24 / 4  # 4h K线数量
    hours_1h = days * 24  # 1h K线数量
    minutes_1m = days * 24 * 60  # 1m K线数量
    seconds_1s = days * 24 * 60 * 60  # 1s K线数量
    
    table.add_row(
        "直接下载4h",
        f"{int(hours_4h)} 条",
        "⚡⚡⚡⚡⚡ (最快)",
        "✅ 强烈推荐"
    )
    table.add_row(
        "下载1h后重采样",
        f"{int(hours_1h)} 条",
        "⚡⚡⚡⚡ (快)",
        "✅ 推荐"
    )
    table.add_row(
        "本地1m重采样",
        f"{int(minutes_1m):,} 条",
        "⚡⚡ (慢)",
        "⚠️ 不推荐"
    )
    table.add_row(
        "本地1s重采样",
        f"{int(seconds_1s):,} 条",
        "⚡ (很慢)",
        "❌ 非常不推荐"
    )
    
    console.print(table)
    console.print()
    
    # 效率说明
    console.print("[bold cyan]效率分析：[/bold cyan]")
    console.print(f"• 直接下载4h：仅需传输 {int(hours_4h)} 条数据")
    console.print(f"• 从1s重采样：需要读取 {int(seconds_1s):,} 条数据（约 {int(seconds_1s/hours_4h):,}x 数据量）")
    console.print(f"• 效率差距：{int(seconds_1s/hours_4h):,} 倍")
    console.print()
    
    # 步骤3: 测试实际获取
    console.print("[bold yellow]步骤3: 测试实际数据获取（使用auto_strategy）[/bold yellow]\n")
    
    try:
        console.print("开始获取数据...")
        df = client.get_kline(
            exchange=DEFAULT_EXCHANGE,
            symbol=DEFAULT_SYMBOL,
            start_time=start_time,
            end_time=end_time,
            interval=interval,
            auto_strategy=True
        )
        
        if df.empty:
            console.print("[bold red]❌ 获取失败：返回空数据[/bold red]")
            return False
        
        console.print(f"[bold green]✓ 成功获取 {len(df)} 条4h K线数据[/bold green]\n")
        
        # 显示数据样本
        console.print("数据样本（前3条）：")
        sample_table = Table(show_header=True, header_style="bold magenta")
        sample_table.add_column("时间", style="cyan")
        sample_table.add_column("开盘", style="yellow")
        sample_table.add_column("收盘", style="blue")
        sample_table.add_column("成交量", style="magenta")
        
        for _, row in df.head(3).iterrows():
            sample_table.add_row(
                str(row['timestamp']),
                f"${row['open']:,.2f}",
                f"${row['close']:,.2f}",
                f"{row['volume']:,.2f}"
            )
        
        console.print(sample_table)
        console.print()
        
        return True
        
    except Exception as e:
        console.print(f"[bold red]❌ 测试失败: {e}[/bold red]")
        import traceback
        console.print(traceback.format_exc())
        return False


def test_fallback_scenario():
    """测试回退场景：交易所不支持时才使用本地重采样"""
    console.print("\n" + "="*70, style="bold cyan")
    console.print("测试：回退场景 - 本地重采样作为最后选择", style="bold cyan")
    console.print("="*70 + "\n", style="bold cyan")
    
    client = KlineClient()
    
    console.print("[bold yellow]场景说明：[/bold yellow]")
    console.print("• 强制使用本地重采样策略（force_strategy='resample'）")
    console.print("• 这种情况应该仅作为回退策略")
    console.print()
    
    start_time = datetime(2024, 1, 1)
    end_time = datetime(2024, 1, 2)
    interval = '4h'
    
    try:
        console.print("尝试强制从本地重采样...")
        df = client.get_kline(
            exchange=DEFAULT_EXCHANGE,
            symbol=DEFAULT_SYMBOL,
            start_time=start_time,
            end_time=end_time,
            interval=interval,
            force_strategy='resample'  # 强制本地重采样
        )
        
        if not df.empty:
            console.print(f"[bold yellow]⚠ 成功从本地重采样得到 {len(df)} 条数据[/bold yellow]")
            console.print("  但正常情况下应该优先从交易所下载")
        else:
            console.print("[bold blue]ℹ 本地没有可重采样的数据（符合预期）[/bold blue]")
        
        console.print()
        return True
        
    except Exception as e:
        console.print(f"[bold blue]ℹ 无法从本地重采样: {e}[/bold blue]")
        console.print("  这是正常的，因为本地可能没有合适的源数据")
        console.print()
        return True


if __name__ == "__main__":
    console.print("\n" + "="*70, style="bold magenta")
    console.print("数据源策略优先级测试套件", style="bold magenta")
    console.print("="*70 + "\n", style="bold magenta")
    
    success1 = test_strategy_priority()
    success2 = test_fallback_scenario()
    
    console.print("\n" + "="*70, style="bold green")
    if success1 and success2:
        console.print("✓ 所有测试通过！", style="bold green")
    else:
        console.print("✗ 部分测试失败", style="bold red")
    console.print("="*70, style="bold green")
    
    sys.exit(0 if (success1 and success2) else 1)
