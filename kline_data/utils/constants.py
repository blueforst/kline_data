"""全局常量定义

该模块定义了项目中使用的所有全局常量，包括：
- 时间周期枚举 (Timeframe)
- 支持的交易所列表
- 数据格式常量
- 其他通用常量

使用示例:
    >>> from utils.constants import Timeframe, SUPPORTED_EXCHANGES
    >>> print(Timeframe.M1.value)  # '1m'
    >>> print(Timeframe.H1.seconds)  # 3600
    >>> print(SUPPORTED_EXCHANGES)  # ['binance', 'okx', 'bybit', ...]
"""

from enum import Enum
from typing import Dict, List, Final


# ============================================================================
# 时间周期枚举 (Timeframe)
# ============================================================================

class Timeframe(str, Enum):
    """时间周期枚举
    
    该枚举定义了所有支持的K线时间周期，每个周期都包含：
    - value: 字符串表示（如 '1m', '1h', '1d'）
    - seconds: 该周期对应的秒数
    - pandas_freq: Pandas频率字符串
    
    使用示例:
        >>> Timeframe.M1.value  # '1m'
        >>> Timeframe.M1.seconds  # 60
        >>> Timeframe.M1.pandas_freq  # '1min'
        >>> Timeframe.from_string('1h')  # Timeframe.H1
    """
    
    # 秒级周期
    S1 = '1s'
    
    # 分钟级周期
    M1 = '1m'
    M3 = '3m'
    M5 = '5m'
    M15 = '15m'
    M30 = '30m'
    
    # 小时级周期
    H1 = '1h'
    H2 = '2h'
    H4 = '4h'
    H6 = '6h'
    H8 = '8h'
    H12 = '12h'
    
    # 天级周期
    D1 = '1d'
    
    # 周级周期
    W1 = '1w'
    
    # 月级周期
    MO1 = '1M'
    
    @property
    def seconds(self) -> int:
        """获取周期对应的秒数"""
        return TIMEFRAME_SECONDS[self.value]
    
    @property
    def pandas_freq(self) -> str:
        """获取pandas的频率字符串"""
        return TIMEFRAME_TO_PANDAS[self.value]
    
    @classmethod
    def from_string(cls, s: str) -> 'Timeframe':
        """从字符串创建Timeframe对象
        
        Args:
            s: 时间周期字符串，如 '1m', '5m', '1h', '1d' 等
            
        Returns:
            Timeframe: 对应的枚举对象
            
        Raises:
            ValueError: 如果字符串不是有效的时间周期
            
        Examples:
            >>> Timeframe.from_string('1m')
            Timeframe.M1
            >>> Timeframe.from_string('1h')
            Timeframe.H1
        """
        for tf in cls:
            if tf.value == s:
                return tf
        raise ValueError(f"Invalid timeframe: {s}. Valid values: {[t.value for t in cls]}")
    
    @classmethod
    def list_all(cls) -> List[str]:
        """获取所有支持的时间周期字符串列表
        
        Returns:
            List[str]: 所有支持的时间周期
            
        Examples:
            >>> Timeframe.list_all()
            ['1s', '1m', '5m', ..., '1d', '1w', '1M']
        """
        return [tf.value for tf in cls]
    


# ============================================================================
# 时间周期映射表
# ============================================================================

# 时间周期到秒数的映射
TIMEFRAME_SECONDS: Final[Dict[str, int]] = {
    '1s': 1,
    '1m': 60,
    '3m': 180,
    '5m': 300,
    '15m': 900,
    '30m': 1800,
    '1h': 3600,
    '2h': 7200,
    '4h': 14400,
    '6h': 21600,
    '8h': 28800,
    '12h': 43200,
    '1d': 86400,
    '1w': 604800,
    '1M': 2592000,  # 30天近似
}

# 时间周期到pandas频率的映射
TIMEFRAME_TO_PANDAS: Final[Dict[str, str]] = {
    '1s': '1s',
    '1m': '1min',
    '3m': '3min',
    '5m': '5min',
    '15m': '15min',
    '30m': '30min',
    '1h': '1h',
    '2h': '2h',
    '4h': '4h',
    '6h': '6h',
    '8h': '8h',
    '12h': '12h',
    '1d': '1D',
    '1w': '1W',
    '1M': '1M',
}

# pandas频率到时间周期的映射（反向映射）
PANDAS_TO_TIMEFRAME: Final[Dict[str, str]] = {v: k for k, v in TIMEFRAME_TO_PANDAS.items()}


# ============================================================================
# 交易所相关常量
# ============================================================================

# 支持的交易所列表
SUPPORTED_EXCHANGES: Final[List[str]] = [
    'binance',
    'okx',
    'bybit',
    'huobi',
    'kraken',
    'coinbase',
    'kucoin',
    'bitfinex',
    'gateio',
    'mexc',
]

# 默认交易所
DEFAULT_EXCHANGE: Final[str] = 'binance'

# 默认交易对
DEFAULT_SYMBOL: Final[str] = 'BTC/USDT'

# 交易对常量
TEST_SYMBOLS: Final[List[str]] = [
    'BTC/USDT',
    'ETH/USDT',
    'BNB/USDT',
    'LTC/USDT'
]  # 测试用交易对列表
DEMO_SYMBOL: Final[str] = 'BTC/USDT'  # 演示用交易对


# ============================================================================
# 数据源相关常量
# ============================================================================

# 默认下载周期（最小粒度）
DEFAULT_SOURCE_INTERVAL: Final[str] = '1s'

# 常用周期列表（用于预计算或优化）
COMMON_INTERVALS: Final[List[str]] = ['1m', '5m', '15m', '30m', '1h', '4h', '1d']

# 常用时间周期默认值
DEFAULT_QUERY_INTERVAL: Final[str] = '1d'  # 默认查询周期
DEFAULT_DOWNLOAD_INTERVAL: Final[str] = '1s'  # 默认下载周期
API_DEFAULT_INTERVAL: Final[str] = '1m'  # API默认周期
DEMO_INTERVALS: Final[List[str]] = ['1m', '5m', '1h', '1d']  # 演示用周期列表


# ============================================================================
# 存储相关常量
# ============================================================================

# 支持的存储格式
SUPPORTED_STORAGE_FORMATS: Final[List[str]] = ['parquet']

# 默认存储格式
DEFAULT_STORAGE_FORMAT: Final[str] = 'parquet'

# 支持的压缩算法
SUPPORTED_COMPRESSIONS: Final[List[str]] = ['snappy', 'gzip', 'brotli', 'lz4', 'zstd']

# 默认压缩算法
DEFAULT_COMPRESSION: Final[str] = 'snappy'

# 分区粒度选项
PARTITION_GRANULARITIES: Final[List[str]] = ['year', 'month', 'day']

# 默认分区粒度
DEFAULT_PARTITION_GRANULARITY: Final[str] = 'month'


# ============================================================================
# OHLCV字段常量
# ============================================================================

# OHLCV字段名称
OHLCV_COLUMNS: Final[List[str]] = ['timestamp', 'open', 'high', 'low', 'close', 'volume']

# OHLCV字段到索引的映射（CCXT格式）
CCXT_OHLCV_INDEX: Final[Dict[str, int]] = {
    'timestamp': 0,
    'open': 1,
    'high': 2,
    'low': 3,
    'close': 4,
    'volume': 5,
}

# OHLCV字段聚合规则
OHLCV_AGGREGATION_RULES: Final[Dict[str, str]] = {
    'open': 'first',   # 开盘价取第一个值
    'high': 'max',     # 最高价取最大值
    'low': 'min',      # 最低价取最小值
    'close': 'last',   # 收盘价取最后一个值
    'volume': 'sum',   # 成交量求和
}


# ============================================================================
# 验证和限制常量
# ============================================================================

# 最小数据完整性阈值（百分比）
MIN_DATA_COMPLETENESS: Final[float] = 0.95  # 95%

# 最大允许重复率（百分比）
MAX_DUPLICATE_RATE: Final[float] = 0.01  # 1%

# 单次下载的最大记录数
MAX_DOWNLOAD_RECORDS: Final[int] = 100000

# 默认查询限制（条数）
DEFAULT_QUERY_LIMIT: Final[int] = 1000

# 最大查询限制
MAX_QUERY_LIMIT: Final[int] = 100000


# ============================================================================
# 时区常量
# ============================================================================

# 内部使用的标准时区（所有数据都以UTC存储）
INTERNAL_TIMEZONE: Final[str] = 'UTC'

# 支持的显示时区
DISPLAY_TIMEZONES: Final[List[str]] = ['UTC', 'local']

# 时间相关常量
LOCAL_TIMEZONE: Final[str] = 'local'  # 本地时区标识
PANDAS_TIMESTAMP_UNIT: Final[str] = 'ms'  # Pandas时间戳单位


# ============================================================================
# API相关常量
# ============================================================================

# API版本
API_VERSION: Final[str] = 'v1'

# API默认端口
DEFAULT_API_PORT: Final[int] = 8000

# API默认主机
DEFAULT_API_HOST: Final[str] = '0.0.0.0'

# API状态常量
API_STATUS_HEALTHY: Final[str] = "healthy"  # API健康状态
API_SERVICE_NAME: Final[str] = "kline-data-service"  # 服务名称
API_SUCCESS_MESSAGE: Final[str] = "数据下载完成"  # 成功消息
API_METADATA_TAG: Final[str] = "元数据"  # 元数据标签


# ============================================================================
# 文件相关常量
# ============================================================================

# 文件目录和扩展名
RAW_DATA_DIR: Final[str] = 'raw'  # 原始数据目录
PARQUET_EXTENSION: Final[str] = '.parquet'  # Parquet文件扩展名

# 文件编码
DEFAULT_ENCODING: Final[str] = 'utf-8'  # 默认文件编码
MARKDOWN_ENCODING: Final[str] = 'text/markdown'  # Markdown文件编码类型


# ============================================================================
# 状态相关常量
# ============================================================================

# 通用状态常量
STATUS_NA: Final[str] = "N/A"  # 不可用状态标识

# 数据验证相关
VALIDATION_METHODS: Final[List[str]] = ['iqr', 'zscore']  # 支持的验证方法
VALIDATION_STATUS: Final[List[str]] = ['success', 'error']  # 验证状态列表


# ============================================================================
# 日志级别常量
# ============================================================================

# 支持的日志级别
LOG_LEVELS: Final[List[str]] = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']

# 默认日志级别
DEFAULT_LOG_LEVEL: Final[str] = 'INFO'


# ============================================================================
# 辅助函数
# ============================================================================

def get_timeframe_seconds(timeframe: str) -> int:
    """获取时间周期对应的秒数
    
    Args:
        timeframe: 时间周期字符串
        
    Returns:
        int: 秒数
        
    Raises:
        ValueError: 如果时间周期无效
    """
    if timeframe not in TIMEFRAME_SECONDS:
        raise ValueError(
            f"Unknown timeframe: {timeframe}. "
            f"Valid timeframes: {list(TIMEFRAME_SECONDS.keys())}"
        )
    return TIMEFRAME_SECONDS[timeframe]


def validate_timeframe(timeframe: str) -> None:
    """验证时间周期是否有效
    
    Args:
        timeframe: 时间周期字符串
        
    Raises:
        ValueError: 如果时间周期无效
    """
    if timeframe not in TIMEFRAME_SECONDS:
        valid_timeframes = ', '.join(sorted(TIMEFRAME_SECONDS.keys()))
        raise ValueError(
            f"Invalid timeframe: {timeframe}. "
            f"Valid timeframes are: {valid_timeframes}"
        )


def validate_exchange(exchange: str) -> None:
    """验证交易所是否支持

    Args:
        exchange: 交易所名称

    Raises:
        ValueError: 如果交易所不支持
    """
    supported_exchanges = get_supported_exchanges()
    if exchange not in supported_exchanges:
        raise ValueError(
            f"Unsupported exchange: {exchange}. "
            f"Supported exchanges: {', '.join(supported_exchanges)}"
        )


def get_supported_exchanges() -> List[str]:
    try:
        from ..config.manager import load_config

        config = load_config()
        exchanges = list(config.ccxt.exchanges)
        if exchanges:
            return exchanges
    except Exception:
        pass

    return SUPPORTED_EXCHANGES.copy()


def get_default_exchange() -> str:
    try:
        from ..config.manager import load_config

        config = load_config()
        default_exchange = config.cli.default_exchange
        if default_exchange:
            return default_exchange
    except Exception:
        pass

    return DEFAULT_EXCHANGE


def validate_symbol(symbol: str) -> None:
    """验证交易对格式是否有效

    Args:
        symbol: 交易对符号，如 'BTC/USDT'

    Raises:
        ValueError: 如果交易对格式无效
    """
    if not symbol or '/' not in symbol:
        raise ValueError(
            f"Invalid symbol format: {symbol}. "
            f"Expected format: 'BASE/QUOTE' (e.g., 'BTC/USDT')"
        )


def validate_ohlcv_aggregation_rule(field: str, rule: str) -> None:
    """验证OHLCV字段聚合规则是否有效

    Args:
        field: OHLCV字段名
        rule: 聚合规则

    Raises:
        ValueError: 如果字段或规则无效
    """
    if field not in OHLCV_AGGREGATION_RULES:
        raise ValueError(
            f"Invalid OHLCV field: {field}. "
            f"Valid fields: {list(OHLCV_AGGREGATION_RULES.keys())}"
        )

    valid_rules = {'first', 'last', 'max', 'min', 'sum'}
    if rule not in valid_rules:
        raise ValueError(
            f"Invalid aggregation rule: {rule}. "
            f"Valid rules: {list(valid_rules)}"
        )


def validate_validation_method(method: str) -> None:
    """验证数据验证方法是否有效

    Args:
        method: 验证方法名称

    Raises:
        ValueError: 如果验证方法无效
    """
    if method not in VALIDATION_METHODS:
        raise ValueError(
            f"Invalid validation method: {method}. "
            f"Valid methods: {VALIDATION_METHODS}"
        )


# ============================================================================
# 导出列表
# ============================================================================

__all__ = [
    # 枚举
    'Timeframe',
    
    # 时间周期相关
    'TIMEFRAME_SECONDS',
    'TIMEFRAME_TO_PANDAS',
    'PANDAS_TO_TIMEFRAME',
    'DEFAULT_SOURCE_INTERVAL',
    'COMMON_INTERVALS',
    'DEFAULT_QUERY_INTERVAL',
    'DEFAULT_DOWNLOAD_INTERVAL',
    'API_DEFAULT_INTERVAL',
    'DEMO_INTERVALS',

    # 交易所相关
    'SUPPORTED_EXCHANGES',
    'DEFAULT_EXCHANGE',
    'DEFAULT_SYMBOL',
    'get_supported_exchanges',
    'get_default_exchange',
    'TEST_SYMBOLS',
    'DEMO_SYMBOL',

    # 存储相关
    'SUPPORTED_STORAGE_FORMATS',
    'DEFAULT_STORAGE_FORMAT',
    'SUPPORTED_COMPRESSIONS',
    'DEFAULT_COMPRESSION',
    'PARTITION_GRANULARITIES',
    'DEFAULT_PARTITION_GRANULARITY',
    
    # OHLCV相关
    'OHLCV_COLUMNS',
    'CCXT_OHLCV_INDEX',
    'OHLCV_AGGREGATION_RULES',

    # 验证和限制
    'MIN_DATA_COMPLETENESS',
    'MAX_DUPLICATE_RATE',
    'MAX_DOWNLOAD_RECORDS',
    'DEFAULT_QUERY_LIMIT',
    'MAX_QUERY_LIMIT',
    
    # 时区
    'INTERNAL_TIMEZONE',
    'DISPLAY_TIMEZONES',
    'LOCAL_TIMEZONE',
    'PANDAS_TIMESTAMP_UNIT',

    # API
    'API_VERSION',
    'DEFAULT_API_PORT',
    'DEFAULT_API_HOST',
    'API_STATUS_HEALTHY',
    'API_SERVICE_NAME',
    'API_SUCCESS_MESSAGE',
    'API_METADATA_TAG',

    # 文件相关
    'RAW_DATA_DIR',
    'PARQUET_EXTENSION',
    'DEFAULT_ENCODING',
    'MARKDOWN_ENCODING',

    # 状态相关
    'STATUS_NA',
    'VALIDATION_METHODS',
    'VALIDATION_STATUS',

    # 日志
    'LOG_LEVELS',
    'DEFAULT_LOG_LEVEL',
    
    # 辅助函数
    'get_timeframe_seconds',
    'validate_timeframe',
    'validate_exchange',
    'validate_symbol',
    'validate_ohlcv_aggregation_rule',
    'validate_validation_method',
]
