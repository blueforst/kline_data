"""数据缓存管理"""

import time
from typing import Optional, Dict, Any
from collections import OrderedDict
import pandas as pd


class LRUCache:
    """
    LRU (Least Recently Used) 缓存
    基于OrderedDict实现的高效缓存
    """
    
    def __init__(self, max_size_mb: int = 512, ttl_seconds: int = 3600):
        """
        初始化缓存
        
        Args:
            max_size_mb: 最大缓存大小（MB）
            ttl_seconds: 缓存过期时间（秒）
        """
        self.max_size_mb = max_size_mb
        self.ttl_seconds = ttl_seconds
        self.cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        self.current_size_mb = 0.0
        
        # 统计信息
        self.hits = 0
        self.misses = 0
    
    def get(self, key: str) -> Optional[pd.DataFrame]:
        """
        获取缓存数据
        
        Args:
            key: 缓存键
            
        Returns:
            Optional[pd.DataFrame]: 缓存的数据，如果不存在或过期返回None
        """
        if key not in self.cache:
            self.misses += 1
            return None
        
        # 检查是否过期
        entry = self.cache[key]
        if time.time() - entry['timestamp'] > self.ttl_seconds:
            # 过期，删除
            self._evict(key)
            self.misses += 1
            return None
        
        # 移到末尾（最近使用）
        self.cache.move_to_end(key)
        self.hits += 1
        
        return entry['data']
    
    def put(self, key: str, data: pd.DataFrame) -> None:
        """
        存入缓存
        
        Args:
            key: 缓存键
            data: 数据
        """
        # 计算数据大小
        size_mb = data.memory_usage(deep=True).sum() / 1024 / 1024
        
        # 如果数据太大，不缓存
        if size_mb > self.max_size_mb:
            return
        
        # 如果键已存在，先删除
        if key in self.cache:
            self._evict(key)
        
        # 淘汰旧数据直到有足够空间
        while self.current_size_mb + size_mb > self.max_size_mb and self.cache:
            # 删除最旧的（第一个）
            oldest_key = next(iter(self.cache))
            self._evict(oldest_key)
        
        # 添加新数据
        self.cache[key] = {
            'data': data,
            'size_mb': size_mb,
            'timestamp': time.time()
        }
        self.current_size_mb += size_mb
    
    def _evict(self, key: str) -> None:
        """
        淘汰缓存项
        
        Args:
            key: 缓存键
        """
        if key in self.cache:
            entry = self.cache[key]
            self.current_size_mb -= entry['size_mb']
            del self.cache[key]
    
    def clear(self) -> None:
        """清空缓存"""
        self.cache.clear()
        self.current_size_mb = 0.0
    
    def remove(self, key: str) -> bool:
        """
        删除指定缓存项
        
        Args:
            key: 缓存键
            
        Returns:
            bool: 是否删除成功
        """
        if key in self.cache:
            self._evict(key)
            return True
        return False
    
    def size(self) -> int:
        """
        获取缓存项数量
        
        Returns:
            int: 缓存项数量
        """
        return len(self.cache)
    
    def get_stats(self) -> dict:
        """
        获取缓存统计信息
        
        Returns:
            dict: 统计信息
        """
        total_requests = self.hits + self.misses
        hit_rate = self.hits / total_requests if total_requests > 0 else 0
        
        return {
            'size': len(self.cache),
            'size_mb': round(self.current_size_mb, 2),
            'max_size_mb': self.max_size_mb,
            'hits': self.hits,
            'misses': self.misses,
            'hit_rate': round(hit_rate * 100, 2),
            'usage_percent': round(self.current_size_mb / self.max_size_mb * 100, 2)
        }
    
    def __len__(self) -> int:
        """返回缓存项数量"""
        return len(self.cache)
    
    def __contains__(self, key: str) -> bool:
        """检查键是否存在"""
        return key in self.cache
    
    def __repr__(self) -> str:
        """字符串表示"""
        return f"LRUCache(size={len(self.cache)}, {self.current_size_mb:.2f}/{self.max_size_mb}MB)"


class DataCache:
    """
    数据缓存管理器
    提供更高级的缓存功能
    """
    
    def __init__(self, max_size_mb: int = 512, ttl_seconds: int = 3600):
        """
        初始化缓存管理器
        
        Args:
            max_size_mb: 最大缓存大小（MB）
            ttl_seconds: 缓存过期时间（秒）
        """
        self.lru_cache = LRUCache(max_size_mb, ttl_seconds)
    
    def get_or_compute(
        self,
        key: str,
        compute_fn,
        *args,
        **kwargs
    ) -> pd.DataFrame:
        """
        获取缓存数据，如果不存在则计算
        
        Args:
            key: 缓存键
            compute_fn: 计算函数
            *args: 计算函数的位置参数
            **kwargs: 计算函数的关键字参数
            
        Returns:
            pd.DataFrame: 数据
        """
        # 尝试从缓存获取
        data = self.lru_cache.get(key)
        
        if data is not None:
            return data
        
        # 缓存未命中，计算数据
        data = compute_fn(*args, **kwargs)
        
        # 存入缓存
        if data is not None and not data.empty:
            self.lru_cache.put(key, data)
        
        return data
    
    def get(self, key: str) -> Optional[pd.DataFrame]:
        """获取缓存数据"""
        return self.lru_cache.get(key)
    
    def put(self, key: str, data: pd.DataFrame) -> None:
        """存入缓存"""
        self.lru_cache.put(key, data)
    
    def remove(self, key: str) -> bool:
        """删除缓存项"""
        return self.lru_cache.remove(key)
    
    def clear(self) -> None:
        """清空缓存"""
        self.lru_cache.clear()
    
    def get_stats(self) -> dict:
        """获取统计信息"""
        return self.lru_cache.get_stats()
    
    def invalidate_pattern(self, pattern: str) -> int:
        """
        删除匹配模式的缓存项
        
        Args:
            pattern: 匹配模式（简单的字符串包含匹配）
            
        Returns:
            int: 删除的缓存项数量
        """
        keys_to_remove = [
            key for key in self.lru_cache.cache.keys()
            if pattern in key
        ]
        
        for key in keys_to_remove:
            self.lru_cache.remove(key)
        
        return len(keys_to_remove)
    
    def __repr__(self) -> str:
        """字符串表示"""
        return repr(self.lru_cache)


class MultiLevelCache:
    """
    多级缓存
    支持L1内存缓存和L2磁盘缓存
    """
    
    def __init__(
        self,
        l1_size_mb: int = 256,
        l2_size_mb: int = 1024,
        ttl_seconds: int = 3600
    ):
        """
        初始化多级缓存
        
        Args:
            l1_size_mb: L1缓存大小（内存）
            l2_size_mb: L2缓存大小（磁盘）
            ttl_seconds: 缓存过期时间
        """
        self.l1_cache = DataCache(l1_size_mb, ttl_seconds)
        self.l2_cache = DataCache(l2_size_mb, ttl_seconds * 2)  # L2过期时间更长
    
    def get(self, key: str) -> Optional[pd.DataFrame]:
        """
        获取缓存数据（优先L1，然后L2）
        
        Args:
            key: 缓存键
            
        Returns:
            Optional[pd.DataFrame]: 缓存数据
        """
        # 先查L1
        data = self.l1_cache.get(key)
        if data is not None:
            return data
        
        # 再查L2
        data = self.l2_cache.get(key)
        if data is not None:
            # 提升到L1
            self.l1_cache.put(key, data)
            return data
        
        return None
    
    def put(self, key: str, data: pd.DataFrame) -> None:
        """
        存入缓存（同时存入L1和L2）
        
        Args:
            key: 缓存键
            data: 数据
        """
        self.l1_cache.put(key, data)
        self.l2_cache.put(key, data)
    
    def clear(self) -> None:
        """清空所有缓存"""
        self.l1_cache.clear()
        self.l2_cache.clear()
    
    def get_stats(self) -> dict:
        """获取统计信息"""
        return {
            'l1': self.l1_cache.get_stats(),
            'l2': self.l2_cache.get_stats()
        }
