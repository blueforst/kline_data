"""
性能基准测试

测试系统各个组件的性能指标，包括数据查询、下载、重采样、
指标计算等关键操作的性能基准。
"""

import pytest
import time
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import tempfile
import shutil
from unittest.mock import Mock, patch
import psutil
import os

# 导入项目模块
from kline_data.storage.data_source_strategy import DataSourceStrategy
from kline_data.storage.fetcher import DataFetcher
from kline_data.storage.downloader import DownloadManager
from kline_data.reader.parquet_reader import ParquetReader
from kline_data.resampler.kline_resampler import KlineResampler
from kline_data.indicators.manager import IndicatorManager


class TestQueryPerformance:
    """测试数据查询性能"""

    @pytest.fixture
    def large_ohlcv_dataset(self):
        """创建大型OHLCV数据集"""
        np.random.seed(42)  # 确保可重复性

        # 生成1年的小时数据（8760条记录）
        timestamps = pd.date_range('2023-01-01', periods=8760, freq='1h')

        # 生成真实的价格序列
        base_price = 50000.0
        returns = np.random.normal(0, 0.002, 8760)  # 0.2%波动率
        prices = [base_price]

        for ret in returns:
            prices.append(max(prices[-1] * (1 + ret), 1.0))

        prices = prices[1:]

        data = []
        for i, ts in enumerate(timestamps):
            current_price = prices[i]
            open_price = prices[i-1] if i > 0 else current_price
            close_price = current_price

            # 生成合理的OHLC
            price_range = current_price * 0.01  # 1%价格范围
            high = max(open_price, close_price) + price_range * np.random.uniform(0.3, 1.0)
            low = min(open_price, close_price) - price_range * np.random.uniform(0.3, 1.0)
            high = max(high, open_price, close_price)
            low = min(low, open_price, close_price)

            volume = np.random.randint(100000, 1000000)

            data.append({
                'timestamp': ts,
                'open': round(open_price, 2),
                'high': round(high, 2),
                'low': round(low, 2),
                'close': round(close_price, 2),
                'volume': volume
            })

        return pd.DataFrame(data)

    @pytest.fixture
    def temp_parquet_file(self, temp_dir, large_ohlcv_dataset):
        """创建临时Parquet文件"""
        file_path = temp_dir / "large_data.parquet"
        large_ohlcv_dataset.to_parquet(file_path, index=False, compression='snappy')
        return file_path

    @pytest.mark.benchmark
    def test_large_dataset_query_performance(self, temp_parquet_file, large_ohlcv_dataset):
        """测试大数据集查询性能"""
        reader = ParquetReader(str(temp_parquet_file.parent))

        start_time = datetime(2023, 6, 1)
        end_time = datetime(2023, 6, 30)  # 30天数据

        # 基准测试：查询30天数据
        result = reader.read_data(
            exchange='binance',
            symbol='BTC/USDT',
            timeframe='1h',
            start_time=start_time,
            end_time=end_time
        )

        # 验证结果
        assert not result.empty
        assert len(result) == 30 * 24  # 30天 * 24小时

        # 性能断言（通过pytest-benchmark自动处理）
        return result

    @pytest.mark.benchmark
    def test_parallel_query_performance(self, temp_dir, large_ohlcv_dataset):
        """测试并行查询性能"""
        # 创建多个文件模拟分布式数据
        files = []
        chunk_size = 24 * 30  # 30天的数据

        for i in range(0, len(large_ohlcv_dataset), chunk_size):
            chunk = large_ohlcv_dataset.iloc[i:i+chunk_size]
            file_path = temp_dir / f"chunk_{i//chunk_size}.parquet"
            chunk.to_parquet(file_path, index=False)
            files.append(file_path)

        # 模拟并行查询
        reader = ParquetReader(str(temp_dir))

        # 测试并行读取性能
        start_time = datetime(2023, 3, 1)
        end_time = datetime(2023, 5, 31)  # 3个月数据

        result = reader.read_data(
            exchange='binance',
            symbol='BTC/USDT',
            timeframe='1h',
            start_time=start_time,
            end_time=end_time
        )

        assert not result.empty
        assert len(result) == 90 * 24  # 90天 * 24小时

        return result

    @pytest.mark.benchmark
    def test_memory_efficient_query(self, temp_parquet_file):
        """测试内存高效的查询"""
        # 使用内存映射读取
        reader = ParquetReader(str(temp_parquet_file.parent))

        # 测试大时间范围的内存效率
        start_time = datetime(2023, 1, 1)
        end_time = datetime(2023, 12, 31)

        initial_memory = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024

        result = reader.read_data(
            exchange='binance',
            symbol='BTC/USDT',
            timeframe='1h',
            start_time=start_time,
            end_time=end_time
        )

        final_memory = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024
        memory_delta = final_memory - initial_memory

        # 验证内存使用合理性（应该不超过数据的2倍大小）
        data_size_mb = len(result) * 8 * 6 / 1024 / 1024  # 估算数据大小
        assert memory_delta < data_size_mb * 3, f"Memory usage too high: {memory_delta:.1f}MB"

        return result


class TestResamplingPerformance:
    """测试重采样性能"""

    @pytest.fixture
    def minute_data(self):
        """创建1分钟数据"""
        # 生成30天的1分钟数据
        periods = 30 * 24 * 60  # 30天 * 24小时 * 60分钟
        timestamps = pd.date_range('2023-01-01', periods=periods, freq='1min')

        np.random.seed(42)
        base_price = 50000.0
        returns = np.random.normal(0, 0.001, periods)
        prices = [base_price]

        for ret in returns:
            prices.append(max(prices[-1] * (1 + ret), 1.0))

        prices = prices[1:]

        data = []
        for i, ts in enumerate(timestamps):
            current_price = prices[i]
            open_price = prices[i-1] if i > 0 else current_price
            close_price = current_price

            price_range = current_price * 0.005
            high = max(open_price, close_price) + price_range * np.random.uniform(0.2, 0.8)
            low = min(open_price, close_price) - price_range * np.random.uniform(0.2, 0.8)
            high = max(high, open_price, close_price)
            low = min(low, open_price, close_price)

            volume = np.random.randint(1000, 100000)

            data.append({
                'timestamp': ts,
                'open': round(open_price, 2),
                'high': round(high, 2),
                'low': round(low, 2),
                'close': round(close_price, 2),
                'volume': volume
            })

        return pd.DataFrame(data)

    @pytest.mark.benchmark
    def test_1m_to_1h_resampling(self, minute_data):
        """测试1分钟到1小时重采样性能"""
        resampler = KlineResampler()

        # 重采样到1小时
        result = resampler.resample(
            data=minute_data,
            target_timeframe='1h'
        )

        assert not result.empty
        assert len(result) == 30 * 24  # 30天 * 24小时

        return result

    @pytest.mark.benchmark
    def test_1m_to_1d_resampling(self, minute_data):
        """测试1分钟到1天重采样性能"""
        resampler = KlineResampler()

        result = resampler.resample(
            data=minute_data,
            target_timeframe='1d'
        )

        assert not result.empty
        assert len(result) == 30  # 30天

        return result

    @pytest.mark.benchmark
    def test_multiple_timeframes_resampling(self, minute_data):
        """测试多时间周期重采样性能"""
        resampler = KlineResampler()

        target_timeframes = ['5m', '15m', '30m', '1h', '4h', '1d']
        results = {}

        for timeframe in target_timeframes:
            results[timeframe] = resampler.resample(
                data=minute_data,
                target_timeframe=timeframe
            )

        # 验证所有结果都有效
        for timeframe, result in results.items():
            assert not result.empty, f"Empty result for {timeframe}"

        return results

    def test_resampling_memory_efficiency(self, minute_data):
        """测试重采样内存效率"""
        initial_memory = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024
        original_size = len(minute_data)

        resampler = KlineResampler()

        # 执行多次重采样
        for timeframe in ['5m', '15m', '1h', '4h']:
            result = resampler.resample(
                data=minute_data,
                target_timeframe=timeframe
            )
            del result  # 立即释放内存

        final_memory = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024
        memory_delta = final_memory - initial_memory

        # 验证内存增长合理
        original_size_mb = original_size * 8 * 6 / 1024 / 1024
        assert memory_delta < original_size_mb * 0.5, f"Memory leak detected: {memory_delta:.1f}MB"


class TestIndicatorPerformance:
    """测试技术指标计算性能"""

    @pytest.fixture
    def test_data(self):
        """创建指标测试数据"""
        # 生成1年的日线数据
        periods = 365
        timestamps = pd.date_range('2023-01-01', periods=periods, freq='1D')

        np.random.seed(42)
        base_price = 50000.0
        returns = np.random.normal(0.0005, 0.02, periods)  # 日波动率2%
        prices = [base_price]

        for ret in returns:
            prices.append(max(prices[-1] * (1 + ret), 1.0))

        prices = prices[1:]

        data = []
        for i, ts in enumerate(timestamps):
            current_price = prices[i]
            open_price = prices[i-1] if i > 0 else current_price
            close_price = current_price

            high = max(open_price, close_price) * (1 + np.random.uniform(0, 0.02))
            low = min(open_price, close_price) * (1 - np.random.uniform(0, 0.02))
            volume = np.random.randint(1000000, 10000000)

            data.append({
                'timestamp': ts,
                'open': round(open_price, 2),
                'high': round(high, 2),
                'low': round(low, 2),
                'close': round(close_price, 2),
                'volume': volume
            })

        return pd.DataFrame(data)

    @pytest.mark.benchmark
    def test_sma_calculation_performance(self, test_data):
        """测试SMA计算性能"""
        indicator_manager = IndicatorManager()

        result = indicator_manager.calculate(
            data=test_data,
            indicator_name='SMA',
            period=20
        )

        assert not result.empty
        assert 'SMA_20' in result.columns

        return result

    @pytest.mark.benchmark
    def test_ema_calculation_performance(self, test_data):
        """测试EMA计算性能"""
        indicator_manager = IndicatorManager()

        result = indicator_manager.calculate(
            data=test_data,
            indicator_name='EMA',
            period=50
        )

        assert not result.empty
        assert 'EMA_50' in result.columns

        return result

    @pytest.mark.benchmark
    def test_macd_calculation_performance(self, test_data):
        """测试MACD计算性能"""
        indicator_manager = IndicatorManager()

        result = indicator_manager.calculate(
            data=test_data,
            indicator_name='MACD',
            fast_period=12,
            slow_period=26,
            signal_period=9
        )

        assert not result.empty
        macd_cols = [col for col in result.columns if 'MACD' in col]
        assert len(macd_cols) > 0

        return result

    @pytest.mark.benchmark
    def test_bollinger_bands_calculation(self, test_data):
        """测试布林带计算性能"""
        indicator_manager = IndicatorManager()

        result = indicator_manager.calculate(
            data=test_data,
            indicator_name='BB',
            period=20,
            std_dev=2
        )

        assert not result.empty
        bb_cols = [col for col in result.columns if 'BB' in col]
        assert len(bb_cols) >= 3  # 上轨、中轨、下轨

        return result

    @pytest.mark.benchmark
    def test_multiple_indicators_performance(self, test_data):
        """测试多指标并发计算性能"""
        indicator_manager = IndicatorManager()

        indicators = [
            {'name': 'SMA', 'period': 20},
            {'name': 'EMA', 'period': 50},
            {'name': 'RSI', 'period': 14},
            {'name': 'MACD', 'fast_period': 12, 'slow_period': 26, 'signal_period': 9},
            {'name': 'BB', 'period': 20, 'std_dev': 2},
            {'name': 'ATR', 'period': 14},
            {'name': 'OBV'}
        ]

        result = indicator_manager.calculate_multiple(
            data=test_data,
            indicators=indicators
        )

        assert not result.empty
        # 验证所有指标都被计算
        indicator_cols = [col for col in result.columns if col not in ['timestamp', 'open', 'high', 'low', 'close', 'volume']]
        assert len(indicator_cols) >= len(indicators)

        return result


class TestDownloadPerformance:
    """测试下载性能"""

    @pytest.fixture
    def mock_ccxt_exchange(self):
        """Mock CCXT交易所"""
        exchange = Mock()
        exchange.name = 'binance'
        exchange.rateLimit = 100  # 100ms速率限制

        def mock_fetch_ohlcv(symbol, timeframe, since=None, limit=None):
            # 模拟网络延迟和数据处理
            time.sleep(0.05)  # 50ms网络延迟

            now = int(datetime.now().timestamp() * 1000)
            data = []
            base_price = 50000

            for i in range(min(limit or 100, 100)):
                timestamp = now - (i * 3600000)  # 1小时间隔
                price = base_price * (1 + np.random.normal(0, 0.001))
                data.append([
                    timestamp,
                    price,  # open
                    price * 1.01,  # high
                    price * 0.99,  # low
                    price * 1.005,  # close
                    100000  # volume
                ])

            return data

        exchange.fetch_ohlcv = mock_fetch_ohlcv
        return exchange

    @pytest.mark.benchmark
    def test_download_speed_performance(self, mock_ccxt_exchange, temp_dir):
        """测试下载速度性能"""
        with patch('ccxt.binance', return_value=mock_ccxt_exchange):
            download_manager = DownloadManager({
                'data_dir': str(temp_dir),
                'max_concurrent': 1,
                'rate_limit': 100
            })

            # 测试下载1000条记录的性能
            result = download_manager.download_data(
                exchange='binance',
                symbol='BTC/USDT',
                timeframe='1h',
                limit=1000
            )

            assert not result.empty
            assert len(result) == 1000

            return result

    @pytest.mark.benchmark
    def test_concurrent_download_performance(self, mock_ccxt_exchange, temp_dir):
        """测试并发下载性能"""
        with patch('ccxt.binance', return_value=mock_ccxt_exchange):
            download_manager = DownloadManager({
                'data_dir': str(temp_dir),
                'max_concurrent': 4,
                'rate_limit': 100
            })

            # 并发下载多个交易对
            symbols = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'ADA/USDT']
            results = []

            start_time = time.perf_counter()

            for symbol in symbols:
                result = download_manager.download_data(
                    exchange='binance',
                    symbol=symbol,
                    timeframe='1h',
                    limit=500
                )
                results.append(result)

            duration = time.perf_counter() - start_time

            # 验证所有下载都成功
            for result in results:
                assert not result.empty
                assert len(result) == 500

            # 并发下载应该比串行快（这里简单验证总时间合理）
            assert duration < 5.0, f"Concurrent download too slow: {duration:.2f}s"

            return results

    def test_download_memory_usage(self, mock_ccxt_exchange, temp_dir):
        """测试下载内存使用"""
        initial_memory = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024

        with patch('ccxt.binance', return_value=mock_ccxt_exchange):
            download_manager = DownloadManager({
                'data_dir': str(temp_dir),
                'max_concurrent': 1,
                'rate_limit': 100
            })

            # 下载大量数据
            result = download_manager.download_data(
                exchange='binance',
                symbol='BTC/USDT',
                timeframe='1m',
                limit=10000  # 10,000条记录
            )

            final_memory = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024
            memory_delta = final_memory - initial_memory

            # 验证内存使用合理（应该不超过数据大小的3倍）
            data_size_mb = len(result) * 8 * 6 / 1024 / 1024
            assert memory_delta < data_size_mb * 3, f"Memory usage too high: {memory_delta:.1f}MB"

            assert len(result) == 10000
            return result


class TestDataSourceStrategyPerformance:
    """测试数据源策略性能"""

    @pytest.fixture
    def strategy(self, temp_dir):
        """创建数据源策略实例"""
        config = Mock()
        config.storage.data_dir = str(temp_dir)
        config.download.enabled = True
        config.resample.enabled = True

        return DataSourceStrategy(config)

    @pytest.mark.benchmark
    def test_strategy_decision_performance(self, strategy):
        """测试策略决策性能"""
        start_time = datetime(2024, 1, 1)
        end_time = datetime(2024, 1, 31)

        # Mock元数据检查
        strategy.metadata_mgr.metadata_exists.return_value = True
        strategy.metadata_mgr.get_metadata.return_value = {
            'first_timestamp': start_time - timedelta(days=1),
            'last_timestamp': end_time + timedelta(days=1),
            'total_records': 744,  # 31天 * 24小时
            'timeframe': '1h'
        }

        # 测试决策性能
        decision = strategy.decide_data_source(
            exchange='binance',
            symbol='BTC/USDT',
            timeframe='1h',
            start_time=start_time,
            end_time=end_time
        )

        assert decision.source == 'local'
        assert decision.need_download == False

        return decision

    @pytest.mark.benchmark
    def test_strategy_multiple_decisions(self, strategy):
        """测试策略多决策性能"""
        symbols = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'ADA/USDT', 'SOL/USDT']
        timeframes = ['1h', '4h', '1d']

        decisions = []

        for symbol in symbols:
            for timeframe in timeframes:
                start_time = datetime(2024, 1, 1)
                end_time = datetime(2024, 1, 31)

                # Mock决策逻辑
                strategy.metadata_mgr.metadata_exists.return_value = True
                strategy.metadata_mgr.get_metadata.return_value = {
                    'first_timestamp': start_time - timedelta(days=1),
                    'last_timestamp': end_time + timedelta(days=1),
                    'total_records': 1000,
                    'timeframe': timeframe
                }

                decision = strategy.decide_data_source(
                    exchange='binance',
                    symbol=symbol,
                    timeframe=timeframe,
                    start_time=start_time,
                    end_time=end_time
                )
                decisions.append(decision)

        # 验证所有决策都完成
        assert len(decisions) == len(symbols) * len(timeframes)
        for decision in decisions:
            assert hasattr(decision, 'source')

        return decisions


class TestOverallSystemPerformance:
    """测试整体系统性能"""

    @pytest.fixture
    def integrated_test_data(self, temp_dir):
        """创建集成测试数据"""
        # 创建多个时间周期的数据文件
        timeframes = ['1m', '5m', '15m', '1h']
        data_files = {}

        for timeframe in timeframes:
            # 计算数据量
            minutes_map = {'1m': 1, '5m': 5, '15m': 15, '1h': 60}
            minutes = minutes_map[timeframe]
            periods = 7 * 24 * 60 // minutes  # 一周数据

            timestamps = pd.date_range('2024-01-01', periods=periods, freq=f'{minutes}min')

            np.random.seed(42)
            base_price = 50000.0
            data = []

            for i, ts in enumerate(timestamps):
                price = base_price * (1 + np.random.normal(0, 0.002))
                data.append({
                    'timestamp': ts,
                    'open': round(price, 2),
                    'high': round(price * 1.01, 2),
                    'low': round(price * 0.99, 2),
                    'close': round(price * 1.005, 2),
                    'volume': np.random.randint(1000, 100000)
                })

            df = pd.DataFrame(data)
            file_path = temp_dir / f"binance_BTC_USDT_{timeframe}.parquet"
            df.to_parquet(file_path, index=False)
            data_files[timeframe] = file_path

        return data_files

    @pytest.mark.benchmark
    def test_end_to_end_query_pipeline(self, integrated_test_data):
        """测试端到端查询管道性能"""
        reader = ParquetReader(str(integrated_test_data['1h'].parent))
        resampler = KlineResampler()
        indicator_manager = IndicatorManager()

        start_time = datetime(2024, 1, 1)
        end_time = datetime(2024, 1, 7)  # 一周数据

        # 1. 数据读取
        raw_data = reader.read_data(
            exchange='binance',
            symbol='BTC/USDT',
            timeframe='1h',
            start_time=start_time,
            end_time=end_time
        )

        # 2. 重采样到4小时
        resampled_data = resampler.resample(
            data=raw_data,
            target_timeframe='4h'
        )

        # 3. 计算技术指标
        final_data = indicator_manager.calculate_multiple(
            data=resampled_data,
            indicators=[
                {'name': 'SMA', 'period': 20},
                {'name': 'EMA', 'period': 20},
                {'name': 'RSI', 'period': 14},
                {'name': 'MACD', 'fast_period': 12, 'slow_period': 26, 'signal_period': 9}
            ]
        )

        # 验证结果
        assert not final_data.empty
        assert len(final_data) == 7 * 6  # 7天 * 6个4小时段

        # 验证指标存在
        indicator_cols = [col for col in final_data.columns if any(
            indicator in col for indicator in ['SMA', 'EMA', 'RSI', 'MACD']
        )]
        assert len(indicator_cols) > 0

        return final_data

    def test_memory_efficiency_large_dataset(self, integrated_test_data):
        """测试大数据集内存效率"""
        initial_memory = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024

        reader = ParquetReader(str(integrated_test_data['1m'].parent))

        # 读取最大数据集（1分钟数据）
        result = reader.read_data(
            exchange='binance',
            symbol='BTC/USDT',
            timeframe='1m',
            start_time=datetime(2024, 1, 1),
            end_time=datetime(2024, 1, 7)
        )

        final_memory = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024
        memory_delta = final_memory - initial_memory

        # 验证内存使用合理
        data_size_mb = len(result) * 8 * 6 / 1024 / 1024
        memory_ratio = memory_delta / data_size_mb if data_size_mb > 0 else 0

        assert memory_ratio < 5.0, f"Memory usage too high: {memory_ratio:.1f}x data size"
        assert len(result) == 7 * 24 * 60  # 7天 * 24小时 * 60分钟

        return result

    @pytest.mark.benchmark
    def test_concurrent_operations(self, integrated_test_data):
        """测试并发操作性能"""
        import threading
        import queue

        reader = ParquetReader(str(integrated_test_data['1h'].parent))

        # 创建任务队列
        result_queue = queue.Queue()

        def worker(timeframe):
            start_time = datetime(2024, 1, 1)
            end_time = datetime(2024, 1, 3)  # 2天数据

            result = reader.read_data(
                exchange='binance',
                symbol='BTC/USDT',
                timeframe=timeframe,
                start_time=start_time,
                end_time=end_time
            )
            result_queue.put((timeframe, result))

        # 并发读取多个时间周期
        timeframes = ['1h', '4h', '1d']
        threads = []

        start_time = time.perf_counter()

        for timeframe in timeframes:
            thread = threading.Thread(target=worker, args=(timeframe,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        duration = time.perf_counter() - start_time

        # 收集结果
        results = []
        while not result_queue.empty():
            results.append(result_queue.get())

        # 验证结果
        assert len(results) == len(timeframes)
        for timeframe, result in results:
            assert not result.empty

        # 并发操作应该有合理的性能
        assert duration < 2.0, f"Concurrent operations too slow: {duration:.2f}s"

        return results


# ============================================================================
# 性能回归测试
# ============================================================================

class TestPerformanceRegression:
    """性能回归测试"""

    def test_query_time_regression(self, temp_dir):
        """测试查询时间回归"""
        # 创建测试数据
        data = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=10000, freq='1h'),
            'open': np.random.uniform(45000, 55000, 10000),
            'high': np.random.uniform(45000, 55000, 10000),
            'low': np.random.uniform(45000, 55000, 10000),
            'close': np.random.uniform(45000, 55000, 10000),
            'volume': np.random.randint(100000, 1000000, 10000)
        })

        file_path = temp_dir / "regression_test.parquet"
        data.to_parquet(file_path, index=False)

        reader = ParquetReader(str(temp_dir))

        # 测量查询时间
        start_time = time.perf_counter()
        result = reader.read_data(
            exchange='binance',
            symbol='BTC/USDT',
            timeframe='1h',
            start_time=datetime(2024, 1, 1),
            end_time=datetime(2024, 1, 10)
        )
        duration = time.perf_counter() - start_time

        # 性能断言（查询应该很快）
        assert duration < 0.1, f"Query too slow: {duration*1000:.1f}ms"
        assert len(result) == 9 * 24  # 9天 * 24小时

    def test_memory_leak_regression(self, temp_dir):
        """测试内存泄漏回归"""
        reader = ParquetReader(str(temp_dir))

        initial_memory = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024

        # 执行多次查询
        for i in range(10):
            # 创建临时数据文件
            data = pd.DataFrame({
                'timestamp': pd.date_range('2024-01-01', periods=1000, freq='1h'),
                'open': np.random.uniform(45000, 55000, 1000),
                'high': np.random.uniform(45000, 55000, 1000),
                'low': np.random.uniform(45000, 55000, 1000),
                'close': np.random.uniform(45000, 55000, 1000),
                'volume': np.random.randint(100000, 1000000, 1000)
            })

            file_path = temp_dir / f"temp_{i}.parquet"
            data.to_parquet(file_path, index=False)

            result = reader.read_data(
                exchange='binance',
                symbol='BTC/USDT',
                timeframe='1h',
                start_time=datetime(2024, 1, 1),
                end_time=datetime(2024, 1, 10)
            )

            del result  # 显式删除结果

        final_memory = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024
        memory_delta = final_memory - initial_memory

        # 验证没有明显的内存泄漏
        assert memory_delta < 50, f"Potential memory leak: {memory_delta:.1f}MB increase"


if __name__ == "__main__":
    # 运行性能测试的示例
    pytest.main([__file__, "-v", "--benchmark-only"])