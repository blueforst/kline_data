"""数据流示例 - 演示如何使用分块数据流进行回测"""

from datetime import datetime
from kline_data.sdk import ChunkedDataFeed, BacktraderDataFeed, StreamingDataFeed
from kline_data.utils.constants import Timeframe, DEFAULT_EXCHANGE, DEFAULT_SYMBOL


def example_chunked_feed():
    """示例1: 基本的分块数据流"""
    print("=" * 60)
    print("示例1: 分块数据流基本使用")
    print("=" * 60)
    
    # 创建数据流
    feed = ChunkedDataFeed(
        exchange=DEFAULT_EXCHANGE,
        symbol=DEFAULT_SYMBOL,
        start_time=datetime(2024, 1, 1),
        end_time=datetime(2024, 2, 1),
        interval=Timeframe.H1.value,
        chunk_size=100  # 每次加载100条数据
    )
    
    print(f"\n数据流创建成功: {feed}")
    
    # 方式1: 迭代数据块
    print("\n方式1: 按块迭代数据")
    chunk_count = 0
    total_rows = 0
    
    for chunk_df in feed:
        chunk_count += 1
        total_rows += len(chunk_df)
        print(f"  块 {chunk_count}: {len(chunk_df)} 行")
        
        # 显示前几行
        if chunk_count == 1:
            print("\n前5行数据:")
            print(chunk_df.head())
    
    print(f"\n总计: {chunk_count} 个块, {total_rows} 行数据")
    
    # 获取统计信息
    stats = feed.get_stats()
    print(f"\n数据流统计: {stats}")


def example_row_iteration():
    """示例2: 逐行迭代（适合backtrader）"""
    print("\n" + "=" * 60)
    print("示例2: 逐行迭代数据")
    print("=" * 60)
    
    feed = ChunkedDataFeed(
        exchange=DEFAULT_EXCHANGE,
        symbol=DEFAULT_SYMBOL,
        start_time=datetime(2024, 1, 1),
        end_time=datetime(2024, 1, 2),
        interval=Timeframe.M15.value,
        chunk_size=50
    )
    
    print("\n逐行处理K线数据:")
    row_count = 0
    
    for timestamp, open_price, high, low, close, volume in feed.iter_rows():
        row_count += 1
        if row_count <= 5 or row_count % 20 == 0:
            print(f"  第{row_count}根K线: {timestamp} | "
                  f"O:{open_price:.2f} H:{high:.2f} L:{low:.2f} "
                  f"C:{close:.2f} V:{volume:.0f}")
    
    print(f"\n总计处理 {row_count} 根K线")


def example_dict_iteration():
    """示例3: 字典格式迭代"""
    print("\n" + "=" * 60)
    print("示例3: 字典格式迭代")
    print("=" * 60)
    
    feed = ChunkedDataFeed(
        exchange=DEFAULT_EXCHANGE,
        symbol=DEFAULT_SYMBOL,
        start_time=datetime(2024, 1, 1),
        end_time=datetime(2024, 1, 2),
        interval=Timeframe.H1.value,
        chunk_size=24
    )
    
    print("\n以字典格式迭代:")
    count = 0
    
    for bar in feed.iter_dicts():
        count += 1
        if count <= 3:
            print(f"\n第{count}根K线:")
            for key, value in bar.items():
                print(f"  {key}: {value}")
    
    print(f"\n总计 {count} 根K线")


def example_backtrader_feed():
    """示例4: Backtrader数据流"""
    print("\n" + "=" * 60)
    print("示例4: Backtrader兼容数据流")
    print("=" * 60)
    
    # 创建backtrader数据流
    feed = BacktraderDataFeed(
        exchange=DEFAULT_EXCHANGE,
        symbol=DEFAULT_SYMBOL,
        start_time=datetime(2023, 1, 1),
        end_time=datetime(2023, 2, 1),
        interval=Timeframe.D1.value,
        chunk_size=100
    )
    
    print(f"\n创建Backtrader数据流: {feed}")
    
    # 转换为backtrader格式
    print("\n转换为Backtrader格式...")
    bt_df = feed.to_backtrader_format(max_rows=10)
    
    print("\nBacktrader格式数据（前10行）:")
    print(bt_df)
    
    # 获取backtrader参数
    params = feed.get_backtrader_params()
    print(f"\nBacktrader PandasData参数配置:")
    for key, value in params.items():
        print(f"  {key}: {value}")
    
    # 使用示例代码
    print("\n" + "-" * 60)
    print("Backtrader集成代码示例:")
    print("-" * 60)
    print("""
import backtrader as bt
from kline_data.sdk import BacktraderDataFeed

# 创建数据流
data_feed = BacktraderDataFeed(
    exchange='binance',
    symbol='BTC/USDT',
    start_time=datetime(2023, 1, 1),
    end_time=datetime(2024, 1, 1),
    interval='1h'
)

# 转换为backtrader数据
bt_data = bt.feeds.PandasData(
    dataname=data_feed.to_backtrader_format(),
    **data_feed.get_backtrader_params()
)

# 创建回测引擎
cerebro = bt.Cerebro()
cerebro.adddata(bt_data)
cerebro.addstrategy(YourStrategy)

# 运行回测
results = cerebro.run()
    """)


def example_streaming_feed():
    """示例5: 流式数据源（模拟实时）"""
    print("\n" + "=" * 60)
    print("示例5: 流式数据源（实时模拟）")
    print("=" * 60)
    
    # 创建流式数据源（100倍速播放）
    feed = StreamingDataFeed(
        exchange=DEFAULT_EXCHANGE,
        symbol=DEFAULT_SYMBOL,
        start_time=datetime(2024, 1, 1, 0, 0),
        end_time=datetime(2024, 1, 1, 1, 0),  # 只播放1小时数据
        interval=Timeframe.M1.value,
        playback_speed=100.0  # 100倍速
    )
    
    print(f"\n流式数据源创建成功: {feed}")
    print(f"播放速度: {feed.playback_speed}x")
    print(f"每根K线延迟: {feed.get_sleep_time():.4f}秒")
    
    print("\n开始流式播放（前10根K线）:")
    count = 0
    
    for bar in feed.stream():
        count += 1
        print(f"  [{count}] {bar['timestamp']} | Close: {bar['close']:.2f}")
        
        if count >= 10:
            print("  ... (仅显示前10根)")
            break
    
    print(f"\n注意: 实际使用时会根据播放速度自动延迟")


def example_memory_efficient():
    """示例6: 大数据集的内存高效处理"""
    print("\n" + "=" * 60)
    print("示例6: 内存高效处理大数据集")
    print("=" * 60)
    
    # 处理1年的分钟级数据（约50万条）
    feed = ChunkedDataFeed(
        exchange=DEFAULT_EXCHANGE,
        symbol=DEFAULT_SYMBOL,
        start_time=datetime(2023, 1, 1),
        end_time=datetime(2024, 1, 1),
        interval=Timeframe.M1.value,
        chunk_size=10000  # 每次处理1万条
    )
    
    print(f"\n数据流: {feed}")
    print("\n开始处理...")
    
    # 统计信息
    total_rows = 0
    total_volume = 0.0
    max_price = float('-inf')
    min_price = float('inf')
    
    chunk_count = 0
    for chunk_df in feed:
        chunk_count += 1
        total_rows += len(chunk_df)
        total_volume += chunk_df['volume'].sum()
        max_price = max(max_price, chunk_df['high'].max())
        min_price = min(min_price, chunk_df['low'].min())
        
        if chunk_count % 10 == 0:
            print(f"  已处理 {total_rows:,} 行...")
    
    print(f"\n处理完成!")
    print(f"总行数: {total_rows:,}")
    print(f"总成交量: {total_volume:,.0f}")
    print(f"价格范围: {min_price:.2f} - {max_price:.2f}")
    print(f"\n内存优势: 每次只加载 {feed.chunk_size:,} 行到内存")


def example_custom_processing():
    """示例7: 自定义数据处理"""
    print("\n" + "=" * 60)
    print("示例7: 自定义数据处理")
    print("=" * 60)
    
    feed = ChunkedDataFeed(
        exchange=DEFAULT_EXCHANGE,
        symbol=DEFAULT_SYMBOL,
        start_time=datetime(2024, 1, 1),
        end_time=datetime(2024, 1, 31),
        interval=Timeframe.H4.value,
        chunk_size=100
    )
    
    print("\n计算简单的移动平均策略信号:")
    
    # 自定义处理: 计算MA交叉信号
    previous_ma_short = None
    previous_ma_long = None
    signals = []
    
    for chunk_df in feed:
        # 计算移动平均
        chunk_df['MA_10'] = chunk_df['close'].rolling(window=10).mean()
        chunk_df['MA_20'] = chunk_df['close'].rolling(window=20).mean()
        
        # 检测交叉
        for idx, row in chunk_df.iterrows():
            ma_short = row['MA_10']
            ma_long = row['MA_20']
            
            if pd.notna(ma_short) and pd.notna(ma_long):
                if previous_ma_short and previous_ma_long:
                    # 金叉
                    if previous_ma_short < previous_ma_long and ma_short > ma_long:
                        signals.append({
                            'time': row['timestamp'],
                            'type': 'BUY',
                            'price': row['close']
                        })
                    # 死叉
                    elif previous_ma_short > previous_ma_long and ma_short < ma_long:
                        signals.append({
                            'time': row['timestamp'],
                            'type': 'SELL',
                            'price': row['close']
                        })
                
                previous_ma_short = ma_short
                previous_ma_long = ma_long
    
    print(f"\n检测到 {len(signals)} 个交易信号:")
    for i, signal in enumerate(signals[:5], 1):
        print(f"  {i}. {signal['type']} @ {signal['time']} | "
              f"价格: {signal['price']:.2f}")
    
    if len(signals) > 5:
        print(f"  ... 还有 {len(signals) - 5} 个信号")


if __name__ == '__main__':
    import pandas as pd
    
    try:
        # 运行所有示例
        example_chunked_feed()
        example_row_iteration()
        example_dict_iteration()
        example_backtrader_feed()
        example_streaming_feed()
        example_memory_efficient()
        example_custom_processing()
        
        print("\n" + "=" * 60)
        print("所有示例运行完成!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()
