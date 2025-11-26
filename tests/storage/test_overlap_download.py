"""测试重叠数据下载逻辑"""

from datetime import datetime, timedelta
from config import Config
from storage.metadata_manager import MetadataManager
from storage.models import IntervalRange, IntervalData

def test_calculate_missing_ranges():
    """测试缺失范围计算"""
    config = Config()
    metadata_mgr = MetadataManager(config)
    
    # 测试用例
    exchange = "binance"
    symbol = "BTC/USDT"
    interval = "1m"
    
    # 假设已有数据段：
    # [1000, 2000], [3000, 4000], [5000, 6000]
    existing_ranges = [
        IntervalRange(start_timestamp=1000, end_timestamp=2000),
        IntervalRange(start_timestamp=3000, end_timestamp=4000),
        IntervalRange(start_timestamp=5000, end_timestamp=6000),
    ]
    
    # 模拟保存现有数据
    metadata = metadata_mgr.get_symbol_metadata(exchange, symbol)
    metadata.intervals[interval] = IntervalData(
        start_timestamp=1000,
        end_timestamp=6000,
        ranges=existing_ranges,
        completeness=0.6  # (3000/5000)
    )
    metadata_mgr.save_symbol_metadata(metadata)
    
    print("测试用例 1: 请求区间完全在已有数据之前")
    missing = metadata_mgr.calculate_missing_ranges(exchange, symbol, interval, 0, 500)
    print(f"  请求: [0, 500], 缺失: {missing}")
    assert missing == [(0, 500)], f"Expected [(0, 500)], got {missing}"
    
    print("\n测试用例 2: 请求区间完全在已有数据之后")
    missing = metadata_mgr.calculate_missing_ranges(exchange, symbol, interval, 7000, 8000)
    print(f"  请求: [7000, 8000], 缺失: {missing}")
    assert missing == [(7000, 8000)], f"Expected [(7000, 8000)], got {missing}"
    
    print("\n测试用例 3: 请求区间完全被已有数据覆盖")
    missing = metadata_mgr.calculate_missing_ranges(exchange, symbol, interval, 1500, 1800)
    print(f"  请求: [1500, 1800], 缺失: {missing}")
    assert missing == [], f"Expected [], got {missing}"
    
    print("\n测试用例 4: 请求区间部分重叠")
    missing = metadata_mgr.calculate_missing_ranges(exchange, symbol, interval, 1500, 2500)
    print(f"  请求: [1500, 2500], 缺失: {missing}")
    assert missing == [(2001, 2500)], f"Expected [(2001, 2500)], got {missing}"
    
    print("\n测试用例 5: 请求区间跨越多个已有数据段")
    missing = metadata_mgr.calculate_missing_ranges(exchange, symbol, interval, 500, 5500)
    print(f"  请求: [500, 5500], 缺失: {missing}")
    expected = [(500, 999), (2001, 2999), (4001, 4999)]
    assert missing == expected, f"Expected {expected}, got {missing}"
    
    print("\n测试用例 6: 请求区间跨越所有数据段")
    missing = metadata_mgr.calculate_missing_ranges(exchange, symbol, interval, 0, 7000)
    print(f"  请求: [0, 7000], 缺失: {missing}")
    expected = [(0, 999), (2001, 2999), (4001, 4999), (6001, 7000)]
    assert missing == expected, f"Expected {expected}, got {missing}"
    
    print("\n测试用例 7: 没有已有数据")
    missing = metadata_mgr.calculate_missing_ranges(exchange, "ETH/USDT", interval, 1000, 5000)
    print(f"  请求: [1000, 5000], 缺失: {missing}")
    assert missing == [(1000, 5000)], f"Expected [(1000, 5000)], got {missing}"
    
    print("\n测试用例 8: 请求区间边界对齐")
    missing = metadata_mgr.calculate_missing_ranges(exchange, symbol, interval, 2000, 3000)
    print(f"  请求: [2000, 3000], 缺失: {missing}")
    assert missing == [(2001, 2999)], f"Expected [(2001, 2999)], got {missing}"
    
    print("\n✅ 所有测试通过!")

def test_merge_ranges():
    """测试时间段合并"""
    from storage.metadata_manager import MetadataManager
    
    print("\n测试时间段合并功能:")
    
    # 测试用例1: 重叠段
    ranges = [
        IntervalRange(start_timestamp=1000, end_timestamp=2000),
        IntervalRange(start_timestamp=1500, end_timestamp=2500),
    ]
    merged = MetadataManager._merge_ranges(ranges, step_ms=1000)
    print(f"  重叠段: {[(r.start_timestamp, r.end_timestamp) for r in merged]}")
    assert len(merged) == 1
    assert merged[0].start_timestamp == 1000
    assert merged[0].end_timestamp == 2500
    
    # 测试用例2: 相邻段（允许1个步长的间隔）
    ranges = [
        IntervalRange(start_timestamp=1000, end_timestamp=2000),
        IntervalRange(start_timestamp=2001, end_timestamp=3000),  # 紧邻
        IntervalRange(start_timestamp=3002, end_timestamp=4000),  # 间隔1步长
    ]
    merged = MetadataManager._merge_ranges(ranges, step_ms=1000)
    print(f"  相邻段: {[(r.start_timestamp, r.end_timestamp) for r in merged]}")
    assert len(merged) == 1
    assert merged[0].start_timestamp == 1000
    assert merged[0].end_timestamp == 4000
    
    # 测试用例3: 不相邻段（间隔超过1个步长）
    ranges = [
        IntervalRange(start_timestamp=1000, end_timestamp=2000),
        IntervalRange(start_timestamp=3002, end_timestamp=4000),  # 间隔>1步长
    ]
    merged = MetadataManager._merge_ranges(ranges, step_ms=1000)
    print(f"  不相邻段: {[(r.start_timestamp, r.end_timestamp) for r in merged]}")
    assert len(merged) == 2
    
    print("  ✅ 合并测试通过!")

if __name__ == "__main__":
    try:
        test_calculate_missing_ranges()
        test_merge_ranges()
        print("\n🎉 所有测试通过！")
    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
