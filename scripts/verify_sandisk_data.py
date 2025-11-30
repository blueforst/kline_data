#!/usr/bin/env python3
"""
验证 SanDisk 磁盘上的实际数据

直接读取 /Volumes/sandisk/kline_data 中的数据
"""

import sys
from pathlib import Path
import pandas as pd
from datetime import datetime

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from kline_data.config import Config
from kline_data.reader.parquet_reader import ParquetReader
from rich.console import Console
from rich.table import Table

console = Console()


def verify_sandisk_data():
    """验证SanDisk上的BTCUSDT数据"""
    console.print("\n[bold cyan]验证 SanDisk 实际数据[/bold cyan]")
    console.print("=" * 80)
    
    # 临时创建配置，指向SanDisk路径
    config = Config()
    # 覆盖root_path
    original_root = config.storage.root_path
    config.storage.root_path = "/Volumes/sandisk/kline_data"
    
    reader = ParquetReader(config)
    
    exchange = "binance"
    symbol = "BTCUSDT"
    
    console.print(f"数据根目录: {config.storage.root_path}")
    console.print(f"交易所: {exchange}")
    console.print(f"交易对: {symbol}\n")
    
    # 测试不同周期
    intervals = ['1s', '1h', '4h', '1d']
    
    table = Table(title="SanDisk 数据验证")
    table.add_column("周期", style="cyan")
    table.add_column("可用年份", style="yellow")
    table.add_column("月份数", justify="right", style="green")
    table.add_column("最新10条数据", style="yellow")
    table.add_column("状态", style="bold")
    
    for interval in intervals:
        console.print(f"[yellow]检查周期: {interval}[/yellow]")
        
        try:
            # 获取可用日期
            available_dates = reader.get_available_dates(exchange, symbol, interval)
            
            if available_dates:
                # 提取年份
                years = sorted(set(d.year for d in available_dates))
                years_str = ", ".join(map(str, years))
                
                console.print(f"  可用年份: {years_str}")
                console.print(f"  总月份数: {len(available_dates)}")
                
                # 尝试读取最新的数据
                try:
                    latest_df = reader.read_latest(exchange, symbol, interval, limit=10)
                    
                    if not latest_df.empty:
                        latest_time = latest_df['timestamp'].iloc[-1]
                        first_time = latest_df['timestamp'].iloc[0]
                        data_info = f"{len(latest_df)}条 ({first_time} ~ {latest_time})"
                        status = "✅ 可用"
                        
                        console.print(f"  最新数据: {latest_time}")
                        console.print(f"  数据条数: {len(latest_df)}")
                    else:
                        data_info = "空DataFrame"
                        status = "⚠️  空"
                except Exception as e:
                    data_info = f"读取错误: {str(e)[:30]}"
                    status = "❌ 读取失败"
                    console.print(f"  [red]错误: {e}[/red]")
            else:
                years_str = "-"
                data_info = "无分区"
                status = "❌ 不存在"
                console.print(f"  [red]未找到数据分区[/red]")
            
            table.add_row(
                interval,
                years_str,
                str(len(available_dates)) if available_dates else "0",
                data_info,
                status
            )
            
            # 直接检查文件系统
            interval_path = Path(config.storage.root_path) / 'raw' / exchange / symbol / interval
            if interval_path.exists():
                year_dirs = [d.name for d in interval_path.iterdir() if d.is_dir()]
                console.print(f"  文件系统年份: {', '.join(sorted(year_dirs))}")
            else:
                console.print(f"  [red]路径不存在: {interval_path}[/red]")
            
            console.print()
            
        except Exception as e:
            console.print(f"  [bold red]异常: {e}[/bold red]")
            table.add_row(
                interval,
                "错误",
                "0",
                str(e)[:40],
                "❌ 异常"
            )
            console.print()
    
    console.print(table)
    
    # 恢复原配置
    config.storage.root_path = original_root


def check_path_structure():
    """检查路径结构"""
    console.print("\n[bold cyan]检查路径结构[/bold cyan]")
    console.print("=" * 80)
    
    base_path = Path("/Volumes/sandisk/kline_data/raw/binance/BTCUSDT")
    
    if not base_path.exists():
        console.print(f"[red]路径不存在: {base_path}[/red]")
        return
    
    console.print(f"基础路径: {base_path}")
    console.print("\n目录结构:")
    
    for interval_dir in sorted(base_path.iterdir()):
        if interval_dir.is_dir():
            console.print(f"\n  📁 {interval_dir.name}/")
            
            year_dirs = [d for d in interval_dir.iterdir() if d.is_dir()]
            for year_dir in sorted(year_dirs)[:3]:  # 只显示前3年
                console.print(f"    📅 {year_dir.name}/")
                
                month_dirs = [d for d in year_dir.iterdir() if d.is_dir()]
                for month_dir in sorted(month_dirs)[:3]:  # 只显示前3个月
                    data_file = month_dir / 'data.parquet'
                    if data_file.exists():
                        size_mb = data_file.stat().st_size / 1024 / 1024
                        console.print(f"      📄 {month_dir.name}/data.parquet ({size_mb:.2f} MB)")
                
                if len(month_dirs) > 3:
                    console.print(f"      ... 还有 {len(month_dirs) - 3} 个月")
            
            if len(year_dirs) > 3:
                console.print(f"    ... 还有 {len(year_dirs) - 3} 年")


if __name__ == "__main__":
    try:
        check_path_structure()
        verify_sandisk_data()
        
        console.print("\n[bold green]✅ 验证完成！[/bold green]")
    except Exception as e:
        console.print(f"\n[bold red]❌ 验证失败: {e}[/bold red]")
        import traceback
        traceback.print_exc()
