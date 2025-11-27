# 数据流使用指南

## 概述

数据流（Data Feed）提供内存高效的K线数据迭代功能，特别适合：
- 大规模回测（避免一次性加载全部数据到内存）
- 实时策略测试
- Backtrader等回测框架集成

**核心特性**：
- ✅ 分块加载，内存高效
- ✅ **自动下载缺失数据**（新功能！）
- ✅ 多种迭代方式（块、行、字典）
- ✅ 支持多种回测框架

## 快速开始

### 基本用法

```python
from sdk import KlineClient
from datetime import datetime

client = KlineClient()

# 创建数据流
feed = client.create_data_feed(
    exchange='binance',
    symbol='BTC/USDT',
    start_time=datetime(2020, 1, 1),
    end_time=datetime(2024, 1, 1),
    interval='1h',
    chunk_size=10000  # 每次加载10000条
)

# 迭代数据块
for chunk in feed:
    print(f"Processing {len(chunk)} bars")
    # 处理数据块
    process_chunk(chunk)
```

## 数据流类型

### 1. ChunkedDataFeed - 分块数据流

内存高效的分块迭代器，适合处理大数据集。

```python
from sdk import KlineClient

client = KlineClient()

feed = client.create_data_feed(
    exchange='binance',
    symbol='BTC/USDT',
    start_time=datetime(2020, 1, 1),
    end_time=datetime(2024, 1, 1),
    interval='1h',
    chunk_size=10000
)

# 方式1: 迭代数据块（推荐）
for chunk_df in feed:
    # chunk_df是pandas DataFrame
    print(f"Chunk shape: {chunk_df.shape}")
    print(f"Columns: {chunk_df.columns.tolist()}")
    
# 方式2: 逐行迭代
for timestamp, open_price, high, low, close, volume in feed.iter_rows():
    # 处理每根K线
    execute_strategy(timestamp, open_price, high, low, close, volume)

# 方式3: 字典格式迭代
for bar in feed.iter_dicts():
    print(f"Time: {bar['timestamp']}, Close: {bar['close']}")
    
# 方式4: 转换为完整DataFrame（注意内存！）
df = feed.to_dataframe(max_rows=100000)
```

### 2. BacktraderDataFeed - Backtrader集成

与Backtrader完美集成的数据流。

```python
import backtrader as bt
from sdk import KlineClient
from datetime import datetime

client = KlineClient()

# 创建Backtrader数据流
feed = client.create_backtrader_feed(
    exchange='binance',
    symbol='BTC/USDT',
    start_time=datetime(2023, 1, 1),
    end_time=datetime(2024, 1, 1),
    interval='1h'
)

# 转换为Backtrader格式
bt_data = bt.feeds.PandasData(
    dataname=feed.to_backtrader_format(),
    **feed.get_backtrader_params()
)

# 添加到Cerebro
cerebro = bt.Cerebro()
cerebro.adddata(bt_data)
cerebro.addstrategy(MyStrategy)
cerebro.run()
```

### 3. StreamingDataFeed - 实时模拟

模拟实时数据流，用于实时策略测试。

```python
from sdk import KlineClient

client = KlineClient()

# 创建流式数据源
feed = client.create_streaming_feed(
    exchange='binance',
    symbol='BTC/USDT',
    start_time=datetime(2024, 1, 1),
    end_time=datetime(2024, 1, 2),
    interval='1m',
    playback_speed=100  # 100倍速播放
)

# 实时流式处理
for bar in feed.stream():
    print(f"New bar at {bar['timestamp']}: Close={bar['close']}")
    
    # 执行交易逻辑
    if should_buy(bar):
        execute_buy_order()
    
    # 自动延迟（根据playback_speed）
    # 无需手动sleep
```

## 核心特性详解

### 自动下载（重要！）

**与旧版的区别**：

```python
# 旧版（问题）：如果数据不存在，返回空结果
from sdk.data_feed import ChunkedDataFeed  # 已废弃
feed = ChunkedDataFeed(...)
for chunk in feed:
    print(len(chunk))  # 可能为0

# 新版（解决）：自动下载缺失数据
from sdk import KlineClient
client = KlineClient()
feed = client.create_data_feed(...)
for chunk in feed:
    print(len(chunk))  # 保证有数据（如果交易所支持）
```

**工作原理**：

数据流内部使用`QueryClient`，通过`DataFetcher`智能获取数据：

```
数据流请求 -> QueryClient -> DataFetcher
    ├─ 检查本地是否有数据
    ├─ 本地没有 -> 自动从交易所下载
    └─ 返回数据给数据流
```

### 内存管理

数据流使用分块加载策略，避免内存溢出：

```python
# ✅ 好：分块处理4年的1分钟数据
feed = client.create_data_feed(
    exchange='binance',
    symbol='BTC/USDT',
    start_time=datetime(2020, 1, 1),
    end_time=datetime(2024, 1, 1),
    interval='1m',
    chunk_size=10000  # 每次只加载10000条到内存
)

for chunk in feed:
    # 处理完自动释放
    process_chunk(chunk)

# ❌ 差：一次性加载全部数据（可能几百万条）
df = client.get_kline(
    exchange='binance',
    symbol='BTC/USDT',
    start_time=datetime(2020, 1, 1),
    end_time=datetime(2024, 1, 1),
    interval='1m'
)  # 可能内存溢出
```

### 预加载优化

数据流支持预加载下一个块，提高性能：

```python
feed = client.create_data_feed(
    exchange='binance',
    symbol='BTC/USDT',
    start_time=datetime(2020, 1, 1),
    end_time=datetime(2024, 1, 1),
    interval='1h',
    chunk_size=10000,
    preload_chunks=2  # 预加载2个块
)

# 第一次迭代时，已经预加载了下一个块
for chunk in feed:
    process_chunk(chunk)  # 处理时，后台加载下一块
```

## 完整示例

### 示例1: 简单回测

```python
from sdk import KlineClient
from datetime import datetime

client = KlineClient()

# 创建数据流
feed = client.create_data_feed(
    exchange='binance',
    symbol='BTC/USDT',
    start_time=datetime(2023, 1, 1),
    end_time=datetime(2024, 1, 1),
    interval='1h',
    chunk_size=1000
)

# 简单均线策略
position = 0
portfolio_value = 100000

for chunk in feed:
    # 计算指标
    chunk['MA_20'] = chunk['close'].rolling(20).mean()
    chunk['MA_50'] = chunk['close'].rolling(50).mean()
    
    # 遍历每根K线
    for _, bar in chunk.iterrows():
        if pd.notna(bar['MA_20']) and pd.notna(bar['MA_50']):
            # 金叉买入
            if bar['MA_20'] > bar['MA_50'] and position == 0:
                position = portfolio_value / bar['close']
                portfolio_value = 0
                print(f"Buy at {bar['close']}")
            
            # 死叉卖出
            elif bar['MA_20'] < bar['MA_50'] and position > 0:
                portfolio_value = position * bar['close']
                position = 0
                print(f"Sell at {bar['close']}")

print(f"Final portfolio value: {portfolio_value}")
```

### 示例2: Backtrader策略

```python
import backtrader as bt
from sdk import KlineClient
from datetime import datetime

# 定义策略
class MovingAverageStrategy(bt.Strategy):
    params = (
        ('fast_period', 20),
        ('slow_period', 50),
    )
    
    def __init__(self):
        self.fast_ma = bt.indicators.SMA(
            self.data.close, 
            period=self.params.fast_period
        )
        self.slow_ma = bt.indicators.SMA(
            self.data.close, 
            period=self.params.slow_period
        )
        self.crossover = bt.indicators.CrossOver(self.fast_ma, self.slow_ma)
    
    def next(self):
        if self.crossover > 0:  # 金叉
            if not self.position:
                self.buy()
        elif self.crossover < 0:  # 死叉
            if self.position:
                self.sell()

# 创建数据流
client = KlineClient()
feed = client.create_backtrader_feed(
    exchange='binance',
    symbol='BTC/USDT',
    start_time=datetime(2023, 1, 1),
    end_time=datetime(2024, 1, 1),
    interval='1h'
)

# 设置Backtrader
cerebro = bt.Cerebro()
cerebro.adddata(bt.feeds.PandasData(
    dataname=feed.to_backtrader_format(),
    **feed.get_backtrader_params()
))
cerebro.addstrategy(MovingAverageStrategy)
cerebro.broker.setcash(100000)
cerebro.broker.setcommission(commission=0.001)

# 运行回测
print(f"Starting Portfolio Value: {cerebro.broker.getvalue()}")
cerebro.run()
print(f"Final Portfolio Value: {cerebro.broker.getvalue()}")
```

### 示例3: 实时模拟交易

```python
from sdk import KlineClient
from datetime import datetime
import time

client = KlineClient()

# 创建实时模拟流
feed = client.create_streaming_feed(
    exchange='binance',
    symbol='BTC/USDT',
    start_time=datetime(2024, 1, 1),
    end_time=datetime(2024, 1, 2),
    interval='1m',
    playback_speed=60  # 60倍速（1分钟K线变1秒）
)

# 实时策略
position = 0
last_prices = []

for bar in feed.stream():
    current_price = bar['close']
    last_prices.append(current_price)
    
    # 保持最近20个价格
    if len(last_prices) > 20:
        last_prices.pop(0)
    
    # 计算简单移动平均
    if len(last_prices) >= 20:
        ma_20 = sum(last_prices) / len(last_prices)
        
        # 价格突破MA买入
        if current_price > ma_20 * 1.01 and position == 0:
            position = 1
            print(f"[{bar['timestamp']}] Buy at {current_price}")
        
        # 价格跌破MA卖出
        elif current_price < ma_20 * 0.99 and position > 0:
            position = 0
            print(f"[{bar['timestamp']}] Sell at {current_price}")
    
    # feed.stream()会自动处理延迟
```

### 示例4: 多周期分析

```python
from sdk import KlineClient
from datetime import datetime

client = KlineClient()

# 创建多个周期的数据流
feeds = {
    '1h': client.create_data_feed(
        'binance', 'BTC/USDT',
        datetime(2024, 1, 1), datetime(2024, 1, 2),
        '1h', chunk_size=100
    ),
    '4h': client.create_data_feed(
        'binance', 'BTC/USDT',
        datetime(2024, 1, 1), datetime(2024, 1, 2),
        '4h', chunk_size=100
    ),
}

# 分析不同周期
for interval, feed in feeds.items():
    print(f"\n=== {interval} 周期分析 ===")
    
    total_bars = 0
    for chunk in feed:
        total_bars += len(chunk)
        
        # 计算统计信息
        avg_volume = chunk['volume'].mean()
        price_range = chunk['high'].max() - chunk['low'].min()
        
        print(f"Chunk: {len(chunk)} bars, "
              f"Avg Volume: {avg_volume:.2f}, "
              f"Price Range: {price_range:.2f}")
    
    print(f"Total {total_bars} bars processed")
```

## 高级功能

### 数据流状态管理

```python
feed = client.create_data_feed(...)

# 获取统计信息
stats = feed.get_stats()
print(f"已加载块数: {stats['chunks_loaded']}")
print(f"已加载行数: {stats['total_rows_loaded']}")
print(f"是否耗尽: {stats['is_exhausted']}")

# 重置数据流
feed.reset()  # 回到起始位置

# 再次迭代
for chunk in feed:
    process_chunk(chunk)
```

### 自定义迭代逻辑

```python
feed = client.create_data_feed(...)

# 自定义处理
def custom_processor(chunk):
    # 添加自定义列
    chunk['custom_indicator'] = (chunk['high'] + chunk['low']) / 2
    return chunk

for chunk in feed:
    processed_chunk = custom_processor(chunk)
    # 使用处理后的数据
    analyze(processed_chunk)
```

### 错误处理

```python
feed = client.create_data_feed(...)

try:
    for chunk in feed:
        if chunk.empty:
            print("Warning: Empty chunk")
            continue
        
        process_chunk(chunk)
        
except Exception as e:
    print(f"Error processing feed: {e}")
    
    # 获取当前状态
    stats = feed.get_stats()
    print(f"Progress: {stats['total_rows_loaded']} rows loaded")
```

## 性能优化建议

### 1. 合理设置块大小

```python
# 小数据集（几个月）
feed = client.create_data_feed(..., chunk_size=1000)

# 中等数据集（1-2年）
feed = client.create_data_feed(..., chunk_size=10000)

# 大数据集（3年以上）
feed = client.create_data_feed(..., chunk_size=50000)
```

### 2. 使用预加载

```python
# 启用预加载提高性能
feed = client.create_data_feed(
    ...,
    preload_chunks=2  # 预加载2个块
)
```

### 3. 选择合适的迭代方式

```python
# 需要DataFrame完整功能 -> 块迭代
for chunk in feed:
    chunk['indicator'] = chunk['close'].rolling(20).mean()

# 只需要OHLCV数据 -> 行迭代（更快）
for timestamp, o, h, l, c, v in feed.iter_rows():
    simple_strategy(o, h, l, c, v)

# 需要字典格式 -> 字典迭代
for bar in feed.iter_dicts():
    process_dict(bar)
```

## 与直接查询的对比

### 数据流 vs 直接查询

| 特性 | 数据流 | 直接查询 |
|------|--------|----------|
| 内存占用 | 低（分块加载） | 高（一次性加载） |
| 适用场景 | 大数据集、回测 | 小数据集、分析 |
| 性能 | 首次较慢，整体快 | 一次性较快 |
| 灵活性 | 流式处理 | 随机访问 |

**何时使用数据流**：
- ✅ 处理超过1年的1分钟数据
- ✅ 回测系统集成
- ✅ 实时策略模拟
- ✅ 内存受限环境

**何时使用直接查询**：
- ✅ 数据量小（<100MB）
- ✅ 需要随机访问数据
- ✅ 一次性数据分析
- ✅ 交互式探索

## 故障排除

### 问题1: 数据流返回空数据

**原因**: 时间范围内没有数据

**解决**:
```python
feed = client.create_data_feed(...)

# 检查是否有数据
first_chunk = next(iter(feed), None)
if first_chunk is None or first_chunk.empty:
    print("No data in this time range")
else:
    print(f"Found {len(first_chunk)} bars")
```

### 问题2: 内存仍然不足

**解决**: 减小块大小
```python
# 从
feed = client.create_data_feed(..., chunk_size=10000)

# 改为
feed = client.create_data_feed(..., chunk_size=1000)
```

### 问题3: 数据流太慢

**解决**: 增加预加载
```python
feed = client.create_data_feed(
    ...,
    chunk_size=10000,
    preload_chunks=3  # 增加预加载
)
```

## 常见问题

**Q: 数据流会自动下载数据吗？**  
A: 是的！新版数据流使用QueryClient，会自动下载缺失数据。

**Q: 如何禁用自动下载？**  
A: 直接实例化数据流类，不通过client：
```python
from sdk.query import ChunkedDataFeed
feed = ChunkedDataFeed(..., config=config)
# 然后设置auto_strategy=False
```

**Q: 数据流可以重复使用吗？**  
A: 可以，使用`feed.reset()`重置到起始位置。

**Q: 如何获取数据流的进度？**  
A: 使用`feed.get_stats()`查看已加载行数和块数。

**Q: Backtrader数据流支持实时数据吗？**  
A: 当前版本仅支持历史数据回测。实时数据正在开发中。

## 相关文档

- [SDK使用文档](../sdk/README.md) - SDK完整文档
- [快速参考](SDK_QUICK_REFERENCE.md) - API快速参考
- [迁移指南](SDK_REFACTORING_GUIDE.md) - 从旧版迁移

## 下一步

- 尝试不同的数据流类型
- 集成到你的回测系统
- 根据数据量调整块大小
- 探索实时模拟功能
