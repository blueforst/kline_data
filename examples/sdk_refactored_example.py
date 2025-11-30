"""
重构后的SDK使用示例

展示新的模块化SDK的基本用法
"""

from datetime import datetime
from kline_data.sdk import KlineClient

def example_basic_usage():
    """基本用法示例"""
    print("=" * 60)
    print("示例1: 基本用法 - 使用统一客户端")
    print("=" * 60)
    
    # 创建客户端
    client = KlineClient()
    
    # 查询数据（自动下载缺失数据）
    print("\n获取数据...")
    df = client.get_kline(
        exchange='binance',
        symbol='BTC/USDT',
        start_time=datetime(2024, 11, 1),
        end_time=datetime(2024, 11, 2),
        interval='1h'
    )
    
    if not df.empty:
        print(f"成功获取 {len(df)} 条数据")
        print(df.head())
    else:
        print("未获取到数据")


def example_with_indicators():
    """带指标的查询示例"""
    print("\n" + "=" * 60)
    print("示例2: 带技术指标的查询")
    print("=" * 60)
    
    client = KlineClient()
    
    # 查询数据并计算指标
    print("\n获取数据并计算指标...")
    df = client.get_kline(
        exchange='binance',
        symbol='BTC/USDT',
        start_time=datetime(2024, 11, 1),
        end_time=datetime(2024, 11, 2),
        interval='1h',
        with_indicators=['MA_20', 'EMA_12', 'RSI_14']
    )
    
    if not df.empty:
        print(f"成功获取 {len(df)} 条数据（含指标）")
        print(df[['timestamp', 'close', 'MA_20', 'EMA_12', 'RSI_14']].head())
    else:
        print("未获取到数据")


def example_sub_clients():
    """子客户端独立使用示例"""
    print("\n" + "=" * 60)
    print("示例3: 使用子客户端")
    print("=" * 60)
    
    from kline_data.sdk import QueryClient, IndicatorClient
    
    # 只使用查询客户端
    query = QueryClient()
    print("\n使用QueryClient获取数据...")
    df = query.get_kline(
        exchange='binance',
        symbol='BTC/USDT',
        start_time=datetime(2024, 11, 1),
        end_time=datetime(2024, 11, 2),
        interval='1h'
    )
    
    if not df.empty:
        print(f"QueryClient: 获取 {len(df)} 条数据")
        
        # 只使用指标客户端
        indicator = IndicatorClient()
        print("\n使用IndicatorClient计算指标...")
        df_with_ind = indicator.calculate(df, ['MA_20', 'RSI_14'])
        print(f"IndicatorClient: 计算完成")
        print(df_with_ind[['timestamp', 'close', 'MA_20', 'RSI_14']].head())
    else:
        print("未获取到数据")


def example_data_feed():
    """数据流使用示例"""
    print("\n" + "=" * 60)
    print("示例4: 使用数据流（支持自动下载）")
    print("=" * 60)
    
    client = KlineClient()
    
    # 创建数据流
    print("\n创建数据流...")
    feed = client.create_data_feed(
        exchange='binance',
        symbol='BTC/USDT',
        start_time=datetime(2024, 11, 1),
        end_time=datetime(2024, 11, 2),
        interval='1h',
        chunk_size=10
    )
    
    # 迭代数据块
    print("迭代数据块:")
    total_bars = 0
    for i, chunk in enumerate(feed):
        if i >= 3:  # 只显示前3块
            print(f"... (更多数据块)")
            break
        print(f"  块 {i+1}: {len(chunk)} 条K线")
        total_bars += len(chunk)
    
    print(f"总计处理: {total_bars} 条K线")


def example_explain_strategy():
    """解释数据获取策略"""
    print("\n" + "=" * 60)
    print("示例5: 解释数据获取策略")
    print("=" * 60)
    
    client = KlineClient()
    
    # 解释策略（不实际获取数据）
    print("\n查询策略说明:")
    explanation = client.explain_strategy(
        exchange='binance',
        symbol='BTC/USDT',
        start_time=datetime(2024, 11, 1),
        end_time=datetime(2024, 11, 2),
        interval='1h'
    )
    print(explanation)


def main():
    """运行所有示例"""
    print("\n")
    print("=" * 60)
    print(" 重构后SDK使用示例")
    print("=" * 60)
    
    try:
        # 运行各个示例
        example_basic_usage()
        example_with_indicators()
        example_sub_clients()
        example_data_feed()
        example_explain_strategy()
        
        print("\n" + "=" * 60)
        print(" 所有示例运行完成！")
        print("=" * 60)
        print("\n新SDK的主要改进:")
        print("  ✅ 统一的数据获取逻辑")
        print("  ✅ 查询和数据流都支持自动下载")
        print("  ✅ 模块化设计，功能清晰")
        print("  ✅ 易于扩展和维护")
        
    except Exception as e:
        print(f"\n❌ 运行示例时出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
