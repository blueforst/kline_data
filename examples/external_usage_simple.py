"""
外部项目使用示例 - 简单模式

这个示例展示如何在外部项目中直接使用 kline-data，
无需额外配置，直接使用项目的默认配置。

注意：
- 外部项目使用时导入: from kline_data.sdk import KlineClient
- 项目内部测试时导入: from sdk import KlineClient
"""

import sys
from pathlib import Path

# 仅用于项目内部测试，外部使用时删除这段
if __name__ == '__main__':
    project_root = Path(__file__).parent.parent
    sys.path.insert(0, str(project_root))

from sdk import KlineClient
from datetime import datetime, timedelta


def example_1_basic_usage():
    """示例1：基本使用 - 直接使用项目配置"""
    print("=" * 60)
    print("示例1：基本使用 - 自动加载项目配置")
    print("=" * 60)
    
    # 不传任何参数，自动使用项目配置
    client = KlineClient()
    
    print(f"✅ 客户端创建成功")
    print(f"   配置版本: {client.config.system.version}")
    print(f"   存储路径: {client.config.storage.root_path}")
    print(f"   日志级别: {client.config.system.log_level}")
    print()
    
    # 查询数据示例（如果有数据的话）
    try:
        end_time = datetime.now()
        start_time = end_time - timedelta(days=7)
        
        df = client.get_kline(
            exchange='binance',
            symbol='BTC/USDT',
            start_time=start_time,
            end_time=end_time,
            interval='1h'
        )
        
        if not df.empty:
            print(f"✅ 查询到 {len(df)} 条数据")
            print(df.head())
        else:
            print("ℹ️ 没有找到数据（可能需要先下载）")
    except Exception as e:
        print(f"ℹ️ 查询数据失败: {e}")
    print()


def example_2_check_metadata():
    """示例2：查询元数据"""
    print("=" * 60)
    print("示例2：查询元数据")
    print("=" * 60)
    
    client = KlineClient()
    
    # 列出所有可用的交易所
    try:
        exchanges = client.metadata.get_exchanges()
        print(f"✅ 可用交易所: {', '.join(exchanges)}")
    except Exception as e:
        print(f"ℹ️ 无法获取交易所列表: {e}")
    
    # 查询某个交易所的交易对
    try:
        symbols = client.metadata.get_symbols('binance')
        print(f"✅ Binance 可用交易对数量: {len(symbols)}")
        if symbols:
            print(f"   前5个: {symbols[:5]}")
    except Exception as e:
        print(f"ℹ️ 无法获取交易对列表: {e}")
    
    print()


def example_3_config_info():
    """示例3：查看配置信息"""
    print("=" * 60)
    print("示例3：查看当前配置")
    print("=" * 60)
    
    from config import load_config
    
    config = load_config()
    
    print("📋 存储配置:")
    print(f"   根目录: {config.storage.root_path}")
    print(f"   格式: {config.storage.format}")
    print(f"   压缩: {config.storage.compression}")
    print(f"   按交易所分离: {config.storage.separate_by_exchange}")
    print()
    
    print("📋 CCXT配置:")
    print(f"   HTTP代理: {config.ccxt.proxy.http}")
    print(f"   限流: {config.ccxt.rate_limit.enabled}")
    print(f"   每分钟请求数: {config.ccxt.rate_limit.requests_per_minute}")
    print()
    
    print("📋 内存配置:")
    print(f"   最大使用: {config.memory.max_usage_mb} MB")
    print(f"   数据块大小: {config.memory.chunk_size}")
    print(f"   缓存: {config.memory.cache.enabled}")
    print()


if __name__ == '__main__':
    # 运行所有示例
    example_1_basic_usage()
    example_2_check_metadata()
    example_3_config_info()
    
    print("=" * 60)
    print("✅ 所有示例运行完成")
    print("=" * 60)
    print()
    print("💡 提示：")
    print("   - 这些示例都使用项目的默认配置")
    print("   - 如需修改配置，参考 external_usage_advanced.py")
    print("   - 详细文档: docs/external_usage.md")
