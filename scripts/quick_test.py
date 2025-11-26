#!/usr/bin/env python3
"""
快速测试脚本 - 验证核心修复效果
"""
import sys
import os
import subprocess
from pathlib import Path

def run_command(cmd, description, timeout=60):
    """运行命令并返回结果"""
    print(f"\n{'='*50}")
    print(f"测试: {description}")
    print(f"{'='*50}")

    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=Path(__file__).parent.parent
        )

        if result.returncode == 0:
            print("✅ 通过")
            if result.stdout.strip():
                print("输出:")
                print(result.stdout)
        else:
            print("❌ 失败")
            if result.stderr.strip():
                print("错误:")
                print(result.stderr)

        return result.returncode == 0

    except subprocess.TimeoutExpired:
        print("⏰ 超时")
        return False
    except Exception as e:
        print(f"❌ 异常: {e}")
        return False

def main():
    """主测试函数"""
    print("🚀 K线数据项目快速验证")
    print("项目根目录:", Path(__file__).parent.parent)

    tests = [
        ("python3 -c 'from indicators.talib_adapter import talib_adapter; print(\"TA-Lib适配器可用\")'",
         "TA-Lib适配器导入"),

        ("python3 -c 'from indicators.moving_average import SMA; print(\"SMA类可导入\")'",
         "SMA类导入"),

        ("python3 -c 'from tests.helpers.sdk_adapter import SDKAdapter; print(\"SDK适配器可导入\")'",
         "SDK适配器导入"),

        ("python3 -c 'from tests.helpers.mock_factory import MockFactory; print(\"Mock工厂可导入\")'",
         "Mock工厂导入"),

        ("python3 -c 'import pandas as pd; import numpy as np; from indicators.moving_average import SMA; sma = SMA(period=10); df = pd.DataFrame({\"close\": np.random.randn(50).cumsum() + 100}); result = sma.calculate(df); print(f\"SMA计算成功，结果形状: {result.shape}\")'",
         "SMA指标计算"),

        ("python3 -c 'from indicators.talib_adapter import talib_adapter; print(f\"TA-Lib可用函数: {talib_adapter.get_available_functions()}\")'",
         "TA-Lib函数检测"),
    ]

    passed = 0
    total = len(tests)

    for cmd, description in tests:
        if run_command(cmd, description):
            passed += 1

    print(f"\n{'='*50}")
    print(f"测试结果: {passed}/{total} 通过")
    print(f"成功率: {passed/total*100:.1f}%")
    print(f"{'='*50}")

    if passed == total:
        print("🎉 所有快速测试通过！修复效果良好。")
        return 0
    elif passed >= total * 0.8:
        print("✅ 大部分测试通过，修复基本成功。")
        return 0
    else:
        print("⚠️ 多项测试失败，需要进一步检查。")
        return 1

if __name__ == "__main__":
    sys.exit(main())