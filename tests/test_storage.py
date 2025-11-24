"""存储层测试"""

import pytest
import pandas as pd
import tempfile
from pathlib import Path
from datetime import datetime, timedelta

from config import load_config
from storage import (
    KlineData,
    DataValidator,
    ParquetWriter,
    MetadataManager,
    TaskStatus,
)

# 导入全局常量
from utils.constants import (
    DEFAULT_EXCHANGE,
    DEFAULT_SYMBOL,
    TEST_SYMBOLS,
    SUPPORTED_EXCHANGES,
)


class TestKlineData:
    """测试KlineData模型"""
    
    def test_create_kline_data(self):
        """测试创建K线数据"""
        kline = KlineData(
            timestamp=1609459200000,
            open=29000.0,
            high=29500.0,
            low=28500.0,
            close=29200.0,
            volume=100.5
        )
        
        assert kline.timestamp == 1609459200000
        assert kline.open == 29000.0
        assert kline.high == 29500.0
    
    def test_invalid_kline_data(self):
        """测试无效的K线数据"""
        # high < low
        with pytest.raises(ValueError):
            KlineData(
                timestamp=1609459200000,
                open=29000.0,
                high=28000.0,  # high < low
                low=28500.0,
                close=29200.0,
                volume=100.5
            )
        
        # 负数交易量
        with pytest.raises(ValueError):
            KlineData(
                timestamp=1609459200000,
                open=29000.0,
                high=29500.0,
                low=28500.0,
                close=29200.0,
                volume=-10.0
            )
    
    def test_from_ccxt(self):
        """测试从CCXT数据创建"""
        ccxt_data = [1609459200000, 29000.0, 29500.0, 28500.0, 29200.0, 100.5]
        kline = KlineData.from_ccxt(ccxt_data)
        
        assert kline.timestamp == 1609459200000
        assert kline.close == 29200.0
        assert kline.volume == 100.5
    
    def test_to_dict(self):
        """测试转换为字典"""
        kline = KlineData(
            timestamp=1609459200000,
            open=29000.0,
            high=29500.0,
            low=28500.0,
            close=29200.0,
            volume=100.5
        )
        
        d = kline.to_dict()
        assert isinstance(d, dict)
        assert d['timestamp'] == 1609459200000
        assert d['volume'] == 100.5


class TestDataValidator:
    """测试数据验证器"""
    
    def create_sample_df(self) -> pd.DataFrame:
        """创建示例数据"""
        data = {
            'timestamp': pd.date_range('2024-01-01', periods=10, freq='1s'),
            'open': [100.0] * 10,
            'high': [105.0] * 10,
            'low': [95.0] * 10,
            'close': [102.0] * 10,
            'volume': [1000.0] * 10,
        }
        return pd.DataFrame(data)
    
    def test_validate_kline_valid_data(self):
        """测试验证有效数据"""
        df = self.create_sample_df()
        result = DataValidator.validate_kline(df)
        
        assert len(result) == 10
        assert all(col in result.columns for col in ['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    
    def test_validate_kline_invalid_high_low(self):
        """测试验证无效的high/low"""
        df = self.create_sample_df()
        df.loc[0, 'high'] = 90.0  # high < low
        
        result = DataValidator.validate_kline(df)
        
        # 应该移除无效行
        assert len(result) < 10
    
    def test_validate_kline_negative_volume(self):
        """测试负数交易量"""
        df = self.create_sample_df()
        df.loc[0, 'volume'] = -100.0
        
        result = DataValidator.validate_kline(df)
        
        # 应该修正为0
        assert result.loc[0, 'volume'] == 0.0
    
    def test_validate_kline_duplicates(self):
        """测试去重"""
        df = self.create_sample_df()
        df = pd.concat([df, df.iloc[[0]]], ignore_index=True)  # 添加重复行
        
        result = DataValidator.validate_kline(df)
        
        # 应该去除重复
        assert len(result) == 10
    
    def test_check_completeness(self):
        """测试完整性检查"""
        df = self.create_sample_df()
        
        completeness, missing_ranges = DataValidator.check_completeness(df, '1s')
        
        assert completeness == 1.0  # 完整数据
        assert len(missing_ranges) == 0
    
    def test_check_completeness_with_gaps(self):
        """测试带缺失的完整性检查"""
        df = self.create_sample_df()
        # 移除中间的行，创建缺口
        df = df.drop(index=[4, 5, 6])
        
        completeness, missing_ranges = DataValidator.check_completeness(df, '1s')
        
        assert completeness < 1.0
        assert len(missing_ranges) > 0
    
    def test_check_data_quality(self):
        """测试数据质量检查"""
        df = self.create_sample_df()
        
        quality = DataValidator.check_data_quality(df, '1s')
        
        assert quality.completeness == 1.0
        assert quality.duplicate_rate == 0.0


class TestParquetWriter:
    """测试Parquet写入器"""
    
    @pytest.fixture
    def temp_config(self):
        """创建临时配置"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = load_config('config/config.yaml')
            config.storage.root_path = tmpdir
            yield config
    
    @pytest.fixture
    def sample_df(self):
        """创建示例数据"""
        data = {
            'timestamp': pd.date_range('2024-01-01', periods=100, freq='1s'),
            'open': [100.0] * 100,
            'high': [105.0] * 100,
            'low': [95.0] * 100,
            'close': [102.0] * 100,
            'volume': [1000.0] * 100,
        }
        return pd.DataFrame(data)
    
    def test_write_parquet(self, temp_config, sample_df):
        """测试写入Parquet文件"""
        writer = ParquetWriter(temp_config)
        
        file_path = Path(temp_config.storage.root_path) / 'test.parquet'
        partition_info = writer.write(sample_df, file_path)
        
        assert file_path.exists()
        assert partition_info.records == 100
        assert partition_info.size_bytes > 0
    
    def test_append_parquet(self, temp_config, sample_df):
        """测试追加数据"""
        writer = ParquetWriter(temp_config)
        
        file_path = Path(temp_config.storage.root_path) / 'test.parquet'
        
        # 首次写入
        writer.write(sample_df.iloc[:50], file_path)
        
        # 追加数据
        partition_info = writer.append(sample_df.iloc[50:], file_path)
        
        assert partition_info.records == 100
    
    def test_write_partitioned(self, temp_config, sample_df):
        """测试分区写入"""
        writer = ParquetWriter(temp_config)
        
        partition_infos = writer.write_partitioned(
            sample_df,
            DEFAULT_EXCHANGE,
            DEFAULT_SYMBOL,
            '1s'
        )
        
        assert len(partition_infos) > 0
        assert all(p.records > 0 for p in partition_infos)
    
    def test_verify_integrity(self, temp_config, sample_df):
        """测试文件完整性验证"""
        writer = ParquetWriter(temp_config)
        
        file_path = Path(temp_config.storage.root_path) / 'test.parquet'
        partition_info = writer.write(sample_df, file_path)
        
        # 验证校验和
        is_valid = writer.verify_integrity(file_path, partition_info.checksum)
        assert is_valid is True
        
        # 验证错误的校验和
        is_valid = writer.verify_integrity(file_path, 'wrong_checksum')
        assert is_valid is False


class TestMetadataManager:
    """测试元数据管理器"""
    
    @pytest.fixture
    def temp_config(self):
        """创建临时配置"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = load_config('config/config.yaml')
            config.storage.root_path = tmpdir
            yield config
    
    def test_create_empty_metadata(self, temp_config):
        """测试创建空元数据"""
        mgr = MetadataManager(temp_config)
        
        metadata = mgr.get_symbol_metadata(DEFAULT_EXCHANGE, DEFAULT_SYMBOL)
        
        assert metadata.exchange == DEFAULT_EXCHANGE
        assert metadata.symbol == DEFAULT_SYMBOL
        assert metadata.base == 'BTC'
        assert metadata.quote == 'USDT'
    
    def test_save_and_load_metadata(self, temp_config):
        """测试保存和加载元数据"""
        mgr = MetadataManager(temp_config)
        
        metadata = mgr.get_symbol_metadata(DEFAULT_EXCHANGE, DEFAULT_SYMBOL)
        mgr.save_symbol_metadata(metadata)
        
        # 重新加载
        loaded = mgr.get_symbol_metadata(DEFAULT_EXCHANGE, DEFAULT_SYMBOL)
        
        assert loaded.exchange == metadata.exchange
        assert loaded.symbol == metadata.symbol
    
    def test_update_data_range(self, temp_config):
        """测试更新数据范围"""
        mgr = MetadataManager(temp_config)
        
        start_ts = int(datetime(2024, 1, 1).timestamp() * 1000)
        end_ts = int(datetime(2024, 1, 31).timestamp() * 1000)
        
        mgr.update_data_range(DEFAULT_EXCHANGE, DEFAULT_SYMBOL, start_ts, end_ts)
        
        metadata = mgr.get_symbol_metadata(DEFAULT_EXCHANGE, DEFAULT_SYMBOL)
        
        assert metadata.data_range is not None
        assert metadata.data_range.start_timestamp == start_ts
        assert metadata.data_range.end_timestamp == end_ts
    
    def test_list_exchanges(self, temp_config):
        """测试列出交易所"""
        mgr = MetadataManager(temp_config)
        
        # 创建一些元数据
        mgr.save_symbol_metadata(
            mgr.get_symbol_metadata(DEFAULT_EXCHANGE, DEFAULT_SYMBOL)
        )
        mgr.save_symbol_metadata(
            mgr.get_symbol_metadata('okx', 'ETH/USDT')
        )
        
        exchanges = mgr.list_exchanges()
        
        assert DEFAULT_EXCHANGE in exchanges
        assert 'okx' in exchanges
    
    def test_list_symbols(self, temp_config):
        """测试列出交易对"""
        mgr = MetadataManager(temp_config)
        
        # 创建元数据
        mgr.save_symbol_metadata(
            mgr.get_symbol_metadata(DEFAULT_EXCHANGE, DEFAULT_SYMBOL)
        )
        mgr.save_symbol_metadata(
            mgr.get_symbol_metadata(DEFAULT_EXCHANGE, TEST_SYMBOLS[1])
        )
        
        symbols = mgr.list_symbols(DEFAULT_EXCHANGE)
        
        assert DEFAULT_SYMBOL in symbols
        assert 'ETH/USDT' in symbols


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
