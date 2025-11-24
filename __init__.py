"""
K线数据本地存储系统
~~~~~~~~~~~~~~~~~~~~~

一个高性能、可扩展的本地K线数据存储系统

基本使用:
    >>> from kline_data import KlineDataClient
    >>> client = KlineDataClient('config/config.yaml')
    >>> df = client.query('binance', 'BTC/USDT').interval('1h').execute()

:copyright: (c) 2024 by Your Name.
:license: MIT, see LICENSE for more details.
"""

__version__ = '1.0.0'
__author__ = 'Your Name'
__license__ = 'MIT'

# 配置层
from config import (
    ConfigManager,
    load_config,
    get_config,
    Config,
)

# 存储层
from storage import (
    KlineData,
    DataValidator,
    ParquetWriter,
    MetadataManager,
    DownloadManager,
    TaskStatus,
)

# 读取层
from reader import (
    ParquetReader,
    QueryEngine,
    QueryBuilder,
    DataCache,
)

# 重采样层
from resampler import (
    KlineResampler,
    SmartResampler,
    TimeframeConverter,
)

# 全局常量（从utils.constants导入）
from utils.constants import (
    Timeframe,
    TIMEFRAME_SECONDS,
    TIMEFRAME_TO_PANDAS,
    SUPPORTED_EXCHANGES,
    DEFAULT_EXCHANGE,
    DEFAULT_SYMBOL,
    COMMON_INTERVALS,
    OHLCV_COLUMNS,
)

# 指标层
from indicators import (
    IndicatorManager,
    IndicatorLibrary,
    calculate_indicator,
    list_available_indicators,
    # 常用指标
    calculate_ma,
    calculate_bollinger,
    calculate_macd,
    calculate_rsi,
    calculate_atr,
    calculate_obv,
)

# SDK层
from sdk import (
    KlineClient,
)

# 服务层
from service import (
    create_app,
)

# CLI层
from cli import get_cli_main
cli_main = get_cli_main()

__all__ = [
    # Version
    '__version__',
    '__author__',
    '__license__',
    
    # Config
    'ConfigManager',
    'load_config',
    'get_config',
    'Config',
    
    # Storage
    'KlineData',
    'DataValidator',
    'ParquetWriter',
    'MetadataManager',
    'DownloadManager',
    'TaskStatus',
    
    # Reader
    'ParquetReader',
    'QueryEngine',
    'QueryBuilder',
    'DataCache',
    
    # Resampler
    'KlineResampler',
    'SmartResampler',
    'TimeframeConverter',
    
    # Constants (from utils.constants)
    'Timeframe',
    'TIMEFRAME_SECONDS',
    'TIMEFRAME_TO_PANDAS',
    'SUPPORTED_EXCHANGES',
    'DEFAULT_EXCHANGE',
    'DEFAULT_SYMBOL',
    'COMMON_INTERVALS',
    'OHLCV_COLUMNS',
    
    # Indicators
    'IndicatorManager',
    'IndicatorLibrary',
    'calculate_indicator',
    'list_available_indicators',
    'calculate_ma',
    'calculate_bollinger',
    'calculate_macd',
    'calculate_rsi',
    'calculate_atr',
    'calculate_obv',
    
    # SDK
    'KlineClient',
    
    # Service
    'create_app',
    
    # CLI
    'cli_main',
]
