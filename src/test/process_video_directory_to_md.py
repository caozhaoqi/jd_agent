#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量处理视频目录，提取知识点并生成Markdown文档
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
OPENAI_API_BASE = os.getenv("OPENAI_API_BASE", "https://api..cn/v1")
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


def transcribe_audio_file(audio_path: str) -> tuple:
    """
    转录音频文件为文字，并返回带时间戳的转录结果
    返回: (transcript_text, segments)
    """
    client = OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_API_BASE)

    try:
        with open(audio_path, "rb") as audio_file:
            # 先尝试普通转录，不使用verbose_json
            transcript = client.audio.transcriptions.create(
                model=ASR_MODEL, file=audio_file, temperature=0.0
            )

        # 提取完整文本
        transcript_text = transcript.text if transcript.text else ""
        # 由于模型不支持verbose_json，返回空segments
        segments = []

        return transcript_text, segments
    except Exception as e:
        raise RuntimeError(f"音频转录失败: {e}")


def analyze_key_knowledge(text: str, segments: list) -> dict:
    """
    分析文字内容，提取关键知识点，并关联时间戳
    """
    client = OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_API_BASE)

    try:
        # 如果有segments，使用带时间戳的格式
        if segments:
            segments_text = "\n".join(
                [
                    f"[{seg['start']:.2f}s-{seg['end']:.2f}s] {seg['text']}"
                    for seg in segments
                ]
            )
            user_content = f"以下是带时间戳的课程内容：\n{segments_text}"
        else:
            # 没有segments时，直接使用纯文本
            user_content = f"以下是课程内容：\n{text}"

        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {
                    "role": "system",
                    "content": "你是一位专业的课程分析助手，请从以下课程文字内容中提取关键知识点，按照层级结构组织，并对每个知识点进行简要说明。输出格式为JSON，包含knowledge_points（知识点列表）和summary（总结）。每个知识点应包含title（标题）、description（描述）和level（层级，1-3）。如果能根据内容推断出时间顺序，也可以为每个知识点添加近似的timestamp（时间戳，格式为'HH:MM:SS'）。",
                },
                {"role": "user", "content": user_content},
            ],
            response_format={"type": "json_object"},
        )

        return json.loads(response.choices[0].message.content)
    except Exception as e:
        raise RuntimeError(f"知识点分析失败: {e}")


def generate_markdown_output(video_results: list, output_file: str):
    """
    生成Markdown格式的输出文档
    """
    with open(output_file, "w", encoding="utf-8") as f:
        # 标题
        f.write("# PaaS 培训课程知识点总结\n\n")

        # 目录
        f.write("## 目录\n\n")
        for i, result in enumerate(video_results):
            if "error" in result:
                continue
            f.write(
                f"{i+1}. [{result['video_name']}](#{i+1}-{result['video_name'].replace(' ', '-')})\n"
            )
        f.write("\n")

        # 按视频逐个生成内容
        for i, result in enumerate(video_results):
            f.write("---\n\n")

            if "error" in result:
                f.write(f"## {i+1}. {result['video_name']}\n\n")
                f.write(f"**处理失败**: {result['error']}\n\n")
                continue

            f.write(f"## {i+1}. {result['video_name']}\n\n")

            # 视频信息
            f.write("### 视频信息\n\n")
            f.write(f"- 文件路径: {result['video_path']}\n")
            f.write(f"- 处理时间: {result['total_time']:.2f} 秒\n")
            f.write(f"- 转录文本长度: {len(result['transcript'])} 字符\n")
            f.write(
                f"- 知识点数量: {len(result['knowledge_points'].get('knowledge_points', []))}\n\n"
            )

            # 知识点总结
            f.write("### 课程总结\n\n")
            f.write(f"{result['knowledge_points'].get('summary', '')}\n\n")

            # 详细知识点
            f.write("### 关键知识点\n\n")

            for kp in result["knowledge_points"].get("knowledge_points", []):
                level = kp.get("level", 1)
                indent = "  " * (level - 1)
                timestamp = kp.get("timestamp", "")

                if timestamp:
                    if level == 1:
                        f.write(
                            f"{indent}- **{kp['title']}** [{timestamp}]: {kp['description']}\n\n"
                        )
                    elif level == 2:
                        f.write(
                            f"{indent}- {kp['title']} [{timestamp}]: {kp['description']}\n\n"
                        )
                    else:
                        f.write(
                            f"{indent}- {kp['title']} [{timestamp}]: {kp['description']}\n"
                        )
                else:
                    if level == 1:
                        f.write(f"{indent}- **{kp['title']}**: {kp['description']}\n\n")
                    elif level == 2:
                        f.write(f"{indent}- {kp['title']}: {kp['description']}\n\n")
                    else:
                        f.write(f"{indent}- {kp['title']}: {kp['description']}\n")
            f.write("\n")

        # 汇总所有知识点
        f.write("---\n\n")
        f.write("## 所有知识点汇总\n\n")

        # 按层级汇总知识点
        all_knowledge_points = []
        for result in video_results:
            if "error" in result:
                continue
            all_knowledge_points.extend(
                result["knowledge_points"].get("knowledge_points", [])
            )

        # 按层级分组
        level1_kps = [kp for kp in all_knowledge_points if kp.get("level") == 1]
        level2_kps = [kp for kp in all_knowledge_points if kp.get("level") == 2]
        level3_kps = [kp for kp in all_knowledge_points if kp.get("level") == 3]

        f.write(f"### 一级知识点 ({len(level1_kps)}个)\n\n")
        for kp in level1_kps:
            f.write(f"- **{kp['title']}**\n")
            f.write(f"  {kp['description']}\n\n")

        f.write(f"### 二级知识点 ({len(level2_kps)}个)\n\n")
        for kp in level2_kps:
            f.write(f"- {kp['title']}: {kp['description']}\n")
        f.write("\n")

        f.write(f"### 三级知识点 ({len(level3_kps)}个)\n\n")
        for kp in level3_kps:
            f.write(f"- {kp['title']}: {kp['description']}\n")
        f.write("\n")


def main():
    """
    主函数，批量处理视频目录并生成MD文档
    """
    print("=== 视频课程知识点提取与MD生成 ===")
    print(f"ASR模型: {ASR_MODEL}")
    print(f"LLM模型: {MODEL_NAME}")
    print(f"API Base: {OPENAI_API_BASE}")

    # 视频目录
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

        print(f"\n找到 {len(video_files)} 个视频文件:")
        for i, video_path in enumerate(video_files):
            print(f"{i+1}. {os.path.basename(video_path)}")

        # 处理所有视频
        video_results = []

        for i, video_path in enumerate(video_files):
            print(f"\n=== 处理视频 {i+1}/{len(video_files)} ===")
            print(f"视频文件: {os.path.basename(video_path)}")

            try:
                # 开始计时
                total_start_time = time.time()

                # 步骤1: 提取音频
                print("1. 提取音频...")
                start_time = time.time()
                audio_path = extract_audio_from_video(video_path)
                elapsed = time.time() - start_time
                print(f"   ✓ 完成，耗时: {elapsed:.2f} 秒")

                # 步骤2: 转录音频
                print("2. 转录音频...")
                start_time = time.time()
                transcript_text, segments = transcribe_audio_file(audio_path)
                elapsed = time.time() - start_time
                print(f"   ✓ 完成，耗时: {elapsed:.2f} 秒")
                print(f"   文本长度: {len(transcript_text)} 字符")
                print(f"   时间片段数: {len(segments)} 个")

                # 步骤3: 分析知识点
                print("3. 分析知识点...")
                start_time = time.time()
                knowledge_data = analyze_key_knowledge(transcript_text, segments)
                elapsed = time.time() - start_time
                print(f"   ✓ 完成，耗时: {elapsed:.2f} 秒")
                print(
                    f"   知识点数量: {len(knowledge_data.get('knowledge_points', []))}"
                )

                # 计算总耗时
                total_elapsed = time.time() - total_start_time
                print(f"\n✓ 视频处理完成，总耗时: {total_elapsed:.2f} 秒")

                # 保存结果
                result = {
                    "video_name": os.path.basename(video_path),
                    "video_path": video_path,
                    "total_time": total_elapsed,
                    "transcript": transcript_text,
                    "segments": segments,
                    "knowledge_points": knowledge_data,
                }

                video_results.append(result)

                # 清理临时文件
                if os.path.exists(audio_path):
                    os.remove(audio_path)
                    print("   ✓ 临时音频文件已清理")

            except Exception as e:
                print(f"✗ 处理失败: {str(e)}")
                video_results.append(
                    {
                        "video_name": os.path.basename(video_path),
                        "video_path": video_path,
                        "error": str(e),
                    }
                )

        # 生成Markdown文档
        print("\n=== 生成Markdown文档 ===")
        md_file = "../../paas_training_knowledge_summary.md"
        generate_markdown_output(video_results, md_file)

        print(f"✓ Markdown文档已生成: {md_file}")

        # 保存完整JSON结果
        json_file = "../../paas_training_knowledge_results.json"
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(video_results, f, ensure_ascii=False, indent=2)

        print(f"✓ 完整JSON结果已保存: {json_file}")

        # 统计信息
        processed = len([r for r in video_results if "error" not in r])
        total = len(video_results)

        print("\n=== 处理完成 ===")
        print(f"总视频数: {total}")
        print(f"成功处理: {processed}")
        print(f"处理失败: {total - processed}")

    except Exception as e:
        print(f"处理过程中发生错误: {str(e)}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
