#!/bin/bash
# CLI数据验证示例脚本

echo "=========================================="
echo "K线数据完整性验证 - CLI示例"
echo "=========================================="

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 示例1: 检查单个交易对的完整性
echo -e "\n${CYAN}示例1: 检查单个交易对的完整性${NC}"
echo "命令: kline validate check --symbol BTC/USDT"
echo "----------------------------------------"
python -m cli.main validate check --symbol BTC/USDT

# 示例2: 显示详细的缺失数据范围
echo -e "\n${CYAN}示例2: 显示详细的缺失数据范围${NC}"
echo "命令: kline validate check --symbol BTC/USDT --show-gaps"
echo "----------------------------------------"
python -m cli.main validate check --symbol BTC/USDT --show-gaps

# 示例3: 检查数据质量
echo -e "\n${CYAN}示例3: 检查数据质量${NC}"
echo "命令: kline validate quality --symbol BTC/USDT"
echo "----------------------------------------"
python -m cli.main validate quality --symbol BTC/USDT

# 示例4: 检查所有交易对并导出报告
echo -e "\n${CYAN}示例4: 检查所有交易对并导出报告${NC}"
echo "命令: kline validate check --export validation_report.csv"
echo "----------------------------------------"
python -m cli.main validate check --export validation_report.csv

if [ -f "validation_report.csv" ]; then
    echo -e "${GREEN}✓ 报告已导出到: validation_report.csv${NC}"
    echo "前几行内容:"
    head -n 5 validation_report.csv
fi

# 示例5: 检查特定交易所的所有数据
echo -e "\n${CYAN}示例5: 检查特定交易所的所有数据${NC}"
echo "命令: kline validate check --exchange binance"
echo "----------------------------------------"
python -m cli.main validate check --exchange binance

# 示例6: 预览数据修复计划
echo -e "\n${CYAN}示例6: 预览数据修复计划${NC}"
echo "命令: kline validate repair --symbol BTC/USDT --dry-run"
echo "----------------------------------------"
python -m cli.main validate repair --symbol BTC/USDT --dry-run

# 示例7: 批量验证多个交易对
echo -e "\n${CYAN}示例7: 批量验证多个交易对${NC}"
echo "----------------------------------------"
for symbol in BTC/USDT ETH/USDT BNB/USDT; do
    echo -e "\n${YELLOW}验证 $symbol ...${NC}"
    python -m cli.main validate check --symbol "$symbol"
done

# 示例8: 完整校验并修复元数据 (新增) ⭐
echo -e "\n${CYAN}示例8: 完整校验并修复元数据 (--max)${NC}"
echo "说明: 对比实际数据与元数据，自动修复不一致问题"
echo "命令: kline validate check --symbol BTC/USDT --max"
echo "----------------------------------------"
python -m cli.main validate check --symbol BTC/USDT --max

echo -e "\n${GREEN}=========================================="
echo "✓ 所有示例运行完成！"
echo "==========================================${NC}"

echo -e "\n${CYAN}快速参考:${NC}"
echo "  检查完整性:   kline validate check --symbol BTC/USDT"
echo "  显示缺失段:   kline validate check --symbol BTC/USDT --show-gaps"
echo "  检查质量:     kline validate quality --symbol BTC/USDT"
echo "  导出报告:     kline validate check --export report.csv"
echo "  修复预览:     kline validate repair --symbol BTC/USDT --dry-run"
echo "  完整校验:     kline validate check --max  ⭐ (新增)"
echo "  查看帮助:     kline validate --help"
