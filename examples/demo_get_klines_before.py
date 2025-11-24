"""简单演示：get_klines_before接口"""

from datetime import datetime
from sdk import KlineClient
from utils.timezone import to_utc, format_datetime, timestamp_to_datetime

def demo():
    """演示get_klines_before接口的基本使用"""
    
    print("=" * 70)
    print("get_klines_before 接口演示")
    print("=" * 70)
    
    # 创建客户端
    client = KlineClient()
    
    # 示例1：获取指定日期前的K线
    print("\n[示例1] 获取2024年1月1日前10条日线")
    print("-" * 70)
    
    before_time = datetime(2024, 1, 1)
    df = client.get_klines_before(
        exchange='binance',
        symbol='BTC/USDT',
        before_time=before_time,
        interval='1d',
        limit=10
    )
    
    if not df.empty:
        print(f"✓ 成功获取 {len(df)} 条K线数据")
        print(f"  时间范围: {df['timestamp'].min()} 至 {df['timestamp'].max()}")
        print(f"\n  最后3条数据:")
        for idx, row in df.tail(3).iterrows():
            dt = timestamp_to_datetime(row['timestamp'])
            print(f"    {format_datetime(dt, for_display=True)} | "
                  f"开:{row['open']:.2f} 高:{row['high']:.2f} "
                  f"低:{row['low']:.2f} 收:{row['close']:.2f}")
    else:
        print("✗ 未获取到数据")
    
    # 示例2：使用UTC时间获取小时线
    print("\n[示例2] 使用UTC时间获取2024年6月15日12:00前的5条小时线")
    print("-" * 70)
    
    before_time_utc = to_utc(datetime(2024, 6, 15, 12, 0, 0))
    print(f"截止时间(UTC): {format_datetime(before_time_utc, for_display=True)}")
    
    df2 = client.get_klines_before(
        exchange='binance',
        symbol='BTC/USDT',
        before_time=before_time_utc,
        interval='1h',
        limit=5
    )
    
    if not df2.empty:
        print(f"✓ 成功获取 {len(df2)} 条K线数据")
        print(f"\n  数据列表:")
        for idx, row in df2.iterrows():
            dt = timestamp_to_datetime(row['timestamp'])
            print(f"    {format_datetime(dt, for_display=True)} | 收盘:{row['close']:.2f}")
    else:
        print("✗ 未获取到数据")
    
    # 示例3：获取数据并计算指标
    print("\n[示例3] 获取数据并计算技术指标")
    print("-" * 70)
    
    df3 = client.get_klines_before(
        exchange='binance',
        symbol='BTC/USDT',
        before_time=datetime(2024, 3, 1),
        interval='1d',
        limit=30,
        with_indicators=['MA_20', 'RSI_14']
    )
    
    if not df3.empty:
        print(f"✓ 成功获取 {len(df3)} 条K线数据，已计算指标")
        print(f"  数据列: {', '.join(df3.columns.tolist())}")
        
        # 显示最后5条数据的指标
        print(f"\n  最后5条数据的指标:")
        for idx, row in df3.tail(5).iterrows():
            dt = timestamp_to_datetime(row['timestamp'])
            ma_val = f"{row['MA_20']:.2f}" if not pd.isna(row['MA_20']) else "N/A"
            rsi_val = f"{row['RSI_14']:.2f}" if not pd.isna(row['RSI_14']) else "N/A"
            print(f"    {format_datetime(dt, for_display=True)[:10]} | "
                  f"收盘:{row['close']:.2f} MA20:{ma_val} RSI:{rsi_val}")
    else:
        print("✗ 未获取到数据")
    
    print("\n" + "=" * 70)
    print("演示完成！")
    print("=" * 70)


if __name__ == '__main__':
    # 需要导入pandas用于isna检查
    import pandas as pd
    
    demo()
