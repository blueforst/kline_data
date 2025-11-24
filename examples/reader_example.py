"""读取层使用示例"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config import load_config
from reader import (
    LRUCache,
    DataCache,
    ParquetReader,
    QueryEngine,
    QueryBuilder,
)
import pandas as pd


def example_lru_cache():
    """示例1: LRU缓存"""
    print("=" * 60)
    print("示例1: LRU缓存")
    print("=" * 60)
    
    # 创建缓存
    cache = LRUCache(max_size_mb=100, ttl_seconds=300)
    
    # 创建测试数据
    df = pd.DataFrame({
        'timestamp': pd.date_range('2024-01-01', periods=100, freq='1s'),
        'price': range(100)
    })
    
    print(f"原始数据: {len(df)} 行")
    
    # 存入缓存
    cache.put('test_data', df)
    print(f"✓ 数据已缓存")
    
    # 从缓存获取
    cached_df = cache.get('test_data')
    print(f"✓ 从缓存获取: {len(cached_df)} 行")
    
    # 获取统计信息
    stats = cache.get_stats()
    print(f"\n缓存统计:")
    print(f"  - 大小: {stats['size']} 项")
    print(f"  - 内存: {stats['size_mb']} MB")
    print(f"  - 命中率: {stats['hit_rate']}%")
    print()


def example_data_cache():
    """示例2: 数据缓存管理器"""
    print("=" * 60)
    print("示例2: 数据缓存管理器")
    print("=" * 60)
    
    cache = DataCache(max_size_mb=100, ttl_seconds=300)
    
    def expensive_computation():
        """模拟耗时计算"""
        print("  执行耗时计算...")
        return pd.DataFrame({'value': range(1000)})
    
    # 第一次调用（缓存未命中）
    print("第一次调用:")
    df1 = cache.get_or_compute('key1', expensive_computation)
    print(f"  获得数据: {len(df1)} 行\n")
    
    # 第二次调用（缓存命中）
    print("第二次调用:")
    df2 = cache.get_or_compute('key1', expensive_computation)
    print(f"  从缓存获取: {len(df2)} 行")
    
    stats = cache.get_stats()
    print(f"\n命中率: {stats['hit_rate']}%")
    print()


def example_parquet_reader():
    """示例3: Parquet读取器"""
    print("=" * 60)
    print("示例3: Parquet读取器")
    print("=" * 60)
    
    # 加载配置
    config = load_config('config/config.yaml')
    reader = ParquetReader(config)
    
    # 读取数据范围
    start = datetime(2024, 1, 1)
    end = datetime(2024, 1, 1, 0, 10)
    
    print(f"查询时间范围: {start} 到 {end}")
    
    try:
        df = reader.read_range('binance', 'BTC/USDT', start, end, '1s')
        
        if not df.empty:
            print(f"✓ 读取成功: {len(df)} 行")
            print(f"\n前5行数据:")
            print(df.head())
            
            # 获取缓存统计
            stats = reader.get_cache_stats()
            if stats:
                print(f"\n缓存统计:")
                print(f"  - 命中: {stats['hits']}")
                print(f"  - 未命中: {stats['misses']}")
                print(f"  - 命中率: {stats['hit_rate']}%")
        else:
            print("⚠ 没有数据（需要先下载数据）")
    except Exception as e:
        print(f"⚠ 读取失败: {e}")
        print("  提示: 请先使用storage层下载数据")
    
    print()


def example_query_engine():
    """示例4: 查询引擎"""
    print("=" * 60)
    print("示例4: 查询引擎")
    print("=" * 60)
    
    config = load_config('config/config.yaml')
    engine = QueryEngine(config)
    
    start = datetime(2024, 1, 1)
    end = datetime(2024, 1, 1, 0, 10)
    
    try:
        # 基本查询
        print("1. 基本查询:")
        df = engine.query('binance', 'BTC/USDT', start, end, '1s')
        if not df.empty:
            print(f"   ✓ 查询成功: {len(df)} 行")
        else:
            print("   ⚠ 没有数据")
        
        # 条件查询
        print("\n2. 条件查询 (volume > 500):")
        df = engine.query_with_condition(
            'binance',
            'BTC/USDT',
            start,
            end,
            '1s',
            'volume > 500'
        )
        if not df.empty:
            print(f"   ✓ 查询成功: {len(df)} 行")
        else:
            print("   ⚠ 没有匹配数据")
        
        # 统计查询
        print("\n3. 统计查询:")
        stats = engine.query_statistics('binance', 'BTC/USDT', start, end, '1s')
        if stats:
            print(f"   ✓ 数据量: {stats.get('count', 0)}")
            if 'price' in stats:
                print(f"   - 最高价: {stats['price'].get('high_max', 0):.2f}")
                print(f"   - 最低价: {stats['price'].get('low_min', 0):.2f}")
    except Exception as e:
        print(f"⚠ 查询失败: {e}")
    
    print()


def example_query_builder():
    """示例5: 查询构建器（链式调用）"""
    print("=" * 60)
    print("示例5: 查询构建器（链式调用）")
    print("=" * 60)
    
    config = load_config('config/config.yaml')
    engine = QueryEngine(config)
    
    start = datetime(2024, 1, 1)
    end = datetime(2024, 1, 1, 0, 10)
    
    print("链式查询示例:")
    print("  builder")
    print("    .exchange('binance')")
    print("    .symbol('BTC/USDT')")
    print("    .time_range(start, end)")
    print("    .interval('1s')")
    print("    .columns('timestamp', 'close', 'volume')")
    print("    .limit(10)")
    print("    .execute()")
    
    try:
        builder = QueryBuilder(engine)
        
        df = (builder
              .exchange('binance')
              .symbol('BTC/USDT')
              .time_range(start, end)
              .interval('1s')
              .columns('timestamp', 'close', 'volume')
              .limit(10)
              .execute())
        
        if not df.empty:
            print(f"\n✓ 查询成功: {len(df)} 行")
            print("\n结果:")
            print(df)
        else:
            print("\n⚠ 没有数据")
    except Exception as e:
        print(f"\n⚠ 查询失败: {e}")
    
    print()


def example_advanced_queries():
    """示例6: 高级查询"""
    print("=" * 60)
    print("示例6: 高级查询")
    print("=" * 60)
    
    config = load_config('config/config.yaml')
    engine = QueryEngine(config)
    
    start = datetime(2024, 1, 1)
    end = datetime(2024, 1, 2)
    
    print("高级查询功能:")
    print("  1. 聚合查询")
    print("  2. Top N查询")
    print("  3. 价格变化查询")
    print("  4. OHLC重采样")
    
    try:
        # Top N查询
        print("\nTop 5 按交易量:")
        df = engine.query_top_n(
            'binance',
            'BTC/USDT',
            start,
            end,
            '1s',
            n=5,
            by='volume'
        )
        if not df.empty:
            print(f"  ✓ 找到 {len(df)} 条记录")
        else:
            print("  ⚠ 没有数据")
        
    except Exception as e:
        print(f"⚠ 查询失败: {e}")
    
    print()


def main():
    """运行所有示例"""
    try:
        example_lru_cache()
        example_data_cache()
        example_parquet_reader()
        example_query_engine()
        example_query_builder()
        example_advanced_queries()
        
        print("=" * 60)
        print("✓ 所有示例运行完成")
        print("=" * 60)
        print("\n提示: 如果数据查询为空，请先使用storage层下载数据:")
        print("  from storage import DownloadManager")
        print("  mgr = DownloadManager(config)")
        print("  mgr.download('binance', 'BTC/USDT', start, end)")
        
    except Exception as e:
        print(f"\n✗ 错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
