"""
外部项目使用示例 - 高级模式

这个示例展示如何在外部项目中自定义配置使用 kline-data

注意：
- 外部项目使用时导入: from kline_data.config import load_config
- 项目内部测试时导入: from config import load_config
"""

import sys
from pathlib import Path

# 仅用于项目内部测试，外部使用时删除这段
if __name__ == '__main__':
    project_root = Path(__file__).parent.parent
    sys.path.insert(0, str(project_root))

from kline_data.config import load_config, Config
from kline_data.sdk import KlineClient
from datetime import datetime, timedelta


def example_1_modify_config():
    """示例1：修改部分配置"""
    print("=" * 60)
    print("示例1：加载默认配置并修改")
    print("=" * 60)
    
    # 加载默认配置
    config = load_config()
    
    # 修改需要的配置项
    config.storage.root_path = '/tmp/my_kline_data'
    config.ccxt.proxy.http = 'http://my-proxy:7890'
    config.ccxt.proxy.https = 'http://my-proxy:7890'
    config.system.log_level = 'DEBUG'
    
    print("✅ 配置修改成功:")
    print(f"   存储路径: {config.storage.root_path}")
    print(f"   HTTP代理: {config.ccxt.proxy.http}")
    print(f"   日志级别: {config.system.log_level}")
    print()
    
    # 使用修改后的配置创建客户端
    client = KlineClient(config=config)
    print("✅ 客户端创建成功")
    print()


def example_2_create_config():
    """示例2：从头创建配置对象"""
    print("=" * 60)
    print("示例2：创建自定义配置对象")
    print("=" * 60)
    
    # 创建完全自定义的配置
    config = Config(
        system={
            'version': '1.0.0',
            'log_level': 'INFO',
            'log_path': './my_logs'
        },
        storage={
            'root_path': '/path/to/my/data',
            'separate_by_exchange': True,
            'separate_by_symbol': True,
            'format': 'parquet',
            'compression': 'snappy',
            'partition': {
                'enabled': True,
                'granularity': 'month'
            },
            'retention': {
                'enabled': False,
                'days': 365
            }
        },
        ccxt={
            'proxy': {
                'http': 'http://127.0.0.1:7890',
                'https': 'http://127.0.0.1:7890'
            },
            'rate_limit': {
                'enabled': True,
                'requests_per_minute': 1200
            },
            'retry': {
                'max_attempts': 3,
                'backoff_factor': 2,
                'timeout': 30
            },
            'exchanges': ['binance', 'okx', 'bybit']
        },
        memory={
            'max_usage_mb': 2048,  # 增加内存限制
            'chunk_size': 100000,
            'cache': {
                'enabled': True,
                'max_size_mb': 1024,
                'ttl_seconds': 3600
            }
        },
        indicators={
            'defaults': {
                'ma_periods': [5, 10, 20, 50, 200],
                'ema_periods': [12, 26],
                'boll_period': 20,
                'boll_std': 2,
                'rsi_period': 14,
                'macd': [12, 26, 9]
            },
            'batch_compute': True
        },
        api={
            'host': '0.0.0.0',
            'port': 8000,
            'workers': 4,
            'auth': {
                'enabled': False,
                'api_key': ''
            },
            'rate_limit': {
                'enabled': True,
                'requests_per_minute': 1000
            },
            'cors': {
                'enabled': True,
                'origins': ['*']
            }
        },
        cli={
            'default_exchange': 'binance',
            'default_symbol': 'BTC/USDT',
            'output_format': 'table'
        }
    )
    
    print("✅ 自定义配置创建成功")
    print(f"   存储路径: {config.storage.root_path}")
    print(f"   内存限制: {config.memory.max_usage_mb} MB")
    print()
    
    # 使用自定义配置创建客户端
    client = KlineClient(config=config)
    print("✅ 客户端创建成功")
    print()


def example_3_config_file():
    """示例3：使用配置文件"""
    print("=" * 60)
    print("示例3：从配置文件加载")
    print("=" * 60)
    
    # 方式1：指定配置文件路径
    try:
        config = load_config('/path/to/your/config.yaml')
        client = KlineClient(config=config)
        print("✅ 从指定路径加载配置成功")
    except FileNotFoundError:
        print("ℹ️ 配置文件不存在（这是示例，实际使用时需要提供真实路径）")
    
    # 方式2：从当前目录自动查找
    # load_config() 会按以下顺序查找：
    # 1. 当前目录的 config/config.yaml
    # 2. 包安装目录的 config/config.yaml
    # 3. 用户主目录的 ~/.kline_data/config.yaml
    config = load_config()
    print(f"✅ 自动查找配置成功")
    print()


def example_4_environment_specific():
    """示例4：环境特定配置"""
    print("=" * 60)
    print("示例4：不同环境使用不同配置")
    print("=" * 60)
    
    import os
    
    # 根据环境变量选择配置
    env = os.getenv('ENV', 'development')
    
    config = load_config()
    
    if env == 'production':
        config.storage.root_path = '/data/production/kline_data'
        config.system.log_level = 'WARNING'
        config.ccxt.rate_limit.requests_per_minute = 600  # 生产环境更保守
    elif env == 'development':
        config.storage.root_path = './dev_data'
        config.system.log_level = 'DEBUG'
    elif env == 'testing':
        config.storage.root_path = '/tmp/test_kline_data'
        config.system.log_level = 'INFO'
    
    print(f"✅ 环境: {env}")
    print(f"   存储路径: {config.storage.root_path}")
    print(f"   日志级别: {config.system.log_level}")
    print()
    
    client = KlineClient(config=config)
    print("✅ 客户端创建成功")
    print()


def example_5_multiple_clients():
    """示例5：多个客户端使用不同配置"""
    print("=" * 60)
    print("示例5：同时使用多个配置")
    print("=" * 60)
    
    # 客户端1：使用默认配置，连接生产数据
    config1 = load_config()
    client1 = KlineClient(config=config1)
    print(f"✅ 客户端1: {config1.storage.root_path}")
    
    # 客户端2：使用自定义配置，连接测试数据
    config2 = load_config()
    config2.storage.root_path = '/tmp/test_data'
    config2.ccxt.proxy.http = None  # 测试环境不使用代理
    client2 = KlineClient(config=config2)
    print(f"✅ 客户端2: {config2.storage.root_path}")
    
    print()
    print("💡 两个客户端可以独立操作不同的数据源")
    print()


if __name__ == '__main__':
    # 运行所有示例
    example_1_modify_config()
    example_2_create_config()
    example_3_config_file()
    example_4_environment_specific()
    example_5_multiple_clients()
    
    print("=" * 60)
    print("✅ 所有高级示例运行完成")
    print("=" * 60)
    print()
    print("💡 配置优先级:")
    print("   1. 显式传入的 Config 对象")
    print("   2. 指定路径的配置文件")
    print("   3. 当前目录的 config/config.yaml")
    print("   4. 包安装目录的 config/config.yaml (项目配置)")
    print("   5. ~/.kline_data/config.yaml")
    print()
    print("📖 详细文档: docs/external_usage.md")
