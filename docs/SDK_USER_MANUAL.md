# K线数据SDK使用手册

## 📖 目录

- [快速开始](#快速开始)
- [安装说明](#安装说明)
- [核心概念](#核心概念)
- [API参考](#api参考)
- [使用示例](#使用示例)
- [配置说明](#配置说明)
- [最佳实践](#最佳实践)
- [常见问题](#常见问题)
- [附录](#附录)

---

## 快速开始

### 5分钟上手

```python
from kline_data.sdk import KlineClient
from datetime import datetime

# 1. 创建客户端
client = KlineClient()

# 2. 查询K线数据
df = client.get_kline(
    exchange='binance',
    symbol='BTC/USDT',
    start_time=datetime(2024, 1, 1),
    end_time=datetime(2024, 1, 2),
    interval='1h'
)

# 3. 查看数据
print(df.head())
```

### 输出示例

```
                     open     high      low    close  volume
timestamp
2024-01-01 00:00:00  42000.5  42150.2  41900.0  42100.0  1234.5
2024-01-01 01:00:00  42100.0  42200.0  42050.0  42180.0  1156.2
...
```

---

## 安装说明

### 环境要求

- Python 3.10 或更高版本
- 操作系统：Linux、macOS、Windows

### 安装步骤

#### 1. 使用 pip 安装（推荐）

```bash
pip install kline-data
```

#### 2. 从源码安装

```bash
# 克隆仓库
git clone https://github.com/your-org/kline_data.git
cd kline_data

# 安装依赖
pip install -r requirements.txt

# 安装项目
pip install -e .
```

#### 3. 安装 TA-Lib（可选，用于技术指标）

**macOS:**
```bash
brew install ta-lib
pip install ta-lib
```

**Linux:**
```bash
wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz
tar -xzf ta-lib-0.4.0-src.tar.gz
cd ta-lib/
./configure --prefix=/usr
make
sudo make install
pip install ta-lib
```

**Windows:**
下载预编译的 wheel 文件：
```bash
pip install https://github.com/cgohlke/talib-build/releases/download/v0.4.28/TA_Lib-0.4.28-cp310-cp310-win_amd64.whl
```

### 验证安装

```bash
# 查看 Python 环境
python -c "import kline_data; print(kline_data.__version__)"

# 使用 CLI 工具
kline version
```

---

## 核心概念

### SDK 架构

```
┌─────────────────────────────────────┐
│         KlineClient (统一入口)       │
│  ┌──────────┬──────────┬──────────┐ │
│  │  Query   │Download  │Indicator │ │
│  │  Client  │  Client  │  Client  │ │
│  └────┬─────┴────┬─────┴────┬─────┘ │
└───────┼──────────┼──────────┼────────┘
        │          │          │
    ┌───▼───┐ ┌──▼────┐ ┌──▼──────┐
    │Query  │ │Down-  │ │Technical│
    │Engine │ │loader │ │Indicators│
    └───────┘ └───────┘ └─────────┘
```

### 数据存储格式

- **格式**: Apache Parquet（列式存储）
- **优势**:
  - 高压缩比（节省 80% 空间）
  - 快速查询（列读取优化）
  - 类型安全（保持数据类型）
  - 跨平台兼容

### 支持的交易所

- Binance（币安）
- OKX（欧易）
- Bybit
- Coinbase
- Kraken
- Huobi（火币）
- KuCoin
- Gate.io
- 所有 CCXT 支持的交易所

### 支持的时间周期

```python
# 秒级：1s, 5s, 10s, 15s, 30s
# 分钟级：1m, 3m, 5m, 15m, 30m
# 小时级：1h, 2h, 4h, 6h, 8h, 12h
# 天级：1d, 3d
# 周级：1w
# 月级：1M
```

---

## API参考

### KlineClient - 统一客户端

#### 初始化

```python
from kline_data.sdk import KlineClient

# 使用默认配置
client = KlineClient()

# 自定义配置
client = KlineClient(config_path='/path/to/config.yaml')
```

#### 数据查询

##### get_kline()

查询指定时间范围的K线数据。

```python
def get_kline(
    exchange: str,          # 交易所名称
    symbol: str,            # 交易对，如 'BTC/USDT'
    start_time: datetime,   # 开始时间
    end_time: datetime,     # 结束时间
    interval: str = '1h',   # 时间周期
    with_indicators: List[str] = None,  # 计算技术指标
    limit: int = None       # 限制返回数量
) -> pd.DataFrame:
    """
    返回包含以下列的 DataFrame：
    - open: 开盘价
    - high: 最高价
    - low: 最低价
    - close: 收盘价
    - volume: 成交量
    """
```

**示例：**

```python
from kline_data.sdk import KlineClient
from datetime import datetime

client = KlineClient()

# 基本查询
df = client.get_kline(
    exchange='binance',
    symbol='BTC/USDT',
    start_time=datetime(2024, 1, 1),
    end_time=datetime(2024, 1, 31),
    interval='1h'
)

# 查询并计算指标
df = client.get_kline(
    exchange='binance',
    symbol='ETH/USDT',
    start_time=datetime(2024, 1, 1),
    end_time=datetime(2024, 1, 2),
    interval='1h',
    with_indicators=['MA_20', 'RSI_14', 'MACD']
)

print(df[['close', 'MA_20', 'RSI_14']].tail())
```

##### get_latest()

获取最新的K线数据。

```python
def get_latest(
    exchange: str,
    symbol: str,
    interval: str = '1h',
    bars: int = 100,
    with_indicators: List[str] = None
) -> pd.DataFrame:
    """获取最近的N根K线"""
```

**示例：**

```python
# 获取最新的100根1小时K线
df = client.get_latest(
    exchange='binance',
    symbol='BTC/USDT',
    interval='1h',
    bars=100
)
```

##### get_klines_before()

获取指定时间之前的K线数据。

```python
def get_klines_before(
    exchange: str,
    symbol: str,
    before_time: datetime,
    interval: str = '1h',
    bars: int = 100
) -> pd.DataFrame:
    """获取指定时间之前的N根K线"""
```

#### 数据下载

##### download_kline()

下载K线数据到本地。

```python
def download_kline(
    exchange: str,
    symbol: str,
    start_time: datetime,
    end_time: datetime,
    interval: str = '1h',
    progress_callback: Callable = None,
    overwrite: bool = False
) -> DownloadResult:
    """
    下载K线数据

    参数：
        progress_callback: 进度回调函数
            callback(progress: float, downloaded: int, total: int)
        overwrite: 是否覆盖已有数据

    返回：
        DownloadResult(
            success=True,
            downloaded=1000,
            failed=0,
            duration=timedelta(seconds=30)
        )
    """
```

**示例：**

```python
from datetime import datetime

# 简单下载
result = client.download_kline(
    exchange='binance',
    symbol='BTC/USDT',
    start_time=datetime(2023, 1, 1),
    end_time=datetime(2024, 1, 1),
    interval='1h'
)
print(f"下载了 {result.downloaded} 条数据")

# 带进度回调
def progress_callback(progress, downloaded, total):
    print(f"进度: {progress:.1f}% - 已下载: {downloaded}/{total}")

result = client.download_kline(
    exchange='binance',
    symbol='ETH/USDT',
    start_time=datetime(2023, 1, 1),
    end_time=datetime(2024, 1, 1),
    interval='1h',
    progress_callback=progress_callback
)
```

##### update_kline()

更新K线数据（增量更新）。

```python
def update_kline(
    exchange: str,
    symbol: str,
    interval: str = '1h'
) -> DownloadResult:
    """更新到最新的数据"""
```

**示例：**

```python
# 更新到最新
result = client.update_kline(
    exchange='binance',
    symbol='BTC/USDT',
    interval='1h'
)
print(f"新增 {result.downloaded} 条数据")
```

#### 数据流处理

##### create_data_feed()

创建数据流，用于分块处理大量数据。

```python
def create_data_feed(
    exchange: str,
    symbol: str,
    start_time: datetime,
    end_time: datetime,
    interval: str = '1h',
    chunk_size: str = '1M'  # 每块大小：'1M'=100万条
) -> Iterator[pd.DataFrame]:
    """
    返回数据流迭代器

    chunk_size 格式：
    - '10K' = 10,000 条
    - '1M' = 1,000,000 条
    - '10M' = 10,000,000 条
    """
```

**示例：**

```python
# 处理大量数据
feed = client.create_data_feed(
    exchange='binance',
    symbol='BTC/USDT',
    start_time=datetime(2020, 1, 1),
    end_time=datetime(2024, 1, 1),
    interval='1m',
    chunk_size='1M'
)

for i, chunk in enumerate(feed):
    print(f"处理第 {i+1} 块数据，共 {len(chunk)} 条")
    # 处理数据...
    process_chunk(chunk)
```

#### 技术指标

##### calculate_indicators()

计算技术指标。

```python
def calculate_indicators(
    df: pd.DataFrame,
    indicators: List[str],
    *,  # 关键字参数
    prepend: bool = False
) -> pd.DataFrame:
    """
    计算技术指标并添加到 DataFrame

    参数：
        prepend: 是否将指标列插入到价格列之后
                 默认 False（添加到最后）

    支持的指标：
    - 趋势：MA_20, EMA_12, WMA_30, DEMA, TEMA, HMA
    - 动量：RSI_14, MACD, STOCH, CCI, Williams %R
    - 波动率：ATR_14, Bollinger_Bands, Keltner
    - 成交量：OBV, VWAP, MFI, AD
    - 自定义：{'MA': {'timeperiod': 20, 'price': 'close'}}
    """
```

**示例：**

```python
# 基本指标计算
df = client.get_kline(
    exchange='binance',
    symbol='BTC/USDT',
    start_time=datetime(2024, 1, 1),
    end_time=datetime(2024, 1, 31),
    interval='1h'
)

# 添加指标
df_with_indicators = client.calculate_indicators(
    df,
    indicators=['MA_20', 'RSI_14', 'MACD', 'ATR_14'],
    prepend=True  # 指标列插入到价格列之后
)

print(df_with_indicators.columns)
# Index(['open', 'high', 'low', 'close', 'volume',
#         'MA_20', 'RSI_14', 'MACD', 'MACD_signal', 'MACD_hist', 'ATR_14'])
```

**支持的指标列表：**

```python
# 移动平均线
indicators = [
    'MA_20',      # 简单移动平均
    'EMA_12',     # 指数移动平均
    'WMA_30',     # 加权移动平均
    'DEMA',       # 双指数移动平均
    'TEMA',       # 三指数移动平均
    'HMA',        # Hull移动平均
    'VWAP'        # 成交量加权平均价
]

# 动量指标
indicators = [
    'RSI_14',           # 相对强弱指标
    'MACD',             # MACD（含信号线、柱状图）
    'STOCH',            # 随机振荡器
    'STOCHRSI',         # RSI随机
    'CCI_14',           # 商品通道指标
    'Williams_%R',      # 威廉指标
    'MOM'               # 动量
]

# 波动率指标
indicators = [
    'ATR_14',           # 平均真实波幅
    'Bollinger_Bands',  # 布林带（上、中、下轨）
    'Keltner',          # 肯特纳通道
    'Donchian'          # 唐奇安通道
]

# 成交量指标
indicators = [
    'OBV',              # 能量潮
    'MFI_14',           # 资金流量指标
    'AD',               # 累积/派发线
    'ADOSC',            # Chaikin振荡器
    'VWAP'              # 成交量加权平均价
]
```

#### 元数据查询

##### get_metadata()

获取交易对元数据。

```python
def get_metadata(
    exchange: str,
    symbol: str = None
) -> Union[Dict, List[str]]:
    """
    获取元数据

    返回：
    - symbol=None: 返回所有交易对列表
    - symbol='BTC/USDT': 返回该交易对的详细信息
    """
```

**示例：**

```python
# 列出所有交易对
symbols = client.get_metadata(exchange='binance')
print(f"共 {len(symbols)} 个交易对")

# 获取特定交易对信息
info = client.get_metadata(exchange='binance', symbol='BTC/USDT')
print(f"交易对信息: {info}")
# {'base': 'BTC', 'quote': 'USDT', 'type': 'spot', 'active': True}
```

##### list_symbols()

列出可用的交易对。

```python
def list_symbols(
    exchange: str,
    quote: str = None     # 过滤计价货币，如 'USDT'
) -> List[str]:
    """列出交易对"""
```

**示例：**

```python
# 所有USDT交易对
usdt_pairs = client.list_symbols(exchange='binance', quote='USDT')
print(usdt_pairs[:10])
# ['BTC/USDT', 'ETH/USDT', 'BNB/USDT', ...]
```

---

## 使用示例

### 示例1：基本数据查询

```python
from kline_data.sdk import KlineClient
from datetime import datetime

client = KlineClient()

# 查询最近的日K线数据
df = client.get_kline(
    exchange='binance',
    symbol='BTC/USDT',
    start_time=datetime(2024, 1, 1),
    end_time=datetime(2024, 12, 31),
    interval='1d'
)

# 计算基本统计
print(f"平均价格: {df['close'].mean():.2f}")
print(f"最高价格: {df['high'].max():.2f}")
print(f"最低价格: {df['low'].min():.2f}")
print(f"总成交量: {df['volume'].sum():.2f}")
```

### 示例2：技术分析策略

```python
from kline_data.sdk import KlineClient
from datetime import datetime

client = KlineClient()

# 获取数据并计算指标
df = client.get_kline(
    exchange='binance',
    symbol='BTC/USDT',
    start_time=datetime(2024, 1, 1),
    end_time=datetime(2024, 1, 31),
    interval='4h',
    with_indicators=['MA_20', 'MA_50', 'RSI_14', 'MACD', 'ATR_14']
)

# 生成交易信号
df['signal'] = 0

# 金叉死叉策略
df.loc[df['MA_20'] > df['MA_50'], 'signal'] = 1   # 金叉买入
df.loc[df['MA_20'] < df['MA_50'], 'signal'] = -1  # 死叉卖出

# RSI过滤
df.loc[(df['signal'] == 1) & (df['RSI_14'] > 70), 'signal'] = 0  # 超买不买
df.loc[(df['signal'] == -1) & (df['RSI_14'] < 30), 'signal'] = 0 # 超卖不卖

# 显示信号
signals = df[df['signal'] != 0]
print(f"共发现 {len(signals)} 个交易信号")
print(signals[['close', 'MA_20', 'MA_50', 'RSI_14', 'signal']].head())
```

### 示例3：批量下载多个交易对

```python
from kline_data.sdk import KlineClient
from datetime import datetime
import time

client = KlineClient()

symbols = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'XRP/USDT']

for symbol in symbols:
    print(f"\n开始下载 {symbol}...")

    result = client.download_kline(
        exchange='binance',
        symbol=symbol,
        start_time=datetime(2023, 1, 1),
        end_time=datetime(2024, 1, 1),
        interval='1h',
        progress_callback=lambda p, d, t: print(f"  进度: {p:.1f}%")
    )

    print(f"完成: {symbol} - 下载 {result.downloaded} 条数据")
    time.sleep(1)  # 避免请求过快
```

### 示例4：数据回测系统

```python
from kline_data.sdk import KlineClient
from datetime import datetime, timedelta
import pandas as pd

client = KlineClient()

# 获取训练数据
train_data = client.get_kline(
    exchange='binance',
    symbol='BTC/USDT',
    start_time=datetime(2023, 1, 1),
    end_time=datetime(2023, 12, 31),
    interval='1h',
    with_indicators=['MA_20', 'RSI_14', 'MACD']
)

# 获取测试数据
test_data = client.get_kline(
    exchange='binance',
    symbol='BTC/USDT',
    start_time=datetime(2024, 1, 1),
    end_time=datetime(2024, 1, 31),
    interval='1h',
    with_indicators=['MA_20', 'RSI_14', 'MACD']
)

# 简单的回测函数
def backtest(data, initial_capital=10000):
    capital = initial_capital
    position = 0
    trades = []

    for i in range(1, len(data)):
        prev_row = data.iloc[i-1]
        curr_row = data.iloc[i]

        # 买入信号：MA金叉且RSI不超买
        if (prev_row['MA_20'] <= prev_row['MA_50'] and
            curr_row['MA_20'] > curr_row['MA_50'] and
            curr_row['RSI_14'] < 70):
            if capital > 0:
                position = capital / curr_row['close']
                capital = 0
                trades.append(('buy', i, curr_row['close']))

        # 卖出信号：MA死叉且RSI不超卖
        elif (prev_row['MA_20'] >= prev_row['MA_50'] and
              curr_row['MA_20'] < curr_row['MA_50'] and
              curr_row['RSI_14'] > 30):
            if position > 0:
                capital = position * curr_row['close']
                trades.append(('sell', i, curr_row['close']))

    # 最终价值
    final_value = capital + position * data.iloc[-1]['close']
    return {
        'initial_capital': initial_capital,
        'final_value': final_value,
        'return': (final_value - initial_capital) / initial_capital,
        'trades': trades
    }

# 执行回测
result = backtest(train_data)
print(f"初始资金: ${result['initial_capital']:.2f}")
print(f"最终价值: ${result['final_value']:.2f}")
print(f"收益率: {result['return']*100:.2f}%")
print(f"交易次数: {len(result['trades'])}")
```

### 示例5：多交易所套利监控

```python
from kline_data.sdk import KlineClient
from datetime import datetime, timedelta

client = KlineClient()

# 获取多个交易所的同一交易对价格
exchanges = ['binance', 'okx', 'bybit']
symbol = 'BTC/USDT'

prices = {}
for exchange in exchanges:
    df = client.get_latest(
        exchange=exchange,
        symbol=symbol,
        interval='1m',
        bars=1
    )
    prices[exchange] = df.iloc[-1]['close']

# 计算价差
print("BTC/USDT 价格对比:")
print("-" * 50)
max_price = max(prices.values())
min_price = min(prices.values())

for exchange, price in prices.items():
    diff_from_min = ((price - min_price) / min_price) * 100
    diff_from_max = ((max_price - price) / max_price) * 100
    print(f"{exchange:15s}: ${price:10.2f}  (与最低价差: {diff_from_min:+.2f}%)")

# 计算套利空间
arbitrage = ((max_price - min_price) / min_price) * 100
print(f"\n套利空间: {arbitrage:.2f}%")
```

### 示例6：自定义指标计算

```python
from kline_data.sdk import KlineClient
from datetime import datetime
import pandas as pd
import numpy as np

client = KlineClient()

# 获取数据
df = client.get_kline(
    exchange='binance',
    symbol='BTC/USDT',
    start_time=datetime(2024, 1, 1),
    end_time=datetime(2024, 1, 31),
    interval='1h'
)

# 计算自定义指标
def calculate_custom_indicators(df):
    """计算自定义技术指标"""

    # 1. 价格动量指标
    df['momentum_5'] = df['close'].pct_change(periods=5) * 100

    # 2. 波动率（20日标准差）
    df['volatility_20'] = df['close'].rolling(window=20).std()

    # 3. 成交量变化率
    df['volume_change'] = df['volume'].pct_change() * 100

    # 4. 价格区间（20日高低点）
    df['high_20'] = df['high'].rolling(window=20).max()
    df['low_20'] = df['low'].rolling(window=20).min()
    df['range_position'] = (df['close'] - df['low_20']) / (df['high_20'] - df['low_20'])

    # 5. 买卖力度
    df['bull_power'] = df['high'] - df['open']
    df['bear_power'] = df['open'] - df['low']

    return df

# 应用自定义指标
df = calculate_custom_indicators(df)

# 显示结果
print(df[['close', 'momentum_5', 'volatility_20', 'range_position']].tail(10))
```

---

## 配置说明

### 配置文件位置

默认配置文件：`kline_data/config/config.yaml`

### 配置项说明

```yaml
# 系统配置
system:
  version: "1.0.0"
  log_level: "INFO"          # DEBUG, INFO, WARNING, ERROR
  timezone: "Asia/Shanghai"

# 存储配置
storage:
  data_root: "./data"        # 数据根目录
  format: "parquet"          # 存储格式：parquet, csv
  compression: "snappy"      # 压缩算法：snappy, gzip, brotli
  partition_by:             # 分区策略
    - "exchange"
    - "symbol"
    - "interval"

# CCXT配置（交易所API）
ccxt:
  rate_limit: 1200          # 每分钟请求次数限制
  timeout: 30000            # 超时时间（毫秒）
  enable_rate_limit: true   # 启用限流
  retries: 3                # 重试次数
  retry_delay: 1000         # 重试延迟（毫秒）
  proxy: null               # 代理设置：http://proxy:port

# 内存管理
memory:
  max_memory_usage: "4GB"   # 最大内存使用
  chunk_size: 100000        # 数据块大小
  cache_size: 1000          # 缓存大小

# 指标配置
indicators:
  default_params:           # 指标默认参数
    MA:
      timeperiod: 20
    RSI:
      timeperiod: 14
    MACD:
      fastperiod: 12
      slowperiod: 26
      signalperiod: 9
  batch_size: 1000          # 批量计算大小

# API服务
api:
  host: "0.0.0.0"
  port: 8000
  enable_cors: true
  rate_limit: 100           # 每分钟请求限制
  auth_required: false

# CLI配置
cli:
  default_exchange: "binance"
  default_interval: "1h"
  output_format: "table"    # table, json, csv
  progress_bar: true
```

### 自定义配置

#### 方法1：修改配置文件

```bash
# 编辑配置文件
vim ~/.kline_data/config.yaml
```

#### 方法2：程序内配置

```python
from kline_data.sdk import KlineClient
from kline_data.config import load_config

# 加载自定义配置
config = load_config('/path/to/config.yaml')
client = KlineClient(config=config)
```

#### 方法3：环境变量

```bash
export KLINE_DATA_ROOT=/path/to/data
export KLINE_LOG_LEVEL=DEBUG
export KLINE_MAX_MEMORY=8GB
```

---

## 最佳实践

### 1. 数据下载策略

#### 增量下载

```python
# 首次下载历史数据
client.download_kline(
    exchange='binance',
    symbol='BTC/USDT',
    start_time=datetime(2020, 1, 1),
    end_time=datetime(2024, 1, 1),
    interval='1h'
)

# 定期增量更新
import schedule
import time

def update_data():
    result = client.update_kline(
        exchange='binance',
        symbol='BTC/USDT',
        interval='1h'
    )
    print(f"更新了 {result.downloaded} 条数据")

# 每小时更新一次
schedule.every().hour.do(update_data)

while True:
    schedule.run_pending()
    time.sleep(60)
```

#### 批量下载

```python
# 使用数据流处理大量数据
feed = client.create_data_feed(
    exchange='binance',
    symbol='BTC/USDT',
    start_time=datetime(2020, 1, 1),
    end_time=datetime(2024, 1, 1),
    interval='1m',
    chunk_size='5M'
)

for chunk in feed:
    # 处理每个数据块
    process_data(chunk)
```

### 2. 性能优化

#### 使用数据列子集

```python
# 只读取需要的列
df = client.get_kline(
    exchange='binance',
    symbol='BTC/USDT',
    start_time=datetime(2024, 1, 1),
    end_time=datetime(2024, 1, 31),
    interval='1h'
)

# 只使用需要的列
prices = df[['open', 'high', 'low', 'close', 'volume']]
```

#### 并发查询

```python
from concurrent.futures import ThreadPoolExecutor

def query_symbol(symbol):
    return client.get_latest(
        exchange='binance',
        symbol=symbol,
        interval='1h',
        bars=100
    )

symbols = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'XRP/USDT']

with ThreadPoolExecutor(max_workers=4) as executor:
    results = list(executor.map(query_symbol, symbols))

for symbol, df in zip(symbols, results):
    print(f"{symbol}: {len(df)} 条数据")
```

### 3. 错误处理

```python
from kline_data.sdk import KlineClient
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

client = KlineClient()

try:
    df = client.get_kline(
        exchange='binance',
        symbol='BTC/USDT',
        start_time=datetime(2024, 1, 1),
        end_time=datetime(2024, 1, 31),
        interval='1h'
    )
except ValueError as e:
    logger.error(f"参数错误: {e}")
except ConnectionError as e:
    logger.error(f"网络连接错误: {e}")
    # 重试逻辑
    time.sleep(5)
    df = client.get_kline(...)
except Exception as e:
    logger.error(f"未知错误: {e}")
```

### 4. 数据验证

```python
def validate_data(df):
    """验证数据完整性"""
    checks = {
        'not_null': df.isnull().sum().sum() == 0,
        'positive_volume': (df['volume'] > 0).all(),
        'valid_ohlc': (df['high'] >= df['low']).all() and
                     (df['high'] >= df['open']).all() and
                     (df['high'] >= df['close']).all(),
        'chronological': df.index.is_monotonic_increasing
    }

    if all(checks.values()):
        print("✅ 数据验证通过")
        return True
    else:
        print("❌ 数据验证失败:")
        for check, passed in checks.items():
            if not passed:
                print(f"  - {check}: 失败")
        return False

# 使用验证
df = client.get_kline(...)
if validate_data(df):
    process_data(df)
```

### 5. 资源管理

```python
# 使用上下文管理器
from kline_data.sdk import KlineClient

with KlineClient() as client:
    df = client.get_kline(...)
    process_data(df)
# 自动释放资源
```

---

## 常见问题

### Q1: 如何处理数据缺失？

**A:** SDK会自动检测并下载缺失数据。

```python
# 自动补全缺失数据
df = client.get_kline(
    exchange='binance',
    symbol='BTC/USDT',
    start_time=datetime(2024, 1, 1),
    end_time=datetime(2024, 1, 31),
    interval='1h'
)
# 如果数据缺失，会自动从交易所下载
```

### Q2: 如何提高下载速度？

**A:** 使用并发下载和合适的时间周期。

```python
# 1. 使用较大的时间周期
# 1m 数据量大，下载慢；1h 数据量小，下载快

# 2. 使用并发
from concurrent.futures import ThreadPoolExecutor

def download_symbol(symbol):
    return client.download_kline(...)

symbols = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT']
with ThreadPoolExecutor(max_workers=3) as executor:
    executor.map(download_symbol, symbols)
```

### Q3: 内存不足怎么办？

**A:** 使用数据流分块处理。

```python
# 使用数据流避免一次性加载所有数据
feed = client.create_data_feed(
    exchange='binance',
    symbol='BTC/USDT',
    start_time=datetime(2020, 1, 1),
    end_time=datetime(2024, 1, 1),
    interval='1m',
    chunk_size='1M'
)

for chunk in feed:
    # 每次只处理一个数据块
    process_chunk(chunk)
```

### Q4: 如何添加自定义交易所？

**A:** 通过CCXT添加交易所支持。

```python
import ccxt

# 初始化自定义交易所
exchange = ccxt.binance({
    'apiKey': 'your_api_key',
    'secret': 'your_secret',
    'enableRateLimit': True,
})

# 使用SDK
from kline_data.sdk import KlineClient
client = KlineClient(exchange=exchange)
```

### Q5: 如何处理代理设置？

**A:** 在配置文件或程序中设置代理。

```yaml
# config.yaml
ccxt:
  proxy: "http://proxy.example.com:8080"
```

```python
# 或在代码中设置
import ccxt

exchange = ccxt.binance({
    'proxies': {
        'http': 'http://proxy.example.com:8080',
        'https': 'https://proxy.example.com:8080',
    }
})
```

### Q6: 如何限制API调用频率？

**A:** SDK已内置限流机制，也可自定义配置。

```yaml
# config.yaml
ccxt:
  rate_limit: 1200        # 每分钟请求次数
  enable_rate_limit: true
```

```python
# 自定义限流
client = KlineClient(rate_limit=60)  # 每秒60次
```

### Q7: 如何导出数据到其他格式？

**A:** 使用Pandas导出功能。

```python
# 导出为CSV
df.to_csv('btc_data.csv')

# 导出为Excel
df.to_excel('btc_data.xlsx')

# 导出为JSON
df.to_json('btc_data.json', orient='records', date_format='iso')
```

### Q8: 如何处理时区问题？

**A:** SDK默认使用UTC时间。

```python
from datetime import datetime
import pytz

# 本地时间
local_time = datetime(2024, 1, 1, tzinfo=pytz.timezone('Asia/Shanghai'))

# 转换为UTC
utc_time = local_time.astimezone(pytz.UTC)

# 查询数据
df = client.get_kline(
    exchange='binance',
    symbol='BTC/USDT',
    start_time=utc_time,
    end_time=utc_time + timedelta(days=1),
    interval='1h'
)
```

---

## 附录

### A. 完整配置示例

```yaml
# ~/.kline_data/config.yaml

system:
  version: "1.0.0"
  log_level: "INFO"
  timezone: "UTC"

storage:
  data_root: "~/kline_data"
  format: "parquet"
  compression: "snappy"
  partition_by:
    - "exchange"
    - "symbol"
    - "interval"
  file_naming: "{exchange}_{symbol}_{interval}.parquet"

ccxt:
  rate_limit: 1200
  timeout: 30000
  enable_rate_limit: true
  retries: 3
  retry_delay: 1000
  proxy: null
  api_key: null
  api_secret: null

memory:
  max_memory_usage: "4GB"
  chunk_size: 100000
  cache_size: 1000
  enable_gc: true

indicators:
  default_params:
    MA:
      timeperiod: 20
      price: "close"
    EMA:
      timeperiod: 20
      price: "close"
    RSI:
      timeperiod: 14
      price: "close"
    MACD:
      fastperiod: 12
      slowperiod: 26
      signalperiod: 9
    ATR:
      timeperiod: 14
  batch_size: 1000
  parallel: true

api:
  host: "0.0.0.0"
  port: 8000
  enable_cors: true
  rate_limit: 100
  auth_required: false
  api_key_header: "X-API-Key"

cli:
  default_exchange: "binance"
  default_interval: "1h"
  output_format: "table"
  progress_bar: true
  color_output: true
```

### B. 技术指标速查表

| 类别 | 指标名称 | 参数 | 说明 |
|------|---------|------|------|
| 趋势 | MA | period | 简单移动平均 |
| 趋势 | EMA | period | 指数移动平均 |
| 趋势 | WMA | period | 加权移动平均 |
| 趋势 | DEMA | period | 双指数移动平均 |
| 趋势 | TEMA | period | 三指数移动平均 |
| 趋势 | HMA | period | Hull移动平均 |
| 动量 | RSI | period | 相对强弱指标 |
| 动量 | MACD | fast, slow, signal | MACD |
| 动量 | STOCH | fastk, slowk, slowd | 随机振荡器 |
| 动量 | CCI | period | 商品通道指标 |
| 动量 | Williams %R | period | 威廉指标 |
| 波动率 | ATR | period | 平均真实波幅 |
| 波动率 | Bollinger Bands | period, nbdevup | 布林带 |
| 波动率 | Keltner | period | 肯特纳通道 |
| 成交量 | OBV | - | 能量潮 |
| 成交量 | MFI | period | 资金流量指标 |
| 成交量 | AD | period | 累积/派发线 |
| 成交量 | VWAP | - | 成交量加权平均价 |

### C. 时间周期对应表

| 周期 | Value | 说明 |
|------|-------|------|
| 1秒 | 1s | 高频交易 |
| 1分钟 | 1m | 短线交易 |
| 5分钟 | 5m | 短线交易 |
| 15分钟 | 15m | 日内交易 |
| 30分钟 | 30m | 日内交易 |
| 1小时 | 1h | 日内交易 |
| 4小时 | 4h | 波段交易 |
| 1天 | 1d | 波段交易 |
| 1周 | 1w | 长线投资 |
| 1月 | 1M | 长线投资 |

### D. 交易所列表

| 交易所 | CCXT ID | 支持现货 | 支持合约 | 需认证 |
|--------|---------|---------|---------|--------|
| Binance | binance | ✅ | ✅ | 否 |
| OKX | okx | ✅ | ✅ | 否 |
| Bybit | bybit | ✅ | ✅ | 否 |
| Coinbase | coinbase | ✅ | ❌ | 否 |
| Kraken | kraken | ✅ | ✅ | 否 |
| Huobi | huobi | ✅ | ✅ | 否 |
| KuCoin | kucoin | ✅ | ✅ | 否 |
| Gate.io | gateio | ✅ | ✅ | 否 |

### E. 错误代码表

| 错误代码 | 说明 | 解决方案 |
|---------|------|---------|
| 1001 | 参数错误 | 检查输入参数 |
| 1002 | 交易所不支持 | 使用支持的交易所 |
| 1003 | 网络连接失败 | 检查网络设置 |
| 1004 | API限流 | 降低请求频率 |
| 1005 | 数据不存在 | 下载相关数据 |
| 1006 | 内存不足 | 使用数据流处理 |
| 1007 | 权限不足 | 配置API密钥 |

### F. 性能基准

| 操作 | 数据量 | 时间 |
|------|--------|------|
| 查询1万条 | 10K | ~0.1s |
| 查询100万条 | 1M | ~2s |
| 下载1天1m数据 | 1440 | ~5s |
| 下载1年1h数据 | 8760 | ~30s |
| 计算10个指标 | 10K | ~0.5s |
| 计算100个指标 | 1M | ~15s |

### G. 相关资源

- **项目主页**: https://github.com/your-org/kline_data
- **文档**: https://docs.kline-data.io
- **问题反馈**: https://github.com/your-org/kline_data/issues
- **CCXT文档**: https://docs.ccxt.com
- **TA-Lib文档**: https://ta-lib.org

---

## 版本历史

### v1.0.0 (2024-01-01)
- ✨ 初始版本发布
- ✅ 支持数据查询、下载、指标计算
- ✅ 提供 SDK、CLI、API 三种使用方式
- 📖 完整文档和示例

---

## 许可证

MIT License

---

## 联系方式

- 邮箱: support@kline-data.io
- Discord: https://discord.gg/kline-data
- Twitter: @kline_data

---

**最后更新**: 2024-12-29
