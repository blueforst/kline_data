# 常量系统API参考文档

## 📋 概述

本文档提供了全局常量系统的完整API参考，包括所有可用的常量、枚举、函数和类型定义。

## 🏗️ 模块结构

```
utils/constants.py
├── 枚举类
│   └── Timeframe          # 时间周期枚举
├── 时间周期常量
│   ├── TIMEFRAME_SECONDS  # 时间周期到秒数映射
│   ├── TIMEFRAME_TO_PANDAS # 时间周期到pandas频率映射
│   └── PANDAS_TO_TIMEFRAME # pandas频率到时间周期映射
├── 交易所常量
│   ├── SUPPORTED_EXCHANGES # 支持的交易所列表
│   ├── DEFAULT_EXCHANGE   # 默认交易所
│   ├── DEFAULT_SYMBOL     # 默认交易对
│   └── TEST_SYMBOLS       # 测试交易对列表
├── 存储常量
│   ├── SUPPORTED_STORAGE_FORMATS    # 支持的存储格式
│   ├── DEFAULT_STORAGE_FORMAT       # 默认存储格式
│   ├── SUPPORTED_COMPRESSIONS       # 支持的压缩算法
│   └── DEFAULT_COMPRESSION          # 默认压缩算法
├── OHLCV常量
│   ├── OHLCV_COLUMNS      # OHLCV字段列表
│   ├── CCXT_OHLCV_INDEX   # OHLCV字段到索引映射
│   └── OHLCV_AGGREGATION_RULES # OHLCV字段聚合规则
├── 验证常量
│   ├── MIN_DATA_COMPLETENESS   # 最小数据完整性阈值
│   ├── MAX_DUPLICATE_RATE      # 最大重复率
│   └── MAX_DOWNLOAD_RECORDS    # 最大下载记录数
├── API常量
│   ├── API_VERSION         # API版本
│   ├── DEFAULT_API_PORT    # 默认API端口
│   └── API_STATUS_HEALTHY  # API健康状态
└── 验证函数
    ├── validate_timeframe      # 验证时间周期
    ├── validate_exchange       # 验证交易所
    ├── validate_symbol         # 验证交易对
    └── validate_*              # 其他验证函数
```

## 🔢 Timeframe枚举类

### 类定义

```python
class Timeframe(str, Enum):
    """时间周期枚举类"""
```

### 枚举值

#### 秒级周期
| 枚举值 | 字符串值 | 描述 |
|--------|----------|------|
| `Timeframe.S1` | `'1s'` | 1秒 |
| `Timeframe.S5` | `'5s'` | 5秒 |
| `Timeframe.S15` | `'15s'` | 15秒 |
| `Timeframe.S30` | `'30s'` | 30秒 |

#### 分钟级周期
| 枚举值 | 字符串值 | 描述 |
|--------|----------|------|
| `Timeframe.M1` | `'1m'` | 1分钟 |
| `Timeframe.M3` | `'3m'` | 3分钟 |
| `Timeframe.M5` | `'5m'` | 5分钟 |
| `Timeframe.M15` | `'15m'` | 15分钟 |
| `Timeframe.M30` | `'30m'` | 30分钟 |

#### 小时级周期
| 枚举值 | 字符串值 | 描述 |
|--------|----------|------|
| `Timeframe.H1` | `'1h'` | 1小时 |
| `Timeframe.H2` | `'2h'` | 2小时 |
| `Timeframe.H4` | `'4h'` | 4小时 |
| `Timeframe.H6` | `'6h'` | 6小时 |
| `Timeframe.H8` | `'8h'` | 8小时 |
| `Timeframe.H12` | `'12h'` | 12小时 |

#### 天级和周级周期
| 枚举值 | 字符串值 | 描述 |
|--------|----------|------|
| `Timeframe.D1` | `'1d'` | 1天 |
| `Timeframe.W1` | `'1w'` | 1周 |

#### 月级周期
| 枚举值 | 字符串值 | 描述 |
|--------|----------|------|
| `Timeframe.MO1` | `'1M'` | 1月 |

### 属性

#### `value: str`
获取时间周期的字符串表示

```python
>>> Timeframe.M1.value
'1m'
```

#### `seconds: int` (只读)
获取时间周期对应的秒数

```python
>>> Timeframe.M1.seconds
60
>>> Timeframe.H1.seconds
3600
>>> Timeframe.D1.seconds
86400
```

#### `pandas_freq: str` (只读)
获取对应的pandas重采样频率字符串

```python
>>> Timeframe.M1.pandas_freq
'1min'
>>> Timeframe.H1.pandas_freq
'1h'
>>> Timeframe.D1.pandas_freq
'1D'
```

### 类方法

#### `from_string(s: str) -> Timeframe`
从字符串创建Timeframe对象

**参数:**
- `s` (str): 时间周期字符串，如 '1m', '5m', '1h', '1d' 等

**返回值:**
- `Timeframe`: 对应的枚举对象

**异常:**
- `ValueError`: 如果字符串不是有效的时间周期

**示例:**
```python
>>> Timeframe.from_string('1m')
Timeframe.M1
>>> Timeframe.from_string('1h')
Timeframe.H1
>>> Timeframe.from_string('invalid')
ValueError: Invalid timeframe: invalid. Valid values: ['1s', '5s', ...]
```

#### `list_all() -> List[str]`
获取所有支持的时间周期字符串列表

**返回值:**
- `List[str]`: 所有支持的时间周期

**示例:**
```python
>>> Timeframe.list_all()
['1s', '5s', '15s', '30s', '1m', '3m', '5m', '15m', '30m', '1h', '2h', '4h', '6h', '8h', '12h', '1d', '1w', '1M']
```

### 实例方法

#### `is_valid_resample_from(source: Timeframe) -> bool`
检查是否可以从源时间周期重采样到当前周期

**参数:**
- `source` (Timeframe): 源时间周期

**返回值:**
- `bool`: 是否可以重采样

**规则:**
- 目标周期必须大于等于源周期
- 目标周期必须是源周期的整数倍

**示例:**
```python
>>> Timeframe.H1.is_valid_resample_from(Timeframe.M1)
True  # 可以从1分钟重采样到1小时
>>> Timeframe.M1.is_valid_resample_from(Timeframe.H1)
False  # 不能从1小时重采样到1分钟
>>> Timeframe.M5.is_valid_resample_from(Timeframe.M3)
False  # 5分钟不是3分钟的整数倍
```

## ⏰ 时间周期常量

### `TIMEFRAME_SECONDS: Dict[str, int]`
时间周期字符串到秒数的映射

**类型:** `Final[Dict[str, int]]`

**内容:**
```python
{
    '1s': 1,
    '5s': 5,
    '15s': 15,
    '30s': 30,
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
```

**使用示例:**
```python
>>> TIMEFRAME_SECONDS['1h']
3600
>>> TIMEFRAME_SECONDS['1d']
86400
```

### `TIMEFRAME_TO_PANDAS: Dict[str, str]`
时间周期字符串到pandas频率字符串的映射

**类型:** `Final[Dict[str, str]]`

**内容:**
```python
{
    '1s': '1s',
    '5s': '5s',
    '15s': '15s',
    '30s': '30s',
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
```

**使用示例:**
```python
>>> TIMEFRAME_TO_PANDAS['1m']
'1min'
>>> TIMEFRAME_TO_PANDAS['1d']
'1D'
```

### `PANDAS_TO_TIMEFRAME: Dict[str, str]`
pandas频率字符串到时间周期字符串的反向映射

**类型:** `Final[Dict[str, str]]`

**内容:** `TIMEFRAME_TO_PANDAS`的反向映射

**使用示例:**
```python
>>> PANDAS_TO_TIMEFRAME['1min']
'1m'
>>> PANDAS_TO_TIMEFRAME['1D']
'1d'
```

## 🏦 交易所相关常量

### `SUPPORTED_EXCHANGES: List[str]`
支持的交易所列表

**类型:** `Final[List[str]]`

**内容:**
```python
[
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
```

**使用示例:**
```python
>>> 'binance' in SUPPORTED_EXCHANGES
True
>>> 'invalid_exchange' in SUPPORTED_EXCHANGES
False
```

### `DEFAULT_EXCHANGE: str`
默认交易所

**类型:** `Final[str]`

**值:** `'binance'`

### `DEFAULT_SYMBOL: str`
默认交易对

**类型:** `Final[str]`

**值:** `'BTC/USDT'`

### `TEST_SYMBOLS: List[str]`
测试用交易对列表

**类型:** `Final[List[str]]`

**内容:**
```python
[
    'BTC/USDT',
    'ETH/USDT',
    'BNB/USDT',
    'LTC/USDT'
]
```

### `DEMO_SYMBOL: str`
演示用交易对

**类型:** `Final[str]`

**值:** `'BTC/USDT'`

## 📁 存储相关常量

### 存储格式常量

#### `SUPPORTED_STORAGE_FORMATS: List[str]`
支持的存储格式列表

**类型:** `Final[List[str]]`

**内容:** `['parquet']`

#### `DEFAULT_STORAGE_FORMAT: str`
默认存储格式

**类型:** `Final[str]`

**值:** `'parquet'`

### 压缩算法常量

#### `SUPPORTED_COMPRESSIONS: List[str]`
支持的压缩算法列表

**类型:** `Final[List[str]]`

**内容:**
```python
['snappy', 'gzip', 'brotli', 'lz4', 'zstd']
```

#### `DEFAULT_COMPRESSION: str`
默认压缩算法

**类型:** `Final[str]`

**值:** `'snappy'`

### 分区相关常量

#### `PARTITION_GRANULARITIES: List[str]`
分区粒度选项

**类型:** `Final[List[str]]`

**内容:** `['year', 'month', 'day']`

#### `DEFAULT_PARTITION_GRANULARITY: str`
默认分区粒度

**类型:** `Final[str]`

**值:** `'month'`

## 📊 OHLCV相关常量

### `OHLCV_COLUMNS: List[str]`
OHLCV字段名称列表

**类型:** `Final[List[str]]`

**内容:**
```python
['timestamp', 'open', 'high', 'low', 'close', 'volume']
```

**使用示例:**
```python
>>> OHLCV_COLUMNS
['timestamp', 'open', 'high', 'low', 'close', 'volume']
```

### `CCXT_OHLCV_INDEX: Dict[str, int]`
OHLCV字段到CCXT数组索引的映射

**类型:** `Final[Dict[str, int]]`

**内容:**
```python
{
    'timestamp': 0,
    'open': 1,
    'high': 2,
    'low': 3,
    'close': 4,
    'volume': 5,
}
```

**使用示例:**
```python
>>> CCXT_OHLCV_INDEX['open']
1
>>> CCXT_OHLCV_INDEX['volume']
5
```

### `OHLCV_AGGREGATION_RULES: Dict[str, str]`
OHLCV字段聚合规则

**类型:** `Final[Dict[str, str]]`

**内容:**
```python
{
    'open': 'first',   # 开盘价取第一个值
    'high': 'max',     # 最高价取最大值
    'low': 'min',      # 最低价取最小值
    'close': 'last',   # 收盘价取最后一个值
    'volume': 'sum',   # 成交量求和
}
```

**使用示例:**
```python
>>> OHLCV_AGGREGATION_RULES['open']
'first'
>>> OHLCV_AGGREGATION_RULES['volume']
'sum'
```

## 🔍 验证和限制常量

### 数据质量常量

#### `MIN_DATA_COMPLETENESS: float`
最小数据完整性阈值

**类型:** `Final[float]`

**值:** `0.95` (95%)

#### `MAX_DUPLICATE_RATE: float`
最大允许重复率

**类型:** `Final[float]`

**值:** `0.01` (1%)

### 查询限制常量

#### `MAX_DOWNLOAD_RECORDS: int`
单次下载的最大记录数

**类型:** `Final[int]`

**值:** `100000`

#### `DEFAULT_QUERY_LIMIT: int`
默认查询限制

**类型:** `Final[int]`

**值:** `1000`

#### `MAX_QUERY_LIMIT: int`
最大查询限制

**类型:** `Final[int]`

**值:** `100000`

## 🕐 时区常量

### `INTERNAL_TIMEZONE: str`
内部使用的标准时区

**类型:** `Final[str]`

**值:** `'UTC'`

### `DISPLAY_TIMEZONES: List[str]`
支持的显示时区

**类型:** `Final[List[str]]`

**内容:** `['UTC', 'local']`

### `LOCAL_TIMEZONE: str`
本地时区标识

**类型:** `Final[str]`

**值:** `'local'`

### `PANDAS_TIMESTAMP_UNIT: str`
Pandas时间戳单位

**类型:** `Final[str]`

**值:** `'ms'`

## 🌐 API相关常量

### `API_VERSION: str`
API版本

**类型:** `Final[str]`

**值:** `'v1'`

### `DEFAULT_API_PORT: int`
API默认端口

**类型:** `Final[int]`

**值:** `8000`

### `DEFAULT_API_HOST: str`
API默认主机

**类型:** `Final[str]`

**值:** `'0.0.0.0'`

### API状态常量

#### `API_STATUS_HEALTHY: str`
API健康状态

**类型:** `Final[str]`

**值:** `"healthy"`

#### `API_SERVICE_NAME: str`
服务名称

**类型:** `Final[str]`

**值:** `"kline-data-service"`

#### `API_SUCCESS_MESSAGE: str`
成功消息

**类型:** `Final[str]`

**值:** `"数据下载完成"`

#### `API_METADATA_TAG: str`
元数据标签

**类型:** `Final[str]`

**值:** `"元数据"`

## 📄 文件相关常量

### `RAW_DATA_DIR: str`
原始数据目录

**类型:** `Final[str]`

**值:** `'raw'`

### `PARQUET_EXTENSION: str`
Parquet文件扩展名

**类型:** `Final[str]`

**值:** `'.parquet'`

### 编码常量

#### `DEFAULT_ENCODING: str`
默认文件编码

**类型:** `Final[str]`

**值:** `'utf-8'`

#### `MARKDOWN_ENCODING: str`
Markdown文件编码类型

**类型:** `Final[str]`

**值:** `'text/markdown'`

## 📊 数据源相关常量

### `DEFAULT_SOURCE_INTERVAL: str`
默认下载周期（最小粒度）

**类型:** `Final[str]`

**值:** `'1s'`

### `COMMON_INTERVALS: List[str]`
常用周期列表

**类型:** `Final[List[str]]`

**内容:** `['1m', '5m', '15m', '30m', '1h', '4h', '1d']`

### `PRECOMPUTE_INTERVALS: List[str]`
预计算周期

**类型:** `Final[List[str]]`

**内容:** `['1m', '5m', '1h']`

### `DEFAULT_QUERY_INTERVAL: str`
常用时间周期默认值

**类型:** `Final[str]`

**值:** `'1d'`

### `DEFAULT_DOWNLOAD_INTERVAL: str`
默认下载周期

**类型:** `Final[str]`

**值:** `'1s'`

### `API_DEFAULT_INTERVAL: str`
API默认周期

**类型:** `Final[str]`

**值:** `'1m'`

### `DEMO_INTERVALS: List[str]`
演示用周期列表

**类型:** `Final[List[str]]`

**内容:** `['1m', '5m', '1h', '1d']`

## 🔧 状态相关常量

### `STATUS_NA: str`
不可用状态标识

**类型:** `Final[str]`

**值:** `"N/A"`

### `VALIDATION_METHODS: List[str]`
支持的验证方法

**类型:** `Final[List[str]]`

**内容:** `['iqr', 'zscore']`

### `VALIDATION_STATUS: List[str]`
验证状态列表

**类型:** `Final[List[str]]`

**内容:** `['success', 'error']`

## 📝 日志常量

### `LOG_LEVELS: List[str]`
支持的日志级别

**类型:** `Final[List[str]]`

**内容:** `['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']`

### `DEFAULT_LOG_LEVEL: str`
默认日志级别

**类型:** `Final[str]`

**值:** `'INFO'`

## 🔧 辅助函数

### 时间周期相关函数

#### `get_timeframe_seconds(timeframe: str) -> int`
获取时间周期对应的秒数

**参数:**
- `timeframe` (str): 时间周期字符串

**返回值:**
- `int`: 秒数

**异常:**
- `ValueError`: 如果时间周期无效

**示例:**
```python
>>> get_timeframe_seconds('1m')
60
>>> get_timeframe_seconds('1h')
3600
>>> get_timeframe_seconds('invalid')
ValueError: Unknown timeframe: invalid. Valid timeframes: ['1s', '5s', ...]
```

#### `validate_timeframe(timeframe: str) -> None`
验证时间周期是否有效

**参数:**
- `timeframe` (str): 时间周期字符串

**异常:**
- `ValueError`: 如果时间周期无效

**示例:**
```python
>>> validate_timeframe('1m')  # 正常执行
>>> validate_timeframe('invalid')
ValueError: Invalid timeframe: invalid. Valid timeframes are: 1d, 1h, 1m, 1s, 1w, 12h, 15m, 15s, 2h, 30m, 30s, 3m, 4h, 5m, 5s, 6h, 8h, 1M
```

### 交易所相关函数

#### `validate_exchange(exchange: str) -> None`
验证交易所是否支持

**参数:**
- `exchange` (str): 交易所名称

**异常:**
- `ValueError`: 如果交易所不支持

**示例:**
```python
>>> validate_exchange('binance')  # 正常执行
>>> validate_exchange('invalid_exchange')
ValueError: Unsupported exchange: invalid_exchange. Supported exchanges: binance, bybit, coinbase, gateio, huobi, kraken, kucoin, mexc, okx, bitfinex
```

### 交易对相关函数

#### `validate_symbol(symbol: str) -> None`
验证交易对格式是否有效

**参数:**
- `symbol` (str): 交易对符号，如 'BTC/USDT'

**异常:**
- `ValueError`: 如果交易对格式无效

**示例:**
```python
>>> validate_symbol('BTC/USDT')  # 正常执行
>>> validate_symbol('INVALID')
ValueError: Invalid symbol format: INVALID. Expected format: 'BASE/QUOTE' (e.g., 'BTC/USDT')
```

### OHLCV相关函数

#### `validate_ohlcv_aggregation_rule(field: str, rule: str) -> None`
验证OHLCV字段聚合规则是否有效

**参数:**
- `field` (str): OHLCV字段名
- `rule` (str): 聚合规则

**异常:**
- `ValueError`: 如果字段或规则无效

**示例:**
```python
>>> validate_ohlcv_aggregation_rule('open', 'first')  # 正常执行
>>> validate_ohlcv_aggregation_rule('invalid_field', 'first')
ValueError: Invalid OHLCV field: invalid_field. Valid fields: ['open', 'high', 'low', 'close', 'volume']
>>> validate_ohlcv_aggregation_rule('open', 'invalid_rule')
ValueError: Invalid aggregation rule: invalid_rule. Valid rules: ['first', 'last', 'max', 'min', 'sum']
```

### 验证方法相关函数

#### `validate_validation_method(method: str) -> None`
验证数据验证方法是否有效

**参数:**
- `method` (str): 验证方法名称

**异常:**
- `ValueError`: 如果验证方法无效

**示例:**
```python
>>> validate_validation_method('iqr')  # 正常执行
>>> validate_validation_method('invalid_method')
ValueError: Invalid validation method: invalid_method. Valid methods: ['iqr', 'zscore']
```

## 📦 导出列表

所有常量和函数都通过 `__all__` 导出，确保正确的模块接口：

```python
__all__ = [
    # 枚举
    'Timeframe',

    # 时间周期相关
    'TIMEFRAME_SECONDS',
    'TIMEFRAME_TO_PANDAS',
    'PANDAS_TO_TIMEFRAME',
    'DEFAULT_SOURCE_INTERVAL',
    'COMMON_INTERVALS',
    'PRECOMPUTE_INTERVALS',
    'DEFAULT_QUERY_INTERVAL',
    'DEFAULT_DOWNLOAD_INTERVAL',
    'API_DEFAULT_INTERVAL',
    'DEMO_INTERVALS',

    # 交易所相关
    'SUPPORTED_EXCHANGES',
    'DEFAULT_EXCHANGE',
    'DEFAULT_SYMBOL',
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
```

## 🚀 使用示例

### 基本使用

```python
from utils.constants import (
    Timeframe,
    SUPPORTED_EXCHANGES,
    DEFAULT_SYMBOL,
    validate_timeframe,
    validate_exchange
)

# 时间周期使用
interval = '1h'
tf = Timeframe.from_string(interval)
print(f"时间周期: {tf.value}, 秒数: {tf.seconds}")

# 交易所使用
exchange = 'binance'
if exchange in SUPPORTED_EXCHANGES:
    print(f"支持交易所: {exchange}")

# 验证使用
try:
    validate_timeframe('1h')
    validate_exchange('binance')
    print("验证通过")
except ValueError as e:
    print(f"验证失败: {e}")
```

### 数据处理

```python
from utils.constants import (
    Timeframe,
    OHLCV_COLUMNS,
    OHLCV_AGGREGATION_RULES,
    CCXT_OHLCV_INDEX
)
import pandas as pd

def process_ohlcv_data(data):
    """处理OHLCV数据"""
    # 确保列顺序正确
    df = pd.DataFrame(data, columns=OHLCV_COLUMNS)

    # 转换为CCXT格式
    ccxt_data = df[OHLCV_COLUMNS].values

    # 重采样示例
    hourly_df = df.resample(Timeframe.H1.pandas_freq).agg(OHLCV_AGGREGATION_RULES)

    return hourly_df, ccxt_data
```

## 🧪 类型提示

```python
from typing import Dict, List, Optional, Union
from utils.constants import Timeframe

def download_data(
    exchange: str,
    symbol: str,
    interval: Union[str, Timeframe],
    limit: Optional[int] = None
) -> Dict:
    """下载数据函数"""
    # 验证参数
    validate_exchange(exchange)
    validate_symbol(symbol)

    if isinstance(interval, str):
        validate_timeframe(interval)
        tf = Timeframe.from_string(interval)
    else:
        tf = interval

    # 实现下载逻辑
    return {
        'exchange': exchange,
        'symbol': symbol,
        'interval': tf.value,
        'seconds': tf.seconds,
        'limit': limit or DEFAULT_QUERY_LIMIT
    }
```

## 📚 相关文档

- [全局常量使用指南](global_constants_guide.md)
- [常量系统迁移指南](constants_migration_guide.md)
- [项目测试](../tests/test_constants.py)

---

*最后更新：2024年1月*