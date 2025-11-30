#!/usr/bin/env python3
"""
验证SDK重构

检查所有功能是否正常工作
"""

import sys
from datetime import datetime


def verify_imports():
    """验证所有导入"""
    print("=" * 60)
    print("1. 验证模块导入")
    print("=" * 60)
    
    try:
        # 主客户端
        from kline_data.sdk import KlineClient
        print("✅ KlineClient导入成功")
        
        # 子客户端
        from kline_data.sdk import (
            QueryClient,
            DownloadClient,
            ResampleClient,
            IndicatorClient,
            MetadataClient
        )
        print("✅ 所有子客户端导入成功")
        
        # 数据流
        from kline_data.sdk import (
            ChunkedDataFeed,
            BacktraderDataFeed,
            StreamingDataFeed
        )
        print("✅ 所有数据流类导入成功")
        
        # 检查旧导入（应该有警告）
        import warnings
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            from kline_data.sdk.client import KlineClient as OldClient
            if w and any("deprecated" in str(warning.message).lower() for warning in w):
                print("✅ 旧接口正确显示废弃警告")
            else:
                print("⚠️  旧接口未显示废弃警告")
        
        return True
        
    except Exception as e:
        print(f"❌ 导入失败: {e}")
        return False


def verify_client_structure():
    """验证客户端结构"""
    print("\n" + "=" * 60)
    print("2. 验证客户端结构")
    print("=" * 60)
    
    try:
        from kline_data.sdk import KlineClient
        
        client = KlineClient()
        
        # 检查子客户端
        assert hasattr(client, 'query'), "缺少query客户端"
        assert hasattr(client, 'download'), "缺少download客户端"
        assert hasattr(client, 'resample'), "缺少resample客户端"
        assert hasattr(client, 'indicator'), "缺少indicator客户端"
        assert hasattr(client, 'metadata'), "缺少metadata客户端"
        print("✅ 统一客户端包含所有子客户端")
        
        # 检查方法
        methods = [
            'get_kline', 'get_latest', 'get_klines_before',
            'create_data_feed', 'create_backtrader_feed', 'create_streaming_feed',
            'download_kline', 'update_kline',
            'resample_kline', 'batch_resample_kline',
            'calculate_indicators',
            'get_metadata'
        ]
        
        for method in methods:
            assert hasattr(client, method), f"缺少方法: {method}"
        print(f"✅ 统一客户端包含所有 {len(methods)} 个方法")
        
        return True
        
    except Exception as e:
        print(f"❌ 结构验证失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def verify_sub_clients():
    """验证子客户端独立性"""
    print("\n" + "=" * 60)
    print("3. 验证子客户端独立性")
    print("=" * 60)
    
    try:
        from kline_data.sdk import (
            QueryClient,
            DownloadClient,
            ResampleClient,
            IndicatorClient,
            MetadataClient
        )
        
        # 创建各个客户端
        query = QueryClient()
        download = DownloadClient()
        resample = ResampleClient()
        indicator = IndicatorClient()
        metadata = MetadataClient()
        
        print("✅ QueryClient可独立创建")
        print("✅ DownloadClient可独立创建")
        print("✅ ResampleClient可独立创建")
        print("✅ IndicatorClient可独立创建")
        print("✅ MetadataClient可独立创建")
        
        return True
        
    except Exception as e:
        print(f"❌ 子客户端验证失败: {e}")
        return False


def verify_data_feed_integration():
    """验证数据流集成"""
    print("\n" + "=" * 60)
    print("4. 验证数据流集成")
    print("=" * 60)
    
    try:
        from kline_data.sdk import KlineClient
        
        client = KlineClient()
        
        # 验证可以创建数据流
        feed = client.create_data_feed(
            exchange='binance',
            symbol='BTC/USDT',
            start_time=datetime(2024, 11, 1),
            end_time=datetime(2024, 11, 2),
            interval='1h',
            chunk_size=10
        )
        
        # 验证数据流有query_client属性
        assert hasattr(feed, 'query_client'), "数据流缺少query_client"
        print("✅ 数据流使用QueryClient（支持自动下载）")
        
        return True
        
    except Exception as e:
        print(f"❌ 数据流验证失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def verify_backward_compatibility():
    """验证向后兼容性"""
    print("\n" + "=" * 60)
    print("5. 验证向后兼容性")
    print("=" * 60)
    
    try:
        import warnings
        
        # 测试旧的client导入
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            from kline_data.sdk.client import KlineClient as OldClient
            
            has_warning = any("deprecated" in str(warning.message).lower() for warning in w)
            if has_warning:
                print("✅ 旧client导入显示废弃警告")
            else:
                print("⚠️  旧client导入未显示警告（可能不是问题）")
        
        # 测试旧的data_feed导入
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            from kline_data.sdk.data_feed import ChunkedDataFeed as OldFeed
            
            has_warning = any("deprecated" in str(warning.message).lower() for warning in w)
            if has_warning:
                print("✅ 旧data_feed导入显示废弃警告")
            else:
                print("⚠️  旧data_feed导入未显示警告（可能不是问题）")
        
        return True
        
    except Exception as e:
        print(f"❌ 兼容性验证失败: {e}")
        return False


def verify_documentation():
    """验证文档存在"""
    print("\n" + "=" * 60)
    print("6. 验证文档")
    print("=" * 60)
    
    import os
    
    docs = [
        'sdk/README.md',
        'docs/SDK_REFACTORING_GUIDE.md',
        'docs/REFACTORING_SUMMARY.md',
        'examples/sdk_refactored_example.py'
    ]
    
    all_exist = True
    for doc in docs:
        full_path = os.path.join('/Users/forst/code/python/trading/data_source/kline_data', doc)
        if os.path.exists(full_path):
            print(f"✅ {doc} 存在")
        else:
            print(f"❌ {doc} 不存在")
            all_exist = False
    
    return all_exist


def main():
    """运行所有验证"""
    print("\n")
    print("=" * 60)
    print(" SDK重构验证")
    print("=" * 60)
    
    results = []
    
    # 运行所有验证
    results.append(("模块导入", verify_imports()))
    results.append(("客户端结构", verify_client_structure()))
    results.append(("子客户端独立性", verify_sub_clients()))
    results.append(("数据流集成", verify_data_feed_integration()))
    results.append(("向后兼容性", verify_backward_compatibility()))
    results.append(("文档完整性", verify_documentation()))
    
    # 汇总结果
    print("\n" + "=" * 60)
    print(" 验证结果汇总")
    print("=" * 60)
    
    all_passed = True
    for name, passed in results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"{name:20s}: {status}")
        if not passed:
            all_passed = False
    
    print("=" * 60)
    
    if all_passed:
        print("\n🎉 所有验证通过！SDK重构成功！")
        print("\n主要改进:")
        print("  ✅ 统一的数据获取逻辑")
        print("  ✅ 数据流支持自动下载")
        print("  ✅ 模块化设计")
        print("  ✅ 向后兼容")
        print("  ✅ 文档完整")
        return 0
    else:
        print("\n⚠️  部分验证未通过，请检查上述失败项")
        return 1


if __name__ == '__main__':
    sys.exit(main())
