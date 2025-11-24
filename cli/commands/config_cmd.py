"""
配置管理命令模块
"""
import typer
from typing import Optional
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.syntax import Syntax
import json
import yaml

from config import get_config, ConfigManager

app = typer.Typer(help="配置管理命令")
console = Console()


@app.command("show")
def show_config(
    key: Optional[str] = typer.Option(None, "--key", "-k", help="显示特定配置项（如: storage.root_path）"),
    format: str = typer.Option("yaml", "--format", "-f", help="输出格式 (yaml/json)"),
):
    """
    显示配置信息
    
    示例:
        kline config show
        kline config show --key storage.root_path
        kline config show --format json
    """
    try:
        cfg = get_config()
        
        if key:
            # 显示特定配置项
            value = cfg.get(key)
            console.print(f"\n[cyan]{key}[/cyan]: [green]{value}[/green]\n")
        else:
            # 显示所有配置
            config_dict = cfg.model_dump()
            
            if format == "json":
                config_str = json.dumps(config_dict, indent=2, ensure_ascii=False)
                syntax = Syntax(config_str, "json", theme="monokai", line_numbers=True)
            else:
                config_str = yaml.dump(config_dict, allow_unicode=True, default_flow_style=False)
                syntax = Syntax(config_str, "yaml", theme="monokai", line_numbers=True)
            
            console.print("\n[bold cyan]当前配置:[/bold cyan]\n")
            console.print(syntax)
            
    except Exception as e:
        console.print(f"[red]✗ 错误:[/red] {e}")
        raise typer.Exit(1)


@app.command("set")
def set_config(
    key: str = typer.Option(..., "--key", "-k", help="配置项键（如: storage.root_path）"),
    value: str = typer.Option(..., "--value", "-v", help="配置值"),
    save: bool = typer.Option(True, "--save", "-s", help="是否保存到文件"),
):
    """
    设置配置项
    
    示例:
        kline config set --key storage.root_path --value /data/kline
        kline config set -k memory.max_cache_size_mb -v 1024
    """
    try:
        manager = ConfigManager()
        
        # 尝试转换值类型
        try:
            # 尝试解析为数字
            if value.isdigit():
                typed_value = int(value)
            elif value.replace(".", "").isdigit():
                typed_value = float(value)
            # 尝试解析为布尔值
            elif value.lower() in ("true", "false"):
                typed_value = value.lower() == "true"
            else:
                typed_value = value
        except:
            typed_value = value
        
        # 更新配置
        manager.update({key: typed_value})
        
        console.print(f"[green]✓[/green] 已更新: [cyan]{key}[/cyan] = [green]{typed_value}[/green]")
        
        # 保存到文件
        if save:
            config_file = manager.config_file or Path("config/config.yaml")
            manager.save(config_file)
            console.print(f"[green]✓[/green] 已保存到: {config_file}")
            
    except Exception as e:
        console.print(f"[red]✗ 错误:[/red] {e}")
        raise typer.Exit(1)


@app.command("reset")
def reset_config(
    confirm: bool = typer.Option(False, "--confirm", "-y", help="确认重置"),
):
    """
    重置为默认配置
    
    示例:
        kline config reset --confirm
    """
    if not confirm:
        console.print("[yellow]警告:[/yellow] 此操作将重置所有配置为默认值")
        console.print("使用 [bold]--confirm[/bold] 确认操作")
        return
    
    try:
        manager = ConfigManager()
        default_config = Path("config/config.yaml")
        
        if default_config.exists():
            manager.load(default_config)
            console.print(f"[green]✓[/green] 已重置为默认配置")
        else:
            console.print(f"[red]✗[/red] 未找到默认配置文件")
            
    except Exception as e:
        console.print(f"[red]✗ 错误:[/red] {e}")
        raise typer.Exit(1)


@app.command("validate")
def validate_config(
    config_file: Optional[Path] = typer.Option(None, "--file", "-f", help="配置文件路径"),
):
    """
    验证配置文件
    
    示例:
        kline config validate
        kline config validate --file config/config.local.yaml
    """
    try:
        if config_file:
            manager = ConfigManager()
            manager.load(config_file)
            console.print(f"[green]✓[/green] 配置文件有效: {config_file}")
        else:
            cfg = get_config()
            console.print(f"[green]✓[/green] 当前配置有效")
        
        # 显示配置摘要
        console.print("\n[bold cyan]配置摘要:[/bold cyan]")
        table = Table()
        table.add_column("模块", style="cyan")
        table.add_column("状态", style="green")
        
        table.add_row("系统配置", "✓")
        table.add_row("存储配置", "✓")
        table.add_row("CCXT配置", "✓")
        table.add_row("内存配置", "✓")
        table.add_row("API配置", "✓")
        
        console.print(table)
        
    except Exception as e:
        console.print(f"[red]✗ 配置验证失败:[/red] {e}")
        raise typer.Exit(1)


@app.command("export")
def export_config(
    output: Path = typer.Option(..., "--output", "-o", help="输出文件路径"),
    format: str = typer.Option("yaml", "--format", "-f", help="输出格式 (yaml/json)"),
):
    """
    导出配置到文件
    
    示例:
        kline config export --output config.yaml
        kline config export -o config.json -f json
    """
    try:
        cfg = get_config()
        config_dict = cfg.model_dump()
        
        with open(output, "w", encoding="utf-8") as f:
            if format == "json":
                json.dump(config_dict, f, indent=2, ensure_ascii=False)
            else:
                yaml.dump(config_dict, f, allow_unicode=True, default_flow_style=False)
        
        console.print(f"[green]✓[/green] 已导出到: {output}")
        
    except Exception as e:
        console.print(f"[red]✗ 错误:[/red] {e}")
        raise typer.Exit(1)


@app.command("list")
def list_config():
    """
    列出所有配置项
    
    示例:
        kline config list
    """
    try:
        cfg = get_config()
        config_dict = cfg.model_dump()
        
        table = Table(title="配置项列表")
        table.add_column("配置键", style="cyan", no_wrap=True)
        table.add_column("当前值", style="green")
        table.add_column("类型", style="yellow")
        
        def flatten_dict(d, parent_key=""):
            """展平嵌套字典"""
            items = []
            for k, v in d.items():
                new_key = f"{parent_key}.{k}" if parent_key else k
                if isinstance(v, dict):
                    items.extend(flatten_dict(v, new_key))
                else:
                    items.append((new_key, v, type(v).__name__))
            return items
        
        for key, value, vtype in flatten_dict(config_dict):
            # 截断长值
            value_str = str(value)
            if len(value_str) > 50:
                value_str = value_str[:47] + "..."
            
            table.add_row(key, value_str, vtype)
        
        console.print(table)
        
    except Exception as e:
        console.print(f"[red]✗ 错误:[/red] {e}")
        raise typer.Exit(1)


@app.command("path")
def show_config_path():
    """
    显示配置文件路径
    
    示例:
        kline config path
    """
    try:
        manager = ConfigManager()
        
        console.print("\n[bold cyan]配置文件路径:[/bold cyan]\n")
        
        table = Table(show_header=False)
        table.add_column("项目", style="cyan")
        table.add_column("路径", style="green")
        
        if manager.config_file:
            table.add_row("当前配置", str(manager.config_file))
        
        default_config = Path("config/config.yaml")
        if default_config.exists():
            table.add_row("默认配置", str(default_config.absolute()))
        
        local_config = Path("config/config.local.yaml")
        if local_config.exists():
            table.add_row("本地配置", str(local_config.absolute()))
        
        console.print(table)
        console.print()
        
    except Exception as e:
        console.print(f"[red]✗ 错误:[/red] {e}")
        raise typer.Exit(1)
