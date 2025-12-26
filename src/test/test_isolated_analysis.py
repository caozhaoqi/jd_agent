#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
隔离测试视频分析功能，避免不必要的依赖
"""
import os
import sys
import json
import time
import tempfile
import ffmpeg
from openai import OpenAI

# 直接从环境变量读取配置
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "sk-")
OPENAI_API_BASE = os.getenv("OPENAI_API_BASE", "https://api.siliconflow.cn/v1")
ASR_MODEL = os.getenv("ASR_MODEL", "FunAudioLLM/SenseVoiceSmall")
MODEL_NAME = os.getenv("MODEL_NAME", "deepseek-ai/DeepSeek-R1-0528-Qwen3-8B")


def extract_audio_from_video(video_path: str) -> str:
    """
    从视频文件中提取音频
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"视频文件不存在: {video_path}")

    temp_dir = tempfile.gettempdir()
    temp_audio_path = os.path.join(
        temp_dir, f"extracted_audio_{os.path.basename(video_path)}.wav"
    )

    try:
        (
            ffmpeg.input(video_path)
            .output(temp_audio_path, format="wav", acodec="pcm_s16le", ac=1, ar="16000")
            .overwrite_output()
            .run(capture_stdout=True, capture_stderr=True)
        )
        return temp_audio_path
    except ffmpeg.Error as e:
        raise RuntimeError(f"视频转音频失败: {e.stderr.decode()}")


def list_video_files(directory: str) -> list:
    """
    列出目录中的所有视频文件
    """
    if not os.path.exists(directory):
        raise FileNotFoundError(f"目录不存在: {directory}")

    if not os.path.isdir(directory):
        raise NotADirectoryError(f"路径不是目录: {directory}")

    # 支持的视频文件扩展名
    video_extensions = [".mp4", ".avi", ".mov", ".mkv", ".flv", ".wmv", ".webm"]

    video_files = []
    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)
        if os.path.isfile(file_path):
            _, ext = os.path.splitext(filename)
            if ext.lower() in video_extensions:
                video_files.append(file_path)

    return sorted(video_files)


def transcribe_audio_file(audio_path: str) -> str:
    """
    转录音频文件为文字
    """
    client = OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_API_BASE)

    try:
        with open(audio_path, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model=ASR_MODEL, file=audio_file, temperature=0.0
            )
        return transcript.text
    except Exception as e:
        raise RuntimeError(f"音频转录失败: {e}")


def analyze_key_knowledge(text: str) -> dict:
    """
    分析文字内容，提取关键知识点
    """
    client = OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_API_BASE)

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {
                    "role": "system",
                    "content": "你是一位专业的课程分析助手，请从以下课程文字内容中提取关键知识点，按照层级结构组织，并对每个知识点进行简要说明。输出格式为JSON，包含knowledge_points（知识点列表）和summary（总结）。每个知识点应包含title（标题）、description（描述）和level（层级，1-3）。",
                },
                {"role": "user", "content": text},
            ],
            response_format={"type": "json_object"},
        )

        return json.loads(response.choices[0].message.content)
    except Exception as e:
        raise RuntimeError(f"知识点分析失败: {e}")


def generate_visual_summary(knowledge_data: dict) -> dict:
    """
    生成可视化总结数据结构
    """
    return {"type": "mind_map", "title": "课程知识点总结", "data": knowledge_data}


def main():
    """
    主函数，执行完整的视频分析流程
    """
    print("=== 隔离式视频分析测试 ===")
    print(f"ASR模型: {ASR_MODEL}")
    print(f"LLM模型: {MODEL_NAME}")
    print(f"API Base: {OPENAI_API_BASE}")

    # 测试视频目录
    video_dir = "/Users/caozhaoqi/Downloads/03-Paas 培训_2508~09 线上"

    if not os.path.exists(video_dir):
        print(f"错误: 视频目录不存在: {video_dir}")
        return

    try:
        # 获取视频文件列表
        video_files = list_video_files(video_dir)

        if not video_files:
            print("错误: 目录中没有找到视频文件")
            return

        # 选择第一个视频文件进行测试
        test_video_path = video_files[1]
        print("\n1. 选择测试视频")
        print(f"视频文件: {os.path.basename(test_video_path)}")
        print(f"文件大小: {os.path.getsize(test_video_path) / (1024 * 1024):.2f} MB")

        # 开始计时
        total_start_time = time.time()

        # 步骤1: 提取音频
        print("\n2. 提取音频")
        start_time = time.time()
        audio_path = extract_audio_from_video(test_video_path)
        elapsed = time.time() - start_time
        print(f"音频提取完成，耗时: {elapsed:.2f} 秒")
        print(f"音频文件: {os.path.basename(audio_path)}")
        print(f"音频大小: {os.path.getsize(audio_path) / (1024 * 1024):.2f} MB")

        # 步骤2: 转录音频
        print("\n3. 转录音频")
        start_time = time.time()
        transcript_text = transcribe_audio_file(audio_path)
        elapsed = time.time() - start_time
        print(f"音频转录完成，耗时: {elapsed:.2f} 秒")
        print(f"转录文本长度: {len(transcript_text)} 字符")

        # 保存转录结果
        transcript_file = "data/test_transcript.txt"
        with open(transcript_file, "w", encoding="utf-8") as f:
            f.write(transcript_text)
        print(f"转录结果已保存到: {transcript_file}")

        # 步骤3: 分析知识点
        print("\n4. 分析知识点")
        start_time = time.time()
        knowledge_data = analyze_key_knowledge(transcript_text)
        elapsed = time.time() - start_time
        print(f"知识点分析完成，耗时: {elapsed:.2f} 秒")

        # 步骤4: 生成可视化总结
        print("\n5. 生成可视化总结")
        visual_summary = generate_visual_summary(knowledge_data)
        print("可视化总结生成完成")

        # 计算总耗时
        total_elapsed = time.time() - total_start_time
        print("\n=== 分析完成 ===")
        print(f"总耗时: {total_elapsed:.2f} 秒")
        print(f"视频文件: {os.path.basename(test_video_path)}")

        # 保存完整结果
        result = {
            "video_name": os.path.basename(test_video_path),
            "video_path": test_video_path,
            "total_time": total_elapsed,
            "transcript": transcript_text,
            "knowledge_points": knowledge_data,
            "visual_summary": visual_summary,
        }

        result_file = "data/isolated_analysis_result.json"
        with open(result_file, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        print(f"\n完整分析结果已保存到: {result_file}")
        print(f"知识点数量: {len(knowledge_data.get('knowledge_points', []))}")
        print(f"总结: {knowledge_data.get('summary', '')[:150]}...")

        # 清理临时文件
        if os.path.exists(audio_path):
            os.remove(audio_path)
            print("\n临时音频文件已清理")

    except Exception as e:
        print(f"测试过程中发生错误: {str(e)}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
