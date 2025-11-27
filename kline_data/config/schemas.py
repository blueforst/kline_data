"""配置数据模型定义"""

from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


class SystemConfig(BaseModel):
    """系统配置"""
    version: str = "1.0.0"
    log_level: str = "INFO"
    log_path: str = "./logs"
    timezone: str = "UTC"
    display_timezone: str = "local"
    
    @field_validator('log_level')
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in valid_levels:
            raise ValueError(f"log_level must be one of {valid_levels}")
        return v.upper()
    
    @field_validator('timezone')
    @classmethod
    def validate_timezone(cls, v: str) -> str:
        if v != "UTC":
            raise ValueError("Internal timezone must be UTC")
        return v
    
    @field_validator('display_timezone')
    @classmethod
    def validate_display_timezone(cls, v: str) -> str:
        if v not in ['local', 'UTC']:
            raise ValueError("display_timezone must be 'local' or 'UTC'")
        return v


class PartitionConfig(BaseModel):
    """分区配置"""
    enabled: bool = True
    granularity: str = "month"
    
    @field_validator('granularity')
    @classmethod
    def validate_granularity(cls, v: str) -> str:
        valid_values = ['year', 'month', 'day']
        if v not in valid_values:
            raise ValueError(f"granularity must be one of {valid_values}")
        return v


class RetentionConfig(BaseModel):
    """数据保留策略配置"""
    enabled: bool = False
    days: int = 365
    
    @field_validator('days')
    @classmethod
    def validate_days(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("days must be positive")
        return v


class StorageConfig(BaseModel):
    """存储配置"""
    root_path: str = "./data"
    separate_by_exchange: bool = True
    separate_by_symbol: bool = True
    format: str = "parquet"
    compression: str = "snappy"
    partition: PartitionConfig = Field(default_factory=PartitionConfig)
    retention: RetentionConfig = Field(default_factory=RetentionConfig)
    
    @field_validator('compression')
    @classmethod
    def validate_compression(cls, v: str) -> str:
        valid_compressions = ['snappy', 'gzip', 'brotli', 'lz4', 'zstd']
        if v not in valid_compressions:
            raise ValueError(f"compression must be one of {valid_compressions}")
        return v
    
    @field_validator('format')
    @classmethod
    def validate_format(cls, v: str) -> str:
        if v != 'parquet':
            raise ValueError("Only 'parquet' format is supported")
        return v
    
    def get_root_path(self) -> Path:
        """获取根路径的Path对象"""
        return Path(self.root_path).resolve()

    @property
    def metadata_path(self) -> Path:
        """元数据目录路径，统一供CLI等调用"""
        return self.get_root_path() / "metadata"


class ProxyConfig(BaseModel):
    """代理配置"""
    http: Optional[str] = None
    https: Optional[str] = None
    
    def to_dict(self) -> Optional[Dict[str, str]]:
        """转换为字典格式"""
        if self.http or self.https:
            return {
                'http': self.http,
                'https': self.https
            }
        return None


class RateLimitConfig(BaseModel):
    """限流配置"""
    enabled: bool = True
    requests_per_minute: int = 1200
    
    @field_validator('requests_per_minute')
    @classmethod
    def validate_rpm(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("requests_per_minute must be positive")
        return v


class RetryConfig(BaseModel):
    """重试配置"""
    max_attempts: int = 3
    backoff_factor: float = 2.0
    timeout: int = 30
    
    @field_validator('max_attempts')
    @classmethod
    def validate_max_attempts(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("max_attempts must be positive")
        return v
    
    @field_validator('backoff_factor')
    @classmethod
    def validate_backoff_factor(cls, v: float) -> float:
        if v < 1:
            raise ValueError("backoff_factor must be >= 1")
        return v
    
    @field_validator('timeout')
    @classmethod
    def validate_timeout(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("timeout must be positive")
        return v


class CCXTConfig(BaseModel):
    """CCXT配置"""
    proxy: ProxyConfig = Field(default_factory=ProxyConfig)
    rate_limit: RateLimitConfig = Field(default_factory=RateLimitConfig)
    retry: RetryConfig = Field(default_factory=RetryConfig)
    exchanges: List[str] = ["binance", "okx", "bybit"]
    
    @field_validator('exchanges')
    @classmethod
    def validate_exchanges(cls, v: List[str]) -> List[str]:
        if not v:
            raise ValueError("At least one exchange must be specified")
        return v


class CacheConfig(BaseModel):
    """缓存配置"""
    enabled: bool = True
    max_size_mb: int = 512
    ttl_seconds: int = 3600
    
    @field_validator('max_size_mb')
    @classmethod
    def validate_max_size(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("max_size_mb must be positive")
        return v
    
    @field_validator('ttl_seconds')
    @classmethod
    def validate_ttl(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("ttl_seconds must be positive")
        return v


class MemoryConfig(BaseModel):
    """内存管理配置"""
    max_usage_mb: int = 4096
    chunk_size: int = 100000
    cache: CacheConfig = Field(default_factory=CacheConfig)
    
    @field_validator('max_usage_mb')
    @classmethod
    def validate_max_usage(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("max_usage_mb must be positive")
        return v
    
    @field_validator('chunk_size')
    @classmethod
    def validate_chunk_size(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("chunk_size must be positive")
        return v

    @property
    def max_cache_size_mb(self) -> int:
        """兼容旧配置键，映射到 cache.max_size_mb"""
        return self.cache.max_size_mb


class AggregationConfig(BaseModel):
    """聚合方法配置"""
    open: str = "first"
    high: str = "max"
    low: str = "min"
    close: str = "last"
    volume: str = "sum"


class ResamplingConfig(BaseModel):
    """重采样配置"""
    supported_intervals: List[str] = [
        "1s", "5s", "15s", "30s",
        "1m", "5m", "15m", "30m",
        "1h", "4h", "1d"
    ]
    precompute_intervals: List[str] = ["1m", "5m", "1h"]
    aggregation: AggregationConfig = Field(default_factory=AggregationConfig)
    
    @field_validator('supported_intervals')
    @classmethod
    def validate_intervals(cls, v: List[str]) -> List[str]:
        if not v:
            raise ValueError("At least one interval must be supported")
        return v


class IndicatorDefaultsConfig(BaseModel):
    """指标默认参数配置"""
    ma_periods: List[int] = [5, 10, 20, 50, 200]
    ema_periods: List[int] = [12, 26]
    boll_period: int = 20
    boll_std: float = 2.0
    rsi_period: int = 14
    macd: List[int] = [12, 26, 9]
    
    @field_validator('ma_periods', 'ema_periods')
    @classmethod
    def validate_periods(cls, v: List[int]) -> List[int]:
        if not all(p > 0 for p in v):
            raise ValueError("All periods must be positive")
        return v
    
    @field_validator('macd')
    @classmethod
    def validate_macd(cls, v: List[int]) -> List[int]:
        if len(v) != 3:
            raise ValueError("MACD must have exactly 3 parameters [fast, slow, signal]")
        if not all(p > 0 for p in v):
            raise ValueError("All MACD periods must be positive")
        return v


class IndicatorsConfig(BaseModel):
    """指标配置"""
    defaults: IndicatorDefaultsConfig = Field(default_factory=IndicatorDefaultsConfig)
    batch_compute: bool = True


class AuthConfig(BaseModel):
    """认证配置"""
    enabled: bool = False
    api_key: str = ""


class APIRateLimitConfig(BaseModel):
    """API限流配置"""
    enabled: bool = True
    requests_per_minute: int = 1000


class CORSConfig(BaseModel):
    """CORS配置"""
    enabled: bool = True
    origins: List[str] = ["*"]


class APIConfig(BaseModel):
    """API服务配置"""
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 4
    auth: AuthConfig = Field(default_factory=AuthConfig)
    rate_limit: APIRateLimitConfig = Field(default_factory=APIRateLimitConfig)
    cors: CORSConfig = Field(default_factory=CORSConfig)
    
    @field_validator('port')
    @classmethod
    def validate_port(cls, v: int) -> int:
        if not (1 <= v <= 65535):
            raise ValueError("port must be between 1 and 65535")
        return v
    
    @field_validator('workers')
    @classmethod
    def validate_workers(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("workers must be positive")
        return v


class CLIConfig(BaseModel):
    """CLI配置"""
    default_exchange: str = "binance"
    default_symbol: str = "BTC/USDT"
    output_format: str = "table"
    
    @field_validator('output_format')
    @classmethod
    def validate_output_format(cls, v: str) -> str:
        valid_formats = ['table', 'json', 'csv']
        if v not in valid_formats:
            raise ValueError(f"output_format must be one of {valid_formats}")
        return v


class Config(BaseModel):
    """完整配置模型"""
    system: SystemConfig = Field(default_factory=SystemConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    ccxt: CCXTConfig = Field(default_factory=CCXTConfig)
    memory: MemoryConfig = Field(default_factory=MemoryConfig)
    resampling: ResamplingConfig = Field(default_factory=ResamplingConfig)
    indicators: IndicatorsConfig = Field(default_factory=IndicatorsConfig)
    api: APIConfig = Field(default_factory=APIConfig)
    cli: CLIConfig = Field(default_factory=CLIConfig)
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值，支持点号分隔的嵌套键

        Args:
            key: 配置键，支持 'system.log_level' 格式
            default: 默认值

        Returns:
            配置值
        """
        keys = key.split('.')
        value = self

        try:
            for k in keys:
                if isinstance(value, dict):
                    value = value[k]
                else:
                    value = getattr(value, k)
            return value
        except (KeyError, AttributeError):
            return default

    def model_post_init(self, __context: Any) -> None:
        """模型初始化后的处理"""
        # 创建必要的目录
        root_path = self.storage.get_root_path()
        root_path.mkdir(parents=True, exist_ok=True)

        log_path = Path(self.system.log_path)
        log_path.mkdir(parents=True, exist_ok=True)


# 别名以便测试导入
ConfigSchema = Config
