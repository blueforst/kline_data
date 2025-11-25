# 数据流使用指南 (Data Feed Guide)

## 概述

数据流模块提供了内存高效的分块数据读取功能，特别适合大规模回测场景和实时策略测试。支持与 backtrader 等回测框架无缝集成。

## 核心特性

- ✅ **内存高效**: 分块加载数据，避免一次性加载大量数据到内存
- ✅ **灵活迭代**: 支持块级、行级、字典格式的多种迭代方式
- ✅ **Backtrader集成**: 提供与 backtrader 完全兼容的数据格式
- ✅ **流式模拟**: 支持实时数据流模拟，可控播放速度
- ✅ **自动边界处理**: 智能处理数据分区和时间边界

## 三种数据流类型

### 1. ChunkedDataFeed - 基础分块数据流

最基础的数据流类，提供分块读取功能。

```python
from datetime import datetime
from sdk import ChunkedDataFeed

# 创建数据流
feed = ChunkedDataFeed(
    exchange='binance',
    symbol='BTC/USDT',
    start_time=datetime(2020, 1, 1),
    end_time=datetime(2024, 1, 1),
    interval='1h',
    chunk_size=10000  # 每次加载10000条数据
)

# 方式1: 按块迭代
for chunk_df in feed:
    print(f"加载了 {len(chunk_df)} 条数据")
    # 处理数据块
    process_chunk(chunk_df)

# 方式2: 逐行迭代
for timestamp, open_price, high, low, close, volume in feed.iter_rows():
    # 处理单根K线
    strategy.on_bar(timestamp, open_price, high, low, close, volume)

# 方式3: 字典格式迭代
for bar in feed.iter_dicts():
    print(f"时间: {bar['timestamp']}, 收盘价: {bar['close']}")
```

### 2. BacktraderDataFeed - Backtrader专用数据流

提供与 backtrader 完全兼容的数据格式。

```python
import backtrader as bt
from sdk import BacktraderDataFeed

# 创建数据流
data_feed = BacktraderDataFeed(
    exchange='binance',
    symbol='BTC/USDT',
    start_time=datetime(2023, 1, 1),
    end_time=datetime(2024, 1, 1),
    interval='1h'
)

# 转换为backtrader格式
bt_data = bt.feeds.PandasData(
    dataname=data_feed.to_backtrader_format(),
    **data_feed.get_backtrader_params()
)

# 创建回测引擎
cerebro = bt.Cerebro()
cerebro.adddata(bt_data)
cerebro.addstrategy(YourStrategy)

# 运行回测
results = cerebro.run()
cerebro.plot()
```

### 3. StreamingDataFeed - 流式数据源

模拟实时数据流，支持可控的播放速度。

```python
from sdk import StreamingDataFeed
import time

# 创建流式数据源（100倍速播放）
feed = StreamingDataFeed(
    exchange='binance',
    symbol='BTC/USDT',
    start_time=datetime(2024, 1, 1),
    end_time=datetime(2024, 1, 2),
    interval='1m',
    playback_speed=100.0  # 100倍速
)

# 实时处理数据
for bar in feed.stream():
    print(f"新K线: {bar['timestamp']} - 收盘价: {bar['close']}")
    # 执行交易逻辑
    # ... 自动按播放速度延迟
```

## 初始化参数

### 通用参数

| 参数 | 类型 | 说明 | 默认值 |
|------|------|------|--------|
| `exchange` | str | 交易所名称 | 必填 |
| `symbol` | str | 交易对 | 必填 |
| `start_time` | datetime | 开始时间 | 必填 |
| `end_time` | datetime | 结束时间 | 必填 |
| `interval` | str | 时间周期 | '1s' |
| `chunk_size` | int | 每块数据大小 | 10000 |
| `config` | Config | 配置对象 | None（使用默认） |
| `preload_chunks` | int | 预加载块数 | 1 |

### StreamingDataFeed 特有参数

| 参数 | 类型 | 说明 | 默认值 |
|------|------|------|--------|
| `playback_speed` | float | 播放速度倍数 | 1.0 |

## 使用场景

### 场景1: 大数据集回测（内存高效）

处理1年的分钟级数据（约50万条），不会占用过多内存：

```python
feed = ChunkedDataFeed(
    exchange='binance',
    symbol='BTC/USDT',
    start_time=datetime(2023, 1, 1),
    end_time=datetime(2024, 1, 1),
    interval='1m',
    chunk_size=10000  # 每次只加载1万条
)

total_volume = 0
max_price = 0

for chunk_df in feed:
    total_volume += chunk_df['volume'].sum()
    max_price = max(max_price, chunk_df['high'].max())

print(f"总成交量: {total_volume}")
print(f"最高价: {max_price}")
```

### 场景2: Backtrader策略回测

```python
import backtrader as bt

class MyStrategy(bt.Strategy):
    def __init__(self):
        self.sma = bt.indicators.SimpleMovingAverage(
            self.data.close, period=20
        )
    
    def next(self):
        if self.data.close[0] > self.sma[0]:
            self.buy()
        elif self.data.close[0] < self.sma[0]:
            self.sell()

# 创建数据流
data_feed = BacktraderDataFeed(
    exchange='binance',
    symbol='BTC/USDT',
    start_time=datetime(2023, 1, 1),
    end_time=datetime(2024, 1, 1),
    interval='1h'
)

# 运行回测
cerebro = bt.Cerebro()
bt_data = bt.feeds.PandasData(
    dataname=data_feed.to_backtrader_format(),
    **data_feed.get_backtrader_params()
)
cerebro.adddata(bt_data)
cerebro.addstrategy(MyStrategy)
cerebro.broker.setcash(100000.0)
cerebro.run()
```

### 场景3: 实时策略模拟

```python
# 模拟实时交易环境（10倍速）
feed = StreamingDataFeed(
    exchange='binance',
    symbol='BTC/USDT',
    start_time=datetime(2024, 1, 1),
    end_time=datetime(2024, 1, 7),
    interval='5m',
    playback_speed=10.0
)

positions = []

for bar in feed.stream():
    # 简单的均线策略
    if should_buy(bar):
        positions.append({
            'time': bar['timestamp'],
            'price': bar['close'],
            'type': 'LONG'
        })
        print(f"买入 @ {bar['close']}")
    elif should_sell(bar):
        # 平仓逻辑
        print(f"卖出 @ {bar['close']}")
```

### 场景4: 自定义指标计算

```python
import pandas as pd

feed = ChunkedDataFeed(
    exchange='binance',
    symbol='BTC/USDT',
    start_time=datetime(2024, 1, 1),
    end_time=datetime(2024, 2, 1),
    interval='1h',
    chunk_size=200
)

# 维护跨块的状态
prev_ma_short = None
prev_ma_long = None
signals = []

for chunk_df in feed:
    # 计算移动平均
    chunk_df['MA_10'] = chunk_df['close'].rolling(window=10).mean()
    chunk_df['MA_20'] = chunk_df['close'].rolling(window=20).mean()
    
    # 检测交叉信号
    for idx, row in chunk_df.iterrows():
        ma_short = row['MA_10']
        ma_long = row['MA_20']
        
        if pd.notna(ma_short) and pd.notna(ma_long):
            if prev_ma_short and prev_ma_long:
                # 金叉
                if prev_ma_short < prev_ma_long and ma_short > ma_long:
                    signals.append(('BUY', row['timestamp'], row['close']))
                # 死叉
                elif prev_ma_short > prev_ma_long and ma_short < ma_long:
                    signals.append(('SELL', row['timestamp'], row['close']))
            
            prev_ma_short = ma_short
            prev_ma_long = ma_long

print(f"检测到 {len(signals)} 个交易信号")
```

## API 参考

### ChunkedDataFeed

#### 方法

**`__iter__() -> Iterator[pd.DataFrame]`**
- 迭代数据块
- 返回: 数据块迭代器

**`iter_rows() -> Iterator[Tuple]`**
- 逐行迭代数据
- 返回: (timestamp, open, high, low, close, volume) 元组

**`iter_dicts() -> Iterator[dict]`**
- 以字典格式迭代
- 返回: K线数据字典

**`to_dataframe(max_rows=None) -> pd.DataFrame`**
- 将所有数据加载为单个DataFrame
- 参数: `max_rows` - 最大行数限制
- 返回: 完整数据DataFrame

**`reset() -> None`**
- 重置迭代器到起始位置

**`get_stats() -> dict`**
- 获取数据流统计信息
- 返回: 统计信息字典

### BacktraderDataFeed

继承自 `ChunkedDataFeed`，额外提供：

**`to_backtrader_format(max_rows=None) -> pd.DataFrame`**
- 转换为backtrader标准格式
- 参数: `max_rows` - 最大行数
- 返回: backtrader格式的DataFrame

**`get_backtrader_params() -> dict`**
- 获取backtrader PandasData的参数配置
- 返回: 参数字典

### StreamingDataFeed

继承自 `ChunkedDataFeed`，额外提供：

**`stream() -> Iterator[dict]`**
- 流式推送数据（带延迟）
- 返回: K线数据字典迭代器

**`get_sleep_time() -> float`**
- 计算每根K线之间的延迟时间
- 返回: 延迟时间（秒）

## 性能优化建议

### 1. 选择合适的块大小

```python
# 小数据集（< 10万条）
chunk_size = 5000

# 中等数据集（10万 - 100万条）
chunk_size = 10000

# 大数据集（> 100万条）
chunk_size = 50000
```

### 2. 使用缓存

确保配置中启用了缓存：

```yaml
# config.yaml
memory:
  cache:
    enabled: true
    max_size_mb: 512
    ttl_seconds: 3600
```

### 3. 预加载优化

对于频繁访问的数据，可以预加载：

```python
feed = ChunkedDataFeed(
    ...,
    preload_chunks=2  # 预加载2个块
)
```

### 4. 选择合适的迭代方式

```python
# 需要DataFrame操作 -> 使用 __iter__()
for chunk_df in feed:
    chunk_df['custom_indicator'] = ...

# 逐笔处理 -> 使用 iter_rows()（更快）
for timestamp, o, h, l, c, v in feed.iter_rows():
    process_bar(o, h, l, c, v)

# 需要字段名 -> 使用 iter_dicts()
for bar in feed.iter_dicts():
    if bar['close'] > bar['open']:
        ...
```

## 常见问题

### Q1: 如何处理跨块的指标计算？

A: 需要手动维护状态：

```python
# 错误示例：每个块独立计算
for chunk in feed:
    chunk['MA'] = chunk['close'].rolling(20).mean()  # 第一个块的前20行会是NaN

# 正确示例：维护跨块状态
all_closes = []
for chunk in feed:
    all_closes.extend(chunk['close'].tolist())
    if len(all_closes) >= 20:
        ma = sum(all_closes[-20:]) / 20
        # 使用MA值
```

### Q2: 数据流能否重复使用？

A: 可以，使用 `reset()` 方法：

```python
feed = ChunkedDataFeed(...)

# 第一次迭代
for chunk in feed:
    process(chunk)

# 重置并再次迭代
feed.reset()
for chunk in feed:
    process(chunk)
```

### Q3: 如何与其他回测框架集成？

A: 大多数框架支持 pandas DataFrame：

```python
# Vectorbt
import vectorbt as vbt
feed = ChunkedDataFeed(...)
df = feed.to_dataframe()
vbt.Portfolio.from_signals(df['close'], entries, exits)

# Zipline
from zipline.data import bundles
# 将数据写入zipline bundle

# 自定义框架
for timestamp, o, h, l, c, v in feed.iter_rows():
    your_framework.feed_data(timestamp, o, h, l, c, v)
```

### Q4: 内存占用如何？

A: 取决于 `chunk_size`：

```python
# 估算公式
memory_mb = chunk_size * columns * 8 / (1024 * 1024)

# 示例
chunk_size = 10000
columns = 6  # timestamp, open, high, low, close, volume
memory_mb = 10000 * 6 * 8 / (1024 * 1024) ≈ 0.46 MB

# 一个块通常只占用 < 1MB 内存
```

## 完整示例

查看 `examples/data_feed_example.py` 获取更多示例：

```bash
python examples/data_feed_example.py
```

## 相关文档

- [SDK客户端使用指南](./sdk_guide.md)
- [配置文件说明](./configuration.md)
- [Backtrader官方文档](https://www.backtrader.com/)
