"""
集成测试：验证重叠下载优化功能
"""

import sys
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

# 创建临时配置
def create_test_config():
    """创建测试用的临时配置"""
    temp_dir = Path(tempfile.mkdtemp())
    
    # 创建一个简单的配置类
    class TestConfig:
        class Storage:
            def __init__(self, root_path):
                self.root_path = root_path
            
            def get_root_path(self):
                return self.root_path
        
        class Memory:
            chunk_size = 10000
        
        class CCXT:
            class RateLimit:
                enabled = False
                requests_per_minute = 60
            
            class Retry:
                timeout = 30
                backoff_factor = 2
            
            class Proxy:
                def to_dict(self):
                    return {}
            
            rate_limit = RateLimit()
            retry = Retry()
            proxy = Proxy()
        
        def __init__(self, root_path):
            self.storage = self.Storage(root_path)
            self.memory = self.Memory()
            self.ccxt = self.CCXT()
    
    return TestConfig(temp_dir), temp_dir

def test_metadata_manager():
    """测试元数据管理器的重叠检测功能"""
    from storage.metadata_manager import MetadataManager
    from storage.models import IntervalRange, IntervalData
    from utils.timezone import datetime_to_timestamp
    
    config, temp_dir = create_test_config()
    
    try:
        print("=" * 80)
        print("集成测试：元数据管理器")
        print("=" * 80)
        
        metadata_mgr = MetadataManager(config)
        
        exchange = "binance"
        symbol = "BTC/USDT"
        interval = "1m"
        
        # 测试1: 添加第一个时间段
        print("\n测试1: 添加第一个时间段")
        start1 = datetime(2024, 1, 1, 0, 0, 0)
        end1 = datetime(2024, 1, 1, 6, 0, 0)
        start1_ts = datetime_to_timestamp(start1)
        end1_ts = datetime_to_timestamp(end1)
        
        interval_data = metadata_mgr.add_interval_range(
            exchange, symbol, interval, start1_ts, end1_ts
        )
        
        print(f"  添加时间段: {start1} - {end1}")
        print(f"  元数据ranges数量: {len(interval_data.ranges)}")
        assert len(interval_data.ranges) == 1
        print("  ✅ 通过")
        
        # 测试2: 添加重叠的时间段（应该合并）
        print("\n测试2: 添加重叠的时间段")
        start2 = datetime(2024, 1, 1, 3, 0, 0)
        end2 = datetime(2024, 1, 1, 9, 0, 0)
        start2_ts = datetime_to_timestamp(start2)
        end2_ts = datetime_to_timestamp(end2)
        
        interval_data = metadata_mgr.add_interval_range(
            exchange, symbol, interval, start2_ts, end2_ts
        )
        
        print(f"  添加时间段: {start2} - {end2}")
        print(f"  元数据ranges数量: {len(interval_data.ranges)}")
        print(f"  合并后范围: {interval_data.start_timestamp} - {interval_data.end_timestamp}")
        assert len(interval_data.ranges) == 1  # 应该合并为一段
        assert interval_data.start_timestamp == start1_ts
        assert interval_data.end_timestamp == end2_ts
        print("  ✅ 通过")
        
        # 测试3: 计算缺失范围（完全重叠）
        print("\n测试3: 计算缺失范围（完全重叠）")
        start3 = datetime(2024, 1, 1, 1, 0, 0)
        end3 = datetime(2024, 1, 1, 4, 0, 0)
        start3_ts = datetime_to_timestamp(start3)
        end3_ts = datetime_to_timestamp(end3)
        
        missing = metadata_mgr.calculate_missing_ranges(
            exchange, symbol, interval, start3_ts, end3_ts
        )
        
        print(f"  请求范围: {start3} - {end3}")
        print(f"  缺失段数: {len(missing)}")
        assert len(missing) == 0
        print("  ✅ 通过（无需下载）")
        
        # 测试4: 计算缺失范围（部分重叠）
        print("\n测试4: 计算缺失范围（部分重叠）")
        start4 = datetime(2024, 1, 1, 8, 0, 0)
        end4 = datetime(2024, 1, 1, 12, 0, 0)
        start4_ts = datetime_to_timestamp(start4)
        end4_ts = datetime_to_timestamp(end4)
        
        missing = metadata_mgr.calculate_missing_ranges(
            exchange, symbol, interval, start4_ts, end4_ts
        )
        
        print(f"  请求范围: {start4} - {end4}")
        print(f"  缺失段数: {len(missing)}")
        print(f"  缺失段: {missing}")
        assert len(missing) == 1
        # 已有数据到 9:00，所以缺失段从 9:00:00.001 开始
        print("  ✅ 通过")
        
        # 测试5: 添加不相邻的时间段
        print("\n测试5: 添加不相邻的时间段")
        start5 = datetime(2024, 1, 1, 15, 0, 0)
        end5 = datetime(2024, 1, 1, 18, 0, 0)
        start5_ts = datetime_to_timestamp(start5)
        end5_ts = datetime_to_timestamp(end5)
        
        interval_data = metadata_mgr.add_interval_range(
            exchange, symbol, interval, start5_ts, end5_ts
        )
        
        print(f"  添加时间段: {start5} - {end5}")
        print(f"  元数据ranges数量: {len(interval_data.ranges)}")
        assert len(interval_data.ranges) == 2  # 不应该合并
        print("  ✅ 通过（保持两段）")
        
        # 测试6: 计算跨越多段的缺失范围
        print("\n测试6: 计算跨越多段的缺失范围")
        start6 = datetime(2024, 1, 1, 0, 0, 0)
        end6 = datetime(2024, 1, 1, 20, 0, 0)
        start6_ts = datetime_to_timestamp(start6)
        end6_ts = datetime_to_timestamp(end6)
        
        missing = metadata_mgr.calculate_missing_ranges(
            exchange, symbol, interval, start6_ts, end6_ts
        )
        
        print(f"  请求范围: {start6} - {end6}")
        print(f"  缺失段数: {len(missing)}")
        for i, (ms, me) in enumerate(missing, 1):
            from utils.timezone import timestamp_to_datetime
            print(f"    段{i}: {timestamp_to_datetime(ms)} - {timestamp_to_datetime(me)}")
        
        # 应该有2个缺失段：9:00-15:00 和 18:00-20:00
        assert len(missing) == 2
        print("  ✅ 通过")
        
        print("\n" + "=" * 80)
        print("✅ 所有集成测试通过！")
        print("=" * 80)
        
        return True
        
    finally:
        # 清理临时目录
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
            print(f"\n清理临时目录: {temp_dir}")

if __name__ == "__main__":
    try:
        success = test_metadata_manager()
        if success:
            print("\n🎉 测试成功！")
            sys.exit(0)
        else:
            print("\n❌ 测试失败！")
            sys.exit(1)
    except Exception as e:
        print(f"\n❌ 测试出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
