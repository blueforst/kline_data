import pytest
from pathlib import Path

from kline_data.config.manager import ConfigManager, load_config
from kline_data.sdk.metadata import MetadataClient
from kline_data.storage.metadata_manager import MetadataManager
from kline_data.storage.models import PartitionInfo
from kline_data.utils.timezone import format_datetime, now_utc


@pytest.fixture
def temp_config(tmp_path):
    manager = ConfigManager()
    manager.reset()

    config = load_config(Path(__file__).parents[2] / "kline_data/config/config.yaml")
    config.storage.root_path = str(tmp_path)

    yield config

    manager.reset()


def test_get_metadata_reports_interval_records(temp_config):
    exchange = "binance"
    symbol = "BTC/USDT"
    mgr = MetadataManager(temp_config)

    start_ts = 1_700_000_000_000
    end_ts = 1_700_000_060_000
    now_str = format_datetime(now_utc())

    mgr.add_partition(
        exchange,
        symbol,
        PartitionInfo(
            year=2024,
            month=1,
            file_path="raw/binance/BTCUSDT/1m/2024/01/data.parquet",
            records=120,
            size_bytes=2048,
            checksum="abc123",
            created_at=now_str,
            updated_at=now_str,
            interval="1m",
        ),
    )
    mgr.add_interval_range(exchange, symbol, "1m", start_ts, end_ts)

    metadata = MetadataClient(temp_config).get_metadata(exchange, symbol)

    interval_info = metadata["intervals"]["1m"]
    assert interval_info["records"] == 120
    assert interval_info["size_bytes"] == 2048
    assert interval_info["start_time"].timestamp() == pytest.approx(start_ts / 1000)
    assert interval_info["end_time"].timestamp() == pytest.approx(end_ts / 1000)
