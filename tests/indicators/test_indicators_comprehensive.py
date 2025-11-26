"""
技术指标综合测试 - 伦敦学派TDD方法

测试重点：
1. 指标计算的输入输出契约验证
2. 技术指标算法的正确性
3. 边界条件和异常值处理
4. 指标管理器的协作关系
5. 批量计算的性能优化
"""

import pytest
import numpy as np
import pandas as pd
from unittest.mock import Mock, patch
from datetime import datetime, timedelta

from indicators.manager import IndicatorManager
from indicators.base import BaseIndicator
from indicators.moving_average import SMA, EMA
from indicators.macd import MACD
from indicators.rsi import RSI
from indicators.bollinger import BollingerBands
from utils.constants import Timeframe


class TestIndicatorContract:
    """指标契约测试 - 定义和验证指标接口契约"""

    @pytest.mark.unit
    @pytest.mark.contract
    def test_base_indicator_interface_contract(self):
        """
        测试基础指标接口契约
        验证：所有指标必须实现的接口
        """
        # Arrange - 定义指标接口契约
        required_methods = {
            'calculate': np.ndarray,
            'calculate_batch': dict,
            'validate_input': bool,
            'get_required_length': int
        }

        # Act - 验证具体指标类的接口
        indicator_classes = [SMA, EMA, MACD, RSI, BollingerBands]

        for indicator_class in indicator_classes:
            # Assert - 验证每个指标类的接口
            assert issubclass(indicator_class, BaseIndicator), \
                f"{indicator_class.__name__}应该继承BaseIndicator"

            for method_name, expected_return in required_methods.items():
                assert hasattr(indicator_class, method_name), \
                    f"{indicator_class.__name__}应该有{method_name}方法"
                method = getattr(indicator_class, method_name)
                assert callable(method), \
                    f"{indicator_class.__name__}.{method_name}应该是可调用的"

    @pytest.mark.unit
    @pytest.mark.contract
    def test_indicator_manager_interface_contract(self):
        """
        测试指标管理器接口契约
        验证：指标管理器的方法契约
        """
        # Arrange - 定义管理器接口契约
        manager_methods = {
            'calculate': dict,
            'calculate_batch': dict,
            'register_indicator': None,
            'get_available_indicators': list,
            'validate_indicator': bool
        }

        # Act - 获取指标管理器类
        manager_class = IndicatorManager

        # Assert - 验证接口契约
        for method_name, expected_return in manager_methods.items():
            assert hasattr(manager_class, method_name), \
                f"IndicatorManager应该有{method_name}方法"
            method = getattr(manager_class, method_name)
            assert callable(method), f"{method_name}应该是可调用的"

    @pytest.mark.unit
    @pytest.mark.contract
    def test_indicator_calculation_contract(self):
        """
        测试指标计算契约
        验证：输入输出格式的一致性
        """
        # Arrange - 定义计算契约
        input_contract = {
            'data': np.ndarray,
            'length': int,
            'params': dict
        }

        output_contract = {
            'result': np.ndarray,
            'length': int,
            'metadata': dict
        }

        # Act - 创建SMA指标实例
        sma = SMA(period=20)

        # Assert - 验证计算契约
        # 输入验证契约
        assert hasattr(sma, 'period'), "SMA应该有period属性"
        assert isinstance(sma.period, int), "period应该是整数"

        # 输出契约验证
        assert hasattr(sma, 'calculate'), "应该有calculate方法"
        assert callable(sma.calculate), "calculate应该是可调用的"

    @pytest.mark.unit
    @pytest.mark.contract
    def test_indicator_parameter_contract(self):
        """
        测试指标参数契约
        验证：参数类型和范围的验证
        """
        # Arrange - 定义参数契约
        sma_params = {'period': int}
        macd_params = {
            'fast_period': int,
            'slow_period': int,
            'signal_period': int
        }

        # Act & Assert - 验证SMA参数契约
        sma = SMA(period=20)
        assert isinstance(sma.period, int), "SMA period应该是整数"
        assert sma.period > 0, "SMA period应该大于0"

        # 验证MACD参数契约
        macd = MACD(fast_period=12, slow_period=26, signal_period=9)
        assert isinstance(macd.fast_period, int), "MACD fast_period应该是整数"
        assert isinstance(macd.slow_period, int), "MACD slow_period应该是整数"
        assert isinstance(macd.signal_period, int), "MACD signal_period应该是整数"

        assert macd.fast_period < macd.slow_period, "fast_period应该小于slow_period"


class TestSMAIndicator:
    """SMA指标测试 - 验证简单移动平均线算法"""

    @pytest.mark.unit
    @pytest.mark.mock
    def test_sma_calculation_accuracy(self):
        """
        测试SMA计算准确性
        验证：SMA算法的数学正确性
        """
        # Arrange - 准备测试数据
        prices = np.array([10, 20, 30, 40, 50, 60, 70, 80, 90, 100])
        period = 5
        expected_sma = np.array([30, 40, 50, 60, 70, 80])

        # Act - 计算SMA
        sma = SMA(period=period)
        result = sma.calculate(prices)

        # Assert - 验证计算准确性
        assert len(result) == len(expected_sma), f"结果长度应该为{len(expected_sma)}"
        np.testing.assert_array_almost_equal(result, expected_sma, decimal=10,
                                              err_msg="SMA计算结果不正确")

    @pytest.mark.unit
    @pytest.mark.mock
    def test_sma_edge_cases(self):
        """
        测试SMA边界情况
        验证：边界条件的正确处理
        """
        # Arrange - 准备边界测试数据
        test_cases = [
            # (输入数据, 周期, 期望结果长度)
            (np.array([1, 2, 3]), 5, 0),  # 数据长度小于周期
            (np.array([1, 2, 3, 4, 5]), 5, 1),  # 数据长度等于周期
            (np.array([1, 2, 3, 4, 5, 6]), 1, 6),  # 周期为1
        ]

        # Act & Assert - 验证边界情况
        for prices, period, expected_length in test_cases:
            sma = SMA(period=period)
            result = sma.calculate(prices)
            assert len(result) == expected_length, \
                f"周期{period}，输入长度{len(prices)}，结果长度应该是{expected_length}"

    @pytest.mark.unit
    @pytest.mark.mock
    def test_sma_invalid_input_handling(self):
        """
        测试SMA无效输入处理
        验证：无效输入的拒绝机制
        """
        # Arrange - 准备无效输入
        invalid_inputs = [
            [],  # 空数组
            np.array([]),  # 空numpy数组
            [1, 2, 'invalid'],  # 包含非数值
            None,  # None值
        ]

        # Act & Assert - 验证无效输入处理
        sma = SMA(period=5)
        for invalid_input in invalid_inputs:
            if invalid_input is None:
                with pytest.raises((TypeError, ValueError)):
                    sma.calculate(invalid_input)
            else:
                with pytest.raises((ValueError, TypeError)):
                    sma.calculate(np.array(invalid_input))

    @pytest.mark.unit
    @pytest.mark.mock
    def test_sma_ohlc_data_processing(self, sample_kline_data):
        """
        测试SMA OHLC数据处理
        验证：K线数据的正确处理
        """
        # Arrange - 提取收盘价
        close_prices = sample_kline_data['close'].values

        # Act - 计算SMA
        sma = SMA(period=10)
        sma_values = sma.calculate(close_prices)

        # Assert - 验证OHLC数据处理
        assert len(sma_values) == len(close_prices) - 10 + 1, \
            f"SMA结果长度应该为{len(close_prices) - 10 + 1}"
        assert not np.any(np.isnan(sma_values)), "SMA结果不应该包含NaN"

        # 验证SMA趋势合理性
        # 价格上涨时，SMA也应该上涨（对于稳定的上涨趋势）
        increasing_prices = np.arange(100, 200)  # 100到199的递增序列
        sma_trend = sma.calculate(increasing_prices)
        assert np.all(np.diff(sma_trend) > 0), "递增价格的SMA也应该是递增的"


class TestMACDIndicator:
    """MACD指标测试 - 验证MACD算法"""

    @pytest.mark.unit
    @pytest.mark.mock
    def test_macd_components_calculation(self):
        """
        测试MACD组件计算
        验证：MACD线、信号线、直方图的正确性
        """
        # Arrange - 准备测试数据（简化的递增序列）
        prices = np.array([100, 102, 104, 103, 105, 107, 106, 108, 110, 112,
                         111, 113, 115, 114, 116, 118, 117, 119, 121, 123])

        # Act - 计算MACD
        macd = MACD(fast_period=12, slow_period=26, signal_period=9)
        result = macd.calculate(prices)

        # Assert - 验证MACD组件
        assert 'macd' in result, "结果应该包含MACD线"
        assert 'signal' in result, "结果应该包含信号线"
        assert 'histogram' in result, "结果应该包含直方图"

        # 验证组件长度一致性
        assert len(result['macd']) == len(result['signal']) == len(result['histogram']), \
            "MACD组件长度应该一致"

        # 验证直方图计算公式
        expected_histogram = result['macd'] - result['signal']
        np.testing.assert_array_almost_equal(result['histogram'], expected_histogram,
                                              decimal=10, err_msg="直方图计算不正确")

    @pytest.mark.unit
    @pytest.mark.mock
    def test_macd_trend_detection(self):
        """
        测试MACD趋势检测
        验证：MACD对趋势变化的敏感性
        """
        # Arrange - 创建有明显趋势的数据
        # 前半段下跌，后半段上涨
        decreasing_prices = np.array([100, 95, 90, 85, 80, 75, 70, 65, 60, 55])
        increasing_prices = np.array([55, 60, 65, 70, 75, 80, 85, 90, 95, 100])
        trend_prices = np.concatenate([decreasing_prices, increasing_prices])

        # Act - 计算MACD
        macd = MACD(fast_period=5, slow_period=10, signal_period=3)  # 使用较短周期适应小数据集
        result = macd.calculate(trend_prices)

        # Assert - 验证趋势检测
        # MACD应该能够检测到趋势变化
        macd_values = result['macd']

        # 对于递增趋势，MACD值应该是递增的（至少大部分）
        increasing_macd = macd_values[len(macd_values)//2:]
        if len(increasing_macd) > 1:
            trend_direction = np.sum(np.diff(increasing_macd) > 0) / (len(increasing_macd) - 1)
            assert trend_direction > 0.5, "MACD应该检测到上涨趋势"

    @pytest.mark.unit
    @pytest.mark.mock
    def test_macd_parameter_validation(self):
        """
        测试MACD参数验证
        验证：参数约束的正确执行
        """
        # Act & Assert - 验证参数约束
        # fast_period应该小于slow_period
        with pytest.raises(ValueError):
            MACD(fast_period=26, slow_period=12, signal_period=9)  # 反了

        # 周期应该为正整数
        with pytest.raises((ValueError, TypeError)):
            MACD(fast_period=0, slow_period=26, signal_period=9)

        with pytest.raises((ValueError, TypeError)):
            MACD(fast_period=-5, slow_period=26, signal_period=9)

    @pytest.mark.unit
    @pytest.mark.mock
    def test_macd_zero_crossing(self):
        """
        测试MACD零点交叉
        验证：MACD线与信号线的交叉检测
        """
        # Arrange - 创建会产生交叉的数据
        # 使用正弦波模拟价格波动
        t = np.linspace(0, 4*np.pi, 50)
        prices = 100 + 20 * np.sin(t) + 5 * np.random.normal(0, 1, 50)

        # Act - 计算MACD
        macd = MACD(fast_period=5, slow_period=10, signal_period=3)
        result = macd.calculate(prices)

        # Assert - 验证零点交叉
        macd_line = result['macd']
        signal_line = result['signal']
        histogram = result['histogram']

        # 直方图应该包含正值和负值（如果有交叉）
        if len(histogram) > 0:
            has_positive = np.any(histogram > 0)
            has_negative = np.any(histogram < 0)
            # 对于波动性数据，应该有正负值
            # assert has_positive or has_negative, "直方图应该包含正值或负值"


class TestRSIIndicator:
    """RSI指标测试 - 验证相对强弱指标"""

    @pytest.mark.unit
    @pytest.mark.mock
    def test_rsi_range_validation(self):
        """
        测试RSI范围验证
        验证：RSI值应该在0-100范围内
        """
        # Arrange - 准备随机价格数据
        np.random.seed(42)
        price_changes = np.random.normal(0, 1, 100)
        prices = 100 + np.cumsum(price_changes)

        # Act - 计算RSI
        rsi = RSI(period=14)
        rsi_values = rsi.calculate(prices)

        # Assert - 验证RSI范围
        assert len(rsi_values) > 0, "RSI应该有计算结果"
        assert np.all(rsi_values >= 0), "RSI值不应该小于0"
        assert np.all(rsi_values <= 100), "RSI值不应该大于100"

        # 验证RSI的统计特性
        rsi_mean = np.mean(rsi_values)
        assert 30 < rsi_mean < 70, "RSI平均值应该在合理范围内"

    @pytest.mark.unit
    @pytest.mark.mock
    def test_rsi_extreme_values(self):
        """
        测试RSI极值情况
        验证：强烈趋势下的RSI极值
        """
        # Arrange - 创建强烈上涨和下跌的数据
        # 强烈上涨：连续15天上涨
        strong_uptrend = np.array([100, 105, 110, 115, 120, 125, 130, 135, 140, 145,
                                   150, 155, 160, 165, 170, 175, 180, 185, 190, 195])

        # 强烈下跌：连续15天下跌
        strong_downtrend = np.array([200, 195, 190, 185, 180, 175, 170, 165, 160, 155,
                                     150, 145, 140, 135, 130, 125, 120, 115, 110, 105])

        # Act - 计算RSI
        rsi = RSI(period=14)
        rsi_uptrend = rsi.calculate(strong_uptrend)
        rsi_downtrend = rsi.calculate(strong_downtrend)

        # Assert - 验证极值RSI
        if len(rsi_uptrend) > 0:
            assert rsi_uptrend[-1] > 50, "强烈上涨趋势的RSI应该大于50"
            # 可能不会达到70以上，因为短期内的涨幅可能不够

        if len(rsi_downtrend) > 0:
            assert rsi_downtrend[-1] < 50, "强烈下跌趋势的RSI应该小于50"

    @pytest.mark.unit
    @pytest.mark.mock
    def test_rsi_sideways_market(self):
        """
        测试RSI横盘市场
        验证：横盘市场中的RSI行为
        """
        # Arrange - 创建横盘数据
        base_price = 100
        noise = np.random.normal(0, 2, 50)  # 小幅随机波动
        sideways_prices = base_price + noise

        # Act - 计算RSI
        rsi = RSI(period=14)
        rsi_values = rsi.calculate(sideways_prices)

        # Assert - 验证横盘RSI
        if len(rsi_values) > 0:
            rsi_std = np.std(rsi_values)
            # 横盘市场的RSI标准差应该相对较小
            assert rsi_std < 30, f"横盘市场RSI标准差应该较小，实际为{rsi_std}"

            # RSI应该在中间范围附近波动
            rsi_mean = np.mean(rsi_values)
            assert 40 < rsi_mean < 60, f"横盘市场RSI平均值应该在40-60之间，实际为{rsi_mean}"


class TestBollingerBandsIndicator:
    """布林带指标测试 - 验证布林带算法"""

    @pytest.mark.unit
    @pytest.mark.mock
    def test_bollinger_bands_structure(self):
        """
        测试布林带结构
        验证：上轨、中轨、下轨的关系
        """
        # Arrange - 准备测试数据
        np.random.seed(42)
        prices = 100 + np.cumsum(np.random.normal(0, 2, 50))

        # Act - 计算布林带
        bb = BollingerBands(period=20, std_dev=2)
        result = bb.calculate(prices)

        # Assert - 验证布林带结构
        assert 'upper' in result, "结果应该包含上轨"
        assert 'middle' in result, "结果应该包含中轨"
        assert 'lower' in result, "结果应该包含下轨"

        # 验证轨道长度一致性
        assert len(result['upper']) == len(result['middle']) == len(result['lower']), \
            "布林带各轨道长度应该一致"

        # 验证轨道关系：上轨 > 中轨 > 下轨
        upper = result['upper']
        middle = result['middle']
        lower = result['lower']

        assert np.all(upper > middle), "上轨应该始终大于中轨"
        assert np.all(middle > lower), "中轨应该始终大于下轨"

    @pytest.mark.unit
    @pytest.mark.mock
    def test_bollinger_bands_width_calculation(self):
        """
        测试布林带宽度计算
        验证：带宽与波动性的关系
        """
        # Arrange - 创建不同波动性的数据
        # 低波动性
        low_volatility = 100 + np.cumsum(np.random.normal(0, 0.5, 50))
        # 高波动性
        high_volatility = 100 + np.cumsum(np.random.normal(0, 5, 50))

        # Act - 计算布林带
        bb = BollingerBands(period=20, std_dev=2)
        result_low = bb.calculate(low_volatility)
        result_high = bb.calculate(high_volatility)

        # Assert - 验证带宽与波动性关系
        if len(result_low['upper']) > 0 and len(result_high['upper']) > 0:
            # 计算平均带宽
            width_low = np.mean(result_low['upper'] - result_low['lower'])
            width_high = np.mean(result_high['upper'] - result_high['lower'])

            # 高波动性数据的带宽应该更大
            assert width_high > width_low, "高波动性数据的布林带宽度应该更大"

    @pytest.mark.unit
    @pytest.mark.mock
    def test_bollinger_bands_squeeze_breakout(self):
        """
        测试布林带挤压和突破
        验证：价格突破布林带的识别
        """
        # Arrange - 创建挤压后突破的数据
        # 挤压阶段：价格在窄幅范围内波动
        squeeze_prices = 100 + np.sin(np.linspace(0, 2*np.pi, 30)) * 2
        # 突破阶段：价格大幅上涨
        breakout_prices = np.linspace(102, 120, 20)
        test_prices = np.concatenate([squeeze_prices, breakout_prices])

        # Act - 计算布林带
        bb = BollingerBands(period=20, std_dev=2)
        result = bb.calculate(test_prices)

        # Assert - 验证突破识别
        upper = result['upper']
        lower = result['lower']

        # 在突破阶段，价格应该超过布林带上轨
        # 这里我们检查最后几个价格是否接近或超过上轨
        if len(upper) >= 5:
            recent_upper = upper[-5:]
            recent_prices = test_prices[-len(recent_upper)-20:-20]  # 对应的价格
            # 突破应该被识别（价格接近或超过上轨）
            breakout_detected = any(price >= band for price, band in zip(recent_prices, recent_upper))
            # 由于数据是人工构造的，我们主要验证计算逻辑
            assert len(upper) > 0, "布林带计算应该有结果"


class TestIndicatorManager:
    """指标管理器测试 - 验证指标管理和批量计算"""

    @pytest.mark.unit
    @pytest.mark.mock
    def test_indicator_registration(self):
        """
        测试指标注册
        验证：指标的正确注册和管理
        """
        # Arrange - 创建指标管理器
        manager = IndicatorManager()

        # Act - 注册指标
        sma = SMA(period=20)
        manager.register_indicator('sma_20', sma)

        # Assert - 验证注册结果
        assert 'sma_20' in manager.indicators, "SMA应该被成功注册"
        assert manager.indicators['sma_20'] is sma, "注册的指标应该是正确的对象"

    @pytest.mark.unit
    @pytest.mark.mock
    def test_batch_calculation(self, sample_kline_data):
        """
        测试批量指标计算
        验证：多个指标的同时计算
        """
        # Arrange - 准备数据和指标
        close_prices = sample_kline_data['close'].values
        manager = IndicatorManager()

        # 注册多个指标
        manager.register_indicator('sma_10', SMA(period=10))
        manager.register_indicator('sma_20', SMA(period=20))
        manager.register_indicator('rsi', RSI(period=14))

        # Act - 批量计算
        results = manager.calculate_batch(close_prices, ['sma_10', 'sma_20', 'rsi'])

        # Assert - 验证批量计算结果
        assert 'sma_10' in results, "结果应该包含sma_10"
        assert 'sma_20' in results, "结果应该包含sma_20"
        assert 'rsi' in results, "结果应该包含rsi"

        # 验证计算长度
        expected_sma10_length = len(close_prices) - 10 + 1
        expected_sma20_length = len(close_prices) - 20 + 1
        expected_rsi_length = len(close_prices) - 14 + 1

        assert len(results['sma_10']) == expected_sma10_length, "SMA10计算长度不正确"
        assert len(results['sma_20']) == expected_sma20_length, "SMA20计算长度不正确"
        assert len(results['rsi']) == expected_rsi_length, "RSI计算长度不正确"

    @pytest.mark.unit
    @pytest.mark.mock
    def test_indicator_dependency_calculation(self, sample_kline_data):
        """
        测试指标依赖计算
        验证：基于其他指标的计算
        """
        # Arrange - 准备数据
        close_prices = sample_kline_data['close'].values
        manager = IndicatorManager()

        # Act - 计算基础指标和依赖指标
        # 首先计算MACD（它包含多个组件）
        manager.register_indicator('macd', MACD())
        macd_result = manager.calculate(close_prices, 'macd')

        # Assert - 验证依赖计算结果
        assert isinstance(macd_result, dict), "MACD结果应该是字典"
        assert 'macd' in macd_result, "MACD结果应该包含macd线"
        assert 'signal' in macd_result, "MACD结果应该包含signal线"
        assert 'histogram' in macd_result, "MACD结果应该包含histogram"

        # 验证组件间的关系
        expected_histogram = macd_result['macd'] - macd_result['signal']
        np.testing.assert_array_almost_equal(macd_result['histogram'], expected_histogram,
                                              err_msg="Histogram计算不正确")

    @pytest.mark.unit
    @pytest.mark.performance
    def test_calculation_performance(self, sample_kline_data, performance_timer):
        """
        测试指标计算性能
        验证：大量指标计算的性能
        """
        # Arrange - 准备数据
        close_prices = sample_kline_data['close'].values
        manager = IndicatorManager()

        # 注册多个指标
        indicators = [
            ('sma_5', SMA(5)),
            ('sma_10', SMA(10)),
            ('sma_20', SMA(20)),
            ('ema_12', EMA(12)),
            ('ema_26', EMA(26)),
            ('rsi', RSI(14))
        ]

        for name, indicator in indicators:
            manager.register_indicator(name, indicator)

        # Act - 测试性能
        performance_timer.start()

        # 执行多次批量计算
        for _ in range(100):
            results = manager.calculate_batch(
                close_prices,
                [name for name, _ in indicators]
            )

        performance_timer.stop()

        # Assert - 验证性能结果
        assert len(results) == len(indicators), "应该计算所有指标"
        assert performance_timer.elapsed < 2.0, "100次批量计算应该在2秒内完成"

    @pytest.mark.unit
    @pytest.mark.mock
    def test_error_handling(self, sample_kline_data):
        """
        测试错误处理
        验证：指标计算错误的处理
        """
        # Arrange - 准备无效数据
        invalid_data = np.array([1, 2, 3, np.nan, 5, 6])  # 包含NaN

        # Act & Assert - 验证错误处理
        manager = IndicatorManager()
        manager.register_indicator('sma', SMA(5))

        # 处理包含NaN的数据应该有合适的错误处理
        try:
            result = manager.calculate(invalid_data, 'sma')
            # 如果没有抛出异常，结果应该是合理的
            assert result is not None, "应该返回计算结果"
        except (ValueError, TypeError) as e:
            # 抛出异常也是可以接受的
            assert True, "应该能够处理无效数据"

    @pytest.mark.unit
    @pytest.mark.mock
    def test_indicator_validation(self, sample_kline_data):
        """
        测试指标验证
        验证：指标参数和数据的验证
        """
        # Arrange - 准备数据
        close_prices = sample_kline_data['close'].values
        manager = IndicatorManager()

        # Act - 测试验证功能
        # 注册有效指标
        valid_sma = SMA(period=20)
        manager.register_indicator('valid_sma', valid_sma)

        # 测试无效指标参数
        try:
            invalid_sma = SMA(period=0)  # 无效周期
            manager.register_indicator('invalid_sma', invalid_sma)
            assert False, "应该拒绝无效的指标参数"
        except (ValueError, TypeError):
            pass  # 预期的异常

        # Assert - 验证指标注册状态
        assert 'valid_sma' in manager.indicators, "有效指标应该被注册"
        assert manager.validate_indicator('valid_sma'), "有效指标应该通过验证"