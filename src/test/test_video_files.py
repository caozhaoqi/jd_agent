#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试视频文件列表功能
"""
import os
import sys

# 添加src目录到Python路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))

try:
    from app.utils.video_utils import list_video_files
    
    # 测试视频目录
    video_dir = "/Users/caozhaoqi/Downloads"
    
    print(f"正在测试视频目录: {video_dir}")
    print(f"目录是否存在: {os.path.exists(video_dir)}")
    
    if os.path.exists(video_dir):
        # 列出目录中的所有文件
        all_files = os.listdir(video_dir)
        print(f"目录中所有文件 ({len(all_files)}):")
        for file in all_files:
            print(f"  - {file}")
        
        # 使用list_video_files函数筛选视频文件
        video_files = list_video_files(video_dir)
        print(f"\n使用list_video_files函数识别的视频文件 ({len(video_files)}):")
        for video_file in video_files:
            print(f"  - {os.path.basename(video_file)}")
            print(f"    完整路径: {video_file}")
    else:
        print("错误: 视频目录不存在")
        
except Exception as e:
    print(f"测试过程中发生错误: {str(e)}")
    import traceback
    traceback.print_exc()
