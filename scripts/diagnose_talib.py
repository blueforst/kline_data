#!/usr/bin/env python3
"""
TA-Lib诊断脚本 - 检查TA-Lib安装和配置状态
"""

import sys
import importlib
import platform
from pathlib import Path

def check_python_version():
    """检查Python版本"""
    print("=== Python版本检查 ===")
    version = sys.version
    print(f"Python版本: {version}")

    major, minor = sys.version_info[:2]
    if major >= 3 and minor >= 7:
        print("✓ Python版本兼容")
        return True
    else:
        print("✗ Python版本过低，需要3.7+")
        return False

def check_talib_installation():
    """检查TA-Lib安装状态"""
    print("\n=== TA-Lib安装检查 ===")

    # 检查Python包
    try:
        import talib
        print(f"✓ Python TA-Lib包已安装: {talib.__version__}")

        # 检查TA-Lib版本
        version_info = talib.__version__.split('.')
        if len(version_info) >= 2:
            major = int(version_info[0])
            minor = int(version_info[1])

            if major >= 0 and minor >= 4:
                print("✓ TA-Lib版本兼容")
                return True
            else:
                print("⚠️ TA-Lib版本较旧，建议升级到0.4.0+")
                return True
        else:
            print("⚠️ 无法解析TA-Lib版本")
            return True

    except ImportError as e:
        print(f"✗ Python TA-Lib包导入失败: {e}")
        return False

def check_talib_functions():
    """检查TA-Lib核心函数"""
    print("\n=== TA-Lib函数检查 ===")

    try:
        import talib
    except ImportError:
        print("✗ TA-Lib未安装，跳过函数检查")
        return False

    # 检查核心函数
    required_functions = {
        'SMA': '简单移动平均',
        'EMA': '指数移动平均',
        'MACD': 'MACD指标',
        'RSI': '相对强弱指标',
        'BBANDS': '布林带',
        'STOCH': '随机指标',
        'ADX': '平均趋向指数'
    }

    missing_functions = []
    working_functions = []

    for func_name, desc in required_functions.items():
        if hasattr(talib, func_name):
            try:
                func = getattr(talib, func_name)
                # 尝试获取函数文档以验证其可用性
                doc = func.__doc__ if func.__doc__ else "无文档"
                print(f"✓ {func_name} ({desc}) - 可用")
                working_functions.append(func_name)
            except Exception as e:
                print(f"✗ {func_name} ({desc}) - 错误: {e}")
                missing_functions.append(func_name)
        else:
            print(f"✗ {func_name} ({desc}) - 缺失")
            missing_functions.append(func_name)

    if missing_functions:
        print(f"\n⚠️ 缺失/错误函数: {', '.join(missing_functions)}")
        print(f"✓ 可用函数: {', '.join(working_functions)}")
        return len(working_functions) > len(missing_functions)
    else:
        print("✓ 所有核心函数都可用")
        return True

def test_talib_functionality():
    """测试TA-Lib基本功能"""
    print("\n=== TA-Lib功能测试 ===")

    try:
        import talib
        import numpy as np
    except ImportError as e:
        print(f"✗ 导入失败: {e}")
        return False

    # 生成测试数据
    np.random.seed(42)
    data = np.random.randn(100).cumsum() + 100

    try:
        # 测试SMA
        sma = talib.SMA(data, timeperiod=20)
        print("✓ SMA计算成功")

        # 测试EMA
        ema = talib.EMA(data, timeperiod=20)
        print("✓ EMA计算成功")

        # 测试MACD
        macd, signal, hist = talib.MACD(data)
        print("✓ MACD计算成功")

        # 测试RSI
        rsi = talib.RSI(data)
        print("✓ RSI计算成功")

        # 测试布林带
        upper, middle, lower = talib.BBANDS(data)
        print("✓ Bollinger Bands计算成功")

        print("✓ 所有功能测试通过")
        return True

    except Exception as e:
        print(f"✗ 功能测试失败: {e}")
        return False

def check_dependencies():
    """检查相关依赖"""
    print("\n=== 依赖检查 ===")

    dependencies = {
        'numpy': '数值计算库',
        'pandas': '数据处理库',
    }

    all_ok = True
    for dep, desc in dependencies.items():
        try:
            module = importlib.import_module(dep)
            version = getattr(module, '__version__', 'unknown')
            print(f"✓ {dep} {version} - {desc}")
        except ImportError:
            print(f"✗ {dep} - {desc} (缺失)")
            all_ok = False

    return all_ok

def check_system_info():
    """检查系统信息"""
    print("\n=== 系统信息 ===")
    print(f"操作系统: {platform.system()} {platform.release()}")
    print(f"架构: {platform.machine()}")
    print(f"Python路径: {sys.executable}")

def generate_recommendations():
    """生成修复建议"""
    print("\n=== 修复建议 ===")

    # 检查当前状态
    try:
        import talib
        talib_available = True
    except ImportError:
        talib_available = False

    if not talib_available:
        print("🔧 TA-Lib安装建议:")
        print("1. 使用pip安装:")
        print("   pip install ta-lib>=0.4.28")
        print()
        print("2. 如果pip安装失败，尝试conda:")
        print("   conda install -c conda-forge ta-lib")
        print()
        print("3. 如果仍然失败，从源码编译:")
        print("   # macOS")
        print("   brew install ta-lib")
        print("   pip install ta-lib")
        print()
        print("   # Ubuntu/Debian")
        print("   sudo apt-get install libta-lib-dev")
        print("   pip install ta-lib")
        print()

    print("💡 项目修复建议:")
    print("1. 使用TA-Lib适配器: indicators/talib_adapter.py")
    print("2. 启用Pandas后备实现")
    print("3. 运行诊断脚本验证修复: python scripts/diagnose_talib.py")
    print()
    print("📋 验证步骤:")
    print("1. 运行本脚本确认TA-Lib状态")
    print("2. 运行技术指标测试:")
    print("   python -m pytest tests/indicators/ -v")
    print("3. 检查测试覆盖率:")
    print("   python -m pytest --cov=indicators --cov-report=term-missing")

def main():
    """主函数"""
    print("TA-Lib诊断报告")
    print("=" * 50)

    # 执行各项检查
    checks = [
        ("Python版本", check_python_version),
        ("TA-Lib安装", check_talib_installation),
        ("TA-Lib函数", check_talib_functions),
        ("TA-Lib功能", test_talib_functionality),
        ("依赖检查", check_dependencies),
    ]

    results = {}
    for name, check_func in checks:
        try:
            results[name] = check_func()
        except Exception as e:
            print(f"✗ {name}检查出错: {e}")
            results[name] = False

    # 显示系统信息
    check_system_info()

    # 总结
    print("\n" + "=" * 50)
    print("诊断总结:")

    passed_checks = sum(results.values())
    total_checks = len(results)

    print(f"通过检查: {passed_checks}/{total_checks}")

    if passed_checks == total_checks:
        print("🎉 所有检查通过！TA-Lib配置正常")
        return_code = 0
    elif passed_checks >= total_checks // 2:
        print("⚠️ 部分检查通过，TA-Lib基本可用")
        return_code = 1
    else:
        print("❌ 多项检查失败，TA-Lib配置存在问题")
        return_code = 2

    # 生成修复建议
    generate_recommendations()

    print(f"\n诊断完成，退出码: {return_code}")
    return return_code

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)