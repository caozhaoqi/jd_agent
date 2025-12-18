#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试音频转写功能
"""
import os
import sys
import tempfile
import time

# 添加src目录到Python路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))

try:
    from app.utils.video_utils import extract_audio_from_video, list_video_files
    from openai import OpenAI
    from app.core.config import settings
    
    # 测试视频目录
    video_dir = "/Users/caozhaoqi/Downloads/03-Paas 培训_2508~09 线上"
    
    if os.path.exists(video_dir):
        # 获取视频文件列表
        video_files = list_video_files(video_dir)
        
        if video_files:
            # 选择第二个视频文件进行测试
            test_video_path = video_files[1]
            print(f"选择测试的视频文件: {os.path.basename(test_video_path)}")
            
            # 首先提取音频
            print(f"\n1. 从视频中提取音频...")
            audio_path = extract_audio_from_video(test_video_path)
            print(f"音频提取完成: {os.path.basename(audio_path)}")
            
            # 初始化OpenAI客户端
            print(f"\n2. 初始化OpenAI客户端...")
            print(f"使用的API Base: {settings.AUDIO_API_BASE or settings.OPENAI_API_BASE}")
            print(f"使用的模型: {settings.ASR_MODEL}")
            
            client = OpenAI(
                api_key=settings.AUDIO_API_KEY or settings.OPENAI_API_KEY,
                base_url=settings.AUDIO_API_BASE or settings.OPENAI_API_BASE
            )
            
            # 开始转录
            print(f"\n3. 开始音频转录...")
            start_time = time.time()
            
            # 读取音频文件
            with open(audio_path, "rb") as audio_file:
                # 调用转录API
                transcript = client.audio.transcriptions.create(
                    model=settings.ASR_MODEL,
                    file=audio_file,
                    temperature=0.0
                )
            
            # 计算耗时
            elapsed_time = time.time() - start_time
            
            print(f"转录完成！")
            print(f"耗时: {elapsed_time:.2f} 秒")
            print(f"转录文本长度: {len(transcript.text)} 字符")
            print(f"\n转录文本前500字符：")
            print(transcript.text[:500] + "...")
            
            # 将转录结果保存到文件
            transcript_file = os.path.join(tempfile.gettempdir(), f"transcript_{os.path.basename(test_video_path)}.txt")
            with open(transcript_file, "w", encoding="utf-8") as f:
                f.write(transcript.text)
            
            print(f"\n完整转录结果已保存到: {transcript_file}")
            
        else:
            print(f"错误: 视频目录中没有找到视频文件")
    else:
        print("错误: 视频目录不存在")
        
except Exception as e:
    print(f"测试过程中发生错误: {str(e)}")
    import traceback
    traceback.print_exc()
