#!/usr/bin/env python
"""
K线数据系统 - CLI主入口

使用Typer构建现代化命令行工具
"""
import typer
from typing import Optional
from pathlib import Path
from rich.console import Console
from rich.table import Table

from ..config import load_config

app = typer.Typer(
    name="kline",
    help="K线数据系统 - 数据下载、查询和管理工具",
    add_completion=True,
)

console = Console()

# 注册子命令组
from .commands import download, query, config_cmd, server, validate

app.add_typer(download.app, name="download", help="数据下载和更新")
app.add_typer(query.app, name="query", help="数据查询")
app.add_typer(config_cmd.app, name="config", help="配置管理")
app.add_typer(server.app, name="server", help="API服务")
app.add_typer(validate.app, name="validate", help="数据完整性验证")


@app.callback()
def main(
    ctx: typer.Context,
    config_file: Optional[Path] = typer.Option(
        None,
        "--config",
        "-c",
        help="配置文件路径",
        exists=True,
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="详细输出",
    ),
):
    """
    K线数据系统 - 命令行工具
    
    示例:
        kline download --symbol BTC/USDT --start 2024-01-01
        kline query --symbol BTC/USDT --timeframe 1m
        kline config show
        kline server start
    """
    # 加载配置
    if config_file:
        load_config(config_file)
    else:
        load_config()
    
    # 设置上下文
    ctx.obj = {
        "verbose": verbose,
        "console": console,
    }


@app.command()
def version():
    """显示版本信息"""
    __version__ = "1.0.0"
    
    console.print(f"[bold cyan]K线数据系统[/bold cyan] v{__version__}")
    console.print("基于Python的高性能K线数据存储与分析系统")


@app.command()
def info():
    """显示系统信息"""
    from kline_data.config import get_config
    
    cfg = get_config()
    
    table = Table(title="系统信息")
    table.add_column("项目", style="cyan")
    table.add_column("值", style="green")
    
    table.add_row("存储路径", str(cfg.storage.root_path))
    table.add_row("元数据路径", str(cfg.storage.metadata_path))
    table.add_row("缓存大小", f"{cfg.memory.max_cache_size_mb}MB")
    table.add_row("API端口", str(cfg.api.port))
    table.add_row("日志级别", cfg.system.log_level)
    
    console.print(table)


def cli_main():
    """CLI入口点"""
    app()


if __name__ == "__main__":
    cli_main()
