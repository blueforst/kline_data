"""配置管理器"""

import json
from pathlib import Path
from typing import Any, Optional, Union
import yaml
from .schemas import Config


class ConfigManager:
    """
    配置管理器 - 单例模式
    负责加载、获取、更新配置
    """
    
    _instance: Optional['ConfigManager'] = None
    _config: Optional[Config] = None
    _config_path: Optional[Path] = None
    
    def __new__(cls):
        """单例模式实现"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def load(self, config_path: Union[str, Path] = "config/config.yaml") -> Config:
        """
        加载配置文件
        
        Args:
            config_path: 配置文件路径
            
        Returns:
            Config: 配置对象
            
        Raises:
            FileNotFoundError: 配置文件不存在
            ValueError: 配置文件格式错误
        """
        path = Path(config_path)
        
        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {path}")
        
        # 根据文件扩展名选择加载方式
        if path.suffix in ['.yaml', '.yml']:
            data = self._load_yaml(path)
        elif path.suffix == '.json':
            data = self._load_json(path)
        else:
            raise ValueError(f"Unsupported config file format: {path.suffix}")
        
        # 验证并创建配置对象
        try:
            self._config = Config(**data)
            self._config_path = path
            return self._config
        except Exception as e:
            raise ValueError(f"Invalid configuration: {e}")
    
    def _load_yaml(self, path: Path) -> dict:
        """加载YAML配置文件"""
        with open(path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def _load_json(self, path: Path) -> dict:
        """加载JSON配置文件"""
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置项
        支持点号分隔的嵌套键，如: 'storage.root_path'
        
        Args:
            key: 配置键，支持点号分隔
            default: 默认值
            
        Returns:
            Any: 配置值
            
        Example:
            >>> config_mgr.get('storage.root_path')
            './data'
            >>> config_mgr.get('ccxt.proxy.http')
            None
            >>> config_mgr.get('nonexistent.key', 'default_value')
            'default_value'
        """
        if self._config is None:
            raise RuntimeError("Configuration not loaded. Call load() first.")
        
        keys = key.split('.')
        value = self._config.model_dump()
        
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
            
            if value is None:
                return default
        
        return value
    
    def get_config(self) -> Config:
        """
        获取完整配置对象
        
        Returns:
            Config: 配置对象
            
        Raises:
            RuntimeError: 配置未加载
        """
        if self._config is None:
            raise RuntimeError("Configuration not loaded. Call load() first.")
        return self._config
    
    def update(self, key: str, value: Any) -> None:
        """
        更新配置项
        
        Args:
            key: 配置键，支持点号分隔
            value: 新值
            
        Raises:
            RuntimeError: 配置未加载
            ValueError: 键不存在或值无效
        """
        if self._config is None:
            raise RuntimeError("Configuration not loaded. Call load() first.")
        
        keys = key.split('.')
        config_dict = self._config.model_dump()
        
        # 导航到目标位置
        current = config_dict
        for k in keys[:-1]:
            if k not in current:
                raise ValueError(f"Configuration key not found: {key}")
            current = current[k]
        
        # 更新值
        if keys[-1] not in current:
            raise ValueError(f"Configuration key not found: {key}")
        
        current[keys[-1]] = value
        
        # 重新验证配置
        try:
            self._config = Config(**config_dict)
        except Exception as e:
            raise ValueError(f"Invalid configuration value: {e}")
    
    def save(self, path: Optional[Union[str, Path]] = None) -> None:
        """
        保存配置到文件
        
        Args:
            path: 保存路径，如果为None则保存到原路径
            
        Raises:
            RuntimeError: 配置未加载
        """
        if self._config is None:
            raise RuntimeError("Configuration not loaded. Call load() first.")
        
        save_path = Path(path) if path else self._config_path
        
        if save_path is None:
            raise ValueError("No save path specified")
        
        config_dict = self._config.model_dump()
        
        # 根据文件扩展名选择保存方式
        if save_path.suffix in ['.yaml', '.yml']:
            self._save_yaml(save_path, config_dict)
        elif save_path.suffix == '.json':
            self._save_json(save_path, config_dict)
        else:
            raise ValueError(f"Unsupported config file format: {save_path.suffix}")
    
    def _save_yaml(self, path: Path, data: dict) -> None:
        """保存为YAML格式"""
        with open(path, 'w', encoding='utf-8') as f:
            yaml.safe_dump(
                data,
                f,
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False
            )
    
    def _save_json(self, path: Path, data: dict) -> None:
        """保存为JSON格式"""
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def reload(self) -> Config:
        """
        重新加载配置文件（热加载）
        
        Returns:
            Config: 新的配置对象
            
        Raises:
            RuntimeError: 配置未加载或配置路径不存在
        """
        if self._config_path is None:
            raise RuntimeError("No configuration file path available for reload")
        
        return self.load(self._config_path)
    
    def reset(self) -> None:
        """重置配置管理器（主要用于测试）"""
        self._config = None
        self._config_path = None
    
    def validate(self) -> bool:
        """
        验证当前配置是否有效
        
        Returns:
            bool: 配置是否有效
        """
        if self._config is None:
            return False
        
        try:
            # Pydantic会在model_dump时进行验证
            self._config.model_dump()
            return True
        except Exception:
            return False
    
    def to_dict(self) -> dict:
        """
        将配置转换为字典
        
        Returns:
            dict: 配置字典
            
        Raises:
            RuntimeError: 配置未加载
        """
        if self._config is None:
            raise RuntimeError("Configuration not loaded. Call load() first.")
        return self._config.model_dump()
    
    def to_json(self, indent: int = 2) -> str:
        """
        将配置转换为JSON字符串
        
        Args:
            indent: 缩进空格数
            
        Returns:
            str: JSON字符串
            
        Raises:
            RuntimeError: 配置未加载
        """
        if self._config is None:
            raise RuntimeError("Configuration not loaded. Call load() first.")
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)
    
    @property
    def config_file(self) -> Optional[Path]:
        """获取配置文件路径"""
        return self._config_path

    def __repr__(self) -> str:
        """字符串表示"""
        if self._config is None:
            return "ConfigManager(not loaded)"
        return f"ConfigManager(config_path={self._config_path})"


# 便捷函数
def load_config(config_path: Optional[Union[str, Path]] = None) -> Config:
    """
    加载配置的便捷函数
    
    智能查找配置文件：
    1. 如果提供了config_path，直接使用
    2. 否则按以下顺序查找：
       - 当前工作目录的 config/config.yaml
       - 项目安装目录的 config/config.yaml（支持外部导入）
       - 用户主目录的 .kline_data/config.yaml
    
    Args:
        config_path: 配置文件路径（可选）
        
    Returns:
        Config: 配置对象
        
    Raises:
        FileNotFoundError: 找不到配置文件
    """
    manager = ConfigManager()
    
    # 如果提供了路径，直接使用
    if config_path is not None:
        return manager.load(config_path)
    
    # 智能查找配置文件
    search_paths = [
        # 1. 当前工作目录
        Path.cwd() / "config" / "config.yaml",
        # 2. 项目安装目录（支持外部导入使用项目配置）
        Path(__file__).parent / "config.yaml",
        # 3. 用户主目录
        Path.home() / ".kline_data" / "config.yaml",
    ]
    
    for path in search_paths:
        if path.exists():
            return manager.load(path)
    
    # 如果都找不到，抛出详细的错误信息
    searched = "\n  - ".join(str(p) for p in search_paths)
    raise FileNotFoundError(
        f"Configuration file not found. Searched locations:\n  - {searched}\n\n"
        f"You can:\n"
        f"1. Create a config file in one of the above locations\n"
        f"2. Pass config_path explicitly to load_config()\n"
        f"3. Pass a Config object directly when creating clients"
    )


def get_config() -> Config:
    """
    获取当前配置的便捷函数
    
    Returns:
        Config: 配置对象
        
    Raises:
        RuntimeError: 配置未加载
    """
    manager = ConfigManager()
    return manager.get_config()
