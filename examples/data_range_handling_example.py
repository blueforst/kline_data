"""
数据范围处理示例
演示不同模式下的行为
"""

from datetime import datetime, timedelta
from kline_data.sdk import KlineClient


def example_default_mode():
    """示例1: 默认模式 - 仅警告"""
    print("=" * 60)
    print("示例1: 默认模式（仅返回本地数据并警告）")
    print("=" * 60)
    
    client = KlineClient()
    
    # 假设本地数据范围是过去30天
    # 我们请求过去60天的数据（会有30天缺失）
    end_time = datetime.now()
    start_time = end_time - timedelta(days=60)
    
    df = client.get_kline(
        exchange='binance',
        symbol='BTC/USDT',
        start_time=start_time,
        end_time=end_time,
        timeframe='1h'
    )
    
    if df is not None:
        print(f"\n返回数据条数: {len(df)}")
        print(f"数据范围: {df['timestamp'].min()} ~ {df['timestamp'].max()}")
        print("\n提示: 数据可能不完整，仅包含本地已有的部分")
    else:
        print("\n未找到数据")
    
    print("\n" + "=" * 60 + "\n")


def example_auto_download_mode():
    """示例2: 自动下载模式"""
    print("=" * 60)
    print("示例2: 自动下载模式（自动补全缺失数据）")
    print("=" * 60)
    
    client = KlineClient()
    
    # 请求可能部分缺失的数据
    end_time = datetime.now()
    start_time = end_time - timedelta(days=7)
    
    df = client.get_kline(
        exchange='binance',
        symbol='BTC/USDT',
        start_time=start_time,
        end_time=end_time,
        timeframe='1h',
        auto_download=True  # 自动下载缺失数据
    )
    
    if df is not None:
        print(f"\n返回数据条数: {len(df)}")
        print(f"数据范围: {df['timestamp'].min()} ~ {df['timestamp'].max()}")
        print("\n提示: 如有缺失数据，已自动从交易所下载")
    else:
        print("\n下载失败")
    
    print("\n" + "=" * 60 + "\n")


def example_strict_mode():
    """示例3: 严格模式"""
    print("=" * 60)
    print("示例3: 严格模式（数据不完整时抛出异常）")
    print("=" * 60)
    
    client = KlineClient()
    
    # 请求可能不存在的历史数据
    end_time = datetime.now()
    start_time = end_time - timedelta(days=365)
    
    try:
        df = client.get_kline(
            exchange='binance',
            symbol='BTC/USDT',
            start_time=start_time,
            end_time=end_time,
            timeframe='1d',
            strict=True  # 严格模式
        )
        
        print(f"\n成功获取数据: {len(df)} 条")
        print(f"数据范围: {df['timestamp'].min()} ~ {df['timestamp'].max()}")
        
    except ValueError as e:
        print(f"\n捕获异常: {e}")
        print("\n处理方案:")
        print("1. 先下载缺失的数据")
        print("2. 调整请求的时间范围")
        print("3. 使用 auto_download=True 模式")
        
        # 手动下载数据
        print("\n尝试手动下载数据...")
        success = client.download_data(
            exchange='binance',
            symbol='BTC/USDT',
            start_time=start_time,
            end_time=end_time
        )
        
        if success:
            print("下载成功，重新查询...")
            df = client.get_kline(
                exchange='binance',
                symbol='BTC/USDT',
                start_time=start_time,
                end_time=end_time,
                timeframe='1d',
                strict=True
            )
            print(f"成功获取数据: {len(df)} 条")
    
    print("\n" + "=" * 60 + "\n")


def example_check_before_query():
    """示例4: 查询前先检查数据范围"""
    print("=" * 60)
    print("示例4: 查询前先检查本地数据范围")
    print("=" * 60)
    
    client = KlineClient()
    
    exchange = 'binance'
    symbol = 'BTC/USDT'
    
    # 获取元数据
    metadata = client.get_metadata(exchange, symbol)
    
    if metadata:
        print(f"\n本地数据信息:")
        print(f"  交易所: {metadata['exchange']}")
        print(f"  交易对: {metadata['symbol']}")
        print(f"  开始时间: {metadata['start_time']}")
        print(f"  结束时间: {metadata['end_time']}")
        print(f"  记录数: {metadata['total_records']}")
        print(f"  文件数: {metadata['file_count']}")
        
        # 根据本地数据范围决定查询策略
        local_start = metadata['start_time']
        local_end = metadata['end_time']
        
        # 请求范围
        query_start = datetime.now() - timedelta(days=30)
        query_end = datetime.now()
        
        print(f"\n请求范围: {query_start} ~ {query_end}")
        
        if query_start >= local_start and query_end <= local_end:
            print("✅ 请求范围在本地数据范围内，可以直接查询")
            df = client.get_kline(exchange, symbol, query_start, query_end)
        elif query_start < local_start:
            print(f"⚠️ 请求开始时间早于本地数据，缺失 {(local_start - query_start).days} 天")
            print("   建议: 使用 auto_download=True 或先下载数据")
        elif query_end > local_end:
            print(f"⚠️ 请求结束时间晚于本地数据，缺失 {(query_end - local_end).days} 天")
            print("   建议: 使用 update_data() 更新到最新数据")
            
            # 更新数据
            print("\n正在更新到最新数据...")
            client.update_data(exchange, symbol)
            
            # 重新查询
            df = client.get_kline(exchange, symbol, query_start, query_end)
    else:
        print(f"\n本地无 {exchange}/{symbol} 的数据")
        print("需要先下载数据")
    
    print("\n" + "=" * 60 + "\n")


def example_real_world_backtest():
    """示例5: 实际回测场景"""
    print("=" * 60)
    print("示例5: 回测场景 - 确保数据完整性")
    print("=" * 60)
    
    client = KlineClient()
    
    # 回测参数
    exchange = 'binance'
    symbol = 'BTC/USDT'
    backtest_start = datetime(2023, 1, 1)
    backtest_end = datetime(2023, 12, 31)
    
    print(f"\n回测配置:")
    print(f"  交易所: {exchange}")
    print(f"  交易对: {symbol}")
    print(f"  回测期间: {backtest_start} ~ {backtest_end}")
    
    # 策略1: 先检查数据完整性
    print("\n策略1: 先检查数据完整性")
    integrity = client.check_data_integrity(
        exchange=exchange,
        symbol=symbol,
        start_time=backtest_start,
        end_time=backtest_end
    )
    
    print(f"  完整性: {integrity.get('is_complete', False)}")
    if not integrity.get('is_complete'):
        print(f"  缺失记录: {integrity.get('missing_count', 0)}")
        print("  需要先下载数据")
        return
    
    # 策略2: 使用严格模式
    print("\n策略2: 使用严格模式获取数据")
    try:
        df = client.get_kline(
            exchange=exchange,
            symbol=symbol,
            start_time=backtest_start,
            end_time=backtest_end,
            timeframe='1h',
            strict=True
        )
        
        print(f"  ✅ 成功获取完整数据: {len(df)} 条")
        
        # 进行回测
        print("\n开始回测...")
        print("  (这里是回测逻辑)")
        
    except ValueError as e:
        print(f"  ❌ 数据不完整: {e}")
        print("  建议先下载完整数据后再回测")
    
    print("\n" + "=" * 60 + "\n")


def example_real_world_monitoring():
    """示例6: 实时监控场景"""
    print("=" * 60)
    print("示例6: 实时监控场景 - 自动获取最新数据")
    print("=" * 60)
    
    client = KlineClient()
    
    exchange = 'binance'
    symbol = 'BTC/USDT'
    
    # 监控最近24小时的数据
    end_time = datetime.now()
    start_time = end_time - timedelta(hours=24)
    
    print(f"\n监控配置:")
    print(f"  交易所: {exchange}")
    print(f"  交易对: {symbol}")
    print(f"  时间窗口: 最近24小时")
    
    # 使用自动下载模式，确保总是获取最新数据
    df = client.get_kline(
        exchange=exchange,
        symbol=symbol,
        start_time=start_time,
        end_time=end_time,
        timeframe='5m',
        auto_download=True  # 自动下载最新数据
    )
    
    if df is not None:
        print(f"\n✅ 获取数据成功: {len(df)} 条")
        print(f"  最新价格: {df['close'].iloc[-1]}")
        print(f"  24h涨跌幅: {((df['close'].iloc[-1] / df['open'].iloc[0] - 1) * 100):.2f}%")
        print(f"  24h成交量: {df['volume'].sum():.2f}")
    else:
        print("\n❌ 获取数据失败")
    
    print("\n" + "=" * 60 + "\n")


if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("数据范围处理示例")
    print("=" * 60 + "\n")
    
    # 运行所有示例
    example_default_mode()
    example_auto_download_mode()
    example_strict_mode()
    example_check_before_query()
    example_real_world_backtest()
    example_real_world_monitoring()
    
    print("\n所有示例运行完成！")
