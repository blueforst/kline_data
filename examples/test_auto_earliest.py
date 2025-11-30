#!/usr/bin/env python3
"""
示例：演示自动检测最早可用时间功能

这个示例展示了如何：
1. 查询交易所支持的最早数据时间
2. 使用 CLI 下载全部历史数据
"""

from kline_data.sdk import KlineClient
from datetime import datetime

def main():
    print("=" * 70)
    print("自动检测最早可用时间功能演示")
    print("=" * 70)
    
    # 创建客户端
    client = KlineClient()
    
    # 测试参数
    exchanges_symbols = [
        ('binance', 'BTC/USDT'),
        ('binance', 'ETH/USDT'),
    ]
    
    print("\n查询各交易对的最早可用数据时间:\n")
    
    for exchange, symbol in exchanges_symbols:
        print(f"{exchange:10} {symbol:15} ", end="", flush=True)
        
        try:
            # 查询最早时间
            earliest_time = client.get_earliest_available_time(
                exchange=exchange,
                symbol=symbol,
                interval='1d'
            )
            
            if earliest_time:
                # 计算数据跨度
                now = datetime.now()
                span_days = (now - earliest_time).days
                span_years = span_days / 365.25
                
                print(f"✓ {earliest_time.date()} ({span_years:.1f} 年, {span_days} 天)")
            else:
                print("✗ 无法获取")
                
        except Exception as e:
            print(f"✗ 错误: {e}")
    
    print("\n" + "=" * 70)
    print("CLI 使用示例:")
    print("=" * 70)
    print()
    print("# 下载 BTC/USDT 的全部历史数据:")
    print("kline download start -s BTC/USDT --start all")
    print()
    print("# 下载到指定时间:")
    print("kline download start -s BTC/USDT --start all --end 2020-01-01")
    print()
    print("=" * 70)

if __name__ == '__main__':
    main()
