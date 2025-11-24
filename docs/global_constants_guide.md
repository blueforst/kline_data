# 全局常量使用指南

## 📋 概述

本项目的全局常量系统提供了统一、类型安全的方式来管理项目中的所有配置和枚举值。通过使用全局常量，可以避免硬编码、提高代码可维护性，并确保在整个项目中使用一致的值。

## 🎯 为什么使用全局常量

### 1. **避免硬编码**
- ❌ 硬编码：`if interval == '1m':`
- ✅ 常量：`if interval == Timeframe.M1.value:`

### 2. **类型安全**
- 提供类型提示和自动补全
- 在IDE中可以获得更好的开发体验

### 3. **易于维护**
- 所有配置集中在一个地方
- 修改值时只需要更新一个地方

### 4. **减少错误**
- 避免拼写错误
- 提供验证函数确保值的有效性

## 📦 导入和使用

### 基本导入

```python
# 从utils.constants导入
from utils.constants import (
    # 时间周期相关
    Timeframe,
    TIMEFRAME_SECONDS,
    DEFAULT_QUERY_INTERVAL,

    # 交易所相关
    SUPPORTED_EXCHANGES,
    DEFAULT_EXCHANGE,
    DEFAULT_SYMBOL,

    # 存储相关
    DEFAULT_STORAGE_FORMAT,
    SUPPORTED_COMPRESSIONS,

    # OHLCV相关
    OHLCV_COLUMNS,
    OHLCV_AGGREGATION_RULES,

    # 验证函数
    validate_timeframe,
    validate_exchange,
    validate_symbol,
)
```

### 从顶层模块导入

```python
# 从项目根目录导入（推荐）
from kline_data import Timeframe
from utils.constants import SUPPORTED_EXCHANGES
```

### 从旧位置导入（向后兼容）

```python
# 从resampler模块导入（向后兼容）
from resampler.timeframe import Timeframe
from resampler.timeframe import TIMEFRAME_SECONDS
```

## ⏰ 时间周期使用

### Timeframe枚举

`Timeframe`是一个功能丰富的枚举类，提供了多种时间周期的表示和操作方法：

```python
from utils.constants import Timeframe

# 基本使用
print(Timeframe.M1.value)      # '1m'
print(Timeframe.M1.seconds)    # 60
print(Timeframe.M1.pandas_freq)  # '1min'

# 从字符串创建
tf = Timeframe.from_string('1h')
print(tf == Timeframe.H1)      # True

# 获取所有支持的时间周期
all_timeframes = Timeframe.list_all()
print(all_timeframes)
# ['1s', '5s', '15s', '30s', '1m', '3m', '5m', '15m', '30m', '1h', '2h', '4h', '6h', '8h', '12h', '1d', '1w', '1M']

# 检查重采样兼容性
can_resample = Timeframe.H1.is_valid_resample_from(Timeframe.M1)
print(can_resample)  # True - 可以从1分钟重采样到1小时
```

### 时间周期映射

```python
from utils.constants import TIMEFRAME_SECONDS, TIMEFRAME_TO_PANDAS

# 获取时间周期对应的秒数
seconds = TIMEFRAME_SECONDS['1h']  # 3600

# 获取pandas频率字符串
pandas_freq = TIMEFRAME_TO_PANDAS['1d']  # '1D'
```

### 实际应用示例

```python
# 在数据下载中使用
def download_data(exchange, symbol, interval='1h'):
    # 验证时间周期
    validate_timeframe(interval)

    # 转换为Timeframe对象
    tf = Timeframe.from_string(interval)

    # 获取时间范围（按秒计算）
    duration_hours = 24
    duration_seconds = duration_hours * 3600
    start_time = datetime.now() - timedelta(seconds=duration_seconds)

    print(f"下载 {exchange} {symbol} {interval} 数据")
    print(f"时间周期: {tf.value} ({tf.seconds}秒)")

    # 实际下载逻辑...

# 在重采样中使用
def resample_data(df, source_interval, target_interval):
    source_tf = Timeframe.from_string(source_interval)
    target_tf = Timeframe.from_string(target_interval)

    if not target_tf.is_valid_resample_from(source_tf):
        raise ValueError(f"无法从 {source_interval} 重采样到 {target_interval}")

    print(f"使用pandas频率: {target_tf.pandas_freq}")
    # 实际重采样逻辑...
```

## 🏦 交易所相关常量

```python
from utils.constants import (
    SUPPORTED_EXCHANGES,
    DEFAULT_EXCHANGE,
    DEFAULT_SYMBOL,
    TEST_SYMBOLS,
    validate_exchange,
    validate_symbol
)

# 检查支持的交易所
print(f"支持的交易所: {SUPPORTED_EXCHANGES}")
# ['binance', 'okx', 'bybit', 'huobi', 'kraken', 'coinbase', 'kucoin', 'bitfinex', 'gateio', 'mexc']

# 使用默认值
exchange = DEFAULT_EXCHANGE  # 'binance'
symbol = DEFAULT_SYMBOL      # 'BTC/USDT'

# 验证交易所和交易对
def validate_trading_pair(exchange_name, symbol_name):
    try:
        validate_exchange(exchange_name)
        validate_symbol(symbol_name)
        print(f"✅ {exchange_name} {symbol_name} 验证通过")
        return True
    except ValueError as e:
        print(f"❌ 验证失败: {e}")
        return False

# 实际使用
validate_trading_pair('binance', 'BTC/USDT')  # ✅ 验证通过
validate_trading_pair('invalid_exchange', 'BTC/USDT')  # ❌ 验证失败
validate_trading_pair('binance', 'INVALID')  # ❌ 验证失败
```

## 📁 存储相关常量

```python
from utils.constants import (
    SUPPORTED_STORAGE_FORMATS,
    DEFAULT_STORAGE_FORMAT,
    SUPPORTED_COMPRESSIONS,
    DEFAULT_COMPRESSION,
    PARTITION_GRANULARITIES,
    DEFAULT_PARTITION_GRANULARITY
)

# 存储配置
storage_config = {
    'format': DEFAULT_STORAGE_FORMAT,  # 'parquet'
    'compression': DEFAULT_COMPRESSION,  # 'snappy'
    'partition_granularity': DEFAULT_PARTITION_GRANULARITY  # 'month'
}

print(f"支持的存储格式: {SUPPORTED_STORAGE_FORMATS}")
print(f"支持的压缩算法: {SUPPORTED_COMPRESSIONS}")
```

## 📊 OHLCV数据常量

```python
from utils.constants import (
    OHLCV_COLUMNS,
    CCXT_OHLCV_INDEX,
    OHLCV_AGGREGATION_RULES
)

# 字段验证
def validate_ohlcv_data(data):
    """验证OHLCV数据格式"""
    # 检查列名
    expected_columns = set(OHLCV_COLUMNS)
    actual_columns = set(data.columns)

    if expected_columns != actual_columns:
        missing = expected_columns - actual_columns
        extra = actual_columns - expected_columns
        raise ValueError(f"OHLCV列不匹配. 缺失: {missing}, 多余: {extra}")

    print("✅ OHLCV数据格式验证通过")

# 聚合规则使用
def get_aggregation_rule(field):
    """获取字段的聚合规则"""
    if field == 'timestamp':
        return None  # 时间戳不需要聚合

    rule = OHLCV_AGGREGATION_RULES.get(field)
    if not rule:
        raise ValueError(f"未知字段: {field}")

    print(f"字段 {field} 使用聚合规则: {rule}")
    return rule

# 实际使用
get_aggregation_rule('open')    # 'first'
get_aggregation_rule('high')    # 'max'
get_aggregation_rule('volume')  # 'sum'
```

## 🔍 验证函数使用

项目提供了多个验证函数来确保输入值的正确性：

```python
from utils.constants import (
    validate_timeframe,
    validate_exchange,
    validate_symbol,
    validate_ohlcv_aggregation_rule,
    validate_validation_method
)

# 批量验证
def validate_download_params(exchange, symbol, interval):
    """验证下载参数"""
    errors = []

    try:
        validate_exchange(exchange)
    except ValueError as e:
        errors.append(f"交易所错误: {e}")

    try:
        validate_symbol(symbol)
    except ValueError as e:
        errors.append(f"交易对错误: {e}")

    try:
        validate_timeframe(interval)
    except ValueError as e:
        errors.append(f"时间周期错误: {e}")

    if errors:
        raise ValueError("参数验证失败:\n" + "\n".join(errors))

    print("✅ 所有参数验证通过")
    return True

# 使用示例
try:
    validate_download_params('binance', 'BTC/USDT', '1h')
    print("参数正确，可以开始下载")
except ValueError as e:
    print(f"参数错误: {e}")
```

## 🚀 最佳实践

### 1. **始终使用常量而非硬编码**

```python
# ❌ 错误做法
if interval == '1m':
    process_data()

# ✅ 正确做法
if interval == Timeframe.M1.value:
    process_data()
```

### 2. **使用验证函数**

```python
# ❌ 错误做法 - 没有验证
def download_data(exchange, symbol, interval):
    # 直接使用，可能导致错误
    pass

# ✅ 正确做法 - 先验证
def download_data(exchange, symbol, interval):
    validate_exchange(exchange)
    validate_symbol(symbol)
    validate_timeframe(interval)
    # 安全使用
    pass
```

### 3. **利用Timeframe的功能**

```python
# ❌ 错误做法 - 手动映射
interval_seconds = {
    '1m': 60,
    '5m': 300,
    '1h': 3600
}

# ✅ 正确做法 - 使用内置方法
tf = Timeframe.from_string(interval)
seconds = tf.seconds
pandas_freq = tf.pandas_freq
```

### 4. **保持代码简洁**

```python
# ❌ 错误做法 - 重复的验证逻辑
def func1():
    if interval not in ['1m', '5m', '15m', '30m', '1h', '1d']:
        raise ValueError("Invalid interval")

def func2():
    if interval not in ['1m', '5m', '15m', '30m', '1h', '1d']:
        raise ValueError("Invalid interval")

# ✅ 正确做法 - 使用验证函数
def func1():
    validate_timeframe(interval)

def func2():
    validate_timeframe(interval)
```

### 5. **类型提示**

```python
from utils.constants import Timeframe
from typing import Literal

# ✅ 使用类型提示
def process_timeframe(interval: str) -> None:
    tf = Timeframe.from_string(interval)
    # 处理逻辑...

# ✅ 或使用Literal类型
def process_interval(interval: Literal['1m', '5m', '15m', '30m', '1h', '1d']) -> None:
    validate_timeframe(interval)
    # 处理逻辑...
```

## ⚡ 性能考虑

### 1. **导入优化**

```python
# ✅ 只导入需要的常量
from utils.constants import Timeframe, DEFAULT_EXCHANGE

# ❌ 避免导入整个模块
from utils import constants
constants.Timeframe.M1  # 需要额外的属性查找
```

### 2. **缓存Timeframe对象**

```python
# ✅ 缓存常用的Timeframe对象
COMMON_TIMEFRAMES = {
    '1m': Timeframe.M1,
    '5m': Timeframe.M5,
    '1h': Timeframe.H1,
    '1d': Timeframe.D1,
}

def get_cached_timeframe(interval):
    return COMMON_TIMEFRAMES.get(interval, Timeframe.from_string(interval))
```

### 3. **批量验证**

```python
# ✅ 批量验证减少函数调用开销
def validate_all_params(params):
    try:
        validate_exchange(params['exchange'])
        validate_symbol(params['symbol'])
        validate_timeframe(params['interval'])
    except ValueError:
        # 一次性处理所有验证错误
        raise
```

## 🔄 扩展常量

当需要添加新的常量时，请遵循以下模式：

### 1. **添加到适当的分组**

```python
# 在utils/constants.py中添加

# 新的交易所
SUPPORTED_EXCHANGES: Final[List[str]] = [
    # ... 现有交易所
    'new_exchange',  # 新增
]

# 新的时间周期（如果需要）
class Timeframe(str, Enum):
    # ... 现有时间周期
    NEW_INTERVAL = '3h'  # 新增

# 添加对应的映射
TIMEFRAME_SECONDS: Final[Dict[str, int]] = {
    # ... 现有映射
    '3h': 10800,  # 新增
}
```

### 2. **添加验证函数**

```python
def validate_new_param(param: str) -> None:
    """验证新参数是否有效"""
    if param not in VALID_NEW_PARAMS:
        raise ValueError(
            f"Invalid parameter: {param}. "
            f"Valid parameters: {VALID_NEW_PARAMS}"
        )
```

### 3. **更新导出列表**

```python
__all__ = [
    # ... 现有导出
    'validate_new_param',
]
```

## 🧪 测试

所有常量都有对应的测试，确保正确性：

```python
# 运行常量相关测试
pytest tests/test_constants.py -v

# 运行特定测试
pytest tests/test_constants.py::TestTimeframeEnum -v
pytest tests/test_constants.py::TestHelperFunctions -v
```

## 📚 相关文档

- [API参考文档](constants_api_reference.md) - 详细的API文档
- [迁移指南](constants_migration_guide.md) - 从硬编码到常量的迁移
- [项目文档](../README.md) - 项目整体文档

## 🔗 参考链接

- [Python官方文档 - 枚举类型](https://docs.python.org/3/library/enum.html)
- [Pandas时间频率字符串](https://pandas.pydata.org/pandas-docs/stable/user_guide/timeseries.html#offset-aliases)
- [CCXT支持的交易所](https://github.com/ccxt/ccxt#supported-cryptocurrency-exchange-markets)

---

*最后更新：2024年1月*