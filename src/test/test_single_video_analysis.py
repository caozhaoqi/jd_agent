#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试单个视频的完整分析流程
"""
import os
import sys
import json
import time
import tempfile

# 添加src目录到Python路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))

try:
    from app.utils.video_utils import extract_audio_from_video, list_video_files
    from app.api.routers.video_analysis import transcribe_audio_file, analyze_key_knowledge, generate_visual_summary
    from app.core.config import settings
    
    print(f"=== 单个视频完整分析流程测试 ===")
    print(f"使用的ASR模型: {settings.ASR_MODEL}")
    print(f"使用的LLM模型: {settings.MODEL_NAME}")
    
    # 测试视频目录
    video_dir = "/Users/Downloads"
    
    if os.path.exists(video_dir):
        # 获取视频文件列表
        video_files = list_video_files(video_dir)
        
        if video_files:
            # 选择第一个视频文件进行测试
            test_video_path = video_files[1]
            print(f"\n1. 选择测试视频")
            print(f"视频文件: {os.path.basename(test_video_path)}")
            print(f"文件大小: {os.path.getsize(test_video_path) / (1024 * 1024):.2f} MB")
            
            # 开始计时
            total_start_time = time.time()
            
            # 步骤1: 提取音频
            print(f"\n2. 提取音频")
            start_time = time.time()
            audio_path = extract_audio_from_video(test_video_path)
            elapsed = time.time() - start_time
            print(f"音频提取完成，耗时: {elapsed:.2f} 秒")
            print(f"音频文件: {os.path.basename(audio_path)}")
            print(f"音频大小: {os.path.getsize(audio_path) / (1024 * 1024):.2f} MB")
            
            # 步骤2: 转录音频
            print(f"\n3. 转录音频")
            start_time = time.time()
            transcript_text = transcribe_audio_file(audio_path)
            elapsed = time.time() - start_time
            print(f"音频转录完成，耗时: {elapsed:.2f} 秒")
            print(f"转录文本长度: {len(transcript_text)} 字符")
            
            # 步骤3: 分析知识点
            print(f"\n4. 分析知识点")
            start_time = time.time()
            knowledge_data = analyze_key_knowledge(transcript_text)
            elapsed = time.time() - start_time
            print(f"知识点分析完成，耗时: {elapsed:.2f} 秒")
            
            # 解析知识点数据
            if isinstance(knowledge_data, str):
                knowledge_json = json.loads(knowledge_data)
            else:
                knowledge_json = knowledge_data
            
            # 步骤4: 生成可视化总结
            print(f"\n5. 生成可视化总结")
            visual_summary = generate_visual_summary(knowledge_json)
            print(f"可视化总结生成完成")
            
            # 计算总耗时
            total_elapsed = time.time() - total_start_time
            print(f"\n=== 分析完成 ===")
            print(f"总耗时: {total_elapsed:.2f} 秒")
            print(f"视频文件: {os.path.basename(test_video_path)}")
            
            # 保存完整结果
            result = {
                "video_name": os.path.basename(test_video_path),
                "video_path": test_video_path,
                "total_time": total_elapsed,
                "transcript": transcript_text,
                "knowledge_points": knowledge_json,
                "visual_summary": visual_summary
            }
            
            result_file = "single_video_analysis_result.json"
            with open(result_file, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            
            print(f"\n完整分析结果已保存到: {result_file}")
            print(f"知识点数量: {len(knowledge_json.get('knowledge_points', []))}")
            print(f"总结: {knowledge_json.get('summary', '')[:150]}...")
            
            # 清理临时文件
            if os.path.exists(audio_path):
                os.remove(audio_path)
                print(f"\n临时音频文件已清理")
            
        else:
            print("错误: 目录中没有视频文件")
    else:
        print(f"错误: 视频目录不存在: {video_dir}")
        
except Exception as e:
    print(f"测试过程中发生错误: {str(e)}")
    import traceback
    traceback.print_exc()
