#!/bin/bash
# 
# K线数据系统 - 任务管理示例
# 
# 本脚本演示如何使用CLI管理下载任务
#

echo "=================================="
echo "K线数据任务管理示例"
echo "=================================="

# 1. 列出所有下载任务
echo -e "\n1. 列出所有下载任务"
kline download task list

# 2. 列出失败的任务
echo -e "\n2. 列出失败的任务"
kline download task list --status failed

# 3. 列出运行中的任务
echo -e "\n3. 列出运行中的任务"  
kline download task list --status running

# 4. 交互式选择并恢复任务（默认行为）
echo -e "\n4. 交互式任务恢复"
echo "使用命令: kline download task list"
echo "- 自动显示任务列表"
echo "- 如有可恢复任务，自动进入交互式选择"
echo "- 使用 ↑↓ 方向键选择任务"
echo "- 按 Enter 确认恢复"
echo "- 按 Ctrl+C 取消"

# 示例：如果有具体的任务ID
# TASK_ID="your-task-id-here"
# echo -e "\n5. 恢复指定任务"
# kline download task resume $TASK_ID

# 6. 清理已完成的任务
echo -e "\n6. 清理已完成的任务"
kline download task clean --status completed --force

# 7. 查看任务管理帮助
echo -e "\n7. 查看完整帮助信息"
kline download task --help

echo -e "\n=================================="
echo "示例完成！"
echo "=================================="

# 使用说明：
# 
# 场景1：恢复失败的下载任务
# ------------------------------
# $ kline download task list --status failed  # 自动进入交互式选择
# 
# 场景2：清理旧任务
# ------------------------------
# $ kline download task list
# $ kline download task clean --status completed
# 
# 场景3：监控下载进度
# ------------------------------
# $ kline download task list --status running
# 
# 场景4：手动恢复特定任务
# ------------------------------
# $ kline download task list
# $ kline download task resume <task-id>
#
# 注意事项：
# - 已完成的任务会自动删除，无需手动清理
# - 失败的任务会保留，可以随时恢复
# - 交互式恢复支持断点续传
