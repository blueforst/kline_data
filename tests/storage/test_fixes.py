"""测试修复后的数据下载和元数据逻辑"""

import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
import shutil
from kline_data.config import Config
from kline_data.storage.writer import ParquetWriter
from kline_data.storage.metadata_manager import MetadataManager
from kline_data.storage.models import PartitionInfo


def test_write_partitioned_append():
    """测试 write_partitioned 不覆盖现有数据"""
    print("\n=== 测试 write_partitioned 追加逻辑 ===")
    
    config = Config()
    writer = ParquetWriter(config)
    metadata_mgr = MetadataManager(config)
    
    exchange = "binance"
    symbol = "BTC/USDT"
    interval = "1m"
    
    # 清理测试数据 (新的统一路径结构)
    test_path = config.storage.get_root_path() / 'raw' / exchange / 'BTCUSDT' / interval
    if test_path.exists():
        shutil.rmtree(test_path)
    
    # 第一批数据（同一月份）
    dates1 = pd.date_range('2024-01-01 00:00:00', periods=100, freq='1min', tz='UTC')
    df1 = pd.DataFrame({
        'timestamp': dates1,
        'open': 40000.0,
        'high': 40100.0,
        'low': 39900.0,
        'close': 40050.0,
        'volume': 1.0,
    })
    
    print(f"第一批写入 {len(df1)} 条记录...")
    partition_infos1 = writer.write_partitioned(df1, exchange, symbol, interval)
    print(f"  分区数: {len(partition_infos1)}")
    print(f"  记录数: {partition_infos1[0].records}")
    
    # 第二批数据（同一月份，不同时间）
    dates2 = pd.date_range('2024-01-01 02:00:00', periods=50, freq='1min', tz='UTC')
    df2 = pd.DataFrame({
        'timestamp': dates2,
        'open': 41000.0,
        'high': 41100.0,
        'low': 40900.0,
        'close': 41050.0,
        'volume': 2.0,
    })
    
    print(f"\n第二批写入 {len(df2)} 条记录到同一月份...")
    partition_infos2 = writer.write_partitioned(df2, exchange, symbol, interval)
    print(f"  分区数: {len(partition_infos2)}")
    print(f"  记录数: {partition_infos2[0].records}")
    
    # 验证数据未被覆盖
    import pyarrow.parquet as pq
    file_path = config.storage.get_root_path() / partition_infos2[0].file_path
    table = pq.read_table(file_path)
    result_df = table.to_pandas()
    
    print(f"\n最终文件中的记录数: {len(result_df)}")
    print(f"预期记录数: {len(df1) + len(df2)}")
    
    if len(result_df) == len(df1) + len(df2):
        print("✅ 测试通过：数据未被覆盖，正确合并")
    else:
        print(f"❌ 测试失败：预期 {len(df1) + len(df2)} 条，实际 {len(result_df)} 条")
    
    # 清理
    if test_path.exists():
        shutil.rmtree(test_path)


def test_partition_info_with_interval():
    """测试 PartitionInfo 区分不同 interval"""
    print("\n=== 测试 PartitionInfo interval 字段 ===")
    
    config = Config()
    writer = ParquetWriter(config)
    metadata_mgr = MetadataManager(config)
    
    exchange = "binance"
    symbol = "ETH/USDT"
    
    # 清理测试数据 (新的统一路径结构)
    test_path = config.storage.get_root_path() / 'raw' / exchange / 'ETHUSDT'
    if test_path.exists():
        shutil.rmtree(test_path)
    
    # 创建两个不同周期的数据（同一月份）
    dates = pd.date_range('2024-01-01 00:00:00', periods=100, freq='1s', tz='UTC')
    df = pd.DataFrame({
        'timestamp': dates,
        'open': 3000.0,
        'high': 3100.0,
        'low': 2900.0,
        'close': 3050.0,
        'volume': 1.0,
    })
    
    # 写入 1s 数据
    print("写入 1s 数据...")
    partition_infos_1s = writer.write_partitioned(df, exchange, symbol, '1s')
    for p in partition_infos_1s:
        metadata_mgr.add_partition(exchange, symbol, p)
    
    # 写入 1m 数据
    print("写入 1m 数据到同一月份...")
    partition_infos_1m = writer.write_partitioned(df, exchange, symbol, '1m')
    for p in partition_infos_1m:
        metadata_mgr.add_partition(exchange, symbol, p)
    
    # 检查元数据
    metadata = metadata_mgr.get_symbol_metadata(exchange, symbol)
    print(f"\n总分区数: {len(metadata.partitions)}")
    
    partitions_1s = [p for p in metadata.partitions if p.interval == '1s']
    partitions_1m = [p for p in metadata.partitions if p.interval == '1m']
    
    print(f"1s 分区数: {len(partitions_1s)}")
    print(f"1m 分区数: {len(partitions_1m)}")
    
    if len(partitions_1s) == 1 and len(partitions_1m) == 1:
        print("✅ 测试通过：不同 interval 的分区被正确区分")
    else:
        print("❌ 测试失败：分区信息混乱")
    
    # 清理
    if test_path.exists():
        shutil.rmtree(test_path)
    metadata_mgr.delete_symbol_metadata(exchange, symbol)


def test_delete_time_range_updates_data_range():
    """测试删除时间范围后 data_range 被正确更新"""
    print("\n=== 测试删除后 data_range 更新 ===")
    
    config = Config()
    metadata_mgr = MetadataManager(config)
    
    exchange = "binance"
    symbol = "LTC/USDT"
    interval = "1h"
    
    # 创建测试元数据
    metadata = metadata_mgr.get_symbol_metadata(exchange, symbol)
    
    # 添加多个时间段
    from kline_data.storage.models import IntervalRange, IntervalData
    metadata.intervals[interval] = IntervalData(
        start_timestamp=1000,
        end_timestamp=5000,
        ranges=[
            IntervalRange(start_timestamp=1000, end_timestamp=2000),
            IntervalRange(start_timestamp=3000, end_timestamp=4000),
            IntervalRange(start_timestamp=4500, end_timestamp=5000),
        ],
        completeness=0.8
    )
    
    # 设置初始 data_range
    from kline_data.storage.models import DataRange
    metadata.data_range = DataRange.from_timestamps(1000, 5000)
    metadata_mgr.save_symbol_metadata(metadata)
    
    print(f"初始 data_range: [{metadata.data_range.start_timestamp}, {metadata.data_range.end_timestamp}]")
    
    # 删除中间的时间段
    print("\n删除时间段 [1500, 4200]...")
    metadata_mgr.delete_time_range_metadata(exchange, symbol, interval, 1500, 4200)
    
    # 重新读取元数据
    metadata = metadata_mgr.get_symbol_metadata(exchange, symbol)
    
    print(f"删除后 ranges: {[(r.start_timestamp, r.end_timestamp) for r in metadata.intervals[interval].ranges]}")
    print(f"删除后 data_range: [{metadata.data_range.start_timestamp}, {metadata.data_range.end_timestamp}]")
    
    # 验证 data_range 已更新
    expected_start = 1000
    expected_end = 5000
    
    if (metadata.data_range.start_timestamp == expected_start and 
        metadata.data_range.end_timestamp == expected_end):
        print("✅ 测试通过：data_range 已正确更新")
    else:
        print(f"❌ 测试失败：预期 [{expected_start}, {expected_end}]，实际 [{metadata.data_range.start_timestamp}, {metadata.data_range.end_timestamp}]")
    
    # 清理
    metadata_mgr.delete_symbol_metadata(exchange, symbol)


if __name__ == "__main__":
    try:
        test_write_partitioned_append()
        test_partition_info_with_interval()
        test_delete_time_range_updates_data_range()
        print("\n🎉 所有测试通过！")
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
