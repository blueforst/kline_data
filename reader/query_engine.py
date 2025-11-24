"""查询引擎"""

from typing import Optional, List, Callable
from datetime import datetime
import pandas as pd

from config import Config
from .parquet_reader import ParquetReader

from rich.console import Console
console = Console()



class QueryEngine:
    """
    查询引擎
    提供高级查询功能和优化
    """
    
    def __init__(self, config: Config):
        """
        初始化查询引擎
        
        Args:
            config: 配置对象
        """
        self.config = config
        self.reader = ParquetReader(config)
    
    def query(
        self,
        exchange: str,
        symbol: str,
        start_time: datetime,
        end_time: datetime,
        interval: str = '1s',
        filters: Optional[List[Callable]] = None,
        columns: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        执行查询
        
        Args:
            exchange: 交易所
            symbol: 交易对
            start_time: 开始时间
            end_time: 结束时间
            interval: 时间周期
            filters: 过滤函数列表
            columns: 指定列
            
        Returns:
            pd.DataFrame: 查询结果
        """
        # 读取数据
        df = self.reader.read_range(
            exchange,
            symbol,
            start_time,
            end_time,
            interval,
            columns
        )
        
        if df.empty:
            return df
        
        # 应用过滤器
        if filters:
            for filter_fn in filters:
                df = filter_fn(df)
                if df.empty:
                    break
        
        return df
    
    def query_aggregated(
        self,
        exchange: str,
        symbol: str,
        start_time: datetime,
        end_time: datetime,
        interval: str = '1s',
        agg_func: str = 'mean',
        group_by: str = 'D'
    ) -> pd.DataFrame:
        """
        聚合查询
        
        Args:
            exchange: 交易所
            symbol: 交易对
            start_time: 开始时间
            end_time: 结束时间
            interval: 时间周期
            agg_func: 聚合函数 ('mean', 'sum', 'max', 'min')
            group_by: 分组周期 ('D'=天, 'W'=周, 'M'=月)
            
        Returns:
            pd.DataFrame: 聚合结果
        """
        df = self.reader.read_range(
            exchange,
            symbol,
            start_time,
            end_time,
            interval
        )
        
        if df.empty:
            return df
        
        # 设置索引
        df = df.set_index('timestamp')
        
        # 分组聚合
        if agg_func == 'mean':
            result = df.resample(group_by).mean()
        elif agg_func == 'sum':
            result = df.resample(group_by).sum()
        elif agg_func == 'max':
            result = df.resample(group_by).max()
        elif agg_func == 'min':
            result = df.resample(group_by).min()
        else:
            raise ValueError(f"Unsupported aggregation function: {agg_func}")
        
        return result.reset_index()
    
    def query_with_condition(
        self,
        exchange: str,
        symbol: str,
        start_time: datetime,
        end_time: datetime,
        interval: str = '1s',
        condition: Optional[str] = None
    ) -> pd.DataFrame:
        """
        条件查询
        
        Args:
            exchange: 交易所
            symbol: 交易对
            start_time: 开始时间
            end_time: 结束时间
            interval: 时间周期
            condition: 查询条件（pandas query语法）
            
        Returns:
            pd.DataFrame: 查询结果
            
        Example:
            >>> query_with_condition(..., condition="close > 50000 and volume > 100")
        """
        df = self.reader.read_range(
            exchange,
            symbol,
            start_time,
            end_time,
            interval
        )
        
        if df.empty or not condition:
            return df
        
        # 应用查询条件
        try:
            return df.query(condition)
        except Exception as e:
            console.print(f"Error applying condition '{condition}': {e}")
            return df
    
    def query_top_n(
        self,
        exchange: str,
        symbol: str,
        start_time: datetime,
        end_time: datetime,
        interval: str = '1s',
        n: int = 10,
        by: str = 'volume',
        ascending: bool = False
    ) -> pd.DataFrame:
        """
        查询Top N记录
        
        Args:
            exchange: 交易所
            symbol: 交易对
            start_time: 开始时间
            end_time: 结束时间
            interval: 时间周期
            n: 数量
            by: 排序字段
            ascending: 是否升序
            
        Returns:
            pd.DataFrame: Top N记录
        """
        df = self.reader.read_range(
            exchange,
            symbol,
            start_time,
            end_time,
            interval
        )
        
        if df.empty:
            return df
        
        # 排序并返回前N条
        return df.nlargest(n, by) if not ascending else df.nsmallest(n, by)
    
    def query_statistics(
        self,
        exchange: str,
        symbol: str,
        start_time: datetime,
        end_time: datetime,
        interval: str = '1s'
    ) -> dict:
        """
        查询统计信息
        
        Args:
            exchange: 交易所
            symbol: 交易对
            start_time: 开始时间
            end_time: 结束时间
            interval: 时间周期
            
        Returns:
            dict: 统计信息
        """
        df = self.reader.read_range(
            exchange,
            symbol,
            start_time,
            end_time,
            interval
        )
        
        if df.empty:
            return {}
        
        stats = {
            'count': len(df),
            'start_time': df['timestamp'].min().isoformat(),
            'end_time': df['timestamp'].max().isoformat(),
            'price': {
                'open_first': float(df['open'].iloc[0]),
                'close_last': float(df['close'].iloc[-1]),
                'high_max': float(df['high'].max()),
                'low_min': float(df['low'].min()),
                'mean': float(df['close'].mean()),
                'std': float(df['close'].std()),
            },
            'volume': {
                'total': float(df['volume'].sum()),
                'mean': float(df['volume'].mean()),
                'max': float(df['volume'].max()),
                'min': float(df['volume'].min()),
            }
        }
        
        return stats
    
    def query_ohlc(
        self,
        exchange: str,
        symbol: str,
        start_time: datetime,
        end_time: datetime,
        interval: str = '1s',
        resample_to: Optional[str] = None
    ) -> pd.DataFrame:
        """
        查询OHLC数据（可选重采样）
        
        Args:
            exchange: 交易所
            symbol: 交易对
            start_time: 开始时间
            end_time: 结束时间
            interval: 原始时间周期
            resample_to: 重采样目标周期
            
        Returns:
            pd.DataFrame: OHLC数据
        """
        df = self.reader.read_range(
            exchange,
            symbol,
            start_time,
            end_time,
            interval,
            columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
        )
        
        if df.empty or not resample_to:
            return df
        
        # 重采样
        df = df.set_index('timestamp')
        
        ohlc_dict = {
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }
        
        resampled = df.resample(resample_to).agg(ohlc_dict)
        resampled = resampled.dropna()
        
        return resampled.reset_index()
    
    def query_price_changes(
        self,
        exchange: str,
        symbol: str,
        start_time: datetime,
        end_time: datetime,
        interval: str = '1s',
        threshold: Optional[float] = None
    ) -> pd.DataFrame:
        """
        查询价格变化
        
        Args:
            exchange: 交易所
            symbol: 交易对
            start_time: 开始时间
            end_time: 结束时间
            interval: 时间周期
            threshold: 变化阈值（百分比）
            
        Returns:
            pd.DataFrame: 包含价格变化的数据
        """
        df = self.reader.read_range(
            exchange,
            symbol,
            start_time,
            end_time,
            interval
        )
        
        if df.empty:
            return df
        
        # 计算变化
        df['price_change'] = df['close'].pct_change() * 100
        df['price_diff'] = df['close'].diff()
        
        # 应用阈值过滤
        if threshold is not None:
            df = df[abs(df['price_change']) >= threshold]
        
        return df
    
    def clear_cache(self) -> None:
        """清空缓存"""
        self.reader.clear_cache()
    
    def get_cache_stats(self) -> Optional[dict]:
        """获取缓存统计"""
        return self.reader.get_cache_stats()


class QueryBuilder:
    """
    查询构建器
    提供链式调用接口
    """
    
    def __init__(self, engine: QueryEngine):
        """
        初始化查询构建器
        
        Args:
            engine: 查询引擎
        """
        self.engine = engine
        self._exchange: Optional[str] = None
        self._symbol: Optional[str] = None
        self._start_time: Optional[datetime] = None
        self._end_time: Optional[datetime] = None
        self._interval: str = '1s'
        self._filters: List[Callable] = []
        self._columns: Optional[List[str]] = None
        self._limit: Optional[int] = None
        self._condition: Optional[str] = None
    
    def exchange(self, exchange: str) -> 'QueryBuilder':
        """设置交易所"""
        self._exchange = exchange
        return self
    
    def symbol(self, symbol: str) -> 'QueryBuilder':
        """设置交易对"""
        self._symbol = symbol
        return self
    
    def time_range(
        self,
        start: datetime,
        end: datetime
    ) -> 'QueryBuilder':
        """设置时间范围"""
        self._start_time = start
        self._end_time = end
        return self
    
    def interval(self, interval: str) -> 'QueryBuilder':
        """设置时间周期"""
        self._interval = interval
        return self
    
    def filter(self, filter_fn: Callable) -> 'QueryBuilder':
        """添加过滤器"""
        self._filters.append(filter_fn)
        return self
    
    def columns(self, *cols: str) -> 'QueryBuilder':
        """指定列"""
        self._columns = list(cols)
        return self
    
    def limit(self, n: int) -> 'QueryBuilder':
        """限制数量"""
        self._limit = n
        return self
    
    def where(self, condition: str) -> 'QueryBuilder':
        """添加条件"""
        self._condition = condition
        return self
    
    def execute(self) -> pd.DataFrame:
        """执行查询"""
        if not self._exchange or not self._symbol:
            raise ValueError("Exchange and symbol are required")
        
        if not self._start_time or not self._end_time:
            raise ValueError("Time range is required")
        
        # 执行查询
        if self._condition:
            df = self.engine.query_with_condition(
                self._exchange,
                self._symbol,
                self._start_time,
                self._end_time,
                self._interval,
                self._condition
            )
        else:
            df = self.engine.query(
                self._exchange,
                self._symbol,
                self._start_time,
                self._end_time,
                self._interval,
                self._filters,
                self._columns
            )
        
        # 应用限制
        if self._limit and not df.empty:
            df = df.head(self._limit)
        
        return df
    
    def to_csv(self, path: str) -> None:
        """导出到CSV"""
        df = self.execute()
        df.to_csv(path, index=False)
    
    def to_json(self, path: str) -> None:
        """导出到JSON"""
        df = self.execute()
        df.to_json(path, orient='records', date_format='iso')
