"""
服务启动命令模块
"""
import typer
from typing import Optional
from rich.console import Console
import uvicorn

from ...config import get_config

app = typer.Typer(help="API服务管理命令")
console = Console()


@app.command("start")
def start_server(
    host: Optional[str] = typer.Option(None, "--host", "-h", help="主机地址"),
    port: Optional[int] = typer.Option(None, "--port", "-p", help="端口号"),
    workers: int = typer.Option(1, "--workers", "-w", help="工作进程数"),
    reload: bool = typer.Option(False, "--reload", "-r", help="自动重载（开发模式）"),
    log_level: str = typer.Option("info", "--log-level", help="日志级别"),
):
    """
    启动FastAPI服务
    
    示例:
        kline server start
        kline server start --host 0.0.0.0 --port 8000
        kline server start --reload --log-level debug
    """
    try:
        cfg = get_config()
        
        # 使用配置文件中的默认值
        host = host or cfg.api.host
        port = port or cfg.api.port
        
        console.print(f"[cyan]启动K线数据API服务...[/cyan]")
        console.print(f"主机: [bold]{host}[/bold]")
        console.print(f"端口: [bold]{port}[/bold]")
        console.print(f"工作进程: [bold]{workers}[/bold]")
        console.print(f"重载模式: [bold]{'是' if reload else '否'}[/bold]")
        console.print(f"\n访问: [bold cyan]http://{host}:{port}[/bold cyan]")
        console.print(f"文档: [bold cyan]http://{host}:{port}/docs[/bold cyan]\n")
        
        # 启动服务
        uvicorn.run(
            "kline_data.service.api:app",
            host=host,
            port=port,
            workers=workers if not reload else 1,
            reload=reload,
            log_level=log_level,
        )
        
    except KeyboardInterrupt:
        console.print("\n[yellow]服务已停止[/yellow]")
    except Exception as e:
        console.print(f"[red]✗ 错误:[/red] {e}")
        raise typer.Exit(1)


@app.command("status")
def check_server_status(
    host: Optional[str] = typer.Option(None, "--host", "-h", help="主机地址"),
    port: Optional[int] = typer.Option(None, "--port", "-p", help="端口号"),
):
    """
    检查服务状态
    
    示例:
        kline server status
        kline server status --host localhost --port 8000
    """
    try:
        import requests
        
        cfg = get_config()
        host = host or cfg.api.host
        port = port or cfg.api.port
        
        url = f"http://{host}:{port}/health"
        
        console.print(f"[cyan]检查服务状态...[/cyan]")
        console.print(f"URL: {url}\n")
        
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            console.print(f"[green]✓[/green] 服务正常运行")
            console.print(f"状态: [bold]{data.get('status')}[/bold]")
            console.print(f"版本: [bold]{data.get('version')}[/bold]")
            console.print(f"时间: [bold]{data.get('timestamp')}[/bold]")
        else:
            console.print(f"[red]✗[/red] 服务异常: HTTP {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        console.print(f"[red]✗[/red] 无法连接到服务")
        console.print(f"请确认服务是否启动: [cyan]kline server start[/cyan]")
    except Exception as e:
        console.print(f"[red]✗ 错误:[/red] {e}")
        raise typer.Exit(1)


@app.command("config")
def show_server_config():
    """
    显示服务配置
    
    示例:
        kline server config
    """
    try:
        from rich.table import Table
        
        cfg = get_config()
        
        table = Table(title="API服务配置")
        table.add_column("配置项", style="cyan")
        table.add_column("值", style="green")
        
        table.add_row("主机", cfg.api.host)
        table.add_row("端口", str(cfg.api.port))
        table.add_row("CORS允许", str(cfg.api.cors.origins))
        table.add_row("认证", "启用" if cfg.api.auth.enabled else "禁用")
        table.add_row("速率限制", f"{cfg.api.rate_limit.requests_per_minute}/分钟")
        table.add_row("工作进程", str(cfg.api.workers))
        
        console.print(table)
        
    except Exception as e:
        console.print(f"[red]✗ 错误:[/red] {e}")
        raise typer.Exit(1)


@app.command("stop")
def stop_server():
    """
    停止服务（需要进程管理工具支持）
    
    示例:
        kline server stop
    """
    console.print("[yellow]提示:[/yellow] 请使用 Ctrl+C 停止服务")
    console.print("或使用进程管理工具如 systemd, supervisor 等")


@app.command("test")
def test_server(
    host: Optional[str] = typer.Option(None, "--host", "-h", help="主机地址"),
    port: Optional[int] = typer.Option(None, "--port", "-p", help="端口号"),
):
    """
    测试API端点
    
    示例:
        kline server test
        kline server test --host localhost --port 8000
    """
    try:
        import requests
        from rich.table import Table
        
        cfg = get_config()
        host = host or cfg.api.host
        port = port or cfg.api.port
        base_url = f"http://{host}:{port}"
        
        console.print(f"[cyan]测试API端点...[/cyan]\n")
        
        # 测试端点列表
        endpoints = [
            ("GET", "/", "根路径"),
            ("GET", "/health", "健康检查"),
            ("GET", "/metadata", "元数据"),
        ]
        
        table = Table(title=f"API测试结果 ({base_url})")
        table.add_column("方法", style="cyan")
        table.add_column("路径", style="blue")
        table.add_column("描述", style="white")
        table.add_column("状态", style="green")
        table.add_column("响应时间", style="yellow")
        
        for method, path, desc in endpoints:
            try:
                url = f"{base_url}{path}"
                import time
                start = time.time()
                
                if method == "GET":
                    response = requests.get(url, timeout=5)
                
                elapsed = (time.time() - start) * 1000  # 转换为毫秒
                
                if response.status_code == 200:
                    status = f"[green]✓ {response.status_code}[/green]"
                else:
                    status = f"[yellow]⚠ {response.status_code}[/yellow]"
                
                table.add_row(
                    method,
                    path,
                    desc,
                    status,
                    f"{elapsed:.0f}ms"
                )
                
            except Exception as e:
                table.add_row(
                    method,
                    path,
                    desc,
                    f"[red]✗ 失败[/red]",
                    "-"
                )
        
        console.print(table)
        
    except Exception as e:
        console.print(f"[red]✗ 错误:[/red] {e}")
        raise typer.Exit(1)
