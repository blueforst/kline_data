"""示例：使用get_klines_before获取指定时间前的K线数据"""

from datetime import datetime
from sdk import KlineClient
from utils.timezone import to_utc, format_datetime
from rich.console import Console
from rich.table import Table

console = Console()


def example_basic_usage():
    """基本用法：获取指定日期前的K线"""
    console.print("\n[bold blue]示例1: 获取2024年1月1日前100条日线[/bold blue]")
    
    with KlineClient() as client:
        # 获取2024年1月1日前100条日线数据
        df = client.get_klines_before(
            exchange='binance',
            symbol='BTC/USDT',
            before_time=datetime(2024, 1, 1),
            interval='1d',
            limit=100
        )
        
        if not df.empty:
            console.print(f"获取到 {len(df)} 条K线数据")
            console.print(f"时间范围: {df['timestamp'].min()} 到 {df['timestamp'].max()}")
            console.print("\n前5条数据:")
            console.print(df.head())
            console.print("\n后5条数据:")
            console.print(df.tail())
        else:
            console.print("[yellow]未获取到数据[/yellow]")


def example_with_timezone():
    """使用timezone处理UTC时间"""
    console.print("\n[bold blue]示例2: 使用UTC时间获取小时线[/bold blue]")
    
    with KlineClient() as client:
        # 指定UTC时间：2024年6月15日 12:00:00 UTC
        before_time = to_utc(datetime(2024, 6, 15, 12, 0, 0))
        
        console.print(f"截止时间: {format_datetime(before_time, for_display=True)}")
        
        # 获取前50条小时线
        df = client.get_klines_before(
            exchange='binance',
            symbol='BTC/USDT',
            before_time=before_time,
            interval='1h',
            limit=50
        )
        
        if not df.empty:
            console.print(f"获取到 {len(df)} 条K线数据")
            
            # 显示时间范围
            from utils.timezone import timestamp_to_datetime
            start_dt = timestamp_to_datetime(df['timestamp'].min())
            end_dt = timestamp_to_datetime(df['timestamp'].max())
            
            console.print(f"开始时间: {format_datetime(start_dt, for_display=True)}")
            console.print(f"结束时间: {format_datetime(end_dt, for_display=True)}")
            
            # 创建展示表格
            table = Table(title="最后10条K线数据")
            table.add_column("时间", style="cyan")
            table.add_column("开盘", justify="right", style="green")
            table.add_column("最高", justify="right", style="green")
            table.add_column("最低", justify="right", style="red")
            table.add_column("收盘", justify="right", style="yellow")
            table.add_column("成交量", justify="right", style="magenta")
            
            for _, row in df.tail(10).iterrows():
                dt = timestamp_to_datetime(row['timestamp'])
                table.add_row(
                    format_datetime(dt, for_display=True),
                    f"{row['open']:.2f}",
                    f"{row['high']:.2f}",
                    f"{row['low']:.2f}",
                    f"{row['close']:.2f}",
                    f"{row['volume']:.2f}"
                )
            
            console.print(table)
        else:
            console.print("[yellow]未获取到数据[/yellow]")


def example_with_indicators():
    """获取数据并计算技术指标"""
    console.print("\n[bold blue]示例3: 获取数据并计算技术指标[/bold blue]")
    
    with KlineClient() as client:
        # 获取数据并计算MA、EMA、RSI指标
        df = client.get_klines_before(
            exchange='binance',
            symbol='BTC/USDT',
            before_time=datetime(2024, 3, 1),
            interval='1d',
            limit=50,
            with_indicators=['MA_20', 'EMA_12', 'RSI_14']
        )
        
        if not df.empty:
            console.print(f"获取到 {len(df)} 条K线数据，已计算指标")
            console.print(f"数据列: {list(df.columns)}")
            
            # 显示最后5条数据的指标
            console.print("\n最后5条数据的指标:")
            indicators_df = df[['timestamp', 'close', 'MA_20', 'EMA_12', 'RSI_14']].tail()
            console.print(indicators_df)
        else:
            console.print("[yellow]未获取到数据[/yellow]")


def example_multiple_intervals():
    """获取不同周期的数据"""
    console.print("\n[bold blue]示例4: 获取不同周期的数据[/bold blue]")
    
    with KlineClient() as client:
        before_time = datetime(2024, 2, 1)
        intervals = ['5m', '15m', '1h', '4h', '1d']
        
        for interval in intervals:
            df = client.get_klines_before(
                exchange='binance',
                symbol='BTC/USDT',
                before_time=before_time,
                interval=interval,
                limit=20
            )
            
            if not df.empty:
                console.print(f"[green]✓[/green] {interval:4s} - 获取 {len(df):3d} 条数据")
            else:
                console.print(f"[red]✗[/red] {interval:4s} - 无数据")


def example_recent_data():
    """获取最近的数据（相对于当前时间）"""
    console.print("\n[bold blue]示例5: 获取当前时间前的最近数据[/bold blue]")
    
    from utils.timezone import now_utc
    
    with KlineClient() as client:
        # 获取当前时间前的100条分钟线
        current_time = now_utc()
        console.print(f"当前时间: {format_datetime(current_time, for_display=True)}")
        
        df = client.get_klines_before(
            exchange='binance',
            symbol='BTC/USDT',
            before_time=current_time,
            interval='1m',
            limit=100
        )
        
        if not df.empty:
            console.print(f"获取到 {len(df)} 条K线数据")
            
            from utils.timezone import timestamp_to_datetime
            latest_dt = timestamp_to_datetime(df['timestamp'].max())
            console.print(f"最新K线时间: {format_datetime(latest_dt, for_display=True)}")
            
            # 显示最近的价格变化
            recent = df.tail(10)
            console.print("\n最近10根K线:")
            for _, row in recent.iterrows():
                dt = timestamp_to_datetime(row['timestamp'])
                time_str = format_datetime(dt, for_display=True)
                console.print(
                    f"  {time_str} - "
                    f"O:{row['open']:.2f} H:{row['high']:.2f} "
                    f"L:{row['low']:.2f} C:{row['close']:.2f}"
                )
        else:
            console.print("[yellow]未获取到数据[/yellow]")


if __name__ == '__main__':
    console.print("[bold cyan]get_klines_before 接口使用示例[/bold cyan]")
    console.print("=" * 60)
    
    # 运行所有示例
    example_basic_usage()
    example_with_timezone()
    example_with_indicators()
    example_multiple_intervals()
    example_recent_data()
    
    console.print("\n[bold green]所有示例运行完成！[/bold green]")
