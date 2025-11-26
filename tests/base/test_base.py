"""
测试基类 - 提供通用的测试功能
"""
import pytest
from unittest.mock import Mock
from typing import List, Dict, Any
import pandas as pd

from tests.helpers.mock_factory import MockFactory
from tests.helpers.sdk_adapter import SDKAdapter

class BaseTest:
    """测试基类"""

    @pytest.fixture
    def mock_client(self):
        """模拟客户端fixture"""
        return MockFactory.create_client()

    @pytest.fixture
    def mock_klines_data(self):
        """模拟K线数据fixture"""
        return MockFactory.create_klines_data()

    @pytest.fixture
    def mock_config(self):
        """模拟配置fixture"""
        return MockFactory.create_config()

    @pytest.fixture
    def mock_indicator_data(self):
        """模拟指标数据fixture"""
        return MockFactory.create_indicator_data()

    @pytest.fixture
    def sdk_adapter(self, mock_client):
        """SDK适配器fixture"""
        return SDKAdapter(mock_client)

    def assert_dataframe_valid(self, df, expected_columns: List[str] = None,
                              min_length: int = 1):
        """验证DataFrame有效性"""
        assert not df.empty, "DataFrame不能为空"
        assert len(df) >= min_length, f"DataFrame长度至少为{min_length}"

        if expected_columns:
            missing_columns = [col for col in expected_columns if col not in df.columns]
            assert not missing_columns, f"缺少列: {missing_columns}"

        # 检查NaN值
        nan_columns = df.columns[df.isnull().any()].tolist()
        if nan_columns:
            print(f"警告: 以下列包含NaN值: {nan_columns}")

    def assert_ohlc_data_valid(self, df):
        """验证OHLC数据有效性"""
        required_columns = ['open', 'high', 'low', 'close']
        self.assert_dataframe_valid(df, required_columns)

        # 验证OHLC逻辑
        assert (df['high'] >= df['low']).all(), "最高价应该大于等于最低价"
        assert (df['high'] >= df['open']).all(), "最高价应该大于等于开盘价"
        assert (df['high'] >= df['close']).all(), "最高价应该大于等于收盘价"
        assert (df['low'] <= df['open']).all(), "最低价应该小于等于开盘价"
        assert (df['low'] <= df['close']).all(), "最低价应该小于等于收盘价"

        # 验证价格为正数
        price_columns = ['open', 'high', 'low', 'close']
        for col in price_columns:
            if col in df.columns:
                assert (df[col] > 0).all(), f"{col}必须为正数"

    def assert_volume_data_valid(self, df):
        """验证成交量数据有效性"""
        if 'volume' in df.columns:
            assert (df['volume'] >= 0).all(), "成交量不能为负数"

    def assert_indicator_data_valid(self, df, indicator_name: str):
        """验证指标数据有效性"""
        assert indicator_name in df.columns, f"缺少指标列: {indicator_name}"
        assert not df[indicator_name].isnull().all(), f"指标{indicator_name}不能全部为NaN"

        # 检查指标值的合理性
        indicator_values = df[indicator_name].dropna()
        if len(indicator_values) > 0:
            assert not np.isinf(indicator_values).any(), f"{indicator_name}包含无穷大值"

    def assert_klines_compatible(self, df):
        """验证K线数据格式兼容性"""
        # 检查基本列
        basic_columns = ['open', 'high', 'low', 'close']
        self.assert_dataframe_valid(df, basic_columns)

        # 检查数据类型
        for col in basic_columns:
            if col in df.columns:
                assert pd.api.types.is_numeric_dtype(df[col]), f"{col}必须是数值类型"

        # 验证OHLC逻辑
        self.assert_ohlc_data_valid(df)

    def get_test_data(self, scenario_type: str = 'default'):
        """获取测试场景数据"""
        scenario = MockFactory.create_test_scenario(scenario_type)
        return scenario['klines']

    def assert_client_interface_compatible(self, adapter):
        """验证客户端接口兼容性"""
        assert adapter.is_compatible_with_tests(), "客户端接口与测试不兼容"

        supported_methods = adapter.get_supported_methods()
        assert supported_methods['unified_interface'], "必须支持统一接口"

    def assert_mock_calls_made(self, mock_obj, expected_calls: int = 1):
        """验证Mock对象被调用"""
        assert mock_obj.call_count >= expected_calls, f"Mock对象至少应该被调用{expected_calls}次"


class BaseIndicatorTest(BaseTest):
    """指标测试基类"""

    @pytest.fixture
    def sample_data(self):
        """示例数据fixture"""
        return MockFactory.create_klines_data(length=100)

    @pytest.fixture
    def short_data(self):
        """短数据fixture（用于边界测试）"""
        return MockFactory.create_klines_data(length=20)

    def assert_indicator_calculation_correct(self, indicator, df, expected_columns: List[str]):
        """验证指标计算正确性"""
        result = indicator.calculate(df)

        # 验证返回格式
        assert isinstance(result, pd.DataFrame), "指标计算应该返回DataFrame"
        assert len(result) == len(df), "结果DataFrame长度应该与输入相同"

        # 验证包含期望的列
        missing_columns = [col for col in expected_columns if col not in result.columns]
        assert not missing_columns, f"缺少指标列: {missing_columns}"

        # 验证指标值的有效性
        for col in expected_columns:
            self.assert_indicator_data_valid(result, col)

    def assert_indicator_handles_empty_data(self, indicator):
        """验证指标处理空数据"""
        empty_df = MockFactory.create_empty_klines_data()

        with pytest.raises((ValueError, IndexError)):
            indicator.calculate(empty_df)

    def assert_indicator_handles_insufficient_data(self, indicator, df):
        """验证指标处理数据不足的情况"""
        # 取很短的数据段
        short_df = df.head(5)

        with pytest.raises((ValueError, IndexError)):
            indicator.calculate(short_df)

    def assert_indicator_params_validation(self, indicator, df):
        """验证指标参数验证"""
        # 测试无效周期
        with pytest.raises(ValueError):
            indicator.calculate(df, period=0)

        with pytest.raises(ValueError):
            indicator.calculate(df, period=-1)


class BaseSDKTest(BaseTest):
    """SDK测试基类"""

    @pytest.fixture(autouse=True)
    def setup_sdk_adapter(self, mock_client):
        """设置SDK适配器"""
        self.adapter = SDKAdapter(mock_client)
        yield
        # 清理资源
        pass

    def get_klines_data(self, exchange: str = "binance",
                       symbol: str = "BTC/USDT",
                       timeframe: str = "1h",
                       limit: int = 100,
                       before = None) -> pd.DataFrame:
        """统一的K线数据获取方法"""
        return self.adapter.get_klines(
            exchange=exchange,
            symbol=symbol,
            timeframe=timeframe,
            limit=limit,
            before=before
        )

    def assert_get_klines_works(self):
        """验证get_klines方法工作正常"""
        df = self.get_klines_data()
        self.assert_klines_compatible(df)

    def assert_interface_info_available(self):
        """验证接口信息可用"""
        info = self.adapter.get_interface_info()
        assert isinstance(info, str)
        assert len(info) > 0

    def assert_supported_methods_available(self):
        """验证支持的方法列表可用"""
        methods = self.adapter.get_supported_methods()
        assert isinstance(methods, dict)
        assert 'unified_interface' in methods

    def test_sdk_adapter_basic_functionality(self):
        """测试SDK适配器基本功能"""
        self.assert_client_interface_compatible(self.adapter)
        self.assert_interface_info_available()
        self.assert_supported_methods_available()


# 导入numpy用于类型检查
try:
    import numpy as np
except ImportError:
    # 如果numpy不可用，创建一个简单的替代
    class np:
        @staticmethod
        def isinf(arr):
            return [False] * len(arr) if hasattr(arr, '__len__') else False

        @staticmethod
        def isnan(arr):
            return [False] * len(arr) if hasattr(arr, '__len__') else False