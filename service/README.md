# Service Layer - 服务层

FastAPI服务层，提供RESTful API接口对外暴露K线数据查询、指标计算等功能。

## 功能特性

- **K线数据查询**: 支持多种周期的K线数据查询
- **技术指标计算**: 支持各类技术指标在线计算
- **元数据管理**: 提供交易对元数据查询
- **数据下载**: 支持通过API触发数据下载任务
- **完整API文档**: 自动生成Swagger/OpenAPI文档

## 架构设计

```
service/
├── __init__.py          # 包入口
├── api.py               # FastAPI路由和主应用
├── models.py            # Pydantic数据模型
├── dependencies.py      # 依赖注入
├── server.py            # 服务启动脚本
└── README.md           # 说明文档
```

## 快速开始

### 1. 启动服务

```bash
# 基本启动
python -m service.server

# 指定端口和配置
python -m service.server --host 0.0.0.0 --port 8000 --config config.yaml

# 开发模式（热重载）
python -m service.server --reload --log-level DEBUG
```

### 2. 访问API文档

启动后访问：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API接口

### 健康检查

```bash
GET /
```

### K线数据查询

```bash
GET /api/v1/kline?exchange=binance&symbol=BTC/USDT&interval=1m
```

**参数:**
- `exchange` (必填): 交易所名称
- `symbol` (必填): 交易对
- `interval` (可选): K线周期，默认1m
- `start_time` (可选): 开始时间（ISO格式）
- `end_time` (可选): 结束时间（ISO格式）
- `limit` (可选): 返回条数限制

**示例:**
```bash
curl "http://localhost:8000/api/v1/kline?exchange=binance&symbol=BTC/USDT&interval=5m&limit=100"
```

### 技术指标计算

```bash
GET /api/v1/indicator?exchange=binance&symbol=BTC/USDT&interval=1m&indicator=ma&params={"period":20}
```

**参数:**
- `exchange` (必填): 交易所名称
- `symbol` (必填): 交易对
- `interval` (可选): K线周期
- `indicator` (必填): 指标名称 (ma, ema, bollinger, rsi, macd, kdj, atr, obv)
- `params` (可选): 指标参数JSON字符串
- `start_time` (可选): 开始时间
- `end_time` (可选): 结束时间
- `limit` (可选): 返回条数限制

**示例:**
```bash
# 计算MA
curl "http://localhost:8000/api/v1/indicator?exchange=binance&symbol=BTC/USDT&indicator=ma&params=%7B%22period%22:20%7D"

# 计算MACD
curl "http://localhost:8000/api/v1/indicator?exchange=binance&symbol=BTC/USDT&indicator=macd&params=%7B%22fast_period%22:12,%22slow_period%22:26,%22signal_period%22:9%7D"
```

### 获取交易对列表

```bash
GET /api/v1/symbols?exchange=binance
```

**参数:**
- `exchange` (可选): 交易所过滤

### 获取元数据

```bash
GET /api/v1/metadata?exchange=binance&symbol=BTC/USDT
```

**参数:**
- `exchange` (必填): 交易所名称
- `symbol` (必填): 交易对

### 下载数据

```bash
POST /api/v1/download?exchange=binance&symbol=BTC/USDT&start_time=2024-01-01T00:00:00Z
```

**参数:**
- `exchange` (必填): 交易所名称
- `symbol` (必填): 交易对
- `start_time` (可选): 开始时间
- `end_time` (可选): 结束时间

## 响应格式

### 成功响应

```json
{
  "success": true,
  "data": [...],
  "total": 100,
  "exchange": "binance",
  "symbol": "BTC/USDT",
  "interval": "1m"
}
```

### 错误响应

```json
{
  "success": false,
  "error": "错误信息",
  "status_code": 500
}
```

## 配置选项

服务层会从SDK层继承配置，主要配置项：

```yaml
service:
  host: "0.0.0.0"
  port: 8000
  workers: 4
  log_level: "INFO"
  cors_origins:
    - "*"
```

## 部署建议

### 生产环境部署

1. **使用多个workers**:
```bash
python -m service.server --workers 4 --host 0.0.0.0 --port 8000
```

2. **使用Gunicorn**:
```bash
gunicorn service.api:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

3. **使用Docker**:
```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "-m", "service.server", "--workers", "4"]
```

### Nginx反向代理

```nginx
server {
    listen 80;
    server_name api.example.com;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 性能优化

1. **启用缓存**: SDK层已实现LRU缓存
2. **连接池**: 使用连接池管理数据库连接
3. **异步处理**: 所有路由都是异步的
4. **分页查询**: 使用limit参数控制返回数据量
5. **压缩响应**: 启用gzip压缩

## 监控和日志

- 日志输出到标准输出，可通过日志收集系统收集
- 支持结构化日志
- 建议配合Prometheus + Grafana监控
- 可使用APM工具（如DataDog, NewRelic）

## 依赖项

```
fastapi >= 0.104.0
uvicorn >= 0.24.0
pydantic >= 2.0.0
```

## 注意事项

1. **认证和授权**: 生产环境建议添加API认证
2. **速率限制**: 建议添加速率限制防止滥用
3. **CORS配置**: 根据需要配置跨域访问策略
4. **错误处理**: 已实现全局异常处理
5. **健康检查**: 实现了基本健康检查接口
