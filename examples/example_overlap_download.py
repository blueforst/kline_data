"""
展示重叠数据下载优化功能的示例

这个示例展示了：
1. 下载一个时间范围的数据
2. 再次下载重叠的时间范围，系统会自动跳过已有数据
3. 只下载缺失的数据段
"""

from datetime import datetime, timedelta
from config import Config
from storage.downloader import DownloadManager
from storage.metadata_manager import MetadataManager

def demo_overlap_download():
    """演示重叠下载优化"""
    config = Config()
    download_mgr = DownloadManager(config)
    metadata_mgr = MetadataManager(config)
    
    exchange = "binance"
    symbol = "BTC/USDT"
    interval = "1m"
    
    print("=" * 80)
    print("演示：重叠数据下载优化")
    print("=" * 80)
    
    # 第一次下载：2024-01-01 00:00 到 2024-01-01 06:00
    start1 = datetime(2024, 1, 1, 0, 0, 0)
    end1 = datetime(2024, 1, 1, 6, 0, 0)
    
    print(f"\n第一次下载:")
    print(f"  交易所: {exchange}")
    print(f"  交易对: {symbol}")
    print(f"  周期: {interval}")
    print(f"  时间范围: {start1} - {end1}")
    print(f"  时长: 6小时")
    print("\n模拟场景：假设这次下载成功...")
    
    # 模拟添加元数据（实际下载会自动添加）
    from storage.models import IntervalRange, IntervalData
    from utils.timezone import datetime_to_timestamp
    
    start1_ts = datetime_to_timestamp(start1)
    end1_ts = datetime_to_timestamp(end1)
    
    # 第二次下载：2024-01-01 03:00 到 2024-01-01 09:00（与第一次有3小时重叠）
    start2 = datetime(2024, 1, 1, 3, 0, 0)
    end2 = datetime(2024, 1, 1, 9, 0, 0)
    
    print(f"\n{'='*80}")
    print(f"第二次下载（与第一次有重叠）:")
    print(f"  时间范围: {start2} - {end2}")
    print(f"  时长: 6小时")
    print(f"  重叠部分: {start2} - {end1} (3小时)")
    print(f"  新增部分: {end1} - {end2} (3小时)")
    
    start2_ts = datetime_to_timestamp(start2)
    end2_ts = datetime_to_timestamp(end2)
    
    # 手动添加第一次下载的元数据
    metadata = metadata_mgr.get_symbol_metadata(exchange, symbol)
    metadata.intervals[interval] = IntervalData(
        start_timestamp=start1_ts,
        end_timestamp=end1_ts,
        ranges=[IntervalRange(start_timestamp=start1_ts, end_timestamp=end1_ts)],
        completeness=1.0
    )
    metadata_mgr.save_symbol_metadata(metadata)
    
    print(f"\n计算需要下载的范围...")
    missing_ranges = metadata_mgr.calculate_missing_ranges(
        exchange, symbol, interval, start2_ts, end2_ts
    )
    
    print(f"\n分析结果:")
    print(f"  已有数据: {start1} - {end1}")
    print(f"  请求范围: {start2} - {end2}")
    print(f"  需要下载的段数: {len(missing_ranges)}")
    
    if missing_ranges:
        print(f"  需要下载:")
        for i, (ms, me) in enumerate(missing_ranges, 1):
            from utils.timezone import timestamp_to_datetime, format_datetime
            ms_dt = timestamp_to_datetime(ms)
            me_dt = timestamp_to_datetime(me)
            duration = (me - ms) / 1000 / 3600  # 小时
            print(f"    段{i}: {format_datetime(ms_dt)} - {format_datetime(me_dt)} ({duration:.1f}小时)")
    else:
        print(f"  ✅ 所有数据已存在，无需下载！")
    
    # 计算节省的下载量
    total_requested = (end2_ts - start2_ts) / 1000 / 3600  # 小时
    total_needed = sum((me - ms) for ms, me in missing_ranges) / 1000 / 3600  # 小时
    saved = total_requested - total_needed
    saved_percent = (saved / total_requested) * 100 if total_requested > 0 else 0
    
    print(f"\n优化效果:")
    print(f"  请求总时长: {total_requested:.1f}小时")
    print(f"  实际需要下载: {total_needed:.1f}小时")
    print(f"  节省下载量: {saved:.1f}小时 ({saved_percent:.1f}%)")
    
    # 第三次下载：完全包含在已有数据中
    print(f"\n{'='*80}")
    print(f"第三次下载（完全重叠）:")
    start3 = datetime(2024, 1, 1, 1, 0, 0)
    end3 = datetime(2024, 1, 1, 4, 0, 0)
    print(f"  时间范围: {start3} - {end3}")
    
    start3_ts = datetime_to_timestamp(start3)
    end3_ts = datetime_to_timestamp(end3)
    
    # 更新元数据，包含第二次下载后的数据
    metadata.intervals[interval] = IntervalData(
        start_timestamp=start1_ts,
        end_timestamp=end2_ts,
        ranges=[
            IntervalRange(start_timestamp=start1_ts, end_timestamp=end1_ts),
            IntervalRange(start_timestamp=end1_ts + 1, end_timestamp=end2_ts),
        ],
        completeness=1.0
    )
    metadata_mgr.save_symbol_metadata(metadata)
    
    missing_ranges = metadata_mgr.calculate_missing_ranges(
        exchange, symbol, interval, start3_ts, end3_ts
    )
    
    print(f"\n分析结果:")
    print(f"  已有数据: {start1} - {end2}")
    print(f"  请求范围: {start3} - {end3}")
    
    if missing_ranges:
        print(f"  需要下载的段数: {len(missing_ranges)}")
    else:
        print(f"  ✅ 所有数据已存在，无需下载！")
    
    # 第四次下载：多个不连续的缺失段
    print(f"\n{'='*80}")
    print(f"第四次下载（跨越多个数据段）:")
    start4 = datetime(2024, 1, 1, 0, 0, 0)
    end4 = datetime(2024, 1, 1, 12, 0, 0)
    print(f"  时间范围: {start4} - {end4}")
    print(f"  时长: 12小时")
    
    start4_ts = datetime_to_timestamp(start4)
    end4_ts = datetime_to_timestamp(end4)
    
    # 更新元数据，模拟有几段不连续的数据
    metadata.intervals[interval] = IntervalData(
        start_timestamp=start1_ts,
        end_timestamp=end2_ts,
        ranges=[
            IntervalRange(start_timestamp=start1_ts, end_timestamp=end1_ts),  # 0-6点
            IntervalRange(start_timestamp=end1_ts + 1, end_timestamp=end2_ts),  # 6-9点
            # 9-12点缺失
        ],
        completeness=0.75  # 9/12
    )
    metadata_mgr.save_symbol_metadata(metadata)
    
    missing_ranges = metadata_mgr.calculate_missing_ranges(
        exchange, symbol, interval, start4_ts, end4_ts
    )
    
    print(f"\n分析结果:")
    print(f"  已有数据段:")
    print(f"    段1: 0:00 - 6:00 (6小时)")
    print(f"    段2: 6:00 - 9:00 (3小时)")
    print(f"  请求范围: 0:00 - 12:00 (12小时)")
    print(f"  需要下载的段数: {len(missing_ranges)}")
    
    if missing_ranges:
        print(f"  需要下载:")
        for i, (ms, me) in enumerate(missing_ranges, 1):
            from utils.timezone import timestamp_to_datetime, format_datetime
            ms_dt = timestamp_to_datetime(ms)
            me_dt = timestamp_to_datetime(me)
            duration = (me - ms) / 1000 / 3600  # 小时
            print(f"    段{i}: {format_datetime(ms_dt)} - {format_datetime(me_dt)} ({duration:.1f}小时)")
    
    total_requested = (end4_ts - start4_ts) / 1000 / 3600  # 小时
    total_needed = sum((me - ms) for ms, me in missing_ranges) / 1000 / 3600  # 小时
    saved = total_requested - total_needed
    saved_percent = (saved / total_requested) * 100 if total_requested > 0 else 0
    
    print(f"\n优化效果:")
    print(f"  请求总时长: {total_requested:.1f}小时")
    print(f"  实际需要下载: {total_needed:.1f}小时")
    print(f"  节省下载量: {saved:.1f}小时 ({saved_percent:.1f}%)")
    
    print(f"\n{'='*80}")
    print("✅ 演示完成！")
    print("\n关键优势:")
    print("  1. 自动检测已有数据，避免重复下载")
    print("  2. 精确计算缺失段，只下载需要的部分")
    print("  3. 支持多个不连续的数据段")
    print("  4. 数据段自动合并，保持元数据整洁")
    print("  5. 显著节省网络带宽和时间")
    print("=" * 80)

if __name__ == "__main__":
    demo_overlap_download()
