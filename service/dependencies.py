"""
FastAPI依赖注入
"""

from functools import lru_cache
from typing import Optional
from fastapi import FastAPI

from sdk import KlineClient as KlineSDK


@lru_cache()
def _get_sdk_instance(config_path: Optional[str] = None) -> KlineSDK:
    """
    获取SDK单例实例（带缓存）
    
    Args:
        config_path: 配置文件路径
        
    Returns:
        KlineSDK实例
    """
    if config_path:
        from config import load_config
        config = load_config(config_path)
        return KlineSDK(config=config)
    return KlineSDK()


def get_kline_sdk(app: FastAPI):
    """
    创建依赖注入函数，用于FastAPI路由
    
    Args:
        app: FastAPI应用实例
        
    Returns:
        依赖注入函数
    """
    def _dependency() -> KlineSDK:
        config_path = getattr(app.state, 'config_path', None)
        return _get_sdk_instance(config_path)
    
    return _dependency
