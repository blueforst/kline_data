#!/bin/bash
# CLI使用示例

echo "=== K线数据系统 CLI 示例 ==="
echo ""

# 1. 查看版本
echo "1. 查看版本信息"
kline version
echo ""

# 2. 查看系统信息
echo "2. 查看系统信息"
kline info
echo ""

# 3. 配置管理
echo "3. 配置管理"
echo "  3.1 显示所有配置"
kline config show
echo ""

echo "  3.2 显示特定配置项"
kline config show --key storage.root_path
echo ""

echo "  3.3 列出所有配置项"
kline config list
echo ""

echo "  3.4 设置配置项"
kline config set --key memory.max_cache_size_mb --value 512
echo ""

echo "  3.5 验证配置"
kline config validate
echo ""

echo "  3.6 显示配置文件路径"
kline config path
echo ""

echo "  3.7 导出配置"
kline config export --output /tmp/config_backup.yaml
echo ""

# 4. 数据下载
echo "4. 数据下载"
echo "  4.1 下载K线数据"
kline download start --symbol BTC/USDT --exchange binance --start 2024-01-01 --end 2024-01-31
echo ""

echo "  4.2 更新K线数据（增量）"
kline download update --symbol BTC/USDT --exchange binance
echo ""

echo "  4.3 列出下载任务"
kline download list
echo ""

echo "  4.4 查看数据状态"
kline download status --symbol BTC/USDT
echo ""

# 5. 数据查询
echo "5. 数据查询"
echo "  5.1 查询K线数据"
kline query kline --symbol BTC/USDT --timeframe 1m --limit 10
echo ""

echo "  5.2 查询最新数据"
kline query latest --symbol BTC/USDT --timeframe 1m --count 5
echo ""

echo "  5.3 查询数据范围"
kline query range --symbol BTC/USDT
echo ""

echo "  5.4 列出所有交易对"
kline query symbols
echo ""

echo "  5.5 查询统计信息"
kline query stats --symbol BTC/USDT --period 30
echo ""

echo "  5.6 带指标查询"
kline query kline --symbol BTC/USDT --timeframe 1h --indicators sma_20,ema_50 --limit 100
echo ""

echo "  5.7 导出到CSV"
kline query kline --symbol BTC/USDT --timeframe 1d --output /tmp/btc_daily.csv
echo ""

# 6. 服务管理
echo "6. API服务管理"
echo "  6.1 显示服务配置"
kline server config
echo ""

echo "  6.2 启动服务（后台）"
# kline server start --host 0.0.0.0 --port 8000 &
echo "kline server start --host 0.0.0.0 --port 8000"
echo ""

echo "  6.3 开发模式启动（自动重载）"
# kline server start --reload --log-level debug
echo "kline server start --reload --log-level debug"
echo ""

echo "  6.4 检查服务状态"
kline server status
echo ""

echo "  6.5 测试API端点"
kline server test
echo ""

# 7. 高级用法
echo "7. 高级用法"
echo "  7.1 使用自定义配置文件"
kline --config /path/to/custom/config.yaml info
echo ""

echo "  7.2 详细输出模式"
kline --verbose download status --symbol BTC/USDT
echo ""

echo "  7.3 管道操作"
kline query symbols | grep BTC
echo ""

echo "  7.4 批量下载"
for symbol in BTC/USDT ETH/USDT BNB/USDT; do
    kline download update --symbol $symbol --exchange binance
done
echo ""

echo "=== 示例完成 ==="
