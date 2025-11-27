"""元数据客户端 - 元数据查询"""

from typing import Optional, List
from datetime import datetime

from config import Config
from storage import MetadataManager
from utils.constants import (
    API_METADATA_TAG,
    validate_exchange,
    validate_symbol,
)


class MetadataClient:
    """
    元数据查询客户端
    
    提供数据元信息查询功能，包括：
    1. 获取交易对元数据
    2. 列出所有交易对
    3. 查询数据范围
    4. 查询数据完整性
    """
    
    def __init__(self, config: Optional[Config] = None):
        """
        初始化元数据客户端
        
        Args:
            config: 配置对象，如果为None使用默认配置
        """
        if config is None:
            from config import load_config
            config = load_config()
        
        self.config = config
        self.metadata_mgr = MetadataManager(config)
    
    def get_metadata(
        self,
        exchange: str,
        symbol: str
    ) -> Optional[dict]:
        """
        获取元数据

        Args:
            exchange: 交易所
            symbol: 交易对

        Returns:
            Optional[dict]: 元数据
        """
        validate_exchange(exchange)
        validate_symbol(symbol)

        metadata = self.metadata_mgr.get_symbol_metadata(exchange, symbol)

        if metadata:
            return {
                'exchange': metadata.exchange,
                'symbol': metadata.symbol,
                'intervals': {
                    interval: {
                        'start_time': datetime.fromtimestamp(
                            data.start_timestamp / 1000
                        ),
                        'end_time': datetime.fromtimestamp(
                            data.end_timestamp / 1000
                        ),
                        'records': data.total_records,
                        'completeness': data.completeness,
                    }
                    for interval, data in metadata.intervals.items()
                },
                'last_updated': metadata.last_updated,
                'data_type': API_METADATA_TAG,
            }

        return None
    
    def list_symbols(self, exchange: Optional[str] = None) -> List[str]:
        """
        列出所有交易对

        Args:
            exchange: 可选，过滤交易所

        Returns:
            List[str]: 交易对列表
        """
        if exchange is not None:
            validate_exchange(exchange)

        # 简化版实现，需要元数据管理器支持
        return []
    
    def get_data_range(
        self,
        exchange: str,
        symbol: str
    ) -> Optional[tuple]:
        """
        获取数据范围
        
        Args:
            exchange: 交易所
            symbol: 交易对
            
        Returns:
            Optional[tuple]: (start_timestamp, end_timestamp) 毫秒时间戳
        """
        validate_exchange(exchange)
        validate_symbol(symbol)
        
        return self.metadata_mgr.get_data_range(exchange, symbol)
