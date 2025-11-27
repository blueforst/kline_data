"""
Service Layer - FastAPI服务层

提供HTTP RESTful API接口，对外暴露K线数据查询、指标计算等功能
"""

from .api import app, create_app

__all__ = ['app', 'create_app']
