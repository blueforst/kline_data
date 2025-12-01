# CLI 使用指南

K线数据系统命令行工具快速参考。

## 快速开始

```bash
# 安装
pip install -e .

# 5分钟上手
kline download start -s BTC/USDT --start 2024-01-01  # 1. 下载
kline validate check -s BTC/USDT --show-gaps          # 2. 验证 ⭐
kline query kline -s BTC/USDT -t 1m -l 10             # 3. 查询
```

## 命令概览

```
主要命令:
  download    数据下载、更新与任务管理
  validate    数据完整性验证 ⭐
  query       数据查询
  config      配置管理
  server      API服务
  
全局选项:
  --config, -c    指定配置文件
  --verbose, -v   详细输出
  --help          帮助信息
```

## 1. 数据下载

```bash
# 下载数据
kline download start -s BTC/USDT --start 2024-01-01

# 更新到最新
kline download update -s BTC/USDT

# 查看状态
kline download status -s BTC/USDT

# 列出所有
kline download list

# 下载所有周期与历史范围
kline download start -s BTC/USDT --start all -i all
```

## 2. 任务管理 ⭐

**管理和恢复下载任务**

```bash
# 列出任务并交互式选择 ⭐
kline download task list                                      # 自动进入交互式选择

# 筛选特定状态的任务
kline download task list --status failed                      # 查看并选择失败任务
kline download task list --status running                     # 查看运行中任务

# 仅显示列表不交互
kline download task list --no-interactive                     # 仅显示，不选择

# 恢复指定任务
kline download task resume <task-id>

# 删除任务
kline download task delete <task-id>
kline download task delete <task-id> --force                  # 强制删除不提示

# 批量清理任务
kline download task clean                                     # 清理已完成的任务
kline download task clean --status failed                     # 清理失败的任务
kline download task clean --status all --force                # 强制清理所有任务
kline download task clean --system-files                      # 清理系统隐藏文件（macOS）
```

**任务状态说明**:
- `pending`: 待执行
- `running`: 运行中（不可恢复）
- `completed`: 已完成（自动删除）
- `failed`: 失败（可恢复）
- `cancelled`: 已取消（可恢复，如 Ctrl+C 中断）

**注意**: 
- `kline download task list` 默认进入交互式选择模式，使用 `--no-interactive` 仅显示列表
- 已完成的任务会自动删除元数据文件，避免累积占用磁盘空间
- 使用 Ctrl+C 中断下载会自动保存进度，任务状态变为 `cancelled`，可随时恢复
- macOS系统可能生成隐藏文件（`._`开头），使用 `kline download task clean --system-files` 清理

## 3. 数据验证 ⭐

**检查完整性和质量**

```bash
# 检查完整性
kline validate check -s BTC/USDT                     # 基本检查
kline validate check --show-gaps                     # 显示缺失段
kline validate check --export report.csv             # 导出报告
kline validate check --exchange binance              # 检查整个交易所

# 完整校验（对比实际数据与元数据，修复不一致问题）⭐
kline validate check --max                           # 全量校验所有交易对
kline validate check -s BTC/USDT --max               # 校验指定交易对
kline validate check --exchange binance --max        # 校验整个交易所

# 检查质量
kline validate quality -s BTC/USDT                   # 完整性、重复率、异常值

# 修复预览
kline validate repair -s BTC/USDT --dry-run         # 查看需修复内容
```



## 4. 数据查询

```bash
# 查询K线
kline query kline -s BTC/USDT -t 1m -l 10
kline query kline -s BTC/USDT -t 1h --indicators sma_20,ema_50,macd -l 100

# 导出数据
kline query kline -s BTC/USDT -t 1d -o output.csv

# 查询最新
kline query latest -s BTC/USDT -t 1m --count 20

# 统计信息
kline query stats -s BTC/USDT --period 30

# 列出交易对
kline query symbols
kline query symbols --exchange binance
```

## 5. 配置管理

```bash
# 查看配置
kline config show
kline config list

# 设置配置
kline config set -k storage.root_path -v /data/kline
kline config set -k memory.max_cache_size_mb -v 2048

# 验证导出
kline config validate
kline config export -o backup.yaml
```

## 6. API服务

```bash
# 启动服务
kline server start
kline server start --host 0.0.0.0 --port 8000 --workers 4

# 检查状态
kline server status

# 测试API
kline server test

# API文档: http://localhost:8000/docs
```

## 7. 常见场景

### 每日数据维护

```bash
# 更新并验证
kline download update -s BTC/USDT
kline validate check -s BTC/USDT --export daily_$(date +%Y%m%d).csv
```

### 批量验证

```bash
# 验证多个交易对
for symbol in BTC/USDT ETH/USDT BNB/USDT; do
  kline validate check -s $symbol
done

# 验证整个交易所
kline validate check --exchange binance --export binance_validation.csv
```

### 数据修复流程

```bash
# 1. 发现问题
kline validate check -s BTC/USDT --show-gaps

# 2. 预览修复
kline validate repair -s BTC/USDT --dry-run

# 3. 重新下载缺失数据
kline download start -s BTC/USDT --start 2024-01-15 --end 2024-01-16

# 4. 再次验证
kline validate check -s BTC/USDT
```

### 元数据修复流程 ⭐

当发现原数据和元数据不一致时（比如手动修改了数据文件、迁移数据后等）：

```bash
# 1. 完整校验所有交易对
kline validate check --max

# 2. 或校验指定交易对
kline validate check -s BTC/USDT --max

# 3. 或校验整个交易所
kline validate check --exchange binance --max

# 说明：
# --max 参数会完整扫描所有实际数据文件，对比元数据中记录的时间范围和统计信息
# 如果发现不一致，会自动修复元数据，确保元数据与实际数据完全对应
# 适用场景：
#   - 手动删除/修改了数据文件
#   - 数据迁移后元数据不同步
#   - 元数据文件损坏或丢失
#   - 定期维护，确保数据一致性
```

### 任务恢复流程 ⭐

```bash
# 1. 查看失败的任务并交互式选择
kline download task list --status failed                      # 自动进入交互选择

# 或直接恢复指定任务
kline download task resume <task-id>

# 3. 清理已完成的任务
kline download task clean
```

### 自动化定时任务

```bash
# 编辑 crontab
crontab -e

# 每天凌晨2点更新，2:05验证
0 2 * * * kline download update -s BTC/USDT >> /var/log/kline_update.log 2>&1
5 2 * * * kline validate check -s BTC/USDT --export /var/log/validation_$(date +\%Y\%m\%d).csv >> /var/log/kline_validate.log 2>&1

# 每周日凌晨3点全量验证
0 3 * * 0 kline validate check --export /var/log/weekly_validation.csv >> /var/log/kline_validate.log 2>&1
```

## 8. 故障排查

```bash
# 数据问题
kline validate check -s BTC/USDT --show-gaps         # 查看缺失段
kline validate quality -s BTC/USDT                   # 检查质量
kline download status -s BTC/USDT                    # 查看状态

# 任务问题
kline download task list --status failed                      # 查看失败任务
kline download task list -i                                   # 交互式恢复任务
kline download task clean --status failed                     # 清理失败任务

# 配置问题
kline config validate                                 # 验证配置
kline --verbose info                                  # 详细信息

# 服务问题
kline server status                                   # 检查状态
lsof -i :8000                                         # 检查端口占用
kline server start --port 8001                        # 使用其他端口
```

## 9. 命令速查表

### 下载相关
```bash
kline download start -s BTC/USDT --start 2024-01-01  # 下载
kline download update -s BTC/USDT                    # 更新
kline download list                                  # 列表
kline download status -s BTC/USDT                    # 状态
```

### 任务管理 ⭐
```bash
kline download task list                                      # 列出任务并交互式选择
kline download task list --status failed                      # 筛选失败任务并选择
kline download task list --no-interactive                     # 仅显示列表
kline download task resume <task-id>                          # 恢复任务
kline download task delete <task-id>                          # 删除任务
kline download task clean --status failed                     # 清理失败任务
```

### 验证相关 ⭐
```bash
kline validate check -s BTC/USDT                     # 检查完整性
kline validate check --show-gaps                     # 显示缺失段
kline validate check --export report.csv             # 导出报告
kline validate check --max                           # 完整校验并修复元数据 ⭐
kline validate check -s BTC/USDT --max               # 校验指定交易对
kline validate quality -s BTC/USDT                   # 检查质量
kline validate repair -s BTC/USDT --dry-run         # 修复预览
```

### 查询相关
```bash
kline query kline -s BTC/USDT -t 1m -l 10           # 查询K线
kline query latest -s BTC/USDT                       # 最新数据
kline query stats -s BTC/USDT --period 30           # 统计信息
kline query symbols                                  # 交易对列表
```

### 配置相关
```bash
kline config show                                    # 显示配置
kline config set -k KEY -v VALUE                    # 设置配置
kline config validate                                # 验证配置
```

### 服务相关
```bash
kline server start --port 8000                       # 启动服务
kline server status                                  # 检查状态
kline server test                                    # 测试API
```

## 10. 推荐工作流程

```bash
# 第1步：初始化
kline version && kline info
kline config set -k storage.root_path -v /data/kline

# 第2步：下载数据
kline download start -s BTC/USDT --start 2024-01-01

# 第3步：验证完整性 ⭐ (重要！)
kline validate check -s BTC/USDT --show-gaps
kline validate quality -s BTC/USDT

# 第3.5步：定期元数据校验（可选）
kline validate check --max                           # 完整校验并自动修复元数据

# 第4步：查询分析
kline query kline -s BTC/USDT -t 1h --indicators sma_20,ema_50 -l 100

# 第5步：定期维护
kline download update -s BTC/USDT
kline validate check --export daily_$(date +%Y%m%d).csv
```

---

## 更多帮助

```bash
# 查看帮助
kline --help                    # 主命令帮助
kline download --help           # 下载命令帮助
kline validate --help           # 验证命令帮助

# 运行示例
python examples/validate_example.py           # Python SDK示例
bash examples/cli_validate_example.sh         # CLI验证示例

# 查看文档
cat cli/README.md              # CLI文档
cat docs/system_design.md      # 系统设计文档
```

**完整功能**:
- ✅ 数据下载和更新
- ✅ **下载任务管理** ⭐ (新增)
- ✅ **交互式任务恢复** ⭐ (新增)
- ✅ **数据完整性验证** ⭐
- ✅ **数据质量检查** ⭐
- ✅ 数据查询和分析
- ✅ 配置管理
- ✅ API服务
- ✅ 批量操作
- ✅ 自动化脚本
- ✅ 任务断点续传
