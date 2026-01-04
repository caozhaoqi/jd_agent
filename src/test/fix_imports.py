#!/usr/bin/env python3
"""
批量修复导入路径脚本
将所有的 from app. 导入修改为相对导入
"""

import os
import re

def fix_imports_in_file(file_path):
    """修复单个文件中的导入路径"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 记录原始内容以便比较
        original_content = content
        
        # 替换 from app. 为 from .
        content = re.sub(r'\bfrom app\.', 'from .', content)
        # 替换 import app. 为 import .
        content = re.sub(r'\bimport app\.', 'import .', content)
        
        # 只有内容发生变化时才写入文件
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ 修复文件: {file_path}")
            return True
        else:
            print(f"⚪ 无需修复: {file_path}")
            return False
            
    except Exception as e:
        print(f"❌ 处理文件失败 {file_path}: {e}")
        return False

def main():
    """主函数"""
    app_dir = "/app"
    
    print("🔧 开始修复导入路径...")
    
    fixed_count = 0
    total_count = 0
    
    # 遍历所有Python文件
    for root, dirs, files in os.walk(app_dir):
        # 跳过 __pycache__ 目录
        dirs[:] = [d for d in dirs if d != '__pycache__']
        
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                total_count += 1
                if fix_imports_in_file(file_path):
                    fixed_count += 1
    
    print(f"\n📊 修复完成:")
    print(f"   总文件数: {total_count}")
    print(f"   已修复: {fixed_count}")
    print(f"   无需修复: {total_count - fixed_count}")

if __name__ == "__main__":
    main()