#!/usr/bin/env python3
"""
修复路由文件中的导入路径脚本
"""

import os
import re

def fix_router_imports_in_file(file_path):
    """修复单个路由文件中的导入路径"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 记录原始内容以便比较
        original_content = content
        
        # 修复路由文件中的导入路径
        # from .core.db_auth  -> from ...core.db_auth
        content = re.sub(r'\bfrom \.core\.db_auth\b', 'from ...core.db_auth', content)
        content = re.sub(r'\bfrom \.core\.models\b', 'from ...core.models', content)
        content = re.sub(r'\bfrom \.core\.error_handler\b', 'from ...core.error_handler', content)
        content = re.sub(r'\bfrom \.core\.config\b', 'from ...core.config', content)
        
        # from .schemas  -> from ...schemas
        content = re.sub(r'\bfrom \.schemas\b', 'from ...schemas', content)
        
        # from .utils  -> from ...utils
        content = re.sub(r'\bfrom \.utils\b', 'from ...utils', content)
        
        # from .chains  -> from ...chains
        content = re.sub(r'\bfrom \.chains\b', 'from ...chains', content)
        
        # from .services  -> from ...services
        content = re.sub(r'\bfrom \.services\b', 'from ...services', content)
        
        # from .confluence  -> from ...confluence
        content = re.sub(r'\bfrom \.confluence\b', 'from ...confluence', content)
        
        # from .blog  -> from ...blog
        content = re.sub(r'\bfrom \.blog\b', 'from ...blog', content)
        
        # from .interview_experience  -> from ...interview_experience
        content = re.sub(r'\bfrom \.interview_experience\b', 'from ...interview_experience', content)
        
        # 修复模块导入
        # import .core  -> import ...core
        content = re.sub(r'\bimport \.core\b', 'import ...core', content)
        
        # 只有内容发生变化时才写入文件
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ 修复路由导入: {file_path}")
            return True
        else:
            return False
            
    except Exception as e:
        print(f"❌ 处理文件失败 {file_path}: {e}")
        return False

def main():
    """主函数"""
    app_dir = "/app"
    
    print("🔧 开始修复路由导入路径...")
    
    fixed_count = 0
    
    # 只处理 routers 目录下的文件
    routers_dir = os.path.join(app_dir, "api", "routers")
    if os.path.exists(routers_dir):
        for file in os.listdir(routers_dir):
            if file.endswith('.py') and file != '__init__.py':
                file_path = os.path.join(routers_dir, file)
                if fix_router_imports_in_file(file_path):
                    fixed_count += 1
    
    print(f"\n📊 修复完成: 已修复 {fixed_count} 个路由文件")

if __name__ == "__main__":
    main()