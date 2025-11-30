"""配置层使用示例"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from kline_data.config import ConfigManager, load_config


def example_basic_usage():
    """基本使用示例"""
    print("=" * 60)
    print("示例1: 基本使用")
    print("=" * 60)
    
    # 方式1: 使用便捷函数
    config = load_config('config/config.yaml')
    print(f"系统版本: {config.system.version}")
    print(f"存储路径: {config.storage.root_path}")
    print(f"压缩格式: {config.storage.compression}")
    print(f"支持的交易所: {', '.join(config.ccxt.exchanges)}")
    print()


def example_manager_usage():
    """使用ConfigManager示例"""
    print("=" * 60)
    print("示例2: 使用ConfigManager")
    print("=" * 60)
    
    # 获取单例实例
    manager = ConfigManager()
    
    # 加载配置
    config = manager.load('config/config.yaml')
    
    # 获取配置值（支持点号分隔）
    print(f"存储根路径: {manager.get('storage.root_path')}")
    print(f"数据块大小: {manager.get('memory.chunk_size')}")
    print(f"API端口: {manager.get('api.port')}")
    print(f"重试次数: {manager.get('ccxt.retry.max_attempts')}")
    
    # 使用默认值
    print(f"不存在的键: {manager.get('nonexistent.key', 'default_value')}")
    print()


def main():
    """运行所有示例"""
    try:
        example_basic_usage()
        example_manager_usage()
        
        print("=" * 60)
        print("✓ 所有示例运行完成")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ 错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
