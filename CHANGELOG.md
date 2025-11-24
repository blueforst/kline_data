# 变更日志

所有重要的变更都将记录在此文件中。

## [Unreleased]

### ✨ 自动检测最早可用时间功能 (2024-11-23)

#### 新功能
- **CLI支持 `--start all` 参数**: 自动查询交易所支持的最早数据时间并从该时间开始下载
  - 使用示例: `kline download start -s BTC/USDT --start all`
  - 系统会自动查询交易所该交易对的最早可用时间
  - 显示查询进度和找到的最早时间
  
- **SDK新增方法**: `KlineClient.get_earliest_available_time()`
  - 支持查询任意交易所和交易对的最早可用时间
  - 返回 `datetime` 对象，便于后续处理
  
- **Downloader新增方法**: `DataDownloader.get_earliest_timestamp()`
  - 底层实现，通过 CCXT API 查询最早时间戳
  - 支持指定时间周期（timeframe）

#### 使用场景
- 下载完整历史数据用于策略回测
- 初始化系统时快速获取全部历史数据
- 数据迁移时对比数据范围

#### 相关文档
- 新增文档: `docs/auto_detect_earliest_time.md`
- 更新文档: `README.md`, `QUICKSTART.md`

#### 影响的文件
- `storage/downloader.py` - 新增 `get_earliest_timestamp()` 方法
- `sdk/client.py` - 新增 `get_earliest_available_time()` 方法
- `cli/commands/download.py` - 支持 `--start all` 参数
- `README.md` - 更新 CLI 使用示例
- `QUICKSTART.md` - 添加新功能说明
- `docs/auto_detect_earliest_time.md` - 完整功能文档

### 🔄 SDK客户端重构 (2024-11-23)

#### 变更内容
- **统一客户端接口**: 将智能客户端重命名为主客户端
  - `SmartKlineClient` → `KlineClient`
  - 归档原有的基础客户端到 `archived/sdk/client_legacy.py`
  - 简化SDK导出接口，只保留 `KlineClient`

- **统一数据获取器命名**:
  - `SmartDataFetcher` → `DataFetcher`
  - `storage/smart_fetcher.py` → `storage/fetcher.py`
  - 更新所有相关导入和引用

#### 原因说明
- SDK模块中同时存在两个客户端造成用户混乱
- 智能客户端提供了更完善的功能，应作为唯一推荐接口
- 简化API使用，降低学习成本
- "Smart" 前缀是冗余的，因为智能获取是默认行为

#### 影响的文件
- `sdk/__init__.py` - 简化导出，只保留 `KlineClient`
- `sdk/client.py` - 由 `smart_client.py` 重命名而来，类名改为 `KlineClient`
- `storage/__init__.py` - 导出 `DataFetcher` 替代 `SmartDataFetcher`
- `storage/fetcher.py` - 由 `smart_fetcher.py` 重命名而来
- `archived/sdk/client_legacy.py` - 归档的基础客户端，更新导入
- `examples/smart_fetch_example.py` - 更新客户端导入
- `archived/docs/QA_data_fetching.md` - 更新文档示例

#### 迁移指南
所有使用旧名称的代码应更新：
```python
# 旧代码
from sdk import SmartKlineClient
from storage import SmartDataFetcher

# 新代码
from sdk import KlineClient
from storage import DataFetcher
```

### 🔧 时区显示修复 (2025-11-23)

#### 修复内容
- **CLI时区显示**: 所有用户界面时间现在正确显示为本地时区
  - `query` 命令: 数据范围、交易对列表、K线数据
  - `download` 命令: 任务列表、数据状态
  - `task` 命令: 任务列表、任务详情、断点恢复
  - `validate` 命令: 数据范围显示
  - 所有时间列添加 "(本地)" 或 "(本地时间)" 标注
  - **不再显示原始时间戳（毫秒数字）**，统一转换为可读格式

- **内部逻辑UTC保证**: 确保底层继续使用UTC时区
  - 修复 `query stats` 使用 `now_utc()` 替代 `datetime.now()`
  - 修复 `download start` 使用 `now_utc()` 替代 `datetime.now()`
  - 所有存储、计算、比较继续使用UTC

#### 新增功能
- ✨ **统一的时区转换函数** (`format_time_for_display()`)
  - 自动处理字符串、datetime、时间戳多种格式
  - 智能处理 `None`, `"N/A"`, 空字符串
  - 避免在各个CLI命令中重复实现转换逻辑
  - 确保一致的用户体验

#### 新增文档
- 📄 时区处理文档 (`docs/TIMEZONE_HANDLING.md`)
  - "内部UTC，外部本地" 设计原则
  - 时区工具函数完整使用指南
  - CLI时间显示规范
  - 最佳实践和常见问题
  
- 📖 快速参考指南 (`docs/TIMEZONE_QUICK_REFERENCE.md`)
  - 常用函数速查表
  - CLI显示模板
  - 代码规范检查清单
  
- 🧪 时区测试脚本 (`test_timezone_display.py`)
  - 验证所有时区转换函数
  - 测试实际显示场景
  - 确保UTC内部 + 本地显示

#### 影响的文件
- `utils/timezone.py` - 新增 `format_time_for_display()` 函数
- `cli/commands/query.py` - 使用统一转换函数
- `cli/commands/download.py` - 使用统一转换函数
- `cli/commands/task.py` - 使用统一转换函数
- `cli/commands/validate.py` - 时区转换
- `docs/TIMEZONE_HANDLING.md` - 新增完整文档
- `docs/TIMEZONE_QUICK_REFERENCE.md` - 新增快速参考
- `test_timezone_display.py` - 新增测试

### 新增功能

#### ⭐ 数据校验增强 - 完整校验模式 (2025-11-23)

- **--max 参数**: 添加完整校验功能，对比实际数据与元数据
  - `kline validate check --max` - 全量校验所有交易对
  - `kline validate check --symbol BTC/USDT --max` - 校验指定交易对
  - `kline validate check --exchange binance --max` - 校验整个交易所
  
- **自动修复元数据不一致**:
  - 完整扫描所有实际数据文件
  - 对比元数据中的时间范围和统计信息
  - 自动修复不一致的元数据
  - 更新数据范围、记录数、完整性等信息
  
- **适用场景**:
  - 手动删除/修改了数据文件
  - 数据迁移后元数据不同步
  - 元数据文件损坏或丢失
  - 定期维护，确保数据一致性

**使用示例**:

```bash
# 完整校验所有交易对
kline validate check --max

# 校验指定交易对
kline validate check --symbol BTC/USDT --max

# 校验整个交易所
kline validate check --exchange binance --max
```

**更新文件**:
- `cli/commands/validate.py` - 添加 `_perform_max_check()` 函数
- `cli/README.md` - 更新文档说明
- `README.md` - 更新主文档
- `examples/cli_validate_example.sh` - 添加示例

#### ⭐ CLI下载任务管理 (2025-11-23)

- **任务列表与交互式恢复**: 一步到位的任务管理
  - `kline task list` - 默认交互式，显示任务后自动进入选择模式
  - 支持按状态筛选（pending/running/completed/failed/cancelled）
  - 使用 ↑↓ 方向键浏览任务列表
  - 回车键确认并自动恢复下载
  - 支持断点续传，从上次失败位置继续
  - `--no-interactive` 选项仅显示列表不交互
  
- **任务管理命令**:
  - `kline task list` - 列出任务并交互式选择（默认）
  - `kline task list --status failed` - 筛选失败任务并选择
  - `kline task list --no-interactive` - 仅显示列表
  - `kline task resume <task-id>` - 恢复指定任务
  - `kline task delete <task-id>` - 删除任务
  - `kline task clean` - 批量清理已完成任务
  - `kline task clean --system-files` - 清理系统隐藏文件
  
- **自动清理机制确认**: 
  - 已完成的任务自动删除元数据文件
  - 失败的任务保留供恢复使用
  - 避免任务文件累积占用磁盘

**使用示例**:

```bash
# 查看任务并交互式选择（默认）
kline task list

# 查看失败的任务并选择
kline task list --status failed

# 仅显示列表不交互
kline task list --no-interactive

# 清理已完成的任务
kline task clean
```

**新增文件**:
- `cli/commands/task.py` - 任务管理命令模块

**修改的文件**:
- `cli/main.py` - 注册 task 命令组
- `cli/README.md` - 更新文档，添加任务管理章节
- `requirements.txt` - 添加 inquirer 依赖

### 修复

#### 🐛 下载中断信号处理 (2025-11-23)

- **问题**: 使用 Ctrl+C 中断下载时，任务状态保持 `running`，无法恢复
- **修复**:
  - 添加信号处理器捕获 SIGINT (Ctrl+C) 和 SIGTERM
  - 中断时自动将任务状态更新为 `cancelled`
  - 保存断点信息，支持后续恢复
  - 优雅退出，显示友好提示信息
- **使用**: 按 Ctrl+C 中断下载后，使用 `kline task list` 即可看到并恢复任务

#### 🐛 任务列表读取编码问题 (2025-11-23)

- **问题**: macOS系统生成的隐藏文件（`._`前缀）导致任务列表读取失败
- **修复**:
  - 在 `MetadataManager.list_download_tasks()` 中添加隐藏文件过滤
  - 跳过 `.` 和 `._` 开头的系统文件
  - 添加错误处理机制，跳过损坏的任务文件
  - 新增 `kline task clean --system-files` 清理系统文件
- **影响**: 解决 `'utf-8' codec can't decode` 错误

#### 🐛 下载任务自动清理 (2025-11-22)

- **问题**: 下载完成后，元数据中的任务文件（`data/metadata/tasks/*.json`）没有自动清理
- **修复**: 
  - 在 `MetadataManager` 中新增 `delete_download_task()` 方法
  - 下载完成后自动删除任务文件
  - 避免任务文件累积占用磁盘空间
- **影响范围**: 仅影响已完成的任务文件清理，不影响任务执行过程

### 新增功能

#### 📊 下载进度实时显示 (2025-11-22)

- **进度回调机制**: 支持通过回调函数实时获取下载进度
  - 进度百分比（0-100%）
  - 已下载数据条数
  - 自定义进度处理逻辑

- **CLI 进度条**: 命令行下载时自动显示美观的进度条
  - 使用 Rich 库实现
  - 显示进度条、百分比和数据量
  - 旋转加载动画

- **Python SDK 集成**: 
  - `SmartKlineClient.download()` 新增 `progress_callback` 参数
  - 支持自定义进度处理逻辑
  - 完全向后兼容（可选参数）

**使用示例**:

```python
from sdk import KlineClient
from rich.progress import Progress

with KlineClient() as client:
    with Progress() as progress:
        task = progress.add_task("下载中...", total=100)
        
        def update(pct, records):
            progress.update(task, completed=pct)
        
        client.download(
            symbol="BTC/USDT",
            exchange="binance",
            start_time=datetime(2024, 1, 1),
            progress_callback=update
        )
```

**相关文档**:
- [功能文档](docs/progress_callback_feature.md)
- [使用示例](examples/download_with_progress.py)

**修改的文件**:
- `storage/downloader.py` - 添加进度回调支持
- `sdk/smart_client.py` - 传递进度回调参数
- `cli/commands/download.py` - CLI 进度条实现

#### 🎉 重叠数据下载优化 (2025-11-22)

- **智能重叠检测**: 下载前自动检查元数据，识别已有数据与请求范围的重叠部分
- **分段下载**: 只下载缺失的数据段，跳过已存在的部分
- **自动区间合并**: 新下载的数据段自动与已有数据合并，保持元数据整洁
- **精确边界处理**: 正确处理时间戳边界，避免数据重复或遗漏

**性能提升**:
- 部分重叠场景：节省 50% 下载量
- 完全重叠场景：节省 100% 下载量（跳过下载）
- 多段缺失场景：节省 75% 下载量

**新增方法**:
- `MetadataManager.get_interval_ranges()` - 获取已下载时间段
- `MetadataManager.calculate_missing_ranges()` - 计算缺失时间段

**相关文档**:
- [详细文档](docs/overlap_download_optimization.md)
- [功能说明](OVERLAP_DOWNLOAD_FEATURE.md)
- [使用示例](examples/example_overlap_download.py)
- [单元测试](tests/test_overlap_download.py)

**修改的文件**:
- `storage/metadata_manager.py` - 添加重叠检测和缺失范围计算
- `storage/downloader.py` - 修改下载逻辑，支持分段下载

---

## 格式说明

本变更日志遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/) 格式，
版本号遵循 [语义化版本 2.0.0](https://semver.org/lang/zh-CN/) 规范。

### 变更类型

- `新增功能` - 新功能
- `变更` - 现有功能的变更
- `弃用` - 即将移除的功能
- `移除` - 已移除的功能
- `修复` - 错误修复
- `安全` - 安全相关的修复
