# 快速开始指南

## 5分钟上手K线数据系统

### 第一步：安装

```bash
# 进入项目目录
cd /path/to/kline_data

# 创建虚拟环境（可选）
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 开发模式安装
pip install -e .
```

### 第二步：验证安装

```bash
# 查看版本
kline version

# 应该看到:
# K线数据系统 v1.0.0
# 基于Python的高性能K线数据存储与分析系统
```

### 第三步：查看配置

```bash
# 显示系统信息
kline info

# 查看配置
kline config show
```

### 第四步：下载数据（支持多种时间周期）

**注意**: 需要配置CCXT相关的交易所API（如有代理需求，请先配置代理）

```bash
# 下载1秒K线数据（默认）
kline download start \
    --symbol BTC/USDT \
    --start 2024-01-01 \
    --end 2024-01-31

# 下载1小时K线数据
kline download start \
    --symbol BTC/USDT \
    --start 2024-01-01 \
    --interval 1h

# 下载4小时K线数据（简写形式）
kline download start -s BTC/USDT --start 2024-01-01 -i 4h

# 下载1天K线数据
kline download start -s BTC/USDT --start 2024-01-01 -i 1d

# 从交易所最早可用时间开始下载
kline download start \
  --symbol BTC/USDT \
  --exchange binance \
  --start 2024-01-01 \
  --end 2024-01-02

# ⭐ 新功能：从交易所最早可用时间开始下载全部历史数据
kline download start \
  --symbol BTC/USDT \
  --exchange binance \
  --start all

# 查看下载状态
kline download status --symbol BTC/USDT
```

### 第五步：验证数据完整性 ⭐

**新功能！** 验证下载的数据完整性：

```bash
# 检查数据完整性
kline validate check --symbol BTC/USDT

# 显示详细的缺失数据范围
kline validate check --symbol BTC/USDT --show-gaps

# 检查数据质量（完整性、重复率、异常值等）
kline validate quality --symbol BTC/USDT

# 导出验证报告
kline validate check --export validation_report.csv

# 预览需要修复的内容
kline validate repair --symbol BTC/USDT --dry-run
```

### 第六步：查询数据

```bash
# 查询1分钟K线（最新10条）
kline query kline \
  --symbol BTC/USDT \
  --timeframe 1m \
  --limit 10

# 查询并添加技术指标
kline query kline \
  --symbol BTC/USDT \
  --timeframe 1h \
  --indicators sma_20,ema_50 \
  --limit 100

# 导出到CSV
kline query kline \
  --symbol BTC/USDT \
  --timeframe 1d \
  --output btc_daily.csv
```

### 第七步：启动API服务

```bash
# 启动服务
kline server start

# 在浏览器中打开
# http://localhost:8000/docs

# 测试API
curl "http://localhost:8000/health"
```

## Python SDK 使用

```python
from kline_data import KlineClient

# 创建客户端
with KlineClient() as client:
    # 下载数据（如果还没有）
    client.download(
        symbol='BTC/USDT',
        exchange='binance',
        start_time='2024-01-01',
        end_time='2024-01-02'
    )
    
    # 查询K线数据
    df = client.get_kline(
        symbol='BTC/USDT',
        timeframe='1m',
        limit=100
    )
    print(f"获取到 {len(df)} 条数据")
    
    # 重采样为1小时
    df_1h = client.resample(df, '1h')
    print(f"重采样后 {len(df_1h)} 条数据")
    
    # 添加技术指标
    df = client.add_indicators(df, ['sma_20', 'ema_50', 'macd'])
    print(df.head())
```

## 常见问题

### Q1: 导入模块失败

**问题**: `ImportError: No module named 'kline_data'`

**解决**:
```bash
# 确保在项目根目录
cd /path/to/kline_data

# 重新安装
pip install -e .
```

### Q2: CLI命令找不到

**问题**: `kline: command not found`

**解决**:
```bash
# 检查是否正确安装
pip list | grep kline

# 如果没有，重新安装
pip install -e .

# 或者使用完整路径
python -m cli.main version
```

### Q3: 配置文件未找到

**问题**: `FileNotFoundError: config/config.yaml`

**解决**:
```bash
# 创建配置文件
cp config/config.yaml config/config.local.yaml

# 或使用绝对路径
kline --config /absolute/path/to/config.yaml info
```

### Q4: 下载数据失败

**问题**: 无法连接到交易所API

**解决**:
```bash
# 检查网络连接
ping binance.com

# 如果需要代理，配置代理
kline config set --key ccxt.proxy --value "http://your-proxy:port"

# 或编辑配置文件
vim config/config.yaml
# 修改 ccxt.proxy 配置
```

### Q5: API服务无法启动

**问题**: 端口被占用

**解决**:
```bash
# 检查端口占用
lsof -i :8000

# 使用其他端口
kline server start --port 8001

# 或停止占用端口的进程
kill -9 <PID>
```

## 下一步

### 学习更多

- 📖 [完整文档](docs/system_design.md)
- 📖 [CLI使用指南](docs/cli_guide.md)
- 📖 [项目总结](docs/project_summary.md)

### 运行测试

```bash
# 运行所有测试
pytest tests/ -v

# 运行特定测试
pytest tests/test_config.py -v

# 查看覆盖率
pytest --cov=. --cov-report=html
open htmlcov/index.html
```

### 查看示例

```bash
# Python示例
python examples/config_example.py

# CLI示例
bash examples/cli_example.sh
```

### 配置管理

```bash
# 查看所有配置项
kline config list

# 修改存储路径
kline config set --key storage.root_path --value /data/kline

# 修改缓存大小
kline config set --key memory.max_cache_size_mb --value 2048

# 导出配置
kline config export --output my_config.yaml
```

### 数据管理与验证 ⭐

```bash
# 列出所有交易对
kline query symbols

# 查看数据范围
kline query range --symbol BTC/USDT

# 验证数据完整性
kline validate check --symbol BTC/USDT --show-gaps

# 更新数据（增量）
kline download update --symbol BTC/USDT

# 更新后验证
kline validate check --symbol BTC/USDT

# 批量更新并验证
for symbol in BTC/USDT ETH/USDT BNB/USDT; do
  echo "更新 $symbol ..."
  kline download update --symbol $symbol
  kline validate check --symbol $symbol
done

# 导出每日验证报告
kline validate check --export daily_validation_$(date +%Y%m%d).csv
```

### API使用

```bash
# 启动服务
kline server start

# 测试健康检查
curl http://localhost:8000/health

# 查询K线
curl "http://localhost:8000/kline/BTC/USDT?timeframe=1m&limit=10"

# 查看API文档
# 浏览器打开: http://localhost:8000/docs
```

## 生产环境部署

### 使用Systemd

创建服务文件 `/etc/systemd/system/kline-api.service`:

```ini
[Unit]
Description=Kline Data API Service
After=network.target

[Service]
Type=simple
User=kline
WorkingDirectory=/opt/kline_data
ExecStart=/usr/local/bin/kline server start --host 0.0.0.0 --port 8000 --workers 4
Restart=always

[Install]
WantedBy=multi-user.target
```

启动服务:

```bash
sudo systemctl daemon-reload
sudo systemctl enable kline-api
sudo systemctl start kline-api
sudo systemctl status kline-api
```

### 使用Docker

```bash
# 构建镜像
docker build -t kline-data:latest .

# 运行容器
docker run -d \
  --name kline-api \
  -p 8000:8000 \
  -v /data/kline:/data/kline \
  kline-data:latest
```

### 定时任务

添加到crontab进行定时更新和验证:

```bash
# 编辑crontab
crontab -e

# 添加以下行（每天凌晨2点更新数据，2:05验证完整性）
0 2 * * * /usr/local/bin/kline download update --symbol BTC/USDT >> /var/log/kline/update.log 2>&1
5 2 * * * /usr/local/bin/kline validate check --symbol BTC/USDT --export /var/log/kline/validation_$(date +\%Y\%m\%d).csv >> /var/log/kline/validate.log 2>&1

# 每周日凌晨3点进行全量验证
0 3 * * 0 /usr/local/bin/kline validate check --export /var/log/kline/weekly_validation_$(date +\%Y\%m\%d).csv >> /var/log/kline/validate.log 2>&1
```

## 获取帮助

```bash
# CLI帮助
kline --help
kline download --help
kline query --help

# Python帮助
python -c "from kline_data import KlineClient; help(KlineClient)"

# 查看文档
ls docs/
```

## 反馈和贡献

如有问题或建议，请：

1. 查看文档: `docs/`
2. 运行测试: `pytest tests/ -v`
3. 查看日志: `logs/kline.log`

---

**祝使用愉快！** 🎉
