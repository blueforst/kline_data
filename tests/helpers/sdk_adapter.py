"""
SDK接口适配器 - 处理API接口版本兼容性
"""
from typing import Optional, Any, Dict, Union
from datetime import datetime
import pandas as pd
import inspect

class SDKAdapter:
    """SDK接口适配器"""

    def __init__(self, client):
        self.client = client
        self._detect_interface()

    def _detect_interface(self):
        """检测可用的接口方法"""
        self.has_get_klines = hasattr(self.client, 'get_klines')
        self.has_get_klines_before = hasattr(self.client, 'get_klines_before')

        # 分析get_klines方法的参数
        if self.has_get_klines:
            self.get_klines_signature = inspect.signature(self.client.get_klines)
            self.get_klines_params = list(self.get_klines_signature.parameters.keys())
        else:
            self.get_klines_signature = None
            self.get_klines_params = []

        # 分析get_klines_before方法的参数
        if self.has_get_klines_before:
            self.get_klines_before_signature = inspect.signature(self.client.get_klines_before)
            self.get_klines_before_params = list(self.get_klines_before_signature.parameters.keys())
        else:
            self.get_klines_before_signature = None
            self.get_klines_before_params = []

    def get_klines(self, exchange: str, symbol: str,
                  timeframe: str, limit: Optional[int] = None,
                  before: Optional[datetime] = None, **kwargs) -> pd.DataFrame:
        """
        统一的K线数据获取接口

        自动适配不同的SDK版本
        """
        if self.has_get_klines_before:
            # 使用新接口 get_klines_before
            return self._call_get_klines_before(
                exchange=exchange,
                symbol=symbol,
                timeframe=timeframe,
                limit=limit,
                before=before,
                **kwargs
            )
        elif self.has_get_klines:
            # 使用旧接口 get_klines
            return self._call_get_klines(
                exchange=exchange,
                symbol=symbol,
                timeframe=timeframe,
                limit=limit,
                before=before,
                **kwargs
            )
        else:
            raise AttributeError("客户端没有可用的K线数据获取方法")

    def _call_get_klines_before(self, exchange: str, symbol: str,
                               timeframe: str, limit: Optional[int] = None,
                               before: Optional[datetime] = None, **kwargs) -> pd.DataFrame:
        """调用get_klines_before方法"""
        # 构建参数字典
        params = {
            'exchange': exchange,
            'symbol': symbol,
            'timeframe': timeframe
        }

        if limit is not None:
            params['limit'] = limit

        if before is not None:
            params['before'] = before
        elif 'before_time' in self.get_klines_before_params:
            # 如果参数名是before_time
            params['before_time'] = before or datetime.now()

        # 添加其他kwargs
        for key, value in kwargs.items():
            if key not in params:
                params[key] = value

        return self.client.get_klines_before(**params)

    def _call_get_klines(self, exchange: str, symbol: str,
                        timeframe: str, limit: Optional[int] = None,
                        before: Optional[datetime] = None, **kwargs) -> pd.DataFrame:
        """调用get_klines方法"""
        # 构建参数字典
        params = {
            'exchange': exchange,
            'symbol': symbol,
            'timeframe': timeframe
        }

        if limit is not None:
            params['limit'] = limit

        if before is not None and 'before' in self.get_klines_params:
            params['before'] = before

        # 添加其他kwargs
        for key, value in kwargs.items():
            if key not in params:
                params[key] = value

        return self.client.get_klines(**params)

    def get_supported_methods(self) -> Dict[str, Any]:
        """获取支持的方法列表和接口信息"""
        return {
            'get_klines': self.has_get_klines,
            'get_klines_before': self.has_get_klines_before,
            'unified_interface': True,
            'get_klines_params': self.get_klines_params,
            'get_klines_before_params': self.get_klines_before_params
        }

    def is_compatible_with_tests(self) -> bool:
        """检查是否与测试兼容"""
        # 如果有get_klines_before方法，通常是兼容的
        if self.has_get_klines_before:
            return True

        # 如果只有get_klines，检查参数是否包含before
        if self.has_get_klines and 'before' in self.get_klines_params:
            return True

        return False

    def get_interface_info(self) -> str:
        """获取接口信息字符串"""
        if self.has_get_klines_before:
            return f"使用 get_klines_before 接口，参数: {self.get_klines_before_params}"
        elif self.has_get_klines:
            return f"使用 get_klines 接口，参数: {self.get_klines_params}"
        else:
            return "无可用的K线数据接口"

    def adapt_test_parameters(self, **test_params) -> Dict[str, Any]:
        """
        适配测试参数到实际接口

        Args:
            **test_params: 测试使用的参数

        Returns:
            适配后的参数字典
        """
        adapted_params = {}

        if self.has_get_klines_before:
            # 映射测试参数到get_klines_before参数
            param_mapping = {
                'exchange': 'exchange',
                'symbol': 'symbol',
                'timeframe': 'timeframe',
                'limit': 'limit',
                'before': 'before',
                'before_time': 'before'  # 如果测试使用before_time，映射到before
            }

            for test_param, value in test_params.items():
                if test_param in param_mapping:
                    actual_param = param_mapping[test_param]
                    if actual_param in self.get_klines_before_params:
                        adapted_params[actual_param] = value

        elif self.has_get_klines:
            # 映射测试参数到get_klines参数
            for test_param, value in test_params.items():
                if test_param in self.get_klines_params:
                    adapted_params[test_param] = value

        return adapted_params


def create_sdk_adapter(client) -> SDKAdapter:
    """
    创建SDK适配器的便捷函数

    Args:
        client: 客户端实例

    Returns:
        SDK适配器实例
    """
    return SDKAdapter(client)