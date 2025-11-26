"""
DataSourceStrategy 单元测试 - 伦敦学派TDD方法

测试重点：
1. 数据源决策策略的契约验证
2. 策略模式的正确实现
3. 决策逻辑的行为验证
4. 与元数据管理器的协作
5. 性能和优化策略
"""

import pytest
from unittest.mock import Mock, patch, call
from datetime import datetime, timedelta
import pandas as pd

from storage.data_source_strategy import DataSourceStrategy, DataSourceDecision


class TestDataSourceStrategyContract:
    """DataSourceStrategy契约测试 - 定义和验证接口契约"""

    @pytest.mark.unit
    @pytest.mark.contract
    def test_strategy_interface_contract(self, mock_config):
        """
        测试策略接口契约
        验证：DataSourceStrategy必须实现的方法和返回值类型
        """
        # Arrange - 定义契约
        strategy_methods = {
            'decide_data_source': DataSourceDecision(
                source='local',
                source_interval=None,
                need_download=False,
                download_interval=None,
                reason='Test decision'
            ),
            'should_download': bool,
            'get_optimal_download_interval': str,
            'is_native_timeframe': bool
        }

        # Act - 创建策略实例
        with patch('storage.data_source_strategy.MetadataManager'):
            strategy = DataSourceStrategy(mock_config)

        # Assert - 验证接口契约
        for method_name, expected_return_type in strategy_methods.items():
            assert hasattr(strategy, method_name), f"策略应该实现{method_name}方法"
            method = getattr(strategy, method_name)
            assert callable(method), f"{method_name}应该是可调用的"

        # 验证常量契约
        assert hasattr(DataSourceStrategy, 'COMMON_NATIVE_TIMEFRAMES'), \
            "应该定义常见原生时间周期"
        assert isinstance(DataSourceStrategy.COMMON_NATIVE_TIMEFRAMES, list), \
            "COMMON_NATIVE_TIMEFRAMES应该是列表"
        assert hasattr(DataSourceStrategy, 'RESAMPLE_THRESHOLD_RECORDS'), \
            "应该定义重采样阈值"
        assert isinstance(DataSourceStrategy.RESAMPLE_THRESHOLD_RECORDS, int), \
            "RESAMPLE_THRESHOLD_RECORDS应该是整数"

    @pytest.mark.unit
    @pytest.mark.contract
    def test_data_source_decision_contract(self):
        """
        测试DataSourceDecision契约
        验证：决策结果的数据结构和类型
        """
        # Arrange & Act - 创建决策对象
        decision = DataSourceDecision(
            source='local',
            source_interval='1m',
            need_download=False,
            download_interval=None,
            reason='Local data available'
        )

        # Assert - 验证数据契约
        assert hasattr(decision, 'source'), "应该有source属性"
        assert hasattr(decision, 'source_interval'), "应该有source_interval属性"
        assert hasattr(decision, 'need_download'), "应该有need_download属性"
        assert hasattr(decision, 'download_interval'), "应该有download_interval属性"
        assert hasattr(decision, 'reason'), "应该有reason属性"

        # 验证类型契约
        assert isinstance(decision.source, str), "source应该是字符串"
        assert decision.source_interval is None or isinstance(decision.source_interval, str), \
            "source_interval应该是字符串或None"
        assert isinstance(decision.need_download, bool), "need_download应该是布尔值"
        assert decision.download_interval is None or isinstance(decision.download_interval, str), \
            "download_interval应该是字符串或None"
        assert isinstance(decision.reason, str), "reason应该是字符串"

    @pytest.mark.unit
    @pytest.mark.contract
    def test_metadata_manager_contract(self, mock_config):
        """
        测试MetadataManager协作契约
        验证：策略与元数据管理器的交互契约
        """
        # Arrange - 定义元数据管理契约
        metadata_contract = {
            'has_data': True,
            'get_earliest_time': datetime(2020, 1, 1),
            'get_latest_time': datetime(2024, 1, 1),
            'get_metadata': {
                'total_records': 100000,
                'interval': '1h'
            }
        }

        mock_metadata = Mock()
        for method, return_value in metadata_contract.items():
            setattr(mock_metadata, method, Mock(return_value=return_value))

        # Act - 创建策略（会注入Mock元数据管理器）
        with patch('storage.data_source_strategy.MetadataManager', return_value=mock_metadata):
            strategy = DataSourceStrategy(mock_config)

            # 测试与元数据管理的协作
            has_data = mock_metadata.has_data('BTC/USDT', '1h')
            earliest = mock_metadata.get_earliest_time('BTC/USDT', '1h')
            latest = mock_metadata.get_latest_time('BTC/USDT', '1h')
            metadata = mock_metadata.get_metadata('BTC/USDT', '1h')

        # Assert - 验证契约遵守
        assert isinstance(has_data, bool), "has_data应该返回布尔值"
        assert isinstance(earliest, datetime), "get_earliest_time应该返回datetime"
        assert isinstance(latest, datetime), "get_latest_time应该返回datetime"
        assert isinstance(metadata, dict), "get_metadata应该返回字典"


class TestDataSourceStrategyBehavior:
    """DataSourceStrategy行为测试 - 验证决策逻辑的正确性"""

    @pytest.mark.unit
    @pytest.mark.mock
    def test_local_data_preferred_behavior(self, mock_config, mock_metadata_manager):
        """
        测试优先使用本地数据的行为
        验证：当有本地数据时的决策逻辑
        """
        # Arrange - 设置有本地数据的场景
        mock_metadata_manager.has_data.return_value = True
        mock_metadata_manager.get_earliest_time.return_value = datetime(2024, 1, 1)
        mock_metadata_manager.get_latest_time.return_value = datetime(2024, 1, 31)

        start_time = datetime(2024, 1, 1)
        end_time = datetime(2024, 1, 31)

        # Act - 执行决策
        with patch('storage.data_source_strategy.MetadataManager', return_value=mock_metadata_manager):
            strategy = DataSourceStrategy(mock_config)
            decision = strategy.decide_data_source(
                exchange='binance',
                symbol='BTC/USDT',
                interval='1h',
                start_time=start_time,
                end_time=end_time
            )

        # Assert - 验证决策行为
        assert decision.source == 'local', "应该优先选择本地数据"
        assert decision.need_download is False, "不需要下载"
        assert decision.source_interval == '1h', "源周期应该与请求一致"
        assert 'local data available' in decision.reason.lower(), "理由应包含本地数据可用"

    @pytest.mark.unit
    @pytest.mark.mock
    def test_download_when_no_local_data_behavior(self, mock_config, mock_metadata_manager):
        """
        测试无本地数据时下载的行为
        验证：当没有本地数据时的决策逻辑
        """
        # Arrange - 设置无本地数据的场景
        mock_metadata_manager.has_data.return_value = False

        start_time = datetime(2024, 1, 1)
        end_time = datetime(2024, 1, 2)

        # Act - 执行决策
        with patch('storage.data_source_strategy.MetadataManager', return_value=mock_metadata_manager):
            strategy = DataSourceStrategy(mock_config)
            decision = strategy.decide_data_source(
                exchange='binance',
                symbol='BTC/USDT',
                interval='1h',
                start_time=start_time,
                end_time=end_time
            )

        # Assert - 验证下载决策行为
        assert decision.source == 'ccxt', "应该选择CCXT数据源"
        assert decision.need_download is True, "需要下载"
        assert decision.download_interval == '1h', "下载周期应该与请求一致"
        assert 'no local data' in decision.reason.lower(), "理由应包含无本地数据"

    @pytest.mark.unit
    @pytest.mark.mock
    def test_resample_when_small_range_behavior(self, mock_config, mock_metadata_manager):
        """
        测试小范围重采样的行为
        验证：当需要数据量小时的智能重采样决策
        """
        # Arrange - 设置小范围数据需求场景
        mock_metadata_manager.has_data.return_value = True
        mock_metadata_manager.get_earliest_time.return_value = datetime(2020, 1, 1)
        mock_metadata_manager.get_latest_time.return_value = datetime(2024, 1, 1)

        # 请求一个非原生周期，且数据量小
        start_time = datetime(2024, 1, 1)
        end_time = datetime(2024, 1, 1, 5, 0, 0)  # 只有5小时数据

        # Act - 执行决策
        with patch('storage.data_source_strategy.MetadataManager', return_value=mock_metadata_manager):
            strategy = DataSourceStrategy(mock_config)
            decision = strategy.decide_data_source(
                exchange='binance',
                symbol='BTC/USDT',
                interval='5m',  # 5分钟周期
                start_time=start_time,
                end_time=end_time
            )

        # Assert - 验证重采样决策行为
        assert decision.source == 'resample', "应该选择重采样"
        assert decision.source_interval == '1h', "应该从1小时重采样到5分钟"
        assert decision.need_download is False, "不需要下载"
        assert 'resample' in decision.reason.lower(), "理由应包含重采样"

    @pytest.mark.unit
    @pytest.mark.mock
    def test_download_large_range_behavior(self, mock_config, mock_metadata_manager):
        """
        测试大范围直接下载的行为
        验证：当需要数据量大时的直接下载决策
        """
        # Arrange - 设置大范围数据需求场景
        mock_metadata_manager.has_data.return_value = False

        # 请求大范围数据
        start_time = datetime(2023, 1, 1)
        end_time = datetime(2024, 1, 1)  # 一整年数据

        # Act - 执行决策
        with patch('storage.data_source_strategy.MetadataManager', return_value=mock_metadata_manager):
            strategy = DataSourceStrategy(mock_config)
            decision = strategy.decide_data_source(
                exchange='binance',
                symbol='BTC/USDT',
                interval='5m',
                start_time=start_time,
                end_time=end_time
            )

        # Assert - 验证直接下载决策行为
        assert decision.source == 'ccxt', "应该选择直接下载"
        assert decision.need_download is True, "需要下载"
        assert decision.download_interval == '5m', "应该直接下载5分钟数据"
        assert 'download' in decision.reason.lower(), "理由应包含下载"

    @pytest.mark.unit
    @pytest.mark.mock
    def test_hybrid_strategy_behavior(self, mock_config, mock_metadata_manager):
        """
        测试混合策略行为
        验证：部分本地数据时的混合策略
        """
        # Arrange - 设置部分本地数据的场景
        mock_metadata_manager.has_data.return_value = True
        mock_metadata_manager.get_earliest_time.return_value = datetime(2024, 1, 1)
        mock_metadata_manager.get_latest_time.return_value = datetime(2024, 1, 15)  # 只有半个月数据

        # 请求超出本地数据范围的数据
        start_time = datetime(2024, 1, 10)  # 从本地数据中间开始
        end_time = datetime(2024, 1, 31)    # 到本地数据之后结束

        # Act - 执行决策
        with patch('storage.data_source_strategy.MetadataManager', return_value=mock_metadata_manager):
            strategy = DataSourceStrategy(mock_config)
            decision = strategy.decide_data_source(
                exchange='binance',
                symbol='BTC/USDT',
                interval='1h',
                start_time=start_time,
                end_time=end_time
            )

        # Assert - 验证混合策略决策行为
        assert decision.source == 'hybrid', "应该选择混合策略"
        assert decision.need_download is True, "需要下载缺失部分"
        assert 'hybrid' in decision.reason.lower() or 'partial' in decision.reason.lower(), \
            "理由应包含混合或部分"


class TestDataSourceStrategyCollaboration:
    """DataSourceStrategy协作测试 - 验证与其他组件的交互"""

    @pytest.mark.unit
    @pytest.mark.contract
    def test_metadata_manager_collaboration(self, mock_config, mock_metadata_manager):
        """
        测试与MetadataManager的协作
        验证：正确调用元数据管理方法和参数传递
        """
        # Arrange - 设置协作场景
        mock_metadata_manager.has_data.return_value = True
        mock_metadata_manager.get_earliest_time.return_value = datetime(2024, 1, 1)
        mock_metadata_manager.get_latest_time.return_value = datetime(2024, 1, 31)

        # Act - 触发协作
        with patch('storage.data_source_strategy.MetadataManager', return_value=mock_metadata_manager):
            strategy = DataSourceStrategy(mock_config)
            decision = strategy.decide_data_source(
                exchange='binance',
                symbol='BTC/USDT',
                interval='1h',
                start_time=datetime(2024, 1, 1),
                end_time=datetime(2024, 1, 31)
            )

        # Assert - 验证协作交互
        mock_metadata_manager.has_data.assert_called_once_with('BTC/USDT', '1h')
        mock_metadata_manager.get_earliest_time.assert_called_once_with('BTC/USDT', '1h')
        mock_metadata_manager.get_latest_time.assert_called_once_with('BTC/USDT', '1h')

        # 验证协作结果
        assert isinstance(decision, DataSourceDecision), "应该返回DataSourceDecision对象"

    @pytest.mark.unit
    @pytest.mark.contract
    def test_config_dependency_collaboration(self, mock_config):
        """
        测试与配置的协作
        验证：正确使用配置参数
        """
        # Arrange - 设置配置参数
        mock_config.exchange = 'binance'
        mock_config.symbol = 'BTC/USDT'
        mock_config.preferred_source = 'local'  # 优先本地数据
        mock_config.resample_threshold = 5000   # 自定义重采样阈值

        # Act - 测试配置协作
        with patch('storage.data_source_strategy.MetadataManager') as mock_metadata_class:
            mock_metadata = Mock()
            mock_metadata.has_data.return_value = False
            mock_metadata_class.return_value = mock_metadata

            strategy = DataSourceStrategy(mock_config)

            # 验证配置的使用
            assert strategy.config == mock_config, "应该持有配置引用"

            # 触发决策来测试配置影响
            decision = strategy.decide_data_source(
                exchange='binance',
                symbol='BTC/USDT',
                interval='1h',
                start_time=datetime(2024, 1, 1),
                end_time=datetime(2024, 1, 2)
            )

        # Assert - 验证配置协作结果
        assert isinstance(decision, DataSourceDecision), "应该基于配置返回决策"

    @pytest.mark.unit
    @pytest.mark.contract
    def test_strategy_parameter_passing_collaboration(self, mock_config, mock_metadata_manager):
        """
        测试参数传递协作
        验证：参数在策略流程中的正确传递
        """
        # Arrange
        mock_metadata_manager.has_data.return_value = True
        mock_metadata_manager.get_earliest_time.return_value = datetime(2024, 1, 1)
        mock_metadata_manager.get_latest_time.return_value = datetime(2024, 1, 31)

        # 测试参数
        exchange = 'binance'
        symbol = 'ETH/USDT'
        interval = '4h'
        start_time = datetime(2024, 1, 1)
        end_time = datetime(2024, 1, 31)

        # Act - 执行决策
        with patch('storage.data_source_strategy.MetadataManager', return_value=mock_metadata_manager):
            strategy = DataSourceStrategy(mock_config)
            decision = strategy.decide_data_source(
                exchange=exchange,
                symbol=symbol,
                interval=interval,
                start_time=start_time,
                end_time=end_time
            )

        # Assert - 验证参数传递协作
        # 验证元数据管理器接收到的参数
        mock_metadata_manager.has_data.assert_called_with(symbol, interval)
        mock_metadata_manager.get_earliest_time.assert_called_with(symbol, interval)
        mock_metadata_manager.get_latest_time.assert_called_with(symbol, interval)


class TestDataSourceStrategyEdgeCases:
    """DataSourceStrategy边界条件测试"""

    @pytest.mark.unit
    @pytest.mark.mock
    def test_invalid_time_range_behavior(self, mock_config, mock_metadata_manager):
        """
        测试无效时间范围行为
        验证：边界条件的处理
        """
        # Arrange - 设置无效时间范围
        mock_metadata_manager.has_data.return_value = False

        start_time = datetime(2024, 1, 2)
        end_time = datetime(2024, 1, 1)  # 开始时间晚于结束时间

        # Act & Assert - 验证错误处理
        with patch('storage.data_source_strategy.MetadataManager', return_value=mock_metadata_manager):
            strategy = DataSourceStrategy(mock_config)

            with pytest.raises(ValueError, match="Start time must be before end time"):
                strategy.decide_data_source(
                    exchange='binance',
                    symbol='BTC/USDT',
                    interval='1h',
                    start_time=start_time,
                    end_time=end_time
                )

    @pytest.mark.unit
    @pytest.mark.mock
    def test_same_time_range_behavior(self, mock_config, mock_metadata_manager):
        """
        测试相同时间范围行为
        验证：单点时间请求的处理
        """
        # Arrange - 设置相同时间范围
        mock_metadata_manager.has_data.return_value = True
        mock_metadata_manager.get_earliest_time.return_value = datetime(2024, 1, 1)
        mock_metadata_manager.get_latest_time.return_value = datetime(2024, 1, 1)

        same_time = datetime(2024, 1, 1)

        # Act - 执行决策
        with patch('storage.data_source_strategy.MetadataManager', return_value=mock_metadata_manager):
            strategy = DataSourceStrategy(mock_config)
            decision = strategy.decide_data_source(
                exchange='binance',
                symbol='BTC/USDT',
                interval='1h',
                start_time=same_time,
                end_time=same_time
            )

        # Assert - 验证单点时间处理
        assert decision.source == 'local', "单点时间应该优先使用本地数据"
        assert decision.need_download is False, "单点时间不需要下载"

    @pytest.mark.unit
    @pytest.mark.mock
    def test_unsupported_interval_behavior(self, mock_config, mock_metadata_manager):
        """
        测试不支持的时间周期行为
        验证：非标准周期的处理
        """
        # Arrange - 设置不支持的周期
        mock_metadata_manager.has_data.return_value = False

        # Act - 执行决策
        with patch('storage.data_source_strategy.MetadataManager', return_value=mock_metadata_manager):
            strategy = DataSourceStrategy(mock_config)
            decision = strategy.decide_data_source(
                exchange='binance',
                symbol='BTC/USDT',
                interval='7m',  # 7分钟（非标准周期）
                start_time=datetime(2024, 1, 1),
                end_time=datetime(2024, 1, 2)
            )

        # Assert - 验证非标准周期处理
        assert decision.source == 'ccxt', "非标准周期应该直接下载"
        assert decision.need_download is True, "非标准周期需要下载"
        assert decision.download_interval == '7m', "应该下载原始周期"

    @pytest.mark.unit
    @pytest.mark.mock
    def test_metadata_error_handling_behavior(self, mock_config):
        """
        测试元数据错误处理行为
        验证：元数据访问失败时的处理
        """
        # Arrange - 设置元数据错误
        mock_metadata_manager = Mock()
        mock_metadata_manager.has_data.side_effect = Exception("Metadata access failed")

        # Act & Assert - 验证错误处理
        with patch('storage.data_source_strategy.MetadataManager', return_value=mock_metadata_manager):
            strategy = DataSourceStrategy(mock_config)

            # 应该能够处理元数据错误
            with pytest.raises(Exception, match="Metadata access failed"):
                strategy.decide_data_source(
                    exchange='binance',
                    symbol='BTC/USDT',
                    interval='1h',
                    start_time=datetime(2024, 1, 1),
                    end_time=datetime(2024, 1, 2)
                )


class TestDataSourceStrategyPerformance:
    """DataSourceStrategy性能测试"""

    @pytest.mark.unit
    @pytest.mark.performance
    def test_decision_performance(self, mock_config, mock_metadata_manager, performance_timer):
        """
        测试决策性能
        验证：快速决策能力
        """
        # Arrange - 设置性能测试场景
        mock_metadata_manager.has_data.return_value = True
        mock_metadata_manager.get_earliest_time.return_value = datetime(2020, 1, 1)
        mock_metadata_manager.get_latest_time.return_value = datetime(2024, 1, 1)

        # Act - 测试决策性能
        with patch('storage.data_source_strategy.MetadataManager', return_value=mock_metadata_manager):
            strategy = DataSourceStrategy(mock_config)

            performance_timer.start()

            # 执行多次决策
            for i in range(100):
                decision = strategy.decide_data_source(
                    exchange='binance',
                    symbol='BTC/USDT',
                    interval='1h',
                    start_time=datetime(2024, 1, 1),
                    end_time=datetime(2024, 1, 2)
                )
                assert isinstance(decision, DataSourceDecision), f"第{i+1}次决策应该成功"

            performance_timer.stop()

        # Assert - 验证性能
        assert performance_timer.elapsed < 1.0, "100次决策应该在1秒内完成"
        assert mock_metadata_manager.has_data.call_count == 100, "应该调用has_data 100次"

    @pytest.mark.unit
    @pytest.mark.performance
    def test_native_timeframe_check_performance(self, mock_config, performance_timer):
        """
        测试原生时间周期检查性能
        验证：快速时间周期判断
        """
        # Act - 测试时间周期检查性能
        with patch('storage.data_source_strategy.MetadataManager'):
            strategy = DataSourceStrategy(mock_config)

            timeframes = ['1m', '5m', '15m', '30m', '1h', '4h', '1d', '1w', '1M',
                         '2m', '3m', '10m', '20m', '2h', '6h', '8h', '12h', '3d']

            performance_timer.start()

            # 执行多次时间周期检查
            for _ in range(1000):
                for timeframe in timeframes:
                    result = strategy.is_native_timeframe(timeframe)
                    assert isinstance(result, bool), f"应该返回布尔值: {timeframe}"

            performance_timer.stop()

        # Assert - 验证性能
        total_checks = len(timeframes) * 1000
        assert performance_timer.elapsed < 0.5, f"{total_checks}次检查应该在0.5秒内完成"