"""
pytest配置文件 - 全局fixtures和测试配置

这个文件包含了所有测试共用的fixtures、配置和辅助函数。
遵循伦敦学派TDD方法，重点关注对象间的协作和交互。
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import pytest
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Generator, Optional
import logging

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 配置日志
logging.basicConfig(level=logging.WARNING)

# 配置pytest插件
pytest_plugins = ["pytest_benchmark"]


# ============================================================================
# 测试配置
# ============================================================================

@pytest.fixture(scope="session")
def test_config() -> Dict[str, Any]:
    """测试配置数据"""
    return {
        "exchange": "binance",
        "symbol": "BTC/USDT",
        "interval": "1h",
        "start_time": datetime(2024, 1, 1),
        "end_time": datetime(2024, 1, 2),
        "test_data_dir": Path(__file__).parent / "test_data",
        "temp_dir": Path(tempfile.gettempdir()) / "kline_tests"
    }


# ============================================================================
# Mock Fixtures - 伦敦学派TDD的核心：定义对象间的契约
# ============================================================================

@pytest.fixture
def mock_config() -> Mock:
    """Mock配置对象 - 定义配置服务的契约"""
    config = Mock()
    config.exchange = "binance"
    config.symbol = "BTC/USDT"
    config.interval = "1h"
    config.data_dir = Path("/tmp/test_data")
    config.cache_dir = Path("/tmp/test_cache")
    config.api_rate_limit = 1200
    config.max_retries = 3
    config.chunk_size = 10000
    return config


@pytest.fixture
def mock_data_fetcher() -> Mock:
    """Mock数据获取器 - 定义数据获取服务的契约"""
    fetcher = Mock()
    # 定义方法签名和行为
    fetcher.fetch_range.return_value = pd.DataFrame({
        'timestamp': pd.date_range('2024-01-01', periods=24, freq='1h'),
        'open': np.random.uniform(40000, 41000, 24),
        'high': np.random.uniform(41000, 42000, 24),
        'low': np.random.uniform(39000, 40000, 24),
        'close': np.random.uniform(40000, 41000, 24),
        'volume': np.random.uniform(100, 1000, 24)
    })
    return fetcher


@pytest.fixture
def mock_metadata_manager() -> Mock:
    """Mock元数据管理器 - 定义元数据服务的契约"""
    manager = Mock()
    manager.get_earliest_time.return_value = datetime(2020, 1, 1)
    manager.get_latest_time.return_value = datetime(2024, 1, 1)
    manager.has_data.return_value = True
    manager.get_metadata.return_value = {
        'earliest_time': datetime(2020, 1, 1),
        'latest_time': datetime(2024, 1, 1),
        'total_records': 100000
    }
    return manager


@pytest.fixture
def mock_parquet_reader() -> Mock:
    """Mock Parquet读取器 - 定义文件读取服务的契约"""
    reader = Mock()
    test_data = pd.DataFrame({
        'timestamp': pd.date_range('2024-01-01', periods=24, freq='1h'),
        'open': np.random.uniform(40000, 41000, 24),
        'high': np.random.uniform(41000, 42000, 24),
        'low': np.random.uniform(39000, 40000, 24),
        'close': np.random.uniform(40000, 41000, 24),
        'volume': np.random.uniform(100, 1000, 24)
    })
    reader.read_range.return_value = test_data
    reader.read_latest.return_value = test_data.tail(1)
    return reader


@pytest.fixture
def mock_download_manager() -> Mock:
    """Mock下载管理器 - 定义下载服务的契约"""
    manager = Mock()
    manager.download_range.return_value = True
    manager.get_progress.return_value = 0.5
    manager.is_completed.return_value = True
    return manager


@pytest.fixture
def mock_indicator_manager() -> Mock:
    """Mock指标管理器 - 定义指标计算服务的契约"""
    manager = Mock()
    manager.calculate.return_value = {
        'sma': np.random.uniform(40000, 41000, 24),
        'rsi': np.random.uniform(30, 70, 24),
        'macd': np.random.uniform(-100, 100, 24)
    }
    manager.calculate_batch.return_value = {
        'sma': np.random.uniform(40000, 41000, 24),
        'ema': np.random.uniform(40000, 41000, 24),
        'bollinger_upper': np.random.uniform(41000, 42000, 24),
        'bollinger_lower': np.random.uniform(39000, 40000, 24)
    }
    return manager


# ============================================================================
# 数据生成器Fixtures - 提供一致的测试数据
# ============================================================================

@pytest.fixture
def sample_kline_data() -> pd.DataFrame:
    """生成示例K线数据"""
    np.random.seed(42)  # 确保可重现的测试数据
    periods = 100

    timestamps = pd.date_range('2024-01-01', periods=periods, freq='1h')
    base_price = 40000

    # 生成更真实的价格数据
    returns = np.random.normal(0, 0.002, periods)  # 0.2% 标准差
    prices = [base_price]

    for i in range(1, periods):
        prices.append(prices[-1] * (1 + returns[i]))

    prices = np.array(prices)

    # 生成OHLCV数据
    high_noise = np.random.uniform(0, 0.01, periods)  # 最高价噪音
    low_noise = np.random.uniform(0, 0.01, periods)   # 最低价噪音

    data = {
        'timestamp': timestamps,
        'open': prices,
        'high': prices * (1 + high_noise),
        'low': prices * (1 - low_noise),
        'close': np.roll(prices, -1),  # 下一期作为收盘价
        'volume': np.random.uniform(100, 1000, periods)
    }

    return pd.DataFrame(data)


@pytest.fixture
def sample_kline_data_list() -> List[Dict[str, Any]]:
    """生成示例K线数据列表格式"""
    data = []
    base_time = int(datetime(2024, 1, 1).timestamp() * 1000)
    base_price = 40000

    for i in range(24):
        timestamp = base_time + i * 3600000  # 每小时
        price_variation = np.random.uniform(-0.01, 0.01) * base_price

        data.append({
            'timestamp': timestamp,
            'open': base_price + price_variation,
            'high': base_price + abs(price_variation) + np.random.uniform(0, 100),
            'low': base_price - abs(price_variation) - np.random.uniform(0, 100),
            'close': base_price + np.random.uniform(-0.005, 0.005) * base_price,
            'volume': np.random.uniform(100, 1000)
        })

        base_price = data[-1]['close']

    return data


# ============================================================================
# 目录管理Fixtures - 提供隔离的测试环境
# ============================================================================

@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """创建临时目录"""
    temp_path = Path(tempfile.mkdtemp())
    try:
        yield temp_path
    finally:
        shutil.rmtree(temp_path)


@pytest.fixture
def test_data_dir(temp_dir: Path) -> Path:
    """创建测试数据目录"""
    data_dir = temp_dir / "test_data"
    data_dir.mkdir(exist_ok=True)
    return data_dir


@pytest.fixture
def mock_config_file(test_data_dir: Path) -> Path:
    """创建模拟配置文件"""
    config_data = {
        'exchange': 'binance',
        'symbol': 'BTC/USDT',
        'interval': '1h',
        'data_dir': str(test_data_dir),
        'cache_dir': str(test_data_dir / 'cache'),
        'api_rate_limit': 1200,
        'max_retries': 3
    }

    config_file = test_data_dir / 'config.yaml'
    import yaml
    with open(config_file, 'w') as f:
        yaml.dump(config_data, f)

    return config_file


# ============================================================================
# 异常处理Fixtures - 测试错误场景
# ============================================================================

@pytest.fixture
def mock_fetcher_with_error() -> Mock:
    """会抛出异常的Mock获取器"""
    fetcher = Mock()
    fetcher.fetch_range.side_effect = Exception("Network error")
    fetcher.read_range.side_effect = FileNotFoundError("File not found")
    return fetcher


@pytest.fixture
def mock_config_with_error() -> Mock:
    """配置错误的Mock配置"""
    config = Mock()
    config.exchange = "invalid_exchange"
    config.symbol = ""
    config.interval = "invalid_interval"
    config.data_dir = Path("/invalid/path")
    return config


# ============================================================================
# 协作验证Fixtures - 伦敦学派TDD的关键工具
# ============================================================================

@pytest.fixture
def interaction_recorder() -> Dict[str, List[tuple]]:
    """记录对象间交互的工具"""
    return {}


@pytest.fixture
def mock_with_recording(interaction_recorder: Dict[str, List[tuple]]) -> Mock:
    """带交互记录功能的Mock工厂"""

    def create_mock(name: str) -> Mock:
        mock = Mock()

        def record_call(method_name: str, *args, **kwargs):
            interaction_recorder.setdefault(name, []).append((method_name, args, kwargs))
            return getattr(mock, f"_original_{method_name}")(*args, **kwargs)

        # 为所有方法添加记录功能
        for attr_name in dir(mock):
            if not attr_name.startswith('_') and callable(getattr(mock, attr_name)):
                original_method = getattr(mock, attr_name)
                setattr(mock, f"_original_{attr_name}", original_method)
                setattr(mock, attr_name, lambda *args, method=attr_name, **kwargs: record_call(method, *args, **kwargs))

        return mock

    return create_mock


# ============================================================================
# 性能测试Fixtures
# ============================================================================

@pytest.fixture
def performance_timer():
    """性能计时器"""
    import time

    class Timer:
        def __init__(self):
            self.start_time = None
            self.end_time = None

        def start(self):
            self.start_time = time.time()

        def stop(self):
            self.end_time = time.time()

        @property
        def elapsed(self):
            if self.start_time and self.end_time:
                return self.end_time - self.start_time
            return None

    return Timer()


# ============================================================================
# 标记和测试分类
# ============================================================================

def pytest_configure(config):
    """配置pytest标记"""
    config.addinivalue_line(
        "markers", "unit: 单元测试"
    )
    config.addinivalue_line(
        "markers", "integration: 集成测试"
    )
    config.addinivalue_line(
        "markers", "performance: 性能测试"
    )
    config.addinivalue_line(
        "markers", "slow: 慢速测试"
    )
    config.addinivalue_line(
        "markers", "mock: Mock测试"
    )
    config.addinivalue_line(
        "markers", "contract: 契约测试"
    )


# ============================================================================
# 辅助函数 - 伦敦学派TDD的工具函数
# ============================================================================

def verify_interaction_sequence(interactions: List[tuple], expected_sequence: List[tuple]) -> bool:
    """验证交互序列 - 伦敦学派TDD的核心"""
    if len(interactions) != len(expected_sequence):
        return False

    for actual, expected in zip(interactions, expected_sequence):
        if actual[0] != expected[0]:  # 方法名不匹配
            return False
        if len(actual) >= 2 and len(expected) >= 2:
            if actual[1] != expected[1]:  # 参数不匹配
                return False

    return True


def create_contract_mock(contract_methods: Dict[str, Any]) -> Mock:
    """创建基于契约的Mock对象"""
    mock = Mock()

    for method_name, return_value in contract_methods.items():
        setattr(mock, method_name, Mock(return_value=return_value))

    return mock


def assert_mock_calls_in_order(mock_obj: Mock, expected_calls: List[tuple]):
    """断言Mock调用顺序"""
    actual_calls = [(call[0], call[1], call[2]) for call in mock_obj.call_args_list]

    assert len(actual_calls) == len(expected_calls), \
        f"Expected {len(expected_calls)} calls, got {len(actual_calls)}"

    for i, (actual, expected) in enumerate(zip(actual_calls, expected_calls)):
        assert actual[0] == expected[0], \
            f"Call {i}: expected method '{expected[0]}', got '{actual[0]}'"

        if len(expected) > 1:
            assert actual[1] == expected[1], \
                f"Call {i}: expected args {expected[1]}, got {actual[1]}"


class MockContract:
    """Mock契约定义类"""

    def __init__(self, name: str):
        self.name = name
        self.methods = {}

    def define_method(self, method_name: str, return_value: Any = None,
                     side_effect: Any = None):
        """定义方法契约"""
        self.methods[method_name] = {
            'return_value': return_value,
            'side_effect': side_effect
        }
        return self

    def create_mock(self) -> Mock:
        """基于契约创建Mock对象"""
        mock = Mock()

        for method_name, spec in self.methods.items():
            method = Mock(return_value=spec['return_value'])
            if spec['side_effect']:
                method.side_effect = spec['side_effect']
            setattr(mock, method_name, method)

        return mock

    def verify_contract(self, mock_obj: Mock) -> bool:
        """验证Mock对象是否符合契约"""
        for method_name in self.methods:
            if not hasattr(mock_obj, method_name):
                return False
            if not callable(getattr(mock_obj, method_name)):
                return False
        return True