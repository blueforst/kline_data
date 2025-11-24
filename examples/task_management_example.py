"""
K线数据系统 - 任务管理Python API示例

演示如何通过Python API管理下载任务
"""

from datetime import datetime
from rich.console import Console
from rich.table import Table

from config import get_config
from storage.metadata_manager import MetadataManager
from storage.models import TaskStatus
from storage.downloader import DataDownloader

console = Console()


def list_tasks_example():
    """示例1: 列出所有任务"""
    console.print("\n[bold cyan]示例1: 列出所有任务[/bold cyan]")
    
    config = get_config()
    metadata_mgr = MetadataManager(config)
    
    # 获取所有任务
    tasks = metadata_mgr.list_download_tasks()
    
    if not tasks:
        console.print("[yellow]没有任务[/yellow]")
        return
    
    # 创建表格
    table = Table(title="下载任务")
    table.add_column("任务ID", style="cyan")
    table.add_column("交易对", style="green")
    table.add_column("状态", style="yellow")
    table.add_column("进度", justify="right")
    
    for task in tasks:
        progress = f"{task.progress.percentage:.1f}%" if task.progress else "N/A"
        table.add_row(
            task.task_id[:12] + "...",
            task.symbol,
            task.status.value,
            progress,
        )
    
    console.print(table)


def list_failed_tasks_example():
    """示例2: 列出失败的任务"""
    console.print("\n[bold cyan]示例2: 列出失败的任务[/bold cyan]")
    
    config = get_config()
    metadata_mgr = MetadataManager(config)
    
    # 获取失败的任务
    failed_tasks = metadata_mgr.list_download_tasks(status=TaskStatus.FAILED)
    
    if not failed_tasks:
        console.print("[green]没有失败的任务[/green]")
        return
    
    for task in failed_tasks:
        console.print(f"\n[red]失败任务:[/red]")
        console.print(f"  ID: {task.task_id}")
        console.print(f"  交易对: {task.symbol}")
        console.print(f"  错误: {', '.join(task.errors)}")


def resume_task_example(task_id: str):
    """示例3: 恢复下载任务"""
    console.print(f"\n[bold cyan]示例3: 恢复任务 {task_id}[/bold cyan]")
    
    config = get_config()
    metadata_mgr = MetadataManager(config)
    
    # 获取任务
    task = metadata_mgr.get_download_task(task_id)
    
    if not task:
        console.print(f"[red]任务不存在: {task_id}[/red]")
        return
    
    if task.status == TaskStatus.COMPLETED:
        console.print("[yellow]任务已完成[/yellow]")
        return
    
    console.print(f"恢复任务: {task.symbol} ({task.exchange})")
    console.print(f"时间范围: {task.start_time} ~ {task.end_time}")
    
    # 解析时间
    from utils.timezone import parse_datetime
    start_time = parse_datetime(task.start_time)
    end_time = parse_datetime(task.end_time)
    
    # 获取断点
    checkpoint = task.checkpoint.last_timestamp if task.checkpoint else None
    
    if checkpoint:
        console.print(f"从断点继续: {checkpoint}")
    
    # 创建下载器并恢复
    downloader = DataDownloader(
        exchange=task.exchange,
        symbol=task.symbol,
        config=config,
    )
    
    try:
        downloader.download_range(
            start_time=start_time,
            end_time=end_time,
            checkpoint=checkpoint,
            task_id=task.task_id,
        )
        console.print("[green]✓ 任务恢复完成[/green]")
    except Exception as e:
        console.print(f"[red]✗ 恢复失败: {e}[/red]")


def clean_completed_tasks_example():
    """示例4: 清理已完成的任务"""
    console.print("\n[bold cyan]示例4: 清理已完成的任务[/bold cyan]")
    
    config = get_config()
    metadata_mgr = MetadataManager(config)
    
    # 获取已完成的任务
    completed_tasks = metadata_mgr.list_download_tasks(status=TaskStatus.COMPLETED)
    
    if not completed_tasks:
        console.print("[yellow]没有已完成的任务需要清理[/yellow]")
        return
    
    console.print(f"发现 {len(completed_tasks)} 个已完成的任务")
    
    # 删除任务
    deleted = 0
    for task in completed_tasks:
        if metadata_mgr.delete_download_task(task.task_id):
            deleted += 1
    
    console.print(f"[green]✓ 已清理 {deleted} 个任务[/green]")


def get_task_statistics_example():
    """示例5: 获取任务统计"""
    console.print("\n[bold cyan]示例5: 任务统计[/bold cyan]")
    
    config = get_config()
    metadata_mgr = MetadataManager(config)
    
    # 获取所有任务
    all_tasks = metadata_mgr.list_download_tasks()
    
    # 统计各状态的任务数
    stats = {
        TaskStatus.PENDING: 0,
        TaskStatus.RUNNING: 0,
        TaskStatus.COMPLETED: 0,
        TaskStatus.FAILED: 0,
        TaskStatus.CANCELLED: 0,
    }
    
    for task in all_tasks:
        stats[task.status] += 1
    
    # 创建统计表格
    table = Table(title="任务统计")
    table.add_column("状态", style="cyan")
    table.add_column("数量", justify="right", style="green")
    
    for status, count in stats.items():
        table.add_row(status.value, str(count))
    
    table.add_row("[bold]总计[/bold]", f"[bold]{len(all_tasks)}[/bold]")
    
    console.print(table)


def monitor_task_progress_example(task_id: str):
    """示例6: 监控任务进度"""
    console.print(f"\n[bold cyan]示例6: 监控任务进度 {task_id}[/bold cyan]")
    
    config = get_config()
    metadata_mgr = MetadataManager(config)
    
    # 获取任务
    task = metadata_mgr.get_download_task(task_id)
    
    if not task:
        console.print(f"[red]任务不存在: {task_id}[/red]")
        return
    
    # 显示任务信息
    console.print(f"任务ID: {task.task_id}")
    console.print(f"交易对: {task.symbol}")
    console.print(f"交易所: {task.exchange}")
    console.print(f"状态: {task.status.value}")
    
    if task.progress:
        console.print(f"进度: {task.progress.percentage:.1f}%")
        console.print(f"已下载: {task.progress.downloaded_records:,} 条")
        console.print(f"预计完成: {task.progress.estimated_completion}")
    
    if task.checkpoint:
        console.print(f"断点: {task.checkpoint.last_timestamp}")


if __name__ == "__main__":
    """
    运行示例
    
    使用方法:
        python examples/task_management_example.py
    """
    
    console.print("[bold green]K线数据系统 - 任务管理示例[/bold green]")
    
    # 示例1: 列出所有任务
    list_tasks_example()
    
    # 示例2: 列出失败的任务
    list_failed_tasks_example()
    
    # 示例5: 获取任务统计
    get_task_statistics_example()
    
    # 其他示例需要提供具体的任务ID
    # resume_task_example("your-task-id")
    # monitor_task_progress_example("your-task-id")
    
    console.print("\n[bold green]✓ 所有示例运行完成[/bold green]")
    
    # 使用说明
    console.print("\n[cyan]更多用法:[/cyan]")
    console.print("  - resume_task_example(task_id)         # 恢复任务")
    console.print("  - clean_completed_tasks_example()      # 清理已完成任务")
    console.print("  - monitor_task_progress_example(id)    # 监控进度")
