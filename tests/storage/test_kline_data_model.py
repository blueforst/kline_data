"""
KlineData模型单元测试 - 伦敦学派TDD方法

测试重点：
1. 数据模型的契约验证
2. 数据验证的行为测试
3. 模型转换和序列化
4. 边界条件和异常处理
5. 模型间的协作关系
"""

import pytest
from datetime import datetime
import pandas as pd
import numpy as np

from storage.models import KlineData, TaskStatus


class TestKlineDataContract:
    """KlineData契约测试 - 定义和验证数据模型契约"""

    @pytest.mark.unit
    @pytest.mark.contract
    def test_kline_data_structure_contract(self):
        """
        测试KlineData数据结构契约
        验证：必须包含的属性和类型
        """
        # Arrange - 定义契约属性
        required_attributes = {
            'timestamp': int,
            'open': float,
            'high': float,
            'low': float,
            'close': float,
            'volume': float
        }

        required_methods = {
            'to_dict': dict,
            'validate': callable,
            '__post_init__': callable
        }

        # Act - 创建KlineData实例
        timestamp = int(datetime(2024, 1, 1).timestamp() * 1000)
        kline = KlineData(
            timestamp=timestamp,
            open=40000.0,
            high=41000.0,
            low=39000.0,
            close=40500.0,
            volume=1000.0
        )

        # Assert - 验证属性契约
        for attr_name, expected_type in required_attributes.items():
            assert hasattr(kline, attr_name), f"KlineData应该有{attr_name}属性"
            value = getattr(kline, attr_name)
            assert isinstance(value, expected_type), \
                f"{attr_name}应该是{expected_type.__name__}类型，实际是{type(value).__name__}"

        # 验证方法契约
        for method_name, expected_return in required_methods.items():
            assert hasattr(kline, method_name), f"KlineData应该有{method_name}方法"
            method = getattr(kline, method_name)
            assert callable(method), f"{method_name}应该是可调用的"

    @pytest.mark.unit
    @pytest.mark.contract
    def test_task_status_enum_contract(self):
        """
        测试TaskStatus枚举契约
        验证：枚举值的完整性和类型
        """
        # Arrange - 定义预期的状态值
        expected_statuses = ['pending', 'running', 'completed', 'failed', 'cancelled']

        # Act & Assert - 验证枚举契约
        for status in expected_statuses:
            assert hasattr(TaskStatus, status.upper()), f"TaskStatus应该有{status.upper()}状态"
            enum_value = getattr(TaskStatus, status.upper())
            assert isinstance(enum_value, str), f"枚举值应该是字符串类型"
            assert enum_value == status, f"枚举值应该是{status}"

        # 验证TaskStatus是枚举类型
        assert hasattr(TaskStatus, '__members__'), "TaskStatus应该有__members__属性"
        assert len(TaskStatus.__members__) == len(expected_statuses), \
            f"TaskStatus应该有{len(expected_statuses)}个状态值"

    @pytest.mark.unit
    @pytest.mark.contract
    def test_kline_data_validation_contract(self):
        """
        测试KlineData验证契约
        验证：数据验证规则的完整性
        """
        # Arrange - 定义验证规则契约
        validation_rules = {
            'high_ge_low': lambda high, low: high >= low,
            'high_ge_open_close': lambda high, open_price, close_price: high >= open_price and high >= close_price,
            'low_le_open_close': lambda low, open_price, close_price: low <= open_price and low <= close_price,
            'volume_non_negative': lambda volume: volume >= 0
        }

        # Act - 测试验证契约
        for rule_name, rule_func in validation_rules.items():
            # 创建有效数据
            valid_data = {
                'timestamp': int(datetime(2024, 1, 1).timestamp() * 1000),
                'open': 40000.0,
                'high': 41000.0,
                'low': 39000.0,
                'close': 40500.0,
                'volume': 1000.0
            }

            # 验证有效数据通过规则
            kline = KlineData(**valid_data)

            if rule_name == 'high_ge_low':
                assert rule_func(kline.high, kline.low), f"规则{rule_name}应该通过"
            elif rule_name == 'high_ge_open_close':
                assert rule_func(kline.high, kline.open, kline.close), f"规则{rule_name}应该通过"
            elif rule_name == 'low_le_open_close':
                assert rule_func(kline.low, kline.open, kline.close), f"规则{rule_name}应该通过"
            elif rule_name == 'volume_non_negative':
                assert rule_func(kline.volume), f"规则{rule_name}应该通过"


class TestKlineDataValidation:
    """KlineData验证测试 - 验证数据模型的验证逻辑"""

    @pytest.mark.unit
    @pytest.mark.mock
    def test_valid_data_creation(self):
        """
        测试有效数据创建
        验证：正确的数据能够成功创建模型
        """
        # Arrange - 准备有效数据
        timestamp = int(datetime(2024, 1, 1, 12, 0, 0).timestamp() * 1000)
        valid_data = {
            'timestamp': timestamp,
            'open': 40000.0,
            'high': 41000.0,
            'low': 39000.0,
            'close': 40500.0,
            'volume': 1500.0
        }

        # Act - 创建KlineData实例
        kline = KlineData(**valid_data)

        # Assert - 验证数据正确设置
        assert kline.timestamp == timestamp
        assert kline.open == 40000.0
        assert kline.high == 41000.0
        assert kline.low == 39000.0
        assert kline.close == 40500.0
        assert kline.volume == 1500.0

    @pytest.mark.unit
    @pytest.mark.mock
    def test_invalid_high_low_validation(self):
        """
        测试无效高低价验证
        验证：当最高价低于最低价时抛出异常
        """
        # Arrange - 准备无效数据（high < low）
        timestamp = int(datetime(2024, 1, 1).timestamp() * 1000)
        invalid_data = {
            'timestamp': timestamp,
            'open': 40000.0,
            'high': 38000.0,  # 低于最低价
            'low': 39000.0,
            'close': 38500.0,
            'volume': 1000.0
        }

        # Act & Assert - 验证异常抛出
        with pytest.raises(ValueError, match="High price .* cannot be less than low price"):
            KlineData(**invalid_data)

    @pytest.mark.unit
    @pytest.mark.mock
    def test_invalid_high_open_close_validation(self):
        """
        测试无效最高价与开盘收盘价验证
        验证：当最高价低于开盘价或收盘价时抛出异常
        """
        # Arrange - 准备无效数据（high < open）
        timestamp = int(datetime(2024, 1, 1).timestamp() * 1000)
        invalid_data = {
            'timestamp': timestamp,
            'open': 41000.0,
            'high': 40000.0,  # 低于开盘价
            'low': 39000.0,
            'close': 40500.0,
            'volume': 1000.0
        }

        # Act & Assert - 验证异常抛出
        with pytest.raises(ValueError, match="High price .* must be >= open and close"):
            KlineData(**invalid_data)

    @pytest.mark.unit
    @pytest.mark.mock
    def test_invalid_low_open_close_validation(self):
        """
        测试无效最低价与开盘收盘价验证
        验证：当最低价高于开盘价或收盘价时抛出异常
        """
        # Arrange - 准备无效数据（low > open）
        timestamp = int(datetime(2024, 1, 1).timestamp() * 1000)
        invalid_data = {
            'timestamp': timestamp,
            'open': 40000.0,
            'high': 41000.0,
            'low': 40500.0,  # 高于开盘价
            'close': 39500.0,
            'volume': 1000.0
        }

        # Act & Assert - 验证异常抛出
        with pytest.raises(ValueError, match="Low price .* must be <= open and close"):
            KlineData(**invalid_data)

    @pytest.mark.unit
    @pytest.mark.mock
    def test_negative_volume_validation(self):
        """
        测试负成交量验证
        验证：当成交量为负数时抛出异常
        """
        # Arrange - 准备无效数据（negative volume）
        timestamp = int(datetime(2024, 1, 1).timestamp() * 1000)
        invalid_data = {
            'timestamp': timestamp,
            'open': 40000.0,
            'high': 41000.0,
            'low': 39000.0,
            'close': 40500.0,
            'volume': -100.0  # 负成交量
        }

        # Act & Assert - 验证异常抛出
        with pytest.raises(ValueError, match="Volume .* cannot be negative"):
            KlineData(**invalid_data)

    @pytest.mark.unit
    @pytest.mark.mock
    def test_boundary_values_validation(self):
        """
        测试边界值验证
        验证：边界条件的正确处理
        """
        # Arrange - 测试边界值
        timestamp = int(datetime(2024, 1, 1).timestamp() * 1000)

        # 测试零成交量
        boundary_data = {
            'timestamp': timestamp,
            'open': 40000.0,
            'high': 40000.0,
            'low': 40000.0,
            'close': 40000.0,
            'volume': 0.0  # 零成交量应该允许
        }

        # Act - 创建边界值数据
        kline = KlineData(**boundary_data)

        # Assert - 验证边界值数据
        assert kline.volume == 0.0
        assert kline.high == kline.low == kline.open == kline.close

    @pytest.mark.unit
    @pytest.mark.mock
    def test_decimal_precision_validation(self):
        """
        测试小数精度验证
        验证：高精度小数的正确处理
        """
        # Arrange - 准备高精度数据
        timestamp = int(datetime(2024, 1, 1).timestamp() * 1000)
        precision_data = {
            'timestamp': timestamp,
            'open': 40000.123456789,
            'high': 41000.987654321,
            'low': 39000.111222333,
            'close': 40500.555666777,
            'volume': 1500.123456789
        }

        # Act - 创建高精度数据
        kline = KlineData(**precision_data)

        # Assert - 验证精度保持
        assert abs(kline.open - 40000.123456789) < 1e-10
        assert abs(kline.high - 41000.987654321) < 1e-10
        assert abs(kline.low - 39000.111222333) < 1e-10
        assert abs(kline.close - 40500.555666777) < 1e-10
        assert abs(kline.volume - 1500.123456789) < 1e-10


class TestKlineDataTransformation:
    """KlineData转换测试 - 验证模型转换功能"""

    @pytest.mark.unit
    @pytest.mark.mock
    def test_to_dict_transformation(self):
        """
        测试转换为字典
        验证：模型到字典的转换正确性
        """
        # Arrange - 准备测试数据
        timestamp = int(datetime(2024, 1, 1, 12, 0, 0).timestamp() * 1000)
        kline = KlineData(
            timestamp=timestamp,
            open=40000.5,
            high=41000.75,
            low=39000.25,
            close=40500.6,
            volume=1500.3
        )

        # Act - 转换为字典
        result = kline.to_dict()

        # Assert - 验证转换结果
        expected_dict = {
            'timestamp': timestamp,
            'open': 40000.5,
            'high': 41000.75,
            'low': 39000.25,
            'close': 40500.6,
            'volume': 1500.3
        }

        assert result == expected_dict, "转换为字典的结果应该正确"
        assert isinstance(result, dict), "应该返回字典类型"

    @pytest.mark.unit
    @pytest.mark.mock
    def test_ohlc_data_frame_conversion(self):
        """
        测试OHLC数据框转换
        验证：批量模型到DataFrame的转换
        """
        # Arrange - 准备多个KlineData实例
        klines = []
        base_timestamp = int(datetime(2024, 1, 1).timestamp() * 1000)

        for i in range(5):
            kline = KlineData(
                timestamp=base_timestamp + i * 3600000,  # 每小时
                open=40000.0 + i * 10,
                high=41000.0 + i * 10,
                low=39000.0 + i * 10,
                close=40500.0 + i * 10,
                volume=1000.0 + i * 100
            )
            klines.append(kline)

        # Act - 转换为DataFrame
        df_data = [kline.to_dict() for kline in klines]
        df = pd.DataFrame(df_data)

        # Assert - 验证DataFrame转换结果
        assert len(df) == 5, "DataFrame应该有5行数据"
        assert list(df.columns) == ['timestamp', 'open', 'high', 'low', 'close', 'volume'], \
            "DataFrame应该有正确的列名"

        # 验证数据正确性
        for i, kline in enumerate(klines):
            assert df.iloc[i]['timestamp'] == kline.timestamp
            assert df.iloc[i]['open'] == kline.open
            assert df.iloc[i]['high'] == kline.high
            assert df.iloc[i]['low'] == kline.low
            assert df.iloc[i]['close'] == kline.close
            assert df.iloc[i]['volume'] == kline.volume

    @pytest.mark.unit
    @pytest.mark.mock
    def test_from_list_creation(self):
        """
        测试从列表创建
        验证：从字典列表批量创建模型
        """
        # Arrange - 准备字典数据
        base_timestamp = int(datetime(2024, 1, 1).timestamp() * 1000)
        dict_data = [
            {
                'timestamp': base_timestamp + i * 3600000,
                'open': 40000.0 + i,
                'high': 41000.0 + i,
                'low': 39000.0 + i,
                'close': 40500.0 + i,
                'volume': 1000.0 + i * 10
            }
            for i in range(3)
        ]

        # Act - 创建KlineData列表
        klines = [KlineData(**data) for data in dict_data]

        # Assert - 验证批量创建结果
        assert len(klines) == 3, "应该创建3个KlineData实例"

        for i, kline in enumerate(klines):
            assert kline.timestamp == dict_data[i]['timestamp']
            assert kline.open == dict_data[i]['open']
            assert kline.high == dict_data[i]['high']
            assert kline.low == dict_data[i]['low']
            assert kline.close == dict_data[i]['close']
            assert kline.volume == dict_data[i]['volume']


class TestKlineDataCollaboration:
    """KlineData协作测试 - 验证与其他组件的交互"""

    @pytest.mark.unit
    @pytest.mark.contract
    def test_pandas_dataframe_collaboration(self):
        """
        测试与Pandas DataFrame的协作
        验证：模型与数据分析工具的集成
        """
        # Arrange - 准备测试数据
        klines = []
        base_timestamp = int(datetime(2024, 1, 1).timestamp() * 1000)

        for i in range(10):
            kline = KlineData(
                timestamp=base_timestamp + i * 3600000,
                open=40000.0 + np.random.uniform(-100, 100),
                high=41000.0 + np.random.uniform(-100, 100),
                low=39000.0 + np.random.uniform(-100, 100),
                close=40500.0 + np.random.uniform(-100, 100),
                volume=1000.0 + np.random.uniform(-100, 100)
            )
            klines.append(kline)

        # Act - 转换为DataFrame进行分析
        df_data = [kline.to_dict() for kline in klines]
        df = pd.DataFrame(df_data)
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

        # Assert - 验证数据分析协作
        assert len(df) == 10, "DataFrame应该有10行数据"
        assert df['close'].mean() > 0, "平均收盘价应该大于0"
        assert df['volume'].sum() > 0, "总成交量应该大于0"
        assert (df['high'] >= df['low']).all(), "所有行的最高价应该大于等于最低价"

    @pytest.mark.unit
    @pytest.mark.contract
    def test_json_serialization_collaboration(self):
        """
        测试与JSON序列化的协作
        验证：模型的序列化和反序列化能力
        """
        # Arrange - 准备测试数据
        timestamp = int(datetime(2024, 1, 1, 12, 0, 0).timestamp() * 1000)
        original_kline = KlineData(
            timestamp=timestamp,
            open=40000.5,
            high=41000.75,
            low=39000.25,
            close=40500.6,
            volume=1500.3
        )

        # Act - 序列化和反序列化
        import json
        serialized = json.dumps(original_kline.to_dict())
        deserialized_data = json.loads(serialized)
        restored_kline = KlineData(**deserialized_data)

        # Assert - 验证序列化协作结果
        assert restored_kline.timestamp == original_kline.timestamp
        assert restored_kline.open == original_kline.open
        assert restored_kline.high == original_kline.high
        assert restored_kline.low == original_kline.low
        assert restored_kline.close == original_kline.close
        assert restored_kline.volume == original_kline.volume

    @pytest.mark.unit
    @pytest.mark.contract
    def test_database_model_collaboration(self):
        """
        测试与数据库模型的协作
        验证：模型与ORM系统的集成
        """
        # Arrange - 准备测试数据
        timestamp = int(datetime(2024, 1, 1).timestamp() * 1000)
        kline = KlineData(
            timestamp=timestamp,
            open=40000.0,
            high=41000.0,
            low=39000.0,
            close=40500.0,
            volume=1000.0
        )

        # Act - 模拟数据库字段映射
        db_fields = {
            'id': 1,
            'symbol': 'BTC/USDT',
            'exchange': 'binance',
            'timeframe': '1h',
            'timestamp': kline.timestamp,
            'open_price': kline.open,
            'high_price': kline.high,
            'low_price': kline.low,
            'close_price': kline.close,
            'volume': kline.volume,
            'created_at': datetime.now()
        }

        # Assert - 验证数据库协作
        assert db_fields['timestamp'] == kline.timestamp
        assert db_fields['open_price'] == kline.open
        assert db_fields['high_price'] == kline.high
        assert db_fields['low_price'] == kline.low
        assert db_fields['close_price'] == kline.close
        assert db_fields['volume'] == kline.volume


class TestKlineDataEdgeCases:
    """KlineData边界条件测试"""

    @pytest.mark.unit
    @pytest.mark.mock
    def test_equal_prices_edge_case(self):
        """
        测试价格相等的边界情况
        验证：当所有价格相等时的处理
        """
        # Arrange - 准备相等价格数据
        timestamp = int(datetime(2024, 1, 1).timestamp() * 1000)
        equal_price_data = {
            'timestamp': timestamp,
            'open': 40000.0,
            'high': 40000.0,
            'low': 40000.0,
            'close': 40000.0,
            'volume': 1000.0
        }

        # Act - 创建相等价格的KlineData
        kline = KlineData(**equal_price_data)

        # Assert - 验证相等价格处理
        assert kline.open == kline.high == kline.low == kline.close == 40000.0
        assert kline.volume == 1000.0

    @pytest.mark.unit
    @pytest.mark.mock
    def test_zero_volume_edge_case(self):
        """
        测试零成交量的边界情况
        验证：成交量为零时的处理
        """
        # Arrange - 准备零成交量数据
        timestamp = int(datetime(2024, 1, 1).timestamp() * 1000)
        zero_volume_data = {
            'timestamp': timestamp,
            'open': 40000.0,
            'high': 40500.0,
            'low': 39500.0,
            'close': 40250.0,
            'volume': 0.0
        }

        # Act - 创建零成交量的KlineData
        kline = KlineData(**zero_volume_data)

        # Assert - 验证零成交量处理
        assert kline.volume == 0.0
        assert kline.high > kline.low
        assert kline.high >= kline.open >= kline.low
        assert kline.high >= kline.close >= kline.low

    @pytest.mark.unit
    @pytest.mark.mock
    def test_large_numbers_edge_case(self):
        """
        测试大数值的边界情况
        验证：极大数值时的处理
        """
        # Arrange - 准备大数值数据
        timestamp = int(datetime(2024, 1, 1).timestamp() * 1000)
        large_numbers_data = {
            'timestamp': timestamp,
            'open': 1e10,  # 100亿
            'high': 1.1e10,  # 110亿
            'low': 9.5e9,  # 95亿
            'close': 1.05e10,  # 105亿
            'volume': 1e15  # 1千万亿
        }

        # Act - 创建大数值的KlineData
        kline = KlineData(**large_numbers_data)

        # Assert - 验证大数值处理
        assert kline.open == 1e10
        assert kline.high == 1.1e10
        assert kline.low == 9.5e9
        assert kline.close == 1.05e10
        assert kline.volume == 1e15

    @pytest.mark.unit
    @pytest.mark.mock
    def test_very_small_numbers_edge_case(self):
        """
        测试极小数值的边界情况
        验证：极小数值时的处理
        """
        # Arrange - 准备极小数值数据
        timestamp = int(datetime(2024, 1, 1).timestamp() * 1000)
        small_numbers_data = {
            'timestamp': timestamp,
            'open': 1e-8,
            'high': 1.1e-8,
            'low': 9e-9,
            'close': 1.05e-8,
            'volume': 1e-6
        }

        # Act - 创建极小数值的KlineData
        kline = KlineData(**small_numbers_data)

        # Assert - 验证极小数值处理
        assert kline.open == 1e-8
        assert kline.high == 1.1e-8
        assert kline.low == 9e-9
        assert kline.close == 1.05e-8
        assert kline.volume == 1e-6

    @pytest.mark.unit
    @pytest.mark.mock
    def test_extreme_timestamp_edge_case(self):
        """
        测试极值时间戳的边界情况
        验证：极值时间戳的处理
        """
        # Arrange - 测试极值时间戳
        min_timestamp = 0  # 最小时间戳
        max_timestamp = 2**63 - 1  # 最大时间戳（64位有符号整数）

        # Act - 测试最小时间戳
        kline_min = KlineData(
            timestamp=min_timestamp,
            open=40000.0,
            high=41000.0,
            low=39000.0,
            close=40500.0,
            volume=1000.0
        )

        # 测试最大时间戳
        kline_max = KlineData(
            timestamp=max_timestamp,
            open=40000.0,
            high=41000.0,
            low=39000.0,
            close=40500.0,
            volume=1000.0
        )

        # Assert - 验证极值时间戳处理
        assert kline_min.timestamp == min_timestamp
        assert kline_max.timestamp == max_timestamp


class TestKlineDataPerformance:
    """KlineData性能测试"""

    @pytest.mark.unit
    @pytest.mark.performance
    def test_bulk_creation_performance(self, performance_timer):
        """
        测试批量创建性能
        验证：大量KlineData实例的创建效率
        """
        # Arrange - 准备大量测试数据
        num_instances = 10000
        base_timestamp = int(datetime(2024, 1, 1).timestamp() * 1000)

        # Act - 测试批量创建性能
        performance_timer.start()

        klines = []
        for i in range(num_instances):
            kline = KlineData(
                timestamp=base_timestamp + i * 1000,  # 每秒
                open=40000.0 + (i % 1000) * 0.1,
                high=41000.0 + (i % 1000) * 0.1,
                low=39000.0 + (i % 1000) * 0.1,
                close=40500.0 + (i % 1000) * 0.1,
                volume=1000.0 + (i % 100)
            )
            klines.append(kline)

        performance_timer.stop()

        # Assert - 验证性能结果
        assert len(klines) == num_instances, f"应该创建{num_instances}个实例"
        assert performance_timer.elapsed < 2.0, f"创建{num_instances}个实例应该在2秒内完成"

    @pytest.mark.unit
    @pytest.mark.performance
    def test_to_dict_conversion_performance(self, performance_timer):
        """
        测试字典转换性能
        验证：to_dict方法的转换效率
        """
        # Arrange - 准备测试实例
        kline = KlineData(
            timestamp=int(datetime(2024, 1, 1).timestamp() * 1000),
            open=40000.0,
            high=41000.0,
            low=39000.0,
            close=40500.0,
            volume=1000.0
        )

        num_conversions = 100000

        # Act - 测试转换性能
        performance_timer.start()

        results = []
        for _ in range(num_conversions):
            result = kline.to_dict()
            results.append(result)

        performance_timer.stop()

        # Assert - 验证性能结果
        assert len(results) == num_conversions, f"应该执行{num_conversions}次转换"
        assert performance_timer.elapsed < 1.0, f"{num_conversions}次转换应该在1秒内完成"
        assert all(isinstance(r, dict) for r in results), "所有结果都应该是字典"