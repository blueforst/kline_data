#!/usr/bin/env python3
"""
修复项目中的绝对导入为相对导入
"""
import os
import re
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent
KLINE_DATA_DIR = PROJECT_ROOT / "kline_data"

# 需要替换的模块名
MODULES = ['config', 'storage', 'reader', 'resampler', 'indicators', 'sdk', 'service', 'utils', 'cli']

def get_relative_depth(filepath: Path) -> int:
    """计算文件相对于 kline_data 包的深度"""
    try:
        rel_path = filepath.relative_to(KLINE_DATA_DIR)
        # 减1是因为文件本身不算
        return len(rel_path.parts) - 1
    except ValueError:
        return 0

def fix_imports_in_file(filepath: Path):
    """修复单个文件中的导入语句"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        modified = False
        
        # 计算需要的相对导入层级
        depth = get_relative_depth(filepath)
        dots = '.' * (depth + 1)  # +1 because we need at least ..
        
        # 修复 from module import ...
        for module in MODULES:
            # from ..module import ... (错误的两层) -> from ...module import ... (正确层级)
            pattern_wrong = rf'^from \.\.{module} import '
            if re.search(pattern_wrong, content, re.MULTILINE):
                replacement = f'from {dots}{module} import '
                content = re.sub(pattern_wrong, replacement, content, flags=re.MULTILINE)
                modified = True
            
            # from ..module.submodule import ... (错误的两层)
            pattern_wrong2 = rf'^from \.\.{module}\.'
            if re.search(pattern_wrong2, content, re.MULTILINE):
                replacement = f'from {dots}{module}.'
                content = re.sub(pattern_wrong2, replacement, content, flags=re.MULTILINE)
                modified = True
            
            # from module import ... (绝对导入)
            pattern1 = rf'^from {module} import '
            if re.search(pattern1, content, re.MULTILINE):
                replacement1 = f'from {dots}{module} import '
                content = re.sub(pattern1, replacement1, content, flags=re.MULTILINE)
                modified = True
            
            # from module.submodule import ... (绝对导入)
            pattern2 = rf'^from {module}\.'
            if re.search(pattern2, content, re.MULTILINE):
                replacement2 = f'from {dots}{module}.'
                content = re.sub(pattern2, replacement2, content, flags=re.MULTILINE)
                modified = True
        
        # 如果文件有修改，写回
        if modified and content != original_content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ Fixed (depth={depth}): {filepath.relative_to(PROJECT_ROOT)}")
            return True
        return False
    except Exception as e:
        print(f"❌ Error processing {filepath}: {e}")
        return False

def main():
    """遍历所有Python文件并修复导入"""
    fixed_count = 0
    total_count = 0
    
    print(f"🔍 Scanning {KLINE_DATA_DIR} for Python files...\n")
    
    for py_file in KLINE_DATA_DIR.rglob("*.py"):
        # 跳过 __init__.py（已经手动修复）
        if py_file.name == "__init__.py":
            continue
        
        total_count += 1
        if fix_imports_in_file(py_file):
            fixed_count += 1
    
    print(f"\n{'='*60}")
    print(f"📊 Summary:")
    print(f"   Total files scanned: {total_count}")
    print(f"   Files fixed: {fixed_count}")
    print(f"   Files unchanged: {total_count - fixed_count}")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
