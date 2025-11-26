# 技术指标层 (Indicators Layer)

完整的技术指标计算模块，支持30+种常用技术指标。

## 🎉 v2.0 重构更新 (2025-11-26)

**主要改进：**
- ✅ 增强 TA-Lib 和 Pandas 的兼容性
- ✅ 新增工具函数模块 (`utils.py`)
- ✅ 改进 TA-Lib 适配器，支持更多指标
- ✅ 统一的数据格式转换和验证
- ✅ 自动回退机制（TA-Lib → Pandas）
- ✅ 完善的类型注解和文档

详见 [REFACTOR_NOTES.md](./REFACTOR_NOTES.md)

## 📊 指标分类

### 1. 移动平均类 (7个)

| 指标 | 类名 | 函数 | 说明 |
|------|------|------|------|
| SMA | `SMA` | `calculate_ma(..., ma_type='sma')` | 简单移动平均 |
| EMA | `EMA` | `calculate_ma(..., ma_type='ema')` | 指数移动平均 |
| WMA | `WMA` | `calculate_ma(..., ma_type='wma')` | 加权移动平均 |
| DEMA | `DEMA` | `calculate_ma(..., ma_type='dema')` | 双重指数移动平均 |
| TEMA | `TEMA` | `calculate_ma(..., ma_type='tema')` | 三重指数移动平均 |
| VWMA | `VWMA` | `calculate_ma(..., ma_type='vwma')` | 成交量加权移动平均 |
| HMA | `HMA` | `calculate_ma(..., ma_type='hma')` | 赫尔移动平均 |

### 2. 布林带类 (3个)

| 指标 | 类名 | 函数 | 说明 |
|------|------|------|------|
| BOLL | `BollingerBands` | `calculate_bollinger()` | 布林带 |
| KC | `KeltnerChannel` | `calculate_keltner()` | 肯特纳通道 |
| DC | `DonchianChannel` | `calculate_donchian()` | 唐奇安通道 |

### 3. MACD类 (3个)

| 指标 | 类名 | 函数 | 说明 |
|------|------|------|------|
| MACD | `MACD` | `calculate_macd()` | 异同移动平均线 |
| PPO | `PPO` | `calculate_ppo()` | 百分比价格振荡器 |
| APO | `APO` | - | 绝对价格振荡器 |

### 4. 振荡指标 (6个)

| 指标 | 类名 | 函数 | 说明 |
|------|------|------|------|
| RSI | `RSI` | `calculate_rsi()` | 相对强弱指标 |
| Stochastic | `StochasticOscillator` | `calculate_stochastic()` | 随机振荡器 |
| CCI | `CCI` | `calculate_cci()` | 顺势指标 |
| Williams %R | `WilliamsR` | `calculate_williams_r()` | 威廉指标 |
| ROC | `ROC` | `calculate_roc()` | 变化率 |
| Momentum | `MOM` | `calculate_momentum()` | 动量指标 |

### 5. 波动率指标 (7个)

| 指标 | 类名 | 函数 | 说明 |
|------|------|------|------|
| ATR | `ATR` | `calculate_atr()` | 平均真实波幅 |
| NATR | `NormalizedATR` | `calculate_natr()` | 归一化ATR |
| STD | `StandardDeviation` | `calculate_std()` | 标准差 |
| HV | `HistoricalVolatility` | `calculate_hv()` | 历史波动率 |
| UI | `UlcerIndex` | `calculate_ulcer_index()` | 溃疡指数 |
| MI | `MassIndex` | - | 质量指数 |
| CI | `ChoppinessIndex` | - | 震荡指数 |

### 6. 成交量指标 (8个)

| 指标 | 类名 | 函数 | 说明 |
|------|------|------|------|
| OBV | `OBV` | `calculate_obv()` | 能量潮 |
| Volume MA | `VolumeMA` | `calculate_volume_ma()` | 成交量移动平均 |
| VWAP | `VWAP` | `calculate_vwap()` | 成交量加权平均价 |
| MFI | `MFI` | `calculate_mfi()` | 资金流量指标 |
| A/D | `AD` | `calculate_ad()` | 累积/派发 |
| CMF | `CMF` | `calculate_cmf()` | 蔡金资金流量 |
| EMV | `EMV` | - | 简易波动指标 |
| Force Index | `ForceIndex` | - | 强力指数 |

## 🚀 快速开始

### 方式1: 使用便捷函数（推荐）

```python
from indicators import (
    calculate_ma,
    calculate_bollinger,
    calculate_macd,
    calculate_rsi,
    calculate_atr,
    calculate_obv,
)

# 计算移动平均
df = calculate_ma(df, period=20, ma_type='sma')
df = calculate_ma(df, period=20, ma_type='ema')

# 计算布林带
df = calculate_bollinger(df, period=20, std_dev=2.0)

# 计算MACD
df = calculate_macd(df, fast_period=12, slow_period=26, signal_period=9)

# 计算RSI
df = calculate_rsi(df, period=14)

# 计算ATR
df = calculate_atr(df, period=14)

# 计算OBV
df = calculate_obv(df)
```

### 方式2: 使用指标管理器

```python
from indicators import IndicatorManager

manager = IndicatorManager()

# 批量计算多个指标
df = manager.calculate_multiple(df, {
    'sma': {'period': 20},
    'ema': {'period': 50},
    'rsi': {'period': 14},
    'macd': {'fast_period': 12, 'slow_period': 26, 'signal_period': 9},
    'boll': {'period': 20, 'std_dev': 2.0},
    'atr': {'period': 14},
    'obv': {},
})
```

### 方式3: 使用指标库（最简单）

```python
from indicators import IndicatorLibrary

# 添加所有常用指标
df = IndicatorLibrary.add_common_indicators(
    df,
    ma_periods=[5, 10, 20, 50, 200],  # MA周期
    include_macd=True,
    include_rsi=True,
    include_boll=True,
    include_atr=True,
    include_volume=True
)

# 或者按类别添加
df = IndicatorLibrary.add_trend_indicators(df)     # 趋势指标
df = IndicatorLibrary.add_momentum_indicators(df)  # 动量指标
df = IndicatorLibrary.add_volatility_indicators(df) # 波动率指标
df = IndicatorLibrary.add_volume_indicators(df)    # 成交量指标
```

### 方式4: 使用指标类

```python
from indicators import SMA, RSI, MACD, BollingerBands

# 创建指标实例
sma = SMA()
rsi = RSI()
macd = MACD()
boll = BollingerBands()

# 计算指标
df = sma.calculate(df, period=20)
df = rsi.calculate(df, period=14)
df = macd.calculate(df)
df = boll.calculate(df, period=20, std_dev=2.0)
```

## 📈 获取交易信号

某些指标支持生成交易信号：

```python
from indicators import get_macd_signals
from indicators import RSI

# MACD信号
df = get_macd_signals(df)

# 检查信号
golden_cross = df[df['macd_golden_cross']]  # 金叉
death_cross = df[df['macd_death_cross']]    # 死叉

# RSI信号
rsi = RSI()
df = rsi.get_signals(df, period=14, oversold=30, overbought=70)

oversold = df[df['rsi_oversold']]      # 超卖
overbought = df[df['rsi_overbought']]  # 超买

# 布林带信号
from indicators import BollingerBands

boll = BollingerBands()
df = boll.get_signals(df, period=20, std_dev=2.0)

breakout_up = df[df['boll_breakout_up']]      # 突破上轨
breakout_down = df[df['boll_breakout_down']]  # 突破下轨
squeeze = df[df['boll_squeeze']]              # 带宽收窄
```

## 🎛️ 指标管理器

### 列出所有可用指标

```python
from indicators import list_available_indicators

indicators = list_available_indicators()
print(f"共有 {len(indicators)} 个指标:")
print(indicators)
# ['sma', 'ema', 'wma', 'dema', 'tema', 'vwma', 'hma',
#  'boll', 'kc', 'dc', 'macd', 'ppo', 'apo', 'rsi',
#  'stoch', 'cci', 'williams_r', 'roc', 'momentum',
#  'atr', 'natr', 'std', 'hv', 'ulcer', 'mass_index',
#  'choppiness', 'obv', 'volume_ma', 'vwap', 'mfi',
#  'ad', 'cmf', 'emv', 'force_index']
```

### 使用流水线计算

```python
from indicators import IndicatorManager, IndicatorPipeline

manager = IndicatorManager()

# 创建流水线
pipeline = manager.create_pipeline([
    ('sma', {'period': 20}),
    ('ema', {'period': 50}),
    ('rsi', {'period': 14}),
    ('macd', {}),
])

# 批量计算
df = pipeline.calculate(df)
```

## 🔧 自定义指标

可以轻松创建自定义指标：

```python
from indicators.base import BaseIndicator
import pandas as pd

class MyCustomIndicator(BaseIndicator):
    """自定义指标"""
    
    def __init__(self):
        super().__init__('MyIndicator')
    
    def calculate(self, df: pd.DataFrame, period: int = 10) -> pd.DataFrame:
        """计算指标"""
        self.validate_data(df, ['close'])
        
        result = df.copy()
        # 你的计算逻辑
        result['my_indicator'] = result['close'].rolling(period).mean()
        
        return result

# 注册到管理器
from indicators import get_indicator_manager

manager = get_indicator_manager()
manager.register('my_indicator', MyCustomIndicator())

# 使用
df = manager.calculate(df, 'my_indicator', period=10)
```

## 📊 性能优化建议

1. **批量计算优于逐个计算**
   ```python
   # ❌ 不推荐
   df = calculate_ma(df, 20, 'sma')
   df = calculate_ma(df, 50, 'sma')
   df = calculate_rsi(df, 14)
   
   # ✅ 推荐
   df = IndicatorLibrary.add_common_indicators(df)
   ```

2. **使用指标管理器批量计算**
   ```python
   manager = IndicatorManager()
   df = manager.calculate_multiple(df, indicators_config)
   ```

3. **避免重复计算**
   ```python
   # 计算一次后保存结果
   df_with_indicators = IndicatorLibrary.add_common_indicators(df)
   ```

## 📝 注意事项

1. **数据要求**
   - 必须包含OHLCV列（open, high, low, close, volume）
   - 时间戳列名为 `timestamp`
   - 数据按时间升序排列

2. **周期限制**
   - 指标周期不能大于数据长度
   - 某些指标需要最小数据量（如MACD需要至少33根K线）

3. **NaN处理**
   - 计算初期会产生NaN值（不足周期）
   - 使用 `df.dropna()` 删除或 `df.fillna()` 填充

4. **列名规则**
   - 指标列名格式: `{indicator}_{period}`
   - 例: `sma_20`, `ema_50`, `rsi_14`

## 🎯 实际应用示例

### 趋势判断

```python
# 计算多周期MA
df = calculate_multiple_ma(df, [20, 50, 200], 'sma')

# 判断趋势
last = df.iloc[-1]
if last['sma_20'] > last['sma_50'] > last['sma_200']:
    print("强势上涨趋势（多头排列）")
elif last['sma_20'] < last['sma_50'] < last['sma_200']:
    print("强势下跌趋势（空头排列）")
```

### 超买超卖判断

```python
df = calculate_rsi(df, 14)

last = df.iloc[-1]
if last['rsi_14'] > 70:
    print("超买，可能回调")
elif last['rsi_14'] < 30:
    print("超卖，可能反弹")
```

### 波动率分析

```python
df = calculate_atr(df, 14)
df = calculate_bollinger(df, 20)

last = df.iloc[-1]
atr_pct = last['atr_14'] / last['close'] * 100

if atr_pct > 3:
    print("高波动环境")
elif last['boll_width'] < df['boll_width'].rolling(50).mean().iloc[-1] * 0.5:
    print("带宽收窄，可能突破")
```

### 综合分析

```python
# 计算所有指标
df = IndicatorLibrary.add_common_indicators(df)

# 最新数据分析
last = df.iloc[-1]

# 趋势
trend = "上涨" if last['sma_20'] > last['sma_50'] else "下跌"

# 动量
momentum = "强" if last['rsi_14'] > 50 else "弱"

# 信号
if last['macd'] > last['macd_signal'] and last['rsi_14'] < 70:
    signal = "买入"
elif last['macd'] < last['macd_signal'] and last['rsi_14'] > 30:
    signal = "卖出"
else:
    signal = "观望"

print(f"趋势: {trend}, 动量: {momentum}, 信号: {signal}")
```

## 📚 更多资源

- **示例代码**: `examples/indicators_example.py`
- **测试代码**: `tests/test_indicators.py`（待添加）
- **API文档**: 查看各个模块的docstring

## 🤝 贡献指南

欢迎贡献新的技术指标！

1. 继承 `BaseIndicator` 或相应的基类
2. 实现 `calculate()` 方法
3. 添加到相应的模块文件
4. 在 `manager.py` 中注册
5. 添加测试和示例

## 📄 许可证

MIT License
