"""配置层测试"""

import pytest
from pathlib import Path
import tempfile
import yaml
from config import ConfigManager, load_config, get_config
from config.schemas import Config

# 导入全局常量
from utils.constants import (
    Timeframe,
    DEFAULT_EXCHANGE,
    DEFAULT_SYMBOL,
    SUPPORTED_EXCHANGES,
    DEFAULT_LOG_LEVEL,
    DEFAULT_STORAGE_FORMAT,
    DEFAULT_COMPRESSION,
    SUPPORTED_STORAGE_FORMATS,
    SUPPORTED_COMPRESSIONS,
    COMMON_INTERVALS,
    PRECOMPUTE_INTERVALS,
)


class TestConfigManager:
    """测试ConfigManager类"""
    
    @pytest.fixture
    def temp_config_file(self):
        """创建临时配置文件"""
        config_data = {
            'system': {
                'version': '1.0.0',
                'log_level': DEFAULT_LOG_LEVEL,
                'log_path': './logs'
            },
            'storage': {
                'root_path': './data',
                'separate_by_exchange': True,
                'separate_by_symbol': True,
                'format': DEFAULT_STORAGE_FORMAT,
                'compression': DEFAULT_COMPRESSION,
                'partition': {
                    'enabled': True,
                    'granularity': 'month'
                },
                'retention': {
                    'enabled': False,
                    'days': 365
                }
            },
            'ccxt': {
                'proxy': {
                    'http': None,
                    'https': None
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
                'exchanges': [DEFAULT_EXCHANGE, 'okx']
            },
            'memory': {
                'max_usage_mb': 4096,
                'chunk_size': 100000,
                'cache': {
                    'enabled': True,
                    'max_size_mb': 512,
                    'ttl_seconds': 3600
                }
            },
            'resampling': {
                'supported_intervals': ['1s', Timeframe.M1.value, Timeframe.H1.value],
                'precompute_intervals': [Timeframe.M1.value],
                'aggregation': {
                    'open': 'first',
                    'high': 'max',
                    'low': 'min',
                    'close': 'last',
                    'volume': 'sum'
                }
            },
            'indicators': {
                'defaults': {
                    'ma_periods': [5, 10, 20],
                    'ema_periods': [12, 26],
                    'boll_period': 20,
                    'boll_std': 2.0,
                    'rsi_period': 14,
                    'macd': [12, 26, 9]
                },
                'batch_compute': True
            },
            'api': {
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
            'cli': {
                'default_exchange': DEFAULT_EXCHANGE,
                'default_symbol': DEFAULT_SYMBOL,
                'output_format': 'table'
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.safe_dump(config_data, f)
            temp_path = f.name
        
        yield temp_path
        
        # 清理
        Path(temp_path).unlink()
    
    @pytest.fixture(autouse=True)
    def reset_manager(self):
        """每个测试前重置ConfigManager"""
        manager = ConfigManager()
        manager.reset()
        yield
        manager.reset()
    
    def test_singleton_pattern(self):
        """测试单例模式"""
        manager1 = ConfigManager()
        manager2 = ConfigManager()
        assert manager1 is manager2
    
    def test_load_config(self, temp_config_file):
        """测试加载配置"""
        manager = ConfigManager()
        config = manager.load(temp_config_file)
        
        assert isinstance(config, Config)
        assert config.system.version == '1.0.0'
        assert config.storage.root_path == './data'
        assert DEFAULT_EXCHANGE in config.ccxt.exchanges
    
    def test_load_nonexistent_file(self):
        """测试加载不存在的文件"""
        manager = ConfigManager()
        with pytest.raises(FileNotFoundError):
            manager.load('nonexistent.yaml')
    
    def test_get_config_value(self, temp_config_file):
        """测试获取配置值"""
        manager = ConfigManager()
        manager.load(temp_config_file)
        
        # 测试嵌套键
        assert manager.get('storage.root_path') == './data'
        assert manager.get('storage.compression') == DEFAULT_COMPRESSION
        assert manager.get('ccxt.retry.max_attempts') == 3
        
        # 测试默认值
        assert manager.get('nonexistent.key', 'default') == 'default'
    
    def test_get_without_load(self):
        """测试未加载时获取配置"""
        manager = ConfigManager()
        with pytest.raises(RuntimeError):
            manager.get('storage.root_path')
    
    def test_get_config_object(self, temp_config_file):
        """测试获取配置对象"""
        manager = ConfigManager()
        manager.load(temp_config_file)
        
        config = manager.get_config()
        assert isinstance(config, Config)
        assert config.storage.compression == DEFAULT_COMPRESSION
    
    def test_update_config(self, temp_config_file):
        """测试更新配置"""
        manager = ConfigManager()
        manager.load(temp_config_file)
        
        # 更新值
        manager.update('storage.compression', 'gzip')
        assert manager.get('storage.compression') == 'gzip'
        
        # 更新嵌套值
        manager.update('ccxt.retry.max_attempts', 5)
        assert manager.get('ccxt.retry.max_attempts') == 5
    
    def test_update_invalid_key(self, temp_config_file):
        """测试更新不存在的键"""
        manager = ConfigManager()
        manager.load(temp_config_file)
        
        with pytest.raises(ValueError):
            manager.update('nonexistent.key', 'value')
    
    def test_update_invalid_value(self, temp_config_file):
        """测试更新无效的值"""
        manager = ConfigManager()
        manager.load(temp_config_file)
        
        # 压缩格式验证
        with pytest.raises(ValueError):
            manager.update('storage.compression', 'invalid_compression')
    
    def test_save_config(self, temp_config_file):
        """测试保存配置"""
        manager = ConfigManager()
        manager.load(temp_config_file)
        
        # 修改配置
        manager.update('storage.compression', 'gzip')
        
        # 保存到新文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            new_path = f.name
        
        try:
            manager.save(new_path)
            
            # 验证保存的文件
            with open(new_path, 'r') as f:
                saved_data = yaml.safe_load(f)
            
            assert saved_data['storage']['compression'] == 'gzip'
        finally:
            Path(new_path).unlink()
    
    def test_reload_config(self, temp_config_file):
        """测试重新加载配置"""
        manager = ConfigManager()
        manager.load(temp_config_file)
        
        # 修改配置
        manager.update('storage.compression', 'gzip')
        
        # 重新加载
        config = manager.reload()
        
        # 应该恢复到文件中的值
        assert config.storage.compression == DEFAULT_COMPRESSION
    
    def test_validate_config(self, temp_config_file):
        """测试验证配置"""
        manager = ConfigManager()
        manager.load(temp_config_file)
        
        assert manager.validate() is True
    
    def test_to_dict(self, temp_config_file):
        """测试转换为字典"""
        manager = ConfigManager()
        manager.load(temp_config_file)
        
        config_dict = manager.to_dict()
        assert isinstance(config_dict, dict)
        assert 'storage' in config_dict
        assert config_dict['storage']['compression'] == DEFAULT_COMPRESSION
    
    def test_to_json(self, temp_config_file):
        """测试转换为JSON"""
        manager = ConfigManager()
        manager.load(temp_config_file)
        
        json_str = manager.to_json()
        assert isinstance(json_str, str)
        assert 'storage' in json_str
        assert DEFAULT_COMPRESSION in json_str


class TestConfigSchema:
    """测试配置数据模型"""
    
    def test_storage_config_validation(self):
        """测试存储配置验证"""
        from config.schemas import StorageConfig
        
        # 有效配置
        config = StorageConfig(
            root_path='./data',
            compression=DEFAULT_COMPRESSION
        )
        assert config.compression == DEFAULT_COMPRESSION
        
        # 无效压缩格式
        with pytest.raises(ValueError):
            StorageConfig(
                root_path='./data',
                compression='invalid'
            )
    
    def test_ccxt_config_validation(self):
        """测试CCXT配置验证"""
        from config.schemas import CCXTConfig
        
        # 有效配置
        config = CCXTConfig(
            exchanges=[DEFAULT_EXCHANGE, 'okx']
        )
        assert len(config.exchanges) == 2
        
        # 空交易所列表
        with pytest.raises(ValueError):
            CCXTConfig(exchanges=[])
    
    def test_memory_config_validation(self):
        """测试内存配置验证"""
        from config.schemas import MemoryConfig
        
        # 有效配置
        config = MemoryConfig(
            max_usage_mb=4096,
            chunk_size=100000
        )
        assert config.max_usage_mb == 4096
        
        # 无效值
        with pytest.raises(ValueError):
            MemoryConfig(max_usage_mb=-1)
        
        with pytest.raises(ValueError):
            MemoryConfig(chunk_size=0)
    
    def test_api_config_validation(self):
        """测试API配置验证"""
        from config.schemas import APIConfig
        
        # 有效配置
        config = APIConfig(
            host='0.0.0.0',
            port=8000,
            workers=4
        )
        assert config.port == 8000
        
        # 无效端口
        with pytest.raises(ValueError):
            APIConfig(port=70000)
        
        # 无效workers数量
        with pytest.raises(ValueError):
            APIConfig(workers=0)


class TestConvenienceFunctions:
    """测试便捷函数"""
    
    @pytest.fixture(autouse=True)
    def reset_manager(self):
        """每个测试前重置ConfigManager"""
        manager = ConfigManager()
        manager.reset()
        yield
        manager.reset()
    
    def test_load_config_function(self, temp_config_file):
        """测试load_config便捷函数"""
        config = load_config(temp_config_file)
        assert isinstance(config, Config)
        assert config.system.version == '1.0.0'
    
    def test_get_config_function(self, temp_config_file):
        """测试get_config便捷函数"""
        # 先加载
        load_config(temp_config_file)
        
        # 获取配置
        config = get_config()
        assert isinstance(config, Config)
        assert config.storage.root_path == './data'
    
    def test_get_config_without_load(self):
        """测试未加载时使用get_config"""
        with pytest.raises(RuntimeError):
            get_config()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
