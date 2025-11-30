"""测试KlineClient初始化"""

import pytest
from unittest.mock import Mock
from kline_data.sdk.sdk_client import KlineClient


class TestClientInitialization:
    """测试客户端初始化"""

    def test_context_manager_interface(self):
        """测试上下文管理器接口存在"""
        # 测试接口存在，不实际初始化
        assert hasattr(KlineClient, '__enter__')
        assert hasattr(KlineClient, '__exit__')

    def test_class_has_correct_methods(self):
        """测试类具有正确的方法"""
        # 检查关键方法存在
        required_methods = [
            '__init__',
            'get_kline',
            'get_latest',
            'get_klines_before',
            'download_kline',
            'create_data_feed',
            'calculate_indicators'
        ]

        for method in required_methods:
            assert hasattr(KlineClient, method), f"Missing method: {method}"

    def test_simple_import_works(self):
        """测试简单的导入和类实例化不报错"""
        # 这个测试只是确保导入和基本语法正确
        # 不实际运行初始化逻辑
        assert KlineClient is not None