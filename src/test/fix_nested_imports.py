#!/usr/bin/env python3
"""
修复嵌套的相对导入路径脚本
"""

import os
import re

def fix_nested_imports_in_file(file_path):
    """修复单个文件中的嵌套相对导入路径"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 记录原始内容以便比较
        original_content = content
        
        # 修复嵌套的相对导入
        # from .api.routers  -> from .routers
        content = re.sub(r'\bfrom \.api\.routers\b', 'from .routers', content)
        # from .api.routers.  -> from .routers.
        content = re.sub(r'\bfrom \.api\.routers\.', 'from .routers.', content)
        
        # from .core. 保持不变，这已经是正确的
        # from .models. 保持不变，这已经是正确的
        
        # 修复其他可能的嵌套导入
        content = re.sub(r'\bfrom \.chains\.chains\b', 'from .chains', content)
        content = re.sub(r'\bfrom \.services\.services\b', 'from .services', content)
        
        # 只有内容发生变化时才写入文件
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ 修复嵌套导入: {file_path}")
            return True
        else:
            return False
            
    except Exception as e:
        print(f"❌ 处理文件失败 {file_path}: {e}")
        return False

def main():
    """主函数"""
    app_dir = "/app"
    
    print("🔧 开始修复嵌套导入路径...")
    
    fixed_count = 0
    
    # 遍历所有Python文件
    for root, dirs, files in os.walk(app_dir):
        # 跳过 __pycache__ 目录
        dirs[:] = [d for d in dirs if d != '__pycache__']
        
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                if fix_nested_imports_in_file(file_path):
                    fixed_count += 1
    
    print(f"\n📊 修复完成: 已修复 {fixed_count} 个文件")

if __name__ == "__main__":
    main()