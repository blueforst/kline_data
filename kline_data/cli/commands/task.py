"""
下载任务管理命令模块
"""
import typer
from typing import Optional
from rich.console import Console
from rich.table import Table
from rich.prompt import Confirm
import inquirer

from ...storage.metadata_manager import MetadataManager
from ...storage.models import TaskStatus
from ...storage.downloader import DataDownloader
from ...config import get_config
from ...utils.timezone import timestamp_to_datetime, format_datetime, format_time_for_display, format_time_for_display

app = typer.Typer(help="下载任务管理命令")
console = Console()


@app.command("list")
def list_tasks(
    status: Optional[str] = typer.Option(None, "--status", help="筛选状态 (pending/running/completed/failed/cancelled)"),
    no_interactive: bool = typer.Option(False, "--no-interactive", help="不进入交互式模式，仅显示列表"),
):
    """
    列出下载任务并交互式选择恢复
    
    默认显示任务列表后，如有可恢复任务会自动进入交互式选择。
    
    示例:
        kline download task list                      # 列出任务并交互式选择
        kline download task list --status failed      # 筛选失败任务并交互式选择
        kline download task list --no-interactive     # 仅显示列表，不交互
    """
    try:
        config = get_config()
        metadata_mgr = MetadataManager(config)
        
        # 过滤状态
        task_status = None
        if status:
            try:
                task_status = TaskStatus(status)
            except ValueError:
                console.print(f"[red]✗ 错误:[/red] 无效的状态: {status}")
                console.print("有效状态: pending, running, completed, failed, cancelled")
                raise typer.Exit(1)
        
        # 获取任务列表
        tasks = metadata_mgr.list_download_tasks(status=task_status)
        
        if not tasks:
            console.print("[yellow]未找到任务[/yellow]")
            return
        
        # 显示任务表格
        table = Table(title="下载任务列表")
        table.add_column("序号", style="cyan", justify="right")
        table.add_column("任务ID", style="blue")
        table.add_column("交易对", style="green")
        table.add_column("交易所", style="magenta")
        table.add_column("开始时间", style="yellow")
        table.add_column("结束时间", style="yellow")
        table.add_column("状态", style="bold")
        table.add_column("进度", justify="right")
        table.add_column("创建时间", style="dim")
        
        status_colors = {
            TaskStatus.PENDING: "yellow",
            TaskStatus.RUNNING: "blue",
            TaskStatus.COMPLETED: "green",
            TaskStatus.FAILED: "red",
            TaskStatus.CANCELLED: "dim",
        }
        
        for idx, task in enumerate(tasks, 1):
            status_color = status_colors.get(task.status, "white")
            progress_text = f"{task.progress.percentage:.1f}%" if task.progress else "N/A"
            
            # 使用统一的时区转换函数
            table.add_row(
                str(idx),
                task.task_id[:8] + "...",
                task.symbol,
                task.exchange,
                format_time_for_display(task.start_time),
                format_time_for_display(task.end_time),
                f"[{status_color}]{task.status.value}[/{status_color}]",
                progress_text,
                format_time_for_display(task.created_at),
            )
        
        console.print(table)
        console.print(f"\n共 [bold]{len(tasks)}[/bold] 个任务")
        
        # 默认进入交互式模式（除非指定 --no-interactive）
        if not no_interactive and tasks:
            _interactive_resume(tasks, metadata_mgr, config)
            
    except typer.Exit:
        # typer.Exit 需要重新抛出
        raise
    except Exception as e:
        console.print(f"[red]✗ 错误:[/red] {e}")
        raise typer.Exit(1)


def _interactive_resume(tasks, metadata_mgr, config):
    """交互式选择并恢复任务"""
    
    # 过滤出可恢复的任务（失败或挂起的）
    resumable_tasks = [t for t in tasks if t.status in [TaskStatus.FAILED, TaskStatus.PENDING, TaskStatus.CANCELLED]]
    
    if not resumable_tasks:
        console.print("\n[yellow]没有可恢复的任务（仅失败、挂起或取消的任务可恢复）[/yellow]")
        return
    
    # 创建选择列表
    choices = []
    for task in resumable_tasks:
        progress_text = f"{task.progress.percentage:.1f}%" if task.progress else "0%"
        choice_text = f"{task.symbol} ({task.exchange}) | {task.start_time} ~ {task.end_time} | {task.status.value} | {progress_text}"
        choices.append((choice_text, task))
    
    # 使用inquirer进行选择
    try:
        questions = [
            inquirer.List(
                'task',
                message="选择要恢复的任务（使用↑↓方向键选择，回车确认）",
                choices=[c[0] for c in choices],
            ),
        ]
        answers = inquirer.prompt(questions)
        
        if not answers:
            console.print("\n[yellow]已取消[/yellow]")
            return
        
        # 找到选中的任务
        selected_text = answers['task']
        selected_task = None
        for choice_text, task in choices:
            if choice_text == selected_text:
                selected_task = task
                break
        
        if not selected_task:
            return
        
        # 确认恢复
        console.print(f"\n[cyan]选中任务:[/cyan]")
        console.print(f"  任务ID: {selected_task.task_id}")
        console.print(f"  交易对: {selected_task.symbol}")
        console.print(f"  交易所: {selected_task.exchange}")
        
        # 使用统一的时区转换函数
        start_time_display = format_time_for_display(selected_task.start_time)
        end_time_display = format_time_for_display(selected_task.end_time)

        console.print(f"  时间范围: {start_time_display} ~ {end_time_display}")
        console.print(f"  状态: {selected_task.status.value}")
        
        if selected_task.errors:
            console.print(f"  错误信息: {', '.join(selected_task.errors[:3])}")
        
        if Confirm.ask("\n是否恢复此任务？"):
            try:
                _resume_task(selected_task, metadata_mgr, config)
            except KeyboardInterrupt:
                # 传播KeyboardInterrupt，不作为错误处理
                raise
        else:
            console.print("[yellow]已取消恢复[/yellow]")
    
    except KeyboardInterrupt:
        console.print("\n\n[yellow]已取消[/yellow]")
    except typer.Exit:
        # typer.Exit 需要重新抛出，不应该被捕获
        raise
    except Exception as e:
        console.print(f"\n[red]✗ 选择错误:[/red] {e}")


def _resume_task(task, metadata_mgr, config):
    """恢复下载任务"""
    from datetime import datetime
    from ...utils.timezone import parse_datetime
    
    console.print(f"\n[cyan]开始恢复下载...[/cyan]")
    
    try:
        # 解析时间
        start_time = parse_datetime(task.start_time)
        end_time = parse_datetime(task.end_time)
        
        # 获取断点
        checkpoint = task.checkpoint.last_timestamp if task.checkpoint else None
        
        if checkpoint:
            checkpoint_dt = timestamp_to_datetime(checkpoint)
            console.print(f"从断点恢复: {format_datetime(checkpoint_dt, for_display=True)}")

        # 恢复下载 - 在 download_range 内部会先打印缺失范围信息，然后才开始下载
        # 进度回调会在实际下载开始后才被调用
        from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>4.1f}%"),
            TextColumn("•"),
            TextColumn("[cyan]{task.fields[downloaded]:,}/{task.fields[total_records]:,}[/cyan] 条"),
            console=console,
        ) as progress:
            progress_task = progress.add_task("下载中...", total=100, downloaded=0, total_records=0, visible=False)
            progress_stopped = False

            def stop_progress():
                nonlocal progress_stopped
                if progress_stopped:
                    return
                progress_stopped = True
                # 隐藏并停止进度条，防止中断时继续渲染
                progress.update(progress_task, visible=False)
                progress.stop()

            # 创建下载器并绑定中断处理器，以便尽快停止进度渲染
            downloader = DataDownloader(
                exchange=task.exchange,
                symbol=task.symbol,
                config=config,
                interrupt_handler=stop_progress,
            )
            
            def update_progress(percentage: float, downloaded_records: int, total_records: int):
                # 如果进度已停止或下载器被中断，不再更新
                if progress_stopped or downloader._interrupted:
                    return
                # 首次调用时显示进度条
                if not progress.tasks[progress_task].visible:
                    progress.update(progress_task, visible=True)
                progress.update(progress_task, completed=percentage, downloaded=downloaded_records, total_records=total_records)
            
            downloader.progress_callback = update_progress
            
            try:
                # 执行下载
                downloader.download_range(
                    start_time=start_time,
                    end_time=end_time,
                    checkpoint=checkpoint,
                    task_id=task.task_id,
                )
            except KeyboardInterrupt:
                # 用户中断时立即停止进度更新
                stop_progress()
                raise
            finally:
                # 确保进度条总是被停止
                if not progress_stopped:
                    progress.stop()
        
        console.print(f"\n[green]✓[/green] 任务恢复完成!")
        
    except KeyboardInterrupt:
        # KeyboardInterrupt 特殊处理，避免显示为错误
        console.print(f"\n已取消")
        raise typer.Exit(0)
    except Exception as e:
        console.print(f"[red]✗ 恢复失败:[/red] {e}")
        raise typer.Exit(1)


@app.command("resume")
def resume_task(
    task_id: str = typer.Argument(..., help="任务ID"),
):
    """
    恢复指定的下载任务
    
    示例:
        kline download task resume <task-id>
    """
    try:
        config = get_config()
        metadata_mgr = MetadataManager(config)
        
        # 获取任务
        task = metadata_mgr.get_download_task(task_id)
        
        if not task:
            console.print(f"[red]✗ 错误:[/red] 未找到任务: {task_id}")
            raise typer.Exit(1)
        
        if task.status == TaskStatus.COMPLETED:
            console.print(f"[yellow]任务已完成，无需恢复[/yellow]")
            return
        
        if task.status == TaskStatus.RUNNING:
            console.print(f"[yellow]任务正在运行中[/yellow]")
            return
        
        _resume_task(task, metadata_mgr, config)
        
    except typer.Exit:
        # typer.Exit 需要重新抛出
        raise
    except Exception as e:
        console.print(f"[red]✗ 错误:[/red] {e}")
        raise typer.Exit(1)


@app.command("delete")
def delete_task(
    task_id: str = typer.Argument(..., help="任务ID"),
    force: bool = typer.Option(False, "--force", "-f", help="强制删除，不提示确认"),
):
    """
    删除下载任务
    
    示例:
        kline download task delete <task-id>
        kline download task delete <task-id> --force
    """
    try:
        config = get_config()
        metadata_mgr = MetadataManager(config)
        
        # 获取任务
        task = metadata_mgr.get_download_task(task_id)
        
        if not task:
            console.print(f"[red]✗ 错误:[/red] 未找到任务: {task_id}")
            raise typer.Exit(1)
        
        # 确认删除
        if not force:
            console.print(f"\n[cyan]任务信息:[/cyan]")
            console.print(f"  任务ID: {task.task_id}")
            console.print(f"  交易对: {task.symbol}")
            console.print(f"  交易所: {task.exchange}")
            console.print(f"  状态: {task.status.value}")
            
            if not Confirm.ask("\n确认删除此任务？"):
                console.print("[yellow]已取消删除[/yellow]")
                return
        
        # 删除任务
        if metadata_mgr.delete_download_task(task_id):
            console.print(f"[green]✓[/green] 任务已删除")
        else:
            console.print(f"[red]✗ 错误:[/red] 删除失败")
            raise typer.Exit(1)
            
    except Exception as e:
        console.print(f"[red]✗ 错误:[/red] {e}")
        raise typer.Exit(1)


@app.command("clean")
def clean_tasks(
    status: str = typer.Option("completed", "--status", help="清理指定状态的任务 (completed/failed/cancelled/all)"),
    force: bool = typer.Option(False, "--force", "-f", help="强制清理，不提示确认"),
    system_files: bool = typer.Option(False, "--system-files", help="清理系统隐藏文件（如macOS的._文件）"),
):
    """
    批量清理任务
    
    示例:
        kline download task clean                    # 清理已完成的任务
        kline download task clean --status failed    # 清理失败的任务
        kline download task clean --status all       # 清理所有任务
        kline download task clean --system-files     # 清理系统隐藏文件
    """
    try:
        config = get_config()
        metadata_mgr = MetadataManager(config)
        
        # 清理系统隐藏文件
        if system_files:
            from pathlib import Path
            tasks_dir = metadata_mgr.metadata_dir / 'tasks'
            if tasks_dir.exists():
                hidden_files = [f for f in tasks_dir.iterdir() if f.name.startswith('.') or f.name.startswith('._')]
                if hidden_files:
                    console.print(f"\n发现 {len(hidden_files)} 个系统隐藏文件:")
                    for f in hidden_files:
                        console.print(f"  - {f.name}")
                    
                    if not force and not Confirm.ask("\n确认删除这些文件？"):
                        console.print("[yellow]已取消[/yellow]")
                        return
                    
                    deleted = 0
                    for f in hidden_files:
                        try:
                            f.unlink()
                            deleted += 1
                        except Exception as e:
                            console.print(f"[red]无法删除 {f.name}: {e}[/red]")
                    
                    console.print(f"[green]✓[/green] 已删除 {deleted} 个系统文件")
                else:
                    console.print("[green]没有找到系统隐藏文件[/green]")
            return
        
        # 确定要清理的状态
        if status == "all":
            tasks = metadata_mgr.list_download_tasks()
        else:
            try:
                task_status = TaskStatus(status)
                tasks = metadata_mgr.list_download_tasks(status=task_status)
            except ValueError:
                console.print(f"[red]✗ 错误:[/red] 无效的状态: {status}")
                console.print("有效状态: completed, failed, cancelled, all")
                raise typer.Exit(1)
        
        if not tasks:
            console.print(f"[yellow]没有 {status} 状态的任务需要清理[/yellow]")
            return
        
        # 确认清理
        if not force:
            console.print(f"\n将清理 [bold]{len(tasks)}[/bold] 个 [bold]{status}[/bold] 状态的任务")
            if not Confirm.ask("确认清理？"):
                console.print("[yellow]已取消清理[/yellow]")
                return
        
        # 批量删除
        deleted_count = 0
        for task in tasks:
            if metadata_mgr.delete_download_task(task.task_id):
                deleted_count += 1
        
        console.print(f"[green]✓[/green] 已清理 {deleted_count} 个任务")
        
    except Exception as e:
        console.print(f"[red]✗ 错误:[/red] {e}")
        raise typer.Exit(1)
