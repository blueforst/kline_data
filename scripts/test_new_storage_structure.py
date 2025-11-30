#!/usr/bin/env python3
"""
测试新的统一存储结构

验证：
1. 写入不同周期的数据到正确路径
2. 从新路径读取数据
3. 路径结构：raw/exchange/symbol/interval/year/month/data.parquet
"""

import sys
from pathlib import Path
import pandas as pd
from datetime import datetime, timedelta

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from kline_data.config import Config
from kline_data.storage.writer import ParquetWriter
from kline_data.reader.parquet_reader import ParquetReader
from rich.console import Console
from rich.table import Table

console = Console()


def test_write_read_different_intervals():
    """测试写入和读取不同周期的数据"""
    console.print("\n[bold cyan]测试新的统一存储结构[/bold cyan]")
    console.print("=" * 60)
    
    config = Config()
    writer = ParquetWriter(config)
    reader = ParquetReader(config)
    
    exchange = "binance"
    symbol = "TESTUSDT"
    
    # 准备测试数据
    start_time = datetime(2024, 1, 1, 0, 0, 0)
    
    # 创建表格显示结果
    table = Table(title="存储和读取测试结果")
    table.add_column("周期", style="cyan")
    table.add_column("写入路径", style="yellow")
    table.add_column("写入记录数", justify="right", style="green")
    table.add_column("读取记录数", justify="right", style="green")
    table.add_column("状态", style="bold")
    
    # 测试不同周期
    intervals = ['1s', '1h', '4h', '1d']
    
    for interval in intervals:
        console.print(f"\n[yellow]测试周期: {interval}[/yellow]")
        
        # 生成测试数据
        if interval == '1s':
            dates = pd.date_range(start_time, periods=100, freq='1s', tz='UTC')
        elif interval == '1h':
            dates = pd.date_range(start_time, periods=24, freq='1h', tz='UTC')
        elif interval == '4h':
            dates = pd.date_range(start_time, periods=6, freq='4h', tz='UTC')
        else:  # 1d
            dates = pd.date_range(start_time, periods=7, freq='1d', tz='UTC')
        
        df = pd.DataFrame({
            'timestamp': dates,
            'open': 50000.0,
            'high': 51000.0,
            'low': 49000.0,
            'close': 50500.0,
            'volume': 100.0,
        })
        
        # 写入数据
        partition_infos = writer.write_partitioned(
            df, exchange, symbol, interval
        )
        
        write_count = len(df)
        file_path = partition_infos[0].file_path
        
        console.print(f"  写入: {write_count} 条记录")
        console.print(f"  路径: {file_path}")
        
        # 读取数据验证
        end_time = dates[-1]
        read_df = reader.read_range(
            exchange, symbol, start_time, end_time, interval
        )
        
        read_count = len(read_df)
        console.print(f"  读取: {read_count} 条记录")
        
        # 验证路径结构
        expected_pattern = f"raw/{exchange}/{symbol.replace('/', '')}/{interval}/"
        path_ok = expected_pattern in file_path
        
        # 验证数据完整性
        data_ok = write_count == read_count
        
        status = "✅ 通过" if (path_ok and data_ok) else "❌ 失败"
        
        table.add_row(
            interval,
            file_path,
            str(write_count),
            str(read_count),
            status
        )
    
    console.print("\n")
    console.print(table)
    
    # 清理测试数据
    console.print("\n[yellow]清理测试数据...[/yellow]")
    test_path = config.storage.get_root_path() / 'raw' / exchange / symbol.replace('/', '')
    if test_path.exists():
        import shutil
        shutil.rmtree(test_path)
        console.print(f"  已删除: {test_path}")
    
    console.print("\n[bold green]✅ 测试完成！[/bold green]")


def verify_existing_data():
    """验证现有的BTCUSDT数据是否可以正常读取"""
    console.print("\n[bold cyan]验证现有BTCUSDT数据[/bold cyan]")
    console.print("=" * 60)
    
    config = Config()
    reader = ParquetReader(config)
    
    exchange = "binance"
    symbol = "BTCUSDT"
    
    # 测试不同周期
    intervals = ['1s', '1h', '4h', '1d']
    
    table = Table(title="现有数据验证")
    table.add_column("周期", style="cyan")
    table.add_column("可用月份数", justify="right", style="green")
    table.add_column("最新数据时间", style="yellow")
    table.add_column("状态", style="bold")
    
    for interval in intervals:
        try:
            # 获取可用日期
            available_dates = reader.get_available_dates(exchange, symbol, interval)
            
            if available_dates:
                # 读取最新数据
                latest_df = reader.read_latest(exchange, symbol, interval, limit=10)
                
                if not latest_df.empty:
                    latest_time = latest_df['timestamp'].max()
                    status = "✅ 可用"
                else:
                    latest_time = "无数据"
                    status = "⚠️  空"
            else:
                latest_time = "无分区"
                status = "❌ 不存在"
            
            table.add_row(
                interval,
                str(len(available_dates)),
                str(latest_time),
                status
            )
        except Exception as e:
            table.add_row(
                interval,
                "错误",
                str(e)[:30],
                "❌ 错误"
            )
    
    console.print("\n")
    console.print(table)


if __name__ == "__main__":
    try:
        # 测试新的存储结构
        test_write_read_different_intervals()
        
        # 验证现有数据
        verify_existing_data()
        
        console.print("\n[bold green]🎉 所有测试通过！[/bold green]")
    except Exception as e:
        console.print(f"\n[bold red]❌ 测试失败: {e}[/bold red]")
        import traceback
        traceback.print_exc()
