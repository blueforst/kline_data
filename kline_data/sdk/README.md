# SDK模块文档

## 概述

SDK模块提供统一的Python接口用于K线数据管理，采用模块化设计，所有功能使用统一的底层逻辑。

## 核心特性

- ✅ **统一逻辑**: 所有数据获取使用相同的智能策略
- ✅ **自动下载**: 查询缺失数据时自动下载
- ✅ **模块化**: 清晰的功能划分
- ✅ **数据流支持**: 内存高效的分块数据迭代（支持自动下载）
- ✅ **技术指标**: 内置常用技术指标计算

## 快速开始

### 基本用法（推荐）

```python
from sdk import KlineClient
from datetime import datetime

# 创建客户端
client = KlineClient()

# 查询数据（自动下载缺失数据）
df = client.get_kline(
    exchange='binance',
    symbol='BTC/USDT',
    start_time=datetime(2024, 1, 1),
    end_time=datetime(2024, 1, 2),
    interval='1h',
    with_indicators=['MA_20', 'RSI_14']  # 可选：计算技术指标
)

print(df.head())
```

### 创建数据流（自动下载支持）

```python
# 创建分块数据流
feed = client.create_data_feed(
    exchange='binance',
    symbol='BTC/USDT',
    start_time=datetime(2020, 1, 1),
    end_time=datetime(2024, 1, 1),
    interval='1h',
    chunk_size=10000
)

# 迭代数据块
for chunk in feed:
    print(f"Processing {len(chunk)} bars")
    # 进行回测或分析
```

## 模块结构

### 1. KlineClient（统一客户端）- 推荐使用

整合了所有功能的主客户端：

```python
from sdk import KlineClient

client = KlineClient()

# 数据查询
df = client.get_kline(...)
df = client.get_latest(...)
df = client.get_klines_before(...)

# 数据流
feed = client.create_data_feed(...)
feed = client.create_backtrader_feed(...)
feed = client.create_streaming_feed(...)

# 数据下载
client.download_kline(...)
client.update_kline(...)

# 所有周期直接获取（无需重采样）
client.get_kline(..., interval='4h')

# 技术指标
client.calculate_indicators(...)

# 元数据
client.get_metadata(...)
```

### 2. 子客户端（按需使用）

#### QueryClient - 数据查询

```python
from sdk import QueryClient

query = QueryClient()

# 查询数据（支持自动下载）
df = query.get_kline(
    exchange='binance',
    symbol='BTC/USDT',
    start_time=datetime(2024, 1, 1),
    end_time=datetime(2024, 1, 2),
    interval='1h',
    auto_strategy=True  # 自动选择策略（包括下载）
)

# 获取最新数据
df = query.get_latest('binance', 'BTC/USDT', '1h', limit=100)

# 获取指定时间前的数据
df = query.get_klines_before(
    'binance', 'BTC/USDT',
    before_time=datetime(2024, 1, 1),
    interval='1h',
    limit=100
)
```

#### DownloadClient - 数据下载

```python
from sdk import DownloadClient

download = DownloadClient()

# 下载历史数据
result = download.download(
    exchange='binance',
    symbol='BTC/USDT',
    start_time=datetime(2023, 1, 1),
    end_time=datetime(2024, 1, 1),
    interval='1m'
)

# 更新到最新
result = download.update('binance', 'BTC/USDT')

# 获取任务状态
status = download.get_task_status(result['task_id'])
```

#### （已移除）ResampleClient

> 本地重采样功能已经移除，所有时间周期都可以直接通过 `QueryClient` / `KlineClient` 从交易所下载。
> 如需不同周期的数据，请直接调用 `get_kline(..., interval='目标周期')`。

#### IndicatorClient - 技术指标

```python
from sdk import IndicatorClient

indicator = IndicatorClient()

# 计算指标
df_with_indicators = indicator.calculate(df, [
    'MA_20',      # 20周期移动平均
    'EMA_12',     # 12周期指数移动平均
    'RSI_14',     # 14周期RSI
    'BOLL_20',    # 20周期布林带
    'MACD'        # MACD指标
])
```

#### MetadataClient - 元数据查询

```python
from sdk import MetadataClient

metadata = MetadataClient()

# 获取元数据
info = metadata.get_metadata('binance', 'BTC/USDT')
print(info['intervals'])  # 可用周期和数据范围

# 获取数据范围
start_ts, end_ts = metadata.get_data_range('binance', 'BTC/USDT')
```

### 3. 数据流类

#### ChunkedDataFeed - 分块数据流

```python
from sdk import ChunkedDataFeed

feed = ChunkedDataFeed(
    exchange='binance',
    symbol='BTC/USDT',
    start_time=datetime(2020, 1, 1),
    end_time=datetime(2024, 1, 1),
    interval='1h',
    chunk_size=10000
)

# 迭代数据块
for chunk_df in feed:
    print(f"Processing {len(chunk_df)} bars")

# 逐行迭代
for timestamp, o, h, l, c, v in feed.iter_rows():
    # 处理每根K线
    pass

# 转换为完整DataFrame（注意内存）
df = feed.to_dataframe(max_rows=100000)
```

#### BacktraderDataFeed - Backtrader兼容

```python
from sdk import BacktraderDataFeed
import backtrader as bt

feed = BacktraderDataFeed(
    exchange='binance',
    symbol='BTC/USDT',
    start_time=datetime(2023, 1, 1),
    end_time=datetime(2024, 1, 1),
    interval='1h'
)

# 转换为backtrader格式
bt_data = bt.feeds.PandasData(
    dataname=feed.to_backtrader_format(),
    **feed.get_backtrader_params()
)

cerebro = bt.Cerebro()
cerebro.adddata(bt_data)
```

#### StreamingDataFeed - 实时模拟

```python
from sdk import StreamingDataFeed

feed = StreamingDataFeed(
    exchange='binance',
    symbol='BTC/USDT',
    start_time=datetime(2024, 1, 1),
    end_time=datetime(2024, 1, 2),
    interval='1m',
    playback_speed=100  # 100倍速播放
)

# 实时流式处理
for bar in feed.stream():
    print(f"New bar: {bar['close']}")
    # 执行交易策略
```

## 智能数据获取策略

所有查询方法（包括数据流）都使用相同的智能策略：

1. **本地优先**: 如果本地有完整数据，直接读取
2. **自动下载**: 如果数据缺失，自动从交易所下载
3. **统一周期**: 所有周期均由CCXT提供，无需本地重采样

```python
# 示例：查询不存在的数据
df = client.get_kline(
    'binance', 'BTC/USDT',
    datetime(2024, 1, 1),
    datetime(2024, 1, 2),
    '1h'
)
# 如果本地没有数据，会自动从binance下载
```

## 完整示例

### 示例1: 下载并分析数据

```python
from sdk import KlineClient
from datetime import datetime

client = KlineClient()

# 自动下载并查询数据（一步完成）
df = client.get_kline(
    exchange='binance',
    symbol='BTC/USDT',
    start_time=datetime(2024, 1, 1),
    end_time=datetime(2024, 1, 2),
    interval='1h',
    with_indicators=['MA_20', 'RSI_14', 'MACD']
)

# 分析数据
print(f"总共 {len(df)} 条K线")
print(f"最高价: {df['high'].max()}")
print(f"最低价: {df['low'].min()}")
print(f"MA_20最新值: {df['MA_20'].iloc[-1]}")
```

### 示例2: 回测应用

```python
from sdk import KlineClient
from datetime import datetime

client = KlineClient()

# 创建数据流（自动下载缺失数据）
feed = client.create_data_feed(
    exchange='binance',
    symbol='BTC/USDT',
    start_time=datetime(2020, 1, 1),
    end_time=datetime(2024, 1, 1),
    interval='1h',
    chunk_size=10000
)

# 执行回测
portfolio_value = 100000
for chunk in feed:
    # 计算指标
    chunk_with_ind = client.calculate_indicators(chunk, ['MA_20', 'MA_50'])
    
    # 交易逻辑
    for _, row in chunk_with_ind.iterrows():
        if row['MA_20'] > row['MA_50']:
            # 金叉买入
            pass
        elif row['MA_20'] < row['MA_50']:
            # 死叉卖出
            pass

print(f"最终资产: {portfolio_value}")
```

### 示例3: 多周期分析

```python
from sdk import KlineClient
from datetime import datetime

client = KlineClient()
intervals = ['1m', '5m', '15m', '1h', '4h']

for interval in intervals:
    df = client.get_kline(
        exchange='binance',
        symbol='BTC/USDT',
        start_time=datetime(2024, 1, 1),
        end_time=datetime(2024, 1, 2),
        interval=interval
    )
    print(f"{interval}: {len(df)} bars")
```

## 注意事项

1. **自动下载**: 所有查询操作都支持自动下载，无需手动检查数据是否存在
2. **内存管理**: 对于大数据集，优先使用数据流而不是一次性加载
3. **配置共享**: 所有客户端共享相同的配置对象
4. **线程安全**: 客户端是线程安全的，可以在多线程环境中使用

## 迁移说明

如果你使用旧版SDK，请参考 [SDK_REFACTORING_GUIDE.md](../docs/SDK_REFACTORING_GUIDE.md) 进行迁移。

## 支持的交易所和周期

- **交易所**: binance, okx, huobi等（所有ccxt支持的交易所）
- **周期**: 1s, 1m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 12h, 1d, 1w, 1M等

## 常见问题

**Q: 数据流会自动下载数据吗？**
A: 是的！新版本的数据流使用QueryClient，支持自动下载缺失数据。

**Q: 如何只使用本地数据，不自动下载？**
A: 设置 `auto_strategy=False`:
```python
df = query.get_kline(..., auto_strategy=False)
```

**Q: 可以只使用某个子客户端吗？**
A: 可以！根据需要导入特定客户端:
```python
from sdk import QueryClient, IndicatorClient
```

**Q: 旧代码还能用吗？**
A: 可以，但会显示废弃警告。建议尽快迁移到新API。

---

## 归档文件

`archived/` 目录包含已废弃的文件（`client.py`和`data_feed.py`），仅供参考。

这些文件存在以下问题：
- 逻辑不统一（data_feed不使用DataFetcher）
- 缺少自动下载（data_feed返回空数据）
- 代码重复，难以维护

请使用新的模块化SDK，不要使用归档文件。详见[归档说明](archived/README.md)。
