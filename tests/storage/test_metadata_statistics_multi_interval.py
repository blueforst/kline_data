from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

from kline_data.config.manager import ConfigManager, load_config
from kline_data.storage.downloader import DataDownloader
from kline_data.storage.metadata_manager import MetadataManager


def _build_records(start: datetime, periods: int, freq: str):
    """快速生成指定周期的K线记录列表"""
    ts = pd.date_range(start, periods=periods, freq=freq, tz="UTC")
    return [
        {
            "timestamp": int(t.timestamp() * 1000),
            "open": 1.0,
            "high": 2.0,
            "low": 0.5,
            "close": 1.5,
            "volume": 10.0,
        }
        for t in ts
    ]


def test_statistics_accumulate_across_intervals(tmp_path: Path):
    # 独立配置到临时目录，避免污染真实数据
    manager = ConfigManager()
    manager.reset()
    config = load_config(Path(__file__).parents[2] / "kline_data/config/config.yaml")
    config.storage.root_path = str(tmp_path)

    # 先写入 1m 数据
    d1 = DataDownloader("binance", "BTC/USDT", config, interval="1m")
    d1._save_batch(_build_records(datetime(2024, 1, 1), 3, "1min"))

    # 再写入 1h 数据
    d2 = DataDownloader("binance", "BTC/USDT", config, interval="1h")
    d2._save_batch(_build_records(datetime(2024, 1, 1), 2, "1h"))

    metadata = MetadataManager(config).get_symbol_metadata("binance", "BTC/USDT")
    assert metadata.statistics is not None
    # 3 条 1m + 2 条 1h = 5，总量应累加而不是被覆盖
    assert metadata.statistics.total_records == 5

    manager.reset()
