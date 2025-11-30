"""DataSourceStrategy tests aligned with the CCXT-only pipeline."""

from datetime import datetime
from unittest.mock import patch

import pytest

from kline_data.storage.data_source_strategy import DataSourceStrategy, DataSourceDecision


@pytest.fixture
def strategy(mock_config):
    """Provide a strategy instance with a mocked MetadataManager."""
    with patch('kline_data.storage.data_source_strategy.MetadataManager'):
        yield DataSourceStrategy(mock_config)


def test_data_source_decision_contract():
    decision = DataSourceDecision(
        source='local',
        source_interval=None,
        need_download=False,
        download_interval=None,
        reason='Local data is complete'
    )

    assert decision.source in {'local', 'ccxt'}
    assert decision.source_interval is None
    assert isinstance(decision.need_download, bool)
    assert decision.download_interval is None or isinstance(decision.download_interval, str)
    assert isinstance(decision.reason, str)


def test_local_data_preferred(strategy):
    with patch.object(DataSourceStrategy, '_check_local_data', return_value=True):
        decision = strategy.decide_data_source(
            exchange='binance',
            symbol='BTC/USDT',
            start_time=datetime(2024, 1, 1),
            end_time=datetime(2024, 1, 2),
            target_interval='1h'
        )

    assert decision.source == 'local'
    assert decision.need_download is False
    assert decision.download_interval is None
    assert 'local' in decision.reason.lower()


def test_download_when_missing(strategy):
    with patch.object(DataSourceStrategy, '_check_local_data', return_value=False):
        decision = strategy.decide_data_source(
            exchange='binance',
            symbol='BTC/USDT',
            start_time=datetime(2024, 1, 1),
            end_time=datetime(2024, 1, 2),
            target_interval='1h'
        )

    assert decision.source == 'ccxt'
    assert decision.need_download is True
    assert decision.download_interval == '1h'
    assert 'download' in decision.reason.lower()


def test_explain_decision(strategy):
    decision = DataSourceDecision(
        source='local',
        source_interval=None,
        need_download=False,
        download_interval=None,
        reason='Local cache is complete'
    )

    summary = strategy.explain_decision(decision)
    assert 'Local cache is complete' in summary
    assert 'Source: local' in summary
