#!/usr/bin/env python3
"""
验证视频处理模块的基本功能
"""

import os
import sys
import tempfile

# 添加src目录到Python路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))

def test_module_imports():
    """测试模块导入"""
    print("测试模块导入...")
    try:
        from app.utils.video_utils import extract_audio_from_video, list_video_files, extract_audio_from_video_bytes
        print("✅ 视频工具模块导入成功")
        return True
    except ImportError as e:
        print(f"❌ 视频工具模块导入失败: {e}")
        return False

def test_function_definitions():
    """测试函数定义"""
    print("\n测试函数定义...")
    try:
        from app.utils.video_utils import extract_audio_from_video, list_video_files, extract_audio_from_video_bytes
        
        # 检查函数是否存在
        functions = [
            extract_audio_from_video,
            list_video_files,
            extract_audio_from_video_bytes
        ]
        
        for func in functions:
            if callable(func):
                print(f"✅ 函数 {func.__name__} 定义正确")
            else:
                print(f"❌ 函数 {func.__name__} 定义不正确")
        
        return True
    except Exception as e:
        print(f"❌ 测试函数定义失败: {e}")
        return False

def test_list_video_files():
    """测试列出视频文件功能"""
    print("\n测试列出视频文件功能...")
    try:
        from app.utils.video_utils import list_video_files
        
        # 创建临时目录
        with tempfile.TemporaryDirectory() as temp_dir:
            # 创建测试文件
            test_files = [
                "video1.mp4",
                "video2.avi", 
                "audio.mp3",
                "document.txt"
            ]
            
            for filename in test_files:
                with open(os.path.join(temp_dir, filename), "w") as f:
                    f.write("test content")
            
            # 测试list_video_files函数
            video_files = list_video_files(temp_dir)
            
            print(f"找到的视频文件: {video_files}")
            expected_count = 2  # 应该只有2个视频文件
            
            if len(video_files) == expected_count:
                print(f"✅ 列出视频文件功能正常，找到 {len(video_files)} 个视频文件")
                return True
            else:
                print(f"❌ 列出视频文件功能异常，找到 {len(video_files)} 个视频文件，预期 {expected_count} 个")
                return False
    except Exception as e:
        print(f"❌ 测试列出视频文件功能失败: {e}")
        return False

def test_api_router():
    """测试API路由注册"""
    print("\n测试API路由注册...")
    try:
        from app.api.routers import video_analysis
        print("✅ 视频分析路由模块导入成功")
        
        # 检查路由是否存在
        if hasattr(video_analysis, 'router'):
            print("✅ 视频分析路由定义正确")
            return True
        else:
            print("❌ 视频分析路由定义不正确")
            return False
    except Exception as e:
        print(f"❌ 测试API路由注册失败: {e}")
        return False

def main():
    """主测试函数"""
    print("开始验证视频处理功能...")
    print("=" * 50)
    
    tests = [
        test_module_imports,
        test_function_definitions,
        test_list_video_files,
        test_api_router
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        if test():
            passed += 1
        else:
            failed += 1
    
    print("\n" + "=" * 50)
    print(f"测试结果: 通过 {passed} 个, 失败 {failed} 个")
    
    if failed == 0:
        print("✅ 所有测试通过，视频处理功能已正确实现")
        return 0
    else:
        print("❌ 部分测试失败，需要进一步检查")
        return 1

if __name__ == "__main__":
    sys.exit(main())