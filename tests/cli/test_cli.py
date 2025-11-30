"""
CLI层测试

测试命令行工具的各个功能
"""
import pytest
from typer.testing import CliRunner
from pathlib import Path
import tempfile
import yaml

from kline_data.cli.main import app
from kline_data.config import load_config, ConfigManager

runner = CliRunner()


class TestCLIMain:
    """测试CLI主命令"""
    
    def test_version_command(self):
        """测试version命令"""
        result = runner.invoke(app, ["version"])
        assert result.exit_code == 0
        assert "K线数据系统" in result.stdout
        assert "v1.0.0" in result.stdout
    
    def test_info_command(self):
        """测试info命令"""
        # 需要先加载配置
        load_config()
        
        result = runner.invoke(app, ["info"])
        assert result.exit_code == 0
        assert "系统信息" in result.stdout
        assert "存储路径" in result.stdout
    
    def test_help_command(self):
        """测试help命令"""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "K线数据系统" in result.stdout
        assert "download" in result.stdout
        assert "query" in result.stdout
        assert "config" in result.stdout
        assert "server" in result.stdout


class TestConfigCommands:
    """测试配置管理命令"""
    
    def setup_method(self):
        """每个测试前的设置"""
        load_config()
    
    def test_show_config(self):
        """测试显示配置"""
        result = runner.invoke(app, ["config", "show"])
        assert result.exit_code == 0
        assert "当前配置" in result.stdout
    
    def test_show_config_with_key(self):
        """测试显示特定配置项"""
        result = runner.invoke(app, ["config", "show", "--key", "system.log_level"])
        assert result.exit_code == 0
    
    def test_list_config(self):
        """测试列出配置项"""
        result = runner.invoke(app, ["config", "list"])
        assert result.exit_code == 0
        assert "配置项列表" in result.stdout
    
    def test_show_config_path(self):
        """测试显示配置路径"""
        result = runner.invoke(app, ["config", "path"])
        assert result.exit_code == 0
        assert "配置文件路径" in result.stdout
    
    def test_validate_config(self):
        """测试验证配置"""
        result = runner.invoke(app, ["config", "validate"])
        assert result.exit_code == 0
        assert "配置" in result.stdout and ("有效" in result.stdout or "✓" in result.stdout)
    
    def test_export_config(self):
        """测试导出配置"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            temp_file = f.name
        
        try:
            result = runner.invoke(app, ["config", "export", "--output", temp_file])
            assert result.exit_code == 0
            assert Path(temp_file).exists()
            
            # 验证导出的文件
            with open(temp_file) as f:
                data = yaml.safe_load(f)
                assert "system" in data
                assert "storage" in data
        finally:
            Path(temp_file).unlink(missing_ok=True)


class TestQueryCommands:
    """测试查询命令"""
    
    def setup_method(self):
        """每个测试前的设置"""
        load_config()
    
    def test_symbols_command(self):
        """测试列出交易对"""
        result = runner.invoke(app, ["query", "symbols"])
        # 可能没有数据，但命令应该能执行
        assert result.exit_code == 0 or "错误" in result.stdout


class TestDownloadCommands:
    """测试下载命令"""
    
    def setup_method(self):
        """每个测试前的设置"""
        load_config()
    
    def test_list_downloads(self):
        """测试列出下载任务"""
        result = runner.invoke(app, ["download", "list"])
        # 可能没有数据，但命令应该能执行
        assert result.exit_code == 0 or "错误" in result.stdout


class TestServerCommands:
    """测试服务命令"""
    
    def setup_method(self):
        """每个测试前的设置"""
        load_config()
    
    def test_server_config(self):
        """测试显示服务配置"""
        result = runner.invoke(app, ["server", "config"])
        assert result.exit_code == 0
        assert "API服务配置" in result.stdout
    
    def test_server_stop(self):
        """测试停止服务命令"""
        result = runner.invoke(app, ["server", "stop"])
        assert result.exit_code == 0
        assert "提示" in result.stdout


class TestCLIIntegration:
    """集成测试"""
    
    def setup_method(self):
        """每个测试前的设置"""
        load_config()
    
    def test_config_workflow(self):
        """测试配置管理工作流"""
        # 1. 显示配置
        result = runner.invoke(app, ["config", "show"])
        assert result.exit_code == 0
        
        # 2. 列出配置项
        result = runner.invoke(app, ["config", "list"])
        assert result.exit_code == 0
        
        # 3. 验证配置
        result = runner.invoke(app, ["config", "validate"])
        assert result.exit_code == 0
    
    def test_query_workflow(self):
        """测试查询工作流"""
        # 1. 列出交易对
        result = runner.invoke(app, ["query", "symbols"])
        # 命令应该能执行，即使没有数据
        assert result.exit_code == 0 or "错误" in result.stdout
    
    def test_help_for_all_commands(self):
        """测试所有命令的帮助信息"""
        commands = [
            ["--help"],
            ["download", "--help"],
            ["query", "--help"],
            ["config", "--help"],
            ["server", "--help"],
        ]
        
        for cmd in commands:
            result = runner.invoke(app, cmd)
            assert result.exit_code == 0
            assert "help" in result.stdout.lower() or "命令" in result.stdout


class TestCLIErrors:
    """测试错误处理"""
    
    def test_invalid_command(self):
        """测试无效命令"""
        result = runner.invoke(app, ["invalid-command"])
        assert result.exit_code != 0
    
    def test_missing_required_option(self):
        """测试缺少必需选项"""
        result = runner.invoke(app, ["download", "start"])
        # 应该因为缺少必需参数而失败
        assert result.exit_code != 0


class TestCLIOutput:
    """测试输出格式"""
    
    def setup_method(self):
        """每个测试前的设置"""
        load_config()
    
    def test_version_output_format(self):
        """测试版本输出格式"""
        result = runner.invoke(app, ["version"])
        assert result.exit_code == 0
        # 检查是否包含版本号
        assert "v" in result.stdout or "版本" in result.stdout
    
    def test_info_output_format(self):
        """测试信息输出格式"""
        result = runner.invoke(app, ["info"])
        assert result.exit_code == 0
        # 检查是否包含系统信息
        assert "系统" in result.stdout or "存储" in result.stdout


def test_cli_import():
    """测试CLI模块导入"""
    from kline_data.cli import get_app, get_cli_main
    app = get_app()
    cli_main = get_cli_main()
    assert app is not None
    assert callable(cli_main)


def test_cli_commands_import():
    """测试CLI命令导入"""
    from kline_data.cli.commands import download, query, config_cmd, server
    assert download.app is not None
    assert query.app is not None
    assert config_cmd.app is not None
    assert server.app is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
