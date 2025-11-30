"""存储层使用示例"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from kline_data.config import load_config
from kline_data.storage import (
    DataValidator,
    ParquetWriter,
    MetadataManager,
    DownloadManager,
    KlineData,
)
import pandas as pd


def example_kline_data():
    """示例1: K线数据模型"""
    print("=" * 60)
    print("示例1: K线数据模型")
    print("=" * 60)
    
    # 创建K线数据
    kline = KlineData(
        timestamp=1609459200000,
        open=29000.0,
        high=29500.0,
        low=28500.0,
        close=29200.0,
        volume=100.5
    )
    
    print(f"时间戳: {kline.timestamp}")
    print(f"开盘价: {kline.open}")
    print(f"最高价: {kline.high}")
    print(f"最低价: {kline.low}")
    print(f"收盘价: {kline.close}")
    print(f"成交量: {kline.volume}")
    
    # 从CCXT格式创建
    ccxt_data = [1609459200000, 29000.0, 29500.0, 28500.0, 29200.0, 100.5]
    kline2 = KlineData.from_ccxt(ccxt_data)
    print(f"\n从CCXT数据创建: {kline2.to_dict()}")
    print()


def example_data_validator():
    """示例2: 数据验证"""
    print("=" * 60)
    print("示例2: 数据验证")
    print("=" * 60)
    
    # 创建测试数据
    data = {
        'timestamp': pd.date_range('2024-01-01', periods=100, freq='1s'),
        'open': [100.0] * 100,
        'high': [105.0] * 100,
        'low': [95.0] * 100,
        'close': [102.0] * 100,
        'volume': [1000.0] * 100,
    }
    df = pd.DataFrame(data)
    
    print(f"原始数据: {len(df)} 行")
    
    # 验证数据
    validator = DataValidator()
    validated_df = validator.validate_kline(df)
    
    print(f"验证后数据: {len(validated_df)} 行")
    
    # 检查完整性
    completeness, missing_ranges = validator.check_completeness(validated_df, '1s')
    print(f"数据完整性: {completeness * 100:.2f}%")
    print(f"缺失范围数: {len(missing_ranges)}")
    
    # 检查数据质量
    quality = validator.check_data_quality(validated_df, '1s')
    print(f"完整性: {quality.completeness * 100:.2f}%")
    print(f"重复率: {quality.duplicate_rate * 100:.2f}%")
    print()


def example_parquet_writer():
    """示例3: Parquet写入"""
    print("=" * 60)
    print("示例3: Parquet文件写入")
    print("=" * 60)
    
    # 加载配置
    config = load_config('config/config.yaml')
    writer = ParquetWriter(config)
    
    # 创建测试数据
    data = {
        'timestamp': pd.date_range('2024-01-01', periods=1000, freq='1s'),
        'open': [100.0] * 1000,
        'high': [105.0] * 1000,
        'low': [95.0] * 1000,
        'close': [102.0] * 1000,
        'volume': [1000.0] * 1000,
    }
    df = pd.DataFrame(data)
    
    print(f"数据量: {len(df)} 行")
    
    # 分区写入
    partition_infos = writer.write_partitioned(
        df,
        'binance',
        'BTC/USDT',
        '1s'
    )
    
    print(f"写入分区数: {len(partition_infos)}")
    for info in partition_infos:
        print(f"  - {info.year}/{info.month:02d}: {info.records} 行, {info.size_bytes} 字节")
        print(f"    校验和: {info.checksum[:16]}...")
    print()


def example_metadata_manager():
    """示例4: 元数据管理"""
    print("=" * 60)
    print("示例4: 元数据管理")
    print("=" * 60)
    
    # 加载配置
    config = load_config('config/config.yaml')
    mgr = MetadataManager(config)
    
    # 获取元数据
    metadata = mgr.get_symbol_metadata('binance', 'BTC/USDT')
    
    print(f"交易所: {metadata.exchange}")
    print(f"交易对: {metadata.symbol}")
    print(f"基础货币: {metadata.base}")
    print(f"报价货币: {metadata.quote}")
    print(f"分区数: {len(metadata.partitions)}")
    
    # 更新数据范围
    start_ts = int(datetime(2024, 1, 1).timestamp() * 1000)
    end_ts = int(datetime(2024, 1, 31).timestamp() * 1000)
    
    mgr.update_data_range('binance', 'BTC/USDT', start_ts, end_ts)
    print(f"\n已更新数据范围:")
    print(f"  开始: {datetime.fromtimestamp(start_ts/1000)}")
    print(f"  结束: {datetime.fromtimestamp(end_ts/1000)}")
    
    # 列出交易所
    exchanges = mgr.list_exchanges()
    print(f"\n交易所列表: {', '.join(exchanges)}")
    
    # 列出交易对
    if 'binance' in exchanges:
        symbols = mgr.list_symbols('binance')
        print(f"Binance交易对数: {len(symbols)}")
    print()


def example_download_manager():
    """示例5: 下载管理器（仅演示，不实际下载）"""
    print("=" * 60)
    print("示例5: 下载管理器")
    print("=" * 60)
    
    # 加载配置
    config = load_config('config/config.yaml')
    mgr = DownloadManager(config)
    
    print("下载管理器已初始化")
    print("\n下载示例（需要实际网络连接）:")
    print("  # 下载数据")
    print("  task_id = mgr.download(")
    print("      'binance',")
    print("      'BTC/USDT',")
    print("      datetime(2024, 1, 1),")
    print("      datetime(2024, 1, 2)")
    print("  )")
    print("")
    print("  # 查看任务状态")
    print("  task = mgr.get_task_status(task_id)")
    print("  print(f'状态: {task.status}')")
    print("  print(f'进度: {task.progress.percentage}%')")
    print("")
    print("  # 更新到最新")
    print("  mgr.update('binance', 'BTC/USDT')")
    print("")
    print("  # 恢复下载")
    print("  mgr.resume(task_id)")
    print()


def main():
    """运行所有示例"""
    try:
        example_kline_data()
        example_data_validator()
        example_parquet_writer()
        example_metadata_manager()
        example_download_manager()
        
        print("=" * 60)
        print("✓ 所有示例运行完成")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ 错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
