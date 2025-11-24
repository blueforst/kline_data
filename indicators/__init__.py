"""技术指标层模块"""

# 基类
from .base import (
    BaseIndicator,
    MovingAverageBase,
    OscillatorBase,
    VolatilityBase,
    VolumeBase,
    IndicatorPipeline,
    validate_ohlcv,
)

# 移动平均
from .moving_average import (
    SMA, EMA, WMA, DEMA, TEMA, VWMA, HMA,
    calculate_ma,
    calculate_multiple_ma,
)

# 布林带类
from .bollinger import (
    BollingerBands,
    KeltnerChannel,
    DonchianChannel,
    calculate_bollinger,
    calculate_keltner,
    calculate_donchian,
)

# MACD类
from .macd import (
    MACD,
    PPO,
    APO,
    calculate_macd,
    calculate_ppo,
    get_macd_signals,
)

# 振荡指标
from .oscillator import (
    RSI,
    StochasticOscillator,
    CCI,
    WilliamsR,
    ROC,
    MOM,
    calculate_rsi,
    calculate_stochastic,
    calculate_cci,
    calculate_williams_r,
    calculate_roc,
    calculate_momentum,
)

# 波动率指标
from .volatility import (
    ATR,
    NormalizedATR,
    StandardDeviation,
    HistoricalVolatility,
    UlcerIndex,
    MassIndex,
    ChoppinessIndex,
    calculate_atr,
    calculate_natr,
    calculate_std,
    calculate_hv,
)

# 成交量指标
from .volume import (
    OBV,
    VolumeMA,
    VWAP,
    MFI,
    AD,
    CMF,
    EMV,
    ForceIndex,
    calculate_obv,
    calculate_volume_ma,
    calculate_vwap,
    calculate_mfi,
    calculate_ad,
    calculate_cmf,
)

# 指标管理器
from .manager import (
    IndicatorManager,
    IndicatorLibrary,
    get_indicator_manager,
    calculate_indicator,
    list_available_indicators,
)

__all__ = [
    # Base
    'BaseIndicator',
    'MovingAverageBase',
    'OscillatorBase',
    'VolatilityBase',
    'VolumeBase',
    'IndicatorPipeline',
    'validate_ohlcv',
    
    # Moving Average
    'SMA', 'EMA', 'WMA', 'DEMA', 'TEMA', 'VWMA', 'HMA',
    'calculate_ma',
    'calculate_multiple_ma',
    
    # Bollinger Bands
    'BollingerBands',
    'KeltnerChannel',
    'DonchianChannel',
    'calculate_bollinger',
    'calculate_keltner',
    'calculate_donchian',
    
    # MACD
    'MACD', 'PPO', 'APO',
    'calculate_macd',
    'calculate_ppo',
    'get_macd_signals',
    
    # Oscillator
    'RSI',
    'StochasticOscillator',
    'CCI',
    'WilliamsR',
    'ROC',
    'MOM',
    'calculate_rsi',
    'calculate_stochastic',
    'calculate_cci',
    'calculate_williams_r',
    'calculate_roc',
    'calculate_momentum',
    
    # Volatility
    'ATR',
    'NormalizedATR',
    'StandardDeviation',
    'HistoricalVolatility',
    'UlcerIndex',
    'MassIndex',
    'ChoppinessIndex',
    'calculate_atr',
    'calculate_natr',
    'calculate_std',
    'calculate_hv',
    
    # Volume
    'OBV',
    'VolumeMA',
    'VWAP',
    'MFI',
    'AD',
    'CMF',
    'EMV',
    'ForceIndex',
    'calculate_obv',
    'calculate_volume_ma',
    'calculate_vwap',
    'calculate_mfi',
    'calculate_ad',
    'calculate_cmf',
    
    # Manager
    'IndicatorManager',
    'IndicatorLibrary',
    'get_indicator_manager',
    'calculate_indicator',
    'list_available_indicators',
]
