#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试视频转音频功能
"""
import os
import sys
import tempfile
import time

# 添加src目录到Python路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))

try:
    from app.utils.video_utils import extract_audio_from_video, list_video_files
    
    # 测试视频目录
    video_dir = "/Users/caozhaoqi/Downloads"
    
    if os.path.exists(video_dir):
        # 获取视频文件列表
        video_files = list_video_files(video_dir)
        
        if video_files:
            # 选择第二个视频文件（较小的那个）进行测试
            test_video_path = video_files[1]
            print(f"选择测试的视频文件: {os.path.basename(test_video_path)}")
            print(f"视频文件大小: {os.path.getsize(test_video_path) / (1024 * 1024):.2f} MB")
            
            # 开始计时
            start_time = time.time()
            
            print(f"\n开始从视频中提取音频...")
            
            # 测试视频转音频功能
            audio_path = extract_audio_from_video(test_video_path)
            
            # 计算耗时
            elapsed_time = time.time() - start_time
            
            print(f"音频提取完成！")
            print(f"耗时: {elapsed_time:.2f} 秒")
            print(f"提取的音频文件: {os.path.basename(audio_path)}")
            print(f"音频文件路径: {audio_path}")
            print(f"音频文件大小: {os.path.getsize(audio_path) / (1024 * 1024):.2f} MB")
            
            # 验证音频文件是否存在
            if os.path.exists(audio_path):
                print(f"\n音频文件验证: 成功，文件存在且可读")
                
                # 使用ffmpeg检查音频文件的格式信息
                print(f"\n音频文件格式信息:")
                import subprocess
                result = subprocess.run(["ffprobe", "-v", "error", "-show_entries", 
                                      "stream=codec_name,sample_rate,channels", 
                                      "-of", "csv=p=0", audio_path],
                                     capture_output=True, text=True)
                print(result.stdout.strip())
            else:
                print(f"\n音频文件验证: 失败，文件不存在")
                
        else:
            print(f"错误: 视频目录中没有找到视频文件")
    else:
        print("错误: 视频目录不存在")
        
except Exception as e:
    print(f"测试过程中发生错误: {str(e)}")
    import traceback
    traceback.print_exc()
