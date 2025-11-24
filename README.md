# K线数据本地存储系统

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

一个高性能、可扩展的本地K线数据存储系统，支持从CCXT获取1秒级K线数据并持久化到本地，提供多周期重采样和技术指标计算功能。

## ✨ 主要特性

- 🚀 **高性能存储**: 基于Apache Parquet列式存储，支持高压缩率和快速查询
- 📊 **多数据源**: 支持CCXT所有交易所（Binance、OKX、Bybit等）
- ⏱️ **多周期支持**: 原始1秒数据可重采样为任意周期（1m、5m、1h、1d等）
- 📈 **技术指标**: 内置MA、EMA、BOLL、RSI、MACD等常用指标，支持自定义扩展
- 🔄 **断点续传**: 支持数据下载中断后继续
- ⚡ **智能下载**: 自动检测已有数据，跳过重叠部分，只下载缺失段（[详见文档](docs/overlap_download_optimization.md)）
- 🎯 **数据完整性**: 自动检测和修复数据缺失，验证后可一键补齐
- 🐍 **Python SDK**: 优雅的链式调用API
- 🌐 **RESTful API**: FastAPI实现的高性能API服务
- 🛠️ **CLI工具**: 便捷的命令行管理工具

## 📦 安装

### 使用pip安装

```bash
pip install -e .
```

### 从源码安装

```bash
git clone <repository-url>
cd kline_data
pip install -r requirements.txt
pip install -e .
```

### 依赖项

- Python 3.10+
- 主要依赖：pandas, pyarrow, ccxt, fastapi, pydantic

## 🚀 快速开始

### 1. 配置

复制并编辑配置文件：

```bash
cp config/config.yaml config/config.local.yaml
```

编辑 `config.local.yaml` 设置你的参数：

```yaml
storage:
  root_path: "./data"  # 数据存储路径
  
ccxt:
  proxy:
    http: "http://127.0.0.1:7890"  # 如需代理
    https: "http://127.0.0.1:7890"
```

### 2. 使用Python SDK

```python
from sdk import KlineClient
from datetime import datetime

# 初始化客户端
client = KlineClient()

# 下载数据
result = client.download(
    exchange='binance',
    symbol='BTC/USDT',
    start_time=datetime(2024, 1, 1),
    end_time=datetime(2024, 12, 31)
)

# 查询时间范围内的数据
df = client.get_kline(
    exchange='binance',
    symbol='BTC/USDT',
    start_time=datetime(2024, 1, 1),
    end_time=datetime(2024, 1, 31),
    interval='1h',
    with_indicators=['MA_20', 'EMA_12', 'RSI_14']
)

print(df.head())

# 获取最新的N条K线
df = client.get_latest(
    exchange='binance',
    symbol='BTC/USDT',
    interval='1d',
    limit=100
)

# 🆕 获取指定时间前的N条K线（使用timezone处理）
from utils.timezone import to_utc

df = client.get_klines_before(
    exchange='binance',
    symbol='BTC/USDT',
    before_time=datetime(2024, 1, 1),  # 或使用 to_utc(datetime(...))
    interval='1d',
    limit=100,
    with_indicators=['MA_20', 'RSI_14']
)

# 数据重采样
df = client.resample(
    exchange='binance',
    symbol='BTC/USDT',
    start_time=datetime(2024, 1, 1),
    end_time=datetime(2024, 1, 31),
    source_interval='1s',
    target_interval='1h'
)
```

**新功能亮点**：`get_klines_before()` 接口
- 获取指定时间前n条K线，适用于回测和策略开发
- 使用 `utils.timezone` 模块确保时区正确性
- 自动过滤数据，返回严格在指定时间之前的K线
- 详细文档见：[get_klines_before API文档](docs/get_klines_before_api.md)

### 3. 使用CLI

```bash
# 下载数据（指定时间范围）
kline-data download -e binance -s BTC/USDT --start 2024-01-01 --end 2024-12-31

# 从交易所最早可用时间开始下载全部历史数据
kline-data download -e binance -s BTC/USDT --start all

# 更新数据
kline-data update -e binance -s BTC/USDT

# 查看元数据
kline-data info -e binance -s BTC/USDT

# 列出交易对
kline-data list-symbols -e binance

# 数据完整性验证
kline-data validate check --symbol BTC/USDT --exchange binance

# 验证并自动修复缺失数据
kline-data validate check --symbol BTC/USDT --exchange binance --auto-repair

# 手动修复指定交易对的缺失数据
kline-data validate repair --symbol BTC/USDT --exchange binance --auto

# 配置管理
kline-data config-get storage.root_path
kline-data config-set storage.compression gzip
```

### 4. 数据验证与自动修复

系统提供强大的数据完整性验证和自动修复功能：

```bash
# 检查单个交易对的数据完整性
kline validate check --symbol BTC/USDT --exchange binance

# 检查所有交易对
kline validate check

# 显示详细的缺失数据范围
kline validate check --symbol BTC/USDT --show-gaps

# 验证并自动修复缺失数据（推荐）
kline validate check --symbol BTC/USDT --auto-repair

# 导出验证报告
kline validate check --export report.csv

# 检查数据质量（完整性、重复率、异常值）
kline validate quality --symbol BTC/USDT

# 预览需要修复的缺失段
kline validate repair --symbol BTC/USDT --dry-run

# 自动修复指定交易对
kline validate repair --symbol BTC/USDT --auto

# ⭐ 完整校验：对比实际数据与元数据，修复不一致问题（新增）
kline validate check --max                           # 全量校验所有交易对
kline validate check --symbol BTC/USDT --max         # 校验指定交易对
kline validate check --exchange binance --max        # 校验整个交易所
```

**自动修复功能特点：**
- ✅ 自动检测数据缺失段
- ✅ 智能下载补齐缺失部分
- ✅ 支持批量修复多个交易对
- ✅ 实时显示修复进度
- ✅ 修复后自动验证完整性
- ✅ **完整校验模式 (--max)：扫描实际数据文件，自动修复元数据不一致** ⭐

**完整校验适用场景：**
- 手动删除/修改了数据文件后
- 数据迁移导致元数据不同步
- 元数据文件损坏或丢失
- 定期维护，确保数据完整性

### 5. 启动API服务

```bash
# 使用CLI启动
kline-data serve --host 0.0.0.0 --port 8000

# 或直接运行
python -m service.app
```

API文档：http://localhost:8000/docs

## 📚 文档

详细文档请查看：

- [项目状态](docs/STATUS.md) - 📌 当前项目状态和里程碑
- [系统设计文档](docs/system_design.md) - 完整的架构设计和技术方案
- [数据获取策略](docs/data_fetching_strategy.md) - 智能数据获取策略详解
- [CLI使用指南](docs/cli_guide.md) - 命令行工具完整指南
- [项目总结](docs/project_summary.md) - 项目概览和实现细节
- [时间周期使用指南](docs/timeframe_usage.md) - 全局时间周期枚举使用说明

### 🆕 全局常量系统文档

项目现在提供了完整的全局常量系统，帮助避免硬编码和提高代码可维护性：

- **[全局常量使用指南](docs/global_constants_guide.md)** - 完整的使用指南和最佳实践
- **[API参考文档](docs/constants_api_reference.md)** - 详细的API文档和类型信息
- **[常量迁移指南](docs/constants_migration_guide.md)** - 从硬编码到常量的完整迁移方案
- **[文档目录](docs/constants_documentation_index.md)** - 常量文档导航

#### 常量系统亮点

```python
# 🆕 使用全局常量替代硬编码
from utils.constants import (
    Timeframe, SUPPORTED_EXCHANGES, DEFAULT_SYMBOL,
    validate_timeframe, validate_exchange
)

# ✅ 类型安全的时间周期
tf = Timeframe.from_string('1h')
print(f"1小时 = {tf.seconds}秒")

# ✅ 内置验证
validate_exchange('binance')  # 验证通过
validate_timeframe('1m')      # 验证通过

# ✅ 避免硬编码
symbol = DEFAULT_SYMBOL       # 'BTC/USDT'
exchanges = SUPPORTED_EXCHANGES  # 支持的交易所列表
```

#### 主要优势

- 🎯 **避免硬编码** - 统一管理所有配置值
- 🔒 **类型安全** - 提供完整的类型提示和验证
- 🚀 **易于维护** - 集中配置，修改一处生效全局
- 📚 **完整文档** - 详细的使用指南和API文档
- 🧪 **全面测试** - 100%测试覆盖，确保正确性

查看[常量使用指南](docs/global_constants_guide.md)了解更多详情。

## 🏗️ 项目结构

```
kline_data/
├── config/              # 配置层
│   ├── config.yaml      # 配置文件
│   ├── manager.py       # 配置管理器
│   └── schemas.py       # 配置数据模型
├── storage/             # 存储层
├── reader/              # 读取层
├── resampler/           # 重采样层
├── indicators/          # 指标层
├── sdk/                 # SDK层
├── service/             # 服务层 (FastAPI)
├── cli/                 # CLI层
├── tests/               # 测试
├── data/                # 数据目录
│   ├── raw/             # 原始1s数据
│   ├── resampled/       # 重采样数据
│   └── metadata/        # 元数据
└── logs/                # 日志
```

## 🧪 测试

```bash
# 运行所有测试
pytest

# 运行特定测试
pytest tests/test_config.py

# 生成覆盖率报告
pytest --cov=. --cov-report=html
```

## 📝 开发计划

- [x] 配置层实现
- [x] 存储层实现（支持智能数据获取策略）
- [x] 读取层实现
- [x] 重采样层实现
- [x] 指标层实现（支持常用技术指标和自定义扩展）
- [x] SDK层实现
- [x] API服务层实现
- [x] CLI工具实现
- [ ] 完整测试覆盖
- [ ] 性能优化
- [ ] 文档完善

## 🎯 核心特性详解

### 智能数据获取策略

系统采用智能数据获取策略，自动选择最优方案：

1. **小范围数据**：本地有1s数据时，通过重采样生成目标周期
2. **大范围数据**：数据范围较大时，直接从CCXT获取目标周期数据
3. **自动判断**：系统根据数据范围大小自动选择最优策略

```python
# 自动选择策略示例
client = KlineDataClient()

# 小范围：使用重采样（快速）
df = client.query('binance', 'BTC/USDT')\
    .time_range(datetime(2024, 1, 1), datetime(2024, 1, 2))\
    .interval('1h')\
    .execute()

# 大范围：直接获取（节省存储）
df = client.query('binance', 'BTC/USDT')\
    .time_range(datetime(2020, 1, 1), datetime(2024, 1, 1))\
    .interval('1w')\
    .execute()
```

## 🤝 贡献

欢迎提交Issue和Pull Request！

## 📄 许可证

MIT License

## 👤 作者

Your Name - your.email@example.com

## 🙏 致谢

- [CCXT](https://github.com/ccxt/ccxt) - 加密货币交易库
- [Apache Parquet](https://parquet.apache.org/) - 列式存储格式
- [FastAPI](https://fastapi.tiangolo.com/) - 现代Web框架
