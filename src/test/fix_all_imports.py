#!/usr/bin/env python3
"""
全面修复导入路径脚本
"""

import os
import re

def fix_all_imports_in_file(file_path):
    """修复单个文件中的所有导入路径"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 记录原始内容以便比较
        original_content = content
        
        # 修复各种导入路径
        replacements = [
            # 路由文件中的导入
            (r'\bfrom \.api\.deps\b', 'from api.deps'),
            (r'\bfrom \.core\.', 'from core.'),
            (r'\bfrom \.chains\.', 'from chains.'),
            (r'\bfrom \.services\.', 'from services.'),
            (r'\bfrom \.confluence\.', 'from confluence.'),
            (r'\bfrom \.blog\.', 'from blog.'),
            (r'\bfrom \.interview_experience\.', 'from interview_experience.'),
            (r'\bfrom \.schemas\.', 'from schemas.'),
            (r'\bfrom \.utils\.', 'from utils.'),
            (r'\bfrom \.graph\.', 'from graph.'),
            (r'\bfrom \.models\.', 'from models.'),
            (r'\bfrom \.scripts\.', 'from scripts.'),
            
            # 绝对导入的修复
            (r'\bfrom \.routers\b', 'from api.routers'),
            (r'\bfrom \.routers\.', 'from api.routers.'),
            
            # 其他相对导入
            (r'\bfrom \.\b', 'from .'),
            
            # 模块导入
            (r'\bimport \.core\b', 'import core'),
            (r'\bimport \.chains\b', 'import chains'),
            (r'\bimport \.services\b', 'import services'),
            (r'\bimport \.confluence\b', 'import confluence'),
            (r'\bimport \.blog\b', 'import blog'),
            (r'\bimport \.interview_experience\b', 'import interview_experience'),
            (r'\bimport \.schemas\b', 'import schemas'),
            (r'\bimport \.utils\b', 'import utils'),
            (r'\bimport \.graph\b', 'import graph'),
            (r'\bimport \.models\b', 'import models'),
            (r'\bimport \.scripts\b', 'import scripts'),
        ]
        
        for pattern, replacement in replacements:
            content = re.sub(pattern, replacement, content)
        
        # 只有内容发生变化时才写入文件
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ 修复文件: {file_path}")
            return True
        else:
            return False
            
    except Exception as e:
        print(f"❌ 处理文件失败 {file_path}: {e}")
        return False

def main():
    """主函数"""
    app_dir = "/app"
    
    print("🔧 开始全面修复导入路径...")
    
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
                if fix_all_imports_in_file(file_path):
                    fixed_count += 1
    
    print(f"\n📊 修复完成:")
    print(f"   总文件数: {total_count}")
    print(f"   已修复: {fixed_count}")
    print(f"   无需修复: {total_count - fixed_count}")

if __name__ == "__main__":
    main()