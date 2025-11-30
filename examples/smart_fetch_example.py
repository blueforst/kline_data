"""智能数据获取示例"""

from datetime import datetime
from kline_data.sdk import KlineClient


def example_weekly_data():
    """
    示例：获取周线数据
    
    系统会自动选择最优策略：
    1. 如果本地有周线数据 -> 直接读取
    2. 否则 -> 直接从交易所下载目标周期
    """
    client = KlineClient()
    
    print("=" * 60)
    print("场景1: 获取币安BTC/USDT从始至终的周线数据")
    print("=" * 60)
    
    # 币安上线时间约为2017年7月
    start_time = datetime(2017, 7, 1)
    end_time = datetime(2024, 1, 1)
    
    # 先查看策略决策
    strategy = client.explain_strategy(
        'binance', 'BTC/USDT',
        start_time, end_time,
        interval='1w'
    )
    print("\n策略决策：")
    print(strategy)
    
    # 实际获取数据（系统会自动选择直接从交易所下载周线数据）
    print("\n开始获取数据...")
    df = client.get_kline(
        exchange='binance',
        symbol='BTC/USDT',
        start_time=start_time,
        end_time=end_time,
        interval='1w',  # 周线
        auto_strategy=True  # 启用智能策略
    )
    
    print(f"\n获取到 {len(df)} 条周线数据")
    print(df.head())
    print(f"\n数据范围: {df['timestamp'].min()} 至 {df['timestamp'].max()}")
    
    # 数据量对比
    print("\n" + "=" * 60)
    print("数据量对比分析：")
    print("=" * 60)
    
    # 周线数据量
    weeks = (end_time - start_time).days // 7
    print(f"周线数据：约 {weeks} 条")
    
    # 如果用1s数据
    seconds = (end_time - start_time).total_seconds()
    print(f"1秒数据：约 {int(seconds):,} 条")
    print(f"节省存储：{int(seconds / weeks):,}x")


def example_strategy_comparison():
    """
    示例：不同策略对比
    """
    client = KlineClient()
    
    print("\n" + "=" * 60)
    print("场景2: 策略对比 - 获取1小时K线")
    print("=" * 60)
    
    start_time = datetime(2024, 1, 1)
    end_time = datetime(2024, 1, 7)  # 一周数据
    
    # 策略1: 自动选择（推荐）
    print("\n[策略1] 自动选择最优策略")
    df1 = client.get_kline(
        'binance', 'BTC/USDT',
        start_time, end_time,
        interval='1h',
        auto_strategy=True
    )
    print(f"获取到 {len(df1)} 条数据")
    
    # 策略2: 强制从交易所下载
    print("\n[策略2] 强制从交易所下载")
    df2 = client.get_kline(
        'binance', 'BTC/USDT',
        start_time, end_time,
        interval='1h',
        force_strategy='ccxt'
    )
    print(f"获取到 {len(df2)} 条数据")
    
    # 策略3: 强制从本地读取
    print("\n[策略3] 强制从本地读取")
    try:
        df3 = client.get_kline(
            'binance', 'BTC/USDT',
            start_time, end_time,
            interval='1h',
            force_strategy='local'
        )
        print(f"获取到 {len(df3)} 条数据")
    except Exception as e:
        print(f"本地读取失败: {e}")
        print("（通常因为本地没有完整的数据范围）")


def example_data_range_handling():
    """
    示例：超出本地数据范围的处理
    """
    client = KlineClient()
    
    print("\n" + "=" * 60)
    print("场景3: 超出本地数据范围")
    print("=" * 60)
    
    # 假设本地只有2024年1月的数据
    # 现在请求2023年全年的数据
    
    start_time = datetime(2023, 1, 1)
    end_time = datetime(2023, 12, 31)
    
    print("\n查看元数据...")
    metadata = client.get_metadata('binance', 'BTC/USDT')
    if metadata:
        print(f"本地数据范围: {metadata.get('intervals', {})}")
    
    print("\n请求2023年全年的5分钟数据...")
    strategy = client.explain_strategy(
        'binance', 'BTC/USDT',
        start_time, end_time,
        interval='5m'
    )
    print(strategy)
    
    # 系统决策：
    # 1. 检查本地是否有5分钟数据 -> 没有或不完整
    # 2. 自动转向CCXT，检查交易所是否支持5分钟数据 -> 支持
    # 3. 决定：直接从交易所下载5分钟数据
    
    print("\n系统会自动从交易所下载缺失的数据")


def example_with_indicators():
    """
    示例：获取数据并计算指标
    """
    client = KlineClient()
    
    print("\n" + "=" * 60)
    print("场景4: 获取数据并计算技术指标")
    print("=" * 60)
    
    df = client.get_kline(
        exchange='binance',
        symbol='BTC/USDT',
        start_time=datetime(2024, 1, 1),
        end_time=datetime(2024, 1, 31),
        interval='1d',
        with_indicators=['MA_20', 'EMA_12', 'RSI_14', 'BOLL_20', 'MACD']
    )
    
    print(f"\n获取到 {len(df)} 条日线数据")
    print("\n数据列：", df.columns.tolist())
    print("\n数据预览：")
    print(df[['timestamp', 'close', 'MA_20', 'EMA_12', 'RSI_14']].tail())


def example_latest_data():
    """
    示例：获取最新数据
    """
    client = KlineClient()
    
    print("\n" + "=" * 60)
    print("场景5: 获取最新的100条日K线")
    print("=" * 60)
    
    df = client.get_latest(
        exchange='binance',
        symbol='BTC/USDT',
        interval='1d',
        limit=100,
        with_indicators=['MA_20', 'RSI_14']
    )
    
    print(f"\n获取到 {len(df)} 条数据")
    if not df.empty:
        print(f"最新数据时间: {df['timestamp'].max()}")
        print(f"最新收盘价: {df['close'].iloc[-1]}")


def example_batch_download():
    """
    示例：批量下载多个周期
    """
    client = KlineClient()
    
    print("\n" + "=" * 60)
    print("场景6: 批量下载多个周期的数据")
    print("=" * 60)
    
    start_time = datetime(2024, 1, 1)
    end_time = datetime(2024, 1, 31)
    
    # 直接下载多个周期
    print("\n下载各个周期的数据...")
    intervals = ['1m', '5m', '15m', '30m', '1h', '4h', '1d']
    for interval in intervals:
        result = client.download(
            'binance', 'BTC/USDT',
            start_time, end_time,
            interval=interval
        )
        status = result.get('status') if isinstance(result, dict) else result
        print(f"  {interval}: 任务状态 {status}")
    
    print("\n提示：所有周期都可直接从CCXT获取，无需本地重采样")


def main():
    """运行所有示例"""
    print("=" * 60)
    print("智能数据获取系统 - 使用示例")
    print("=" * 60)
    
    # 注意：这些示例需要实际的数据才能运行
    # 这里只是展示系统的工作原理
    
    print("\n系统特点：")
    print("1. 自动在本地与交易所之间选择最优数据源")
    print("2. 所有周期都可以直接从CCXT下载，无需重采样")
    print("3. 自动下载缺失的数据并更新本地缓存")
    print("4. 支持强制指定策略（local / ccxt）")
    
    print("\n运行示例...")
    
    try:
        example_weekly_data()
    except Exception as e:
        print(f"示例1失败: {e}")
    
    try:
        example_strategy_comparison()
    except Exception as e:
        print(f"示例2失败: {e}")
    
    try:
        example_data_range_handling()
    except Exception as e:
        print(f"示例3失败: {e}")
    
    try:
        example_with_indicators()
    except Exception as e:
        print(f"示例4失败: {e}")
    
    try:
        example_latest_data()
    except Exception as e:
        print(f"示例5失败: {e}")
    
    try:
        example_batch_download()
    except Exception as e:
        print(f"示例6失败: {e}")


if __name__ == '__main__':
    main()
