# DataFeed SDK 使用文档

## 📚 目录

- [概述](#概述)
- [核心类说明](#核心类说明)
- [快速开始](#快速开始)
- [详细用法](#详细用法)
- [高级特性](#高级特性)
- [性能优化](#性能优化)
- [常见问题](#常见问题)

---

## 概述

DataFeed SDK 提供了三种数据流类，用于高效处理K线数据：

| 类名 | 用途 | 特点 |
|------|------|------|
| `ChunkedDataFeed` | 分块数据流 | 内存高效，适合大规模数据处理 |
| `BacktraderDataFeed` | Backtrader集成 | 兼容backtrader框架 |
| `StreamingDataFeed` | 实时模拟 | 模拟实时数据流，可调速播放 |

### 主要特性

✅ **内存高效** - 分块加载，避免一次性加载大量数据  
✅ **多时间周期** - 支持1m, 5m, 15m, 1h, 4h, 1d, 1w等  
✅ **多种迭代方式** - 支持DataFrame块、行级、字典格式迭代  
✅ **Backtrader兼容** - 可直接用于backtrader策略回测  
✅ **实时模拟** - 支持可变速度的实时数据播放  

---

## 核心类说明

### 1. ChunkedDataFeed - 分块数据流

最基础的数据流类，提供内存高效的K线数据迭代。

**构造参数：**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `exchange` | str | ✅ | - | 交易所名称（binance, okx等） |
| `symbol` | str | ✅ | - | 交易对（BTC/USDT等） |
| `start_time` | datetime | ✅ | - | 开始时间 |
| `end_time` | datetime | ✅ | - | 结束时间 |
| `interval` | str | ❌ | '1h' | 时间周期 |
| `chunk_size` | int | ❌ | 10000 | 每块数据行数 |
| `config` | Config | ❌ | None | 配置对象 |
| `preload_chunks` | int | ❌ | 1 | 预加载块数 |

**主要方法：**

```python
# 1. 块级迭代
for chunk_df in feed:
    process(chunk_df)

# 2. 行级迭代（适合逐笔处理）
for timestamp, o, h, l, c, v in feed.iter_rows():
    process_bar(o, h, l, c, v)

# 3. 字典迭代
for bar in feed.iter_dicts():
    print(bar['close'])

# 4. 转换为完整DataFrame（小心内存）
df = feed.to_dataframe(max_rows=100000)

# 5. 重置迭代器
feed.reset()

# 6. 获取统计信息
stats = feed.get_stats()
```

---

### 2. BacktraderDataFeed - Backtrader集成

继承自`ChunkedDataFeed`，提供与backtrader框架的无缝集成。

**额外方法：**

```python
# 转换为backtrader格式
bt_df = feed.to_backtrader_format(max_rows=50000)

# 获取backtrader参数配置
params = feed.get_backtrader_params()
```

---

### 3. StreamingDataFeed - 实时模拟

继承自`ChunkedDataFeed`，模拟实时数据流。

**额外参数：**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `playback_speed` | float | 1.0 | 播放速度（1.0=实时，10.0=10倍速） |

**主要方法：**

```python
# 流式推送数据（自动延迟）
for bar in feed.stream():
    process_realtime(bar)

# 获取延迟时间（秒）
sleep_time = feed.get_sleep_time()
```

---

## 快速开始

### 安装依赖

```bash
pip install pandas pyarrow
```

### 基础示例

```python
from datetime import datetime
from sdk.data_feed import ChunkedDataFeed

# 创建数据流
feed = ChunkedDataFeed(
    exchange='binance',
    symbol='BTC/USDT',
    start_time=datetime(2023, 1, 1),
    end_time=datetime(2024, 1, 1),
    interval='1h',
    chunk_size=10000
)

# 迭代数据块
for chunk_df in feed:
    print(f"加载 {len(chunk_df)} 根K线")
    print(chunk_df.head())
    # 处理数据...
```

---

## 详细用法

### 1. 基础数据读取

#### 1.1 块级迭代（推荐用于大数据集）

```python
from sdk.data_feed import ChunkedDataFeed
from datetime import datetime

feed = ChunkedDataFeed(
    exchange='binance',
    symbol='ETH/USDT',
    start_time=datetime(2020, 1, 1),
    end_time=datetime(2024, 1, 1),
    interval='1d',
    chunk_size=5000  # 每次加载5000天数据
)

total_bars = 0
for chunk in feed:
    total_bars += len(chunk)
    # 计算指标
    chunk['ma20'] = chunk['close'].rolling(20).mean()
    print(f"处理了 {len(chunk)} 根K线")

print(f"总共处理 {total_bars} 根K线")
```

#### 1.2 行级迭代（适合策略回测）

```python
for timestamp, open_price, high, low, close, volume in feed.iter_rows():
    # 逐笔处理策略逻辑
    if close > open:
        print(f"{timestamp}: 阳线，收盘价={close}")
```

#### 1.3 字典迭代（便于访问字段）

```python
for bar in feed.iter_dicts():
    print(f"时间: {bar['timestamp']}")
    print(f"开盘: {bar['open']}")
    print(f"最高: {bar['high']}")
    print(f"最低: {bar['low']}")
    print(f"收盘: {bar['close']}")
    print(f"成交量: {bar['volume']}")
```

---

### 2. Backtrader集成

#### 2.1 完整回测示例

```python
import backtrader as bt
from datetime import datetime
from sdk.data_feed import BacktraderDataFeed

# 定义策略
class MyStrategy(bt.Strategy):
    def __init__(self):
        self.sma = bt.indicators.SimpleMovingAverage(self.data.close, period=20)
    
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
    interval='1h',
    chunk_size=50000  # 一次性加载所有数据
)

# 转换为backtrader格式
df = data_feed.to_backtrader_format()

# 创建backtrader数据源
bt_data = bt.feeds.PandasData(
    dataname=df,
    **data_feed.get_backtrader_params()
)

# 运行回测
cerebro = bt.Cerebro()
cerebro.adddata(bt_data)
cerebro.addstrategy(MyStrategy)
cerebro.broker.setcash(100000.0)
cerebro.run()
print(f'最终资产: {cerebro.broker.getvalue():.2f}')
```

#### 2.2 多品种回测

```python
# 添加多个数据源
symbols = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT']

for symbol in symbols:
    feed = BacktraderDataFeed(
        exchange='binance',
        symbol=symbol,
        start_time=datetime(2023, 1, 1),
        end_time=datetime(2024, 1, 1),
        interval='1h'
    )
    
    df = feed.to_backtrader_format()
    bt_data = bt.feeds.PandasData(dataname=df, **feed.get_backtrader_params())
    cerebro.adddata(bt_data)

cerebro.run()
```

---

### 3. 实时模拟

#### 3.1 实时策略测试

```python
import time
from sdk.data_feed import StreamingDataFeed
from datetime import datetime

# 创建流式数据源（10倍速）
feed = StreamingDataFeed(
    exchange='binance',
    symbol='BTC/USDT',
    start_time=datetime(2024, 1, 1),
    end_time=datetime(2024, 1, 2),
    interval='1m',
    playback_speed=10.0  # 10倍速播放
)

# 模拟实时处理
for bar in feed.stream():
    timestamp = bar['timestamp']
    close = bar['close']
    
    print(f"[{timestamp}] 当前价格: {close}")
    
    # 执行交易逻辑
    if close > 50000:
        print("  -> 触发卖出信号")
    elif close < 45000:
        print("  -> 触发买入信号")
    
    # stream()已经自动处理延迟，无需手动sleep
```

#### 3.2 自定义播放速度

```python
# 实时播放（1倍速）
feed_realtime = StreamingDataFeed(..., playback_speed=1.0)

# 快速回放（100倍速）
feed_fast = StreamingDataFeed(..., playback_speed=100.0)

# 极速回放（无延迟）
feed_instant = StreamingDataFeed(..., playback_speed=0)  # 或设置很大的值

# 手动控制延迟
for bar in feed_instant.iter_dicts():
    process(bar)
    time.sleep(feed_instant.get_sleep_time() * 0.5)  # 自定义延迟
```

---

## 高级特性

### 1. 统计信息获取

```python
feed = ChunkedDataFeed(...)

# 获取统计信息
stats = feed.get_stats()
print(stats)
# 输出:
# {
#     'exchange': 'binance',
#     'symbol': 'BTC/USDT',
#     'interval': '1h',
#     'start_time': '2023-01-01T00:00:00+00:00',
#     'end_time': '2024-01-01T00:00:00+00:00',
#     'chunk_size': 10000,
#     'chunks_loaded': 5,
#     'total_rows_loaded': 48000,
#     'is_exhausted': False
# }
```

### 2. 迭代器重置

```python
feed = ChunkedDataFeed(...)

# 第一次迭代
for chunk in feed:
    process(chunk)

# 重置后可以再次迭代
feed.reset()

# 第二次迭代
for chunk in feed:
    process_again(chunk)
```

### 3. 限制数据量

```python
# 只加载前100000行
df = feed.to_dataframe(max_rows=100000)

# 只处理前10个块
count = 0
for chunk in feed:
    process(chunk)
    count += 1
    if count >= 10:
        break
```

### 4. 自定义配置

```python
from config import Config, load_config

# 方式1: 使用默认配置
feed = ChunkedDataFeed(...)  # 自动加载config.yaml

# 方式2: 自定义配置
config = Config(
    data_dir='./custom_data',
    max_workers=8
)
feed = ChunkedDataFeed(..., config=config)

# 方式3: 从文件加载配置
config = load_config('custom_config.yaml')
feed = ChunkedDataFeed(..., config=config)
```

---

## 性能优化

### 1. 合理设置块大小

```python
# 小内存环境：使用较小的块
feed = ChunkedDataFeed(..., chunk_size=1000)

# 大内存环境：使用较大的块（减少I/O次数）
feed = ChunkedDataFeed(..., chunk_size=100000)

# 推荐值：
# - 1分钟数据: 10000-50000
# - 1小时数据: 5000-20000
# - 1天数据: 1000-5000
```

### 2. 预加载优化

```python
# 预加载多个块（减少等待时间）
feed = ChunkedDataFeed(
    ...,
    chunk_size=10000,
    preload_chunks=2  # 预加载2个块
)
```

### 3. 内存管理

```python
# 避免：一次性加载全部数据
df = feed.to_dataframe()  # ❌ 可能导致内存溢出

# 推荐：分块处理
for chunk in feed:  # ✅ 内存可控
    result = heavy_computation(chunk)
    save_result(result)
    del result  # 手动释放内存
```

### 4. 并行处理（多品种）

```python
from concurrent.futures import ThreadPoolExecutor

def process_symbol(symbol):
    feed = ChunkedDataFeed(
        exchange='binance',
        symbol=symbol,
        start_time=start,
        end_time=end,
        interval='1h'
    )
    
    results = []
    for chunk in feed:
        results.append(compute_indicators(chunk))
    return results

symbols = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT']

with ThreadPoolExecutor(max_workers=3) as executor:
    results = list(executor.map(process_symbol, symbols))
```

---

## 常见问题

### Q1: 如何处理缺失数据？

```python
for chunk in feed:
    # 检查是否有缺失值
    if chunk.isnull().any().any():
        print("发现缺失数据")
        # 填充缺失值
        chunk = chunk.fillna(method='ffill')
    
    process(chunk)
```

### Q2: 如何处理不同时区？

```python
from utils.timezone import to_utc
from datetime import datetime
import pytz

# 将本地时间转换为UTC
local_tz = pytz.timezone('Asia/Shanghai')
local_time = local_tz.localize(datetime(2023, 1, 1, 9, 0))
utc_time = to_utc(local_time)

feed = ChunkedDataFeed(
    ...,
    start_time=utc_time,  # 使用UTC时间
    end_time=...
)
```

### Q3: 如何验证数据完整性？

```python
feed = ChunkedDataFeed(...)

prev_timestamp = None
for chunk in feed:
    for _, row in chunk.iterrows():
        if prev_timestamp:
            # 检查时间是否连续
            expected_gap = get_timeframe_seconds(feed.interval)
            actual_gap = (row['timestamp'] - prev_timestamp).total_seconds()
            
            if actual_gap > expected_gap * 1.5:
                print(f"警告: 数据缺口 {actual_gap}秒")
        
        prev_timestamp = row['timestamp']
```

### Q4: 如何处理大时间范围？

```python
from datetime import datetime, timedelta

# 分段处理
start = datetime(2020, 1, 1)
end = datetime(2024, 1, 1)
segment_days = 90  # 每次处理90天

current_start = start
while current_start < end:
    current_end = min(current_start + timedelta(days=segment_days), end)
    
    feed = ChunkedDataFeed(
        exchange='binance',
        symbol='BTC/USDT',
        start_time=current_start,
        end_time=current_end,
        interval='1h'
    )
    
    for chunk in feed:
        process(chunk)
    
    current_start = current_end
```

### Q5: 如何导出数据？

```python
# 方式1: 导出为CSV
df = feed.to_dataframe(max_rows=50000)
df.to_csv('output.csv', index=False)

# 方式2: 分块导出
with open('output.csv', 'w') as f:
    is_first = True
    for chunk in feed:
        chunk.to_csv(f, index=False, header=is_first, mode='a')
        is_first = False

# 方式3: 导出为Parquet
df = feed.to_dataframe()
df.to_parquet('output.parquet', compression='snappy')
```

### Q6: 如何处理多个交易所？

```python
exchanges = ['binance', 'okx', 'huobi']

for exchange in exchanges:
    feed = ChunkedDataFeed(
        exchange=exchange,
        symbol='BTC/USDT',
        start_time=start,
        end_time=end,
        interval='1h'
    )
    
    print(f"\n处理 {exchange} 数据:")
    for chunk in feed:
        print(f"  加载 {len(chunk)} 根K线")
        process(chunk)
```

---

## 完整示例

### 示例1: 简单均线策略回测

```python
from sdk.data_feed import ChunkedDataFeed
from datetime import datetime
import pandas as pd

def simple_ma_strategy(feed):
    """简单均线交叉策略"""
    position = 0  # 0: 空仓, 1: 持仓
    cash = 100000.0
    shares = 0
    
    for chunk in feed:
        # 计算均线
        chunk['ma5'] = chunk['close'].rolling(5).mean()
        chunk['ma20'] = chunk['close'].rolling(20).mean()
        
        for _, row in chunk.iterrows():
            if pd.isna(row['ma5']) or pd.isna(row['ma20']):
                continue
            
            # 金叉买入
            if position == 0 and row['ma5'] > row['ma20']:
                shares = cash / row['close']
                cash = 0
                position = 1
                print(f"[{row['timestamp']}] 买入 @{row['close']:.2f}")
            
            # 死叉卖出
            elif position == 1 and row['ma5'] < row['ma20']:
                cash = shares * row['close']
                shares = 0
                position = 0
                print(f"[{row['timestamp']}] 卖出 @{row['close']:.2f}")
    
    # 计算最终收益
    final_value = cash if position == 0 else shares * chunk.iloc[-1]['close']
    profit_pct = (final_value - 100000) / 100000 * 100
    
    print(f"\n最终资产: {final_value:.2f}")
    print(f"收益率: {profit_pct:.2f}%")

# 运行策略
feed = ChunkedDataFeed(
    exchange='binance',
    symbol='BTC/USDT',
    start_time=datetime(2023, 1, 1),
    end_time=datetime(2024, 1, 1),
    interval='1h',
    chunk_size=10000
)

simple_ma_strategy(feed)
```

### 示例2: 多品种监控

```python
from sdk.data_feed import StreamingDataFeed
from datetime import datetime

def monitor_multiple_symbols():
    """监控多个交易对"""
    symbols = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT']
    feeds = {}
    
    # 创建多个流式数据源
    for symbol in symbols:
        feeds[symbol] = StreamingDataFeed(
            exchange='binance',
            symbol=symbol,
            start_time=datetime(2024, 1, 1),
            end_time=datetime(2024, 1, 1, 12),  # 12小时数据
            interval='5m',
            playback_speed=60  # 60倍速
        )
    
    # 同步迭代所有数据流（简化版）
    for symbol in symbols:
        print(f"\n开始监控 {symbol}:")
        for bar in feeds[symbol].stream():
            print(f"  [{bar['timestamp']}] {symbol}: {bar['close']:.2f}")

monitor_multiple_symbols()
```

---

## 支持的时间周期

| 周期代码 | 说明 | 适用场景 |
|---------|------|---------|
| `1m` | 1分钟 | 高频交易、短线策略 |
| `5m` | 5分钟 | 日内交易 |
| `15m` | 15分钟 | 日内交易 |
| `30m` | 30分钟 | 日内/短线交易 |
| `1h` | 1小时 | 短线/中线策略 |
| `4h` | 4小时 | 中线策略 |
| `1d` | 1天 | 中长线策略 |
| `1w` | 1周 | 长线策略 |

---

## 支持的交易所

- Binance (`binance`)
- OKX (`okx`)
- Huobi (`huobi`)
- Bybit (`bybit`)
- 更多交易所持续添加中...

---

## 注意事项

1. **内存使用**：对于大数据集，建议使用块级迭代而不是`to_dataframe()`
2. **时区处理**：所有时间统一使用UTC时区
3. **数据完整性**：使用前建议先检查数据是否完整
4. **性能优化**：合理设置`chunk_size`以平衡内存和性能
5. **并发访问**：同一个feed对象不支持并发迭代

---

## 更新日志

- **v1.0.0** (2024-01-01)
  - 初始版本发布
  - 支持ChunkedDataFeed、BacktraderDataFeed、StreamingDataFeed
  - 支持多种迭代方式
  - Backtrader框架集成

---

## 许可证

本SDK遵循项目主许可证。

## 技术支持

如遇问题，请查阅项目README或提交Issue。
