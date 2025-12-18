#!/usr/bin/env python3
"""
直接测试video_utils模块的功能
"""

import os
import sys
import tempfile

# 将src目录添加到Python路径
src_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "src"))
sys.path.insert(0, src_dir)

# 避免导入其他模块时的副作用
os.environ["PYTHONPATH"] = src_dir + ":" + os.environ.get("PYTHONPATH", "")

print("正在测试 video_utils 模块...")

# 测试1: 检查 ffmpeg 和 moviepy 是否安装
try:
    import ffmpeg

    print("✅ ffmpeg-python 已安装")
except ImportError:
    print("❌ ffmpeg-python 未安装")

try:
    import moviepy

    print("✅ moviepy 已安装")
except ImportError:
    print("❌ moviepy 未安装")

# 测试2: 直接导入 video_utils 模块
try:
    # 使用__import__避免触发所有导入
    video_utils_module = __import__("app.utils.video_utils", fromlist=[""])
    print("✅ video_utils 模块导入成功")

    # 检查关键函数是否存在
    required_functions = [
        "extract_audio_from_video",
        "list_video_files",
        "extract_audio_from_video_bytes",
    ]

    for func_name in required_functions:
        if hasattr(video_utils_module, func_name):
            func = getattr(video_utils_module, func_name)
            if callable(func):
                print(f"✅ 函数 {func_name} 已定义")
            else:
                print(f"⚠️  {func_name} 存在但不是可调用函数")
        else:
            print(f"❌ 函数 {func_name} 未定义")

    # 测试 list_video_files 函数
    print("\n测试 list_video_files 函数...")
    with tempfile.TemporaryDirectory() as temp_dir:
        # 创建测试文件
        test_files = [
            "video1.mp4",
            "video2.avi",
            "audio.mp3",
            "document.txt",
            "video3.mkv",
            "image.jpg",
        ]

        for filename in test_files:
            file_path = os.path.join(temp_dir, filename)
            with open(file_path, "w") as f:
                f.write("test content")

        # 调用函数
        list_func = getattr(video_utils_module, "list_video_files")
        video_files = list_func(temp_dir)

        print(f"找到的视频文件: {[os.path.basename(f) for f in video_files]}")
        expected_videos = ["video1.mp4", "video2.avi", "video3.mkv"]

        found_videos = [os.path.basename(f) for f in video_files]
        if set(found_videos) == set(expected_videos):
            print("✅ list_video_files 函数工作正常")
        else:
            print("❌ list_video_files 函数工作不正常")
            print(f"   预期: {expected_videos}")
            print(f"   实际: {found_videos}")

    print("\n🎉 所有测试完成!")

except Exception as e:
    print(f"\n❌ 测试失败: {e}")
    import traceback

    traceback.print_exc()
