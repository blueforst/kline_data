# 外部项目使用指南

本文档说明如何在外部项目中使用 kline-data 包。

## 安装

### 从本地安装（开发模式）

```bash
# 在kline-data项目目录下
pip install -e .
```

### 从PyPI安装（发布后）

```bash
pip install kline-data
```

## 使用方式

### 方式 1：直接使用项目配置（推荐）

外部项目可以直接使用 kline-data 的内置配置，无需额外配置：

```python
from kline_data.sdk import KlineClient
from datetime import datetime

# 不传config参数，自动使用项目配置
client = KlineClient()

# 查询数据
df = client.get_kline(
    exchange='binance',
    symbol='BTC/USDT',
    start_time=datetime(2024, 1, 1),
    end_time=datetime(2024, 1, 2),
    interval='1h'
)

print(df.head())
```

### 方式 2：自定义配置文件

如果需要修改配置，可以在以下位置创建配置文件（按优先级顺序）：

#### 2.1 当前工作目录

```bash
# 在你的项目根目录
mkdir config
cp /path/to/kline-data/config/config.yaml config/
# 修改 config/config.yaml
```

```python
from kline_data.sdk import KlineClient

# 自动查找当前目录的config/config.yaml
client = KlineClient()
```

#### 2.2 用户主目录

```bash
# 创建用户配置目录
mkdir -p ~/.kline_data
cp /path/to/kline-data/config/config.yaml ~/.kline_data/
# 修改 ~/.kline_data/config.yaml
```

```python
from kline_data.sdk import KlineClient

# 自动查找 ~/.kline_data/config.yaml
client = KlineClient()
```

#### 2.3 指定配置文件路径

```python
from kline_data.config import load_config
from kline_data.sdk import KlineClient

# 显式指定配置文件
config = load_config('/path/to/your/config.yaml')
client = KlineClient(config=config)
```

### 方式 3：代码中创建配置对象

```python
from kline_data.config import Config
from kline_data.sdk import KlineClient

# 创建自定义配置
config = Config(
    system={
        'version': '1.0.0',
        'log_level': 'INFO',
        'log_path': './logs'
    },
    storage={
        'root_path': '/your/custom/data/path',
        'separate_by_exchange': True,
        'separate_by_symbol': True,
        'format': 'parquet',
        'compression': 'snappy'
    },
    ccxt={
        'proxy': {
            'http': 'http://your-proxy:7890',
            'https': 'http://your-proxy:7890'
        }
    }
)

client = KlineClient(config=config)
```

### 方式 4：修改部分配置

```python
from kline_data.config import load_config
from kline_data.sdk import KlineClient

# 加载默认配置
config = load_config()

# 修改特定配置项
config.storage.root_path = '/your/custom/path'
config.ccxt.proxy.http = 'http://your-proxy:7890'

# 使用修改后的配置
client = KlineClient(config=config)
```

## 配置文件查找顺序

`load_config()` 按以下顺序查找配置文件：

1. **显式指定的路径**：`load_config('/path/to/config.yaml')`
2. **当前工作目录**：`./config/config.yaml`
3. **包安装目录**：`site-packages/kline_data/config/config.yaml`（项目配置）
4. **用户主目录**：`~/.kline_data/config.yaml`

## 常见使用场景

### 场景 1：快速开始（使用默认配置）

```python
from kline_data.sdk import KlineClient
from datetime import datetime

# 直接创建客户端，使用项目默认配置
client = KlineClient()

# 查询数据
df = client.get_kline('binance', 'BTC/USDT', 
                      datetime(2024, 1, 1), 
                      datetime(2024, 1, 2), '1h')
```

### 场景 2：仅修改数据存储路径

```python
from kline_data.config import load_config
from kline_data.sdk import KlineClient

config = load_config()
config.storage.root_path = '/your/data/path'

client = KlineClient(config=config)
```

### 场景 3：使用代理

```python
from kline_data.config import load_config
from kline_data.sdk import KlineClient

config = load_config()
config.ccxt.proxy.http = 'http://127.0.0.1:7890'
config.ccxt.proxy.https = 'http://127.0.0.1:7890'

client = KlineClient(config=config)
```

### 场景 4：多个项目共享配置

```bash
# 在用户目录创建共享配置
mkdir -p ~/.kline_data
cat > ~/.kline_data/config.yaml << 'EOF'
storage:
  root_path: /shared/kline/data
ccxt:
  proxy:
    http: http://127.0.0.1:7890
    https: http://127.0.0.1:7890
EOF
```

所有使用 `KlineClient()` 的项目都会自动使用这个配置。

## 配置项说明

详细配置说明请参考 `config/config.yaml` 文件中的注释。主要配置项：

- **storage**: 数据存储配置（路径、格式、压缩等）
- **ccxt**: 交易所API配置（代理、限流、重试等）
- **memory**: 内存管理配置
- **resampling**: 重采样配置
- **indicators**: 技术指标配置
- **api**: API服务配置
- **cli**: 命令行配置

## 注意事项

1. **数据存储路径**：默认配置中的 `storage.root_path` 可能指向原项目的路径，外部使用时建议修改
2. **代理设置**：如果需要代理访问交易所API，记得配置 `ccxt.proxy`
3. **日志路径**：默认日志路径为 `./logs`，确保有写权限
4. **配置优先级**：自定义配置会覆盖默认配置

## 最佳实践

### 推荐方式

对于大多数外部项目，推荐使用以下方式：

```python
from kline_data.config import load_config
from kline_data.sdk import KlineClient

# 加载默认配置并修改需要的部分
config = load_config()

# 只修改必要的配置
config.storage.root_path = '/your/data/path'  # 必改：数据存储路径
config.ccxt.proxy.http = 'http://proxy:port'  # 可选：代理设置

# 创建客户端
client = KlineClient(config=config)
```

这种方式的优点：
- ✅ 使用项目的默认配置（经过测试和优化）
- ✅ 只需修改少量关键配置
- ✅ 代码简洁易维护
- ✅ 配置变更集中管理

## 故障排查

### 找不到配置文件

如果遇到 `FileNotFoundError: Configuration file not found`，说明没有找到配置文件。

解决方案：
1. 在当前目录创建 `config/config.yaml`
2. 在用户主目录创建 `~/.kline_data/config.yaml`
3. 显式传入配置文件路径或配置对象

### 配置加载失败

如果配置文件格式错误，会抛出 `ValueError: Invalid configuration`。

解决方案：
1. 检查YAML语法
2. 参考项目的 `config/config.yaml` 作为模板
3. 使用配置验证工具

## 示例项目结构

```
your-project/
├── main.py              # 你的主程序
├── config/              # 可选：自定义配置
│   └── config.yaml
├── data/                # 数据存储目录
└── requirements.txt     # 包含 kline-data
```

```python
# main.py
from kline_data.sdk import KlineClient
from datetime import datetime

def main():
    # 使用项目配置或当前目录的config/config.yaml
    client = KlineClient()
    
    # 你的业务逻辑
    df = client.get_kline(
        'binance', 'BTC/USDT',
        datetime(2024, 1, 1),
        datetime(2024, 1, 2),
        '1h'
    )
    
    print(df)

if __name__ == '__main__':
    main()
```
