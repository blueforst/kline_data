# 配置使用指南

本文档详细说明 kline-data 项目的配置系统。

## 🎯 核心特性

✅ **零配置启动**：外部项目可直接使用，无需额外配置  
✅ **智能查找**：自动按优先级查找配置文件  
✅ **灵活定制**：支持多种配置方式  
✅ **类型安全**：基于 Pydantic 的配置验证  

## 📁 配置文件查找优先级

`load_config()` 函数按以下顺序查找配置文件：

1. **显式指定**：`load_config('/path/to/config.yaml')`
2. **当前工作目录**：`./config/config.yaml`
3. **包安装目录**：`site-packages/config/config.yaml`（项目默认配置）
4. **用户主目录**：`~/.kline_data/config.yaml`

## 🚀 使用方式

### 方式 1：零配置（推荐给新手）

```python
from kline_data.sdk import KlineClient

# 不传参数，自动使用项目配置
client = KlineClient()
```

**适用场景**：
- 快速开始，不需要自定义配置
- 评估项目功能
- 临时测试

**优点**：
- ✅ 最简单
- ✅ 立即可用
- ✅ 使用经过测试的默认配置

**缺点**：
- ❌ 数据存储路径可能不适合你的环境
- ❌ 代理设置可能需要调整

### 方式 2：修改部分配置（推荐）

```python
from kline_data.config import load_config
from kline_data.sdk import KlineClient

# 加载默认配置
config = load_config()

# 只修改需要的配置
config.storage.root_path = '/your/data/path'
config.ccxt.proxy.http = 'http://your-proxy:port'

# 使用修改后的配置
client = KlineClient(config=config)
```

**适用场景**：
- 生产环境部署
- 需要调整关键配置（存储路径、代理等）
- 保持其他默认配置

**优点**：
- ✅ 灵活但不复杂
- ✅ 利用默认配置的最佳实践
- ✅ 易于维护

**推荐修改的配置**：
- `storage.root_path`: 数据存储路径（几乎总是需要修改）
- `ccxt.proxy`: 代理设置（根据网络环境）
- `system.log_level`: 日志级别（开发时用 DEBUG，生产用 INFO/WARNING）

### 方式 3：自定义配置文件

```python
from kline_data.config import load_config
from kline_data.sdk import KlineClient

# 方式 3.1: 显式指定路径
config = load_config('/path/to/your/config.yaml')
client = KlineClient(config=config)

# 方式 3.2: 放在当前目录（自动查找）
# ./config/config.yaml
client = KlineClient()

# 方式 3.3: 放在用户主目录（自动查找）
# ~/.kline_data/config.yaml
client = KlineClient()
```

**适用场景**：
- 需要大量自定义配置
- 多环境部署（dev/staging/prod）
- 团队共享配置

**优点**：
- ✅ 最灵活
- ✅ 版本控制友好
- ✅ 支持环境变量替换（可扩展）

**配置文件模板**：
```bash
# 复制项目配置作为起点
cp /path/to/kline-data/config/config.yaml ./config/config.yaml
# 编辑配置
vim ./config/config.yaml
```

### 方式 4：代码创建配置对象

```python
from kline_data.config import Config
from kline_data.sdk import KlineClient

# 完全自定义配置
config = Config(
    storage={'root_path': '/your/path'},
    ccxt={'proxy': {'http': 'http://proxy:port'}},
    # ... 其他配置
)

client = KlineClient(config=config)
```

**适用场景**：
- 动态配置生成
- 配置来自数据库/API
- 高级自定义需求

**优点**：
- ✅ 完全控制
- ✅ 支持动态配置

**缺点**：
- ❌ 代码较长
- ❌ 需要了解所有配置项

## 📋 常用配置项速查

### 存储配置 (storage)

```python
config.storage.root_path = '/your/data/path'  # 数据根目录
config.storage.format = 'parquet'             # 数据格式
config.storage.compression = 'snappy'         # 压缩算法
config.storage.separate_by_exchange = True    # 按交易所分目录
config.storage.separate_by_symbol = True      # 按交易对分目录
```

### CCXT 配置 (ccxt)

```python
config.ccxt.proxy.http = 'http://127.0.0.1:7890'   # HTTP代理
config.ccxt.proxy.https = 'http://127.0.0.1:7890'  # HTTPS代理
config.ccxt.rate_limit.enabled = True              # 启用限流
config.ccxt.rate_limit.requests_per_minute = 1200  # 每分钟请求数
config.ccxt.retry.max_attempts = 3                 # 重试次数
config.ccxt.retry.timeout = 30                     # 超时时间
```

### 系统配置 (system)

```python
config.system.log_level = 'INFO'     # DEBUG/INFO/WARNING/ERROR
config.system.log_path = './logs'    # 日志目录
config.system.version = '1.0.0'      # 配置版本
```

### 内存配置 (memory)

```python
config.memory.max_usage_mb = 1024         # 最大内存使用(MB)
config.memory.chunk_size = 100000         # 数据块大小
config.memory.cache.enabled = True        # 启用缓存
config.memory.cache.max_size_mb = 512     # 缓存大小(MB)
```

## 🔧 实用示例

### 示例 1：本地开发环境

```python
from kline_data.config import load_config
from kline_data.sdk import KlineClient

config = load_config()
config.storage.root_path = './dev_data'
config.system.log_level = 'DEBUG'
config.ccxt.proxy.http = None  # 不使用代理

client = KlineClient(config=config)
```

### 示例 2：生产环境

```python
from kline_data.config import load_config
from kline_data.sdk import KlineClient

config = load_config()
config.storage.root_path = '/data/production/kline_data'
config.system.log_level = 'WARNING'
config.system.log_path = '/var/log/kline_data'
config.ccxt.rate_limit.requests_per_minute = 600  # 更保守

client = KlineClient(config=config)
```

### 示例 3：多环境配置

```python
import os
from kline_data.config import load_config
from kline_data.sdk import KlineClient

# 根据环境变量选择配置
env = os.getenv('ENV', 'development')

if env == 'production':
    config = load_config('/etc/kline_data/config.yaml')
elif env == 'staging':
    config = load_config('/etc/kline_data/config.staging.yaml')
else:
    config = load_config()  # 默认配置

client = KlineClient(config=config)
```

### 示例 4：不同存储后端

```python
from kline_data.config import load_config
from kline_data.sdk import KlineClient

# SSD 存储：高性能
config = load_config()
config.storage.root_path = '/ssd/kline_data'
config.storage.compression = 'snappy'  # 快速压缩

# HDD 存储：节省空间
config2 = load_config()
config2.storage.root_path = '/hdd/kline_data'
config2.storage.compression = 'zstd'  # 高压缩率

# 临时存储
config3 = load_config()
config3.storage.root_path = '/tmp/kline_data'
config3.storage.retention.enabled = True
config3.storage.retention.days = 7  # 7天自动清理
```

## ⚠️ 注意事项

### 数据存储路径

默认配置中的 `storage.root_path` 指向原项目的路径：

```yaml
storage:
  root_path: "/Volumes/sandisk/kline_data"
```

**外部使用时务必修改此路径**，否则：
- ❌ 可能没有写权限
- ❌ 可能路径不存在
- ❌ 可能与其他用户冲突

### 代理设置

默认配置包含代理设置：

```yaml
ccxt:
  proxy:
    http: "http://127.0.0.1:7890"
    https: "http://127.0.0.1:7890"
```

如果你的网络环境不同：
- 国外服务器：设置为 `None`
- 其他代理：修改地址和端口
- 认证代理：使用 `http://user:pass@host:port`

### 配置验证

配置加载时会自动验证，无效的配置会抛出异常：

```python
try:
    config = load_config('/path/to/config.yaml')
except FileNotFoundError:
    print("配置文件不存在")
except ValueError as e:
    print(f"配置格式错误: {e}")
```

## 🐛 故障排查

### 问题 1：找不到配置文件

```
FileNotFoundError: Configuration file not found
```

**解决方案**：
1. 检查配置文件是否存在
2. 使用 `load_config('/absolute/path/to/config.yaml')` 指定路径
3. 或者直接传入 Config 对象

### 问题 2：配置格式错误

```
ValueError: Invalid configuration
```

**解决方案**：
1. 检查 YAML 语法
2. 参考 `config/config.yaml` 作为模板
3. 查看详细错误信息

### 问题 3：权限问题

```
PermissionError: Cannot write to /path/to/data
```

**解决方案**：
1. 修改 `storage.root_path` 为有权限的目录
2. 或者授予目录写权限

### 问题 4：代理连接失败

```
ProxyError: Cannot connect to proxy
```

**解决方案**：
1. 检查代理地址和端口
2. 测试代理可用性
3. 或设置 `config.ccxt.proxy.http = None`

## 📚 相关文档

- [外部使用指南](external_usage.md) - 外部项目集成详解
- [配置文件示例](../config/config.yaml) - 完整配置文件
- [API 文档](api_reference.md) - Config 类详细说明

## 💡 最佳实践总结

1. **新手**：直接使用 `KlineClient()`，零配置启动
2. **日常使用**：修改少量关键配置（存储路径、代理）
3. **生产部署**：使用配置文件，支持多环境
4. **高级定制**：代码创建 Config 对象

**推荐配置流程**：
```python
from kline_data.config import load_config
from kline_data.sdk import KlineClient

# 1. 加载默认配置
config = load_config()

# 2. 修改关键配置
config.storage.root_path = '/your/data/path'  # 必改
config.ccxt.proxy.http = 'http://proxy:port'  # 根据环境

# 3. 创建客户端
client = KlineClient(config=config)
```

这种方式平衡了**简洁性**和**灵活性**！
