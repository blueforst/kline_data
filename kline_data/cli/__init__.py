"""CLI命令行工具"""

# 延迟导入，避免runpy警告: 'cli.main' found in sys.modules after import of package 'cli'
def get_app():
    """获取Typer应用实例"""
    from .main import app
    return app

def get_cli_main():
    """获取CLI主函数"""
    from .main import cli_main
    return cli_main

__all__ = ["get_app", "get_cli_main"]
