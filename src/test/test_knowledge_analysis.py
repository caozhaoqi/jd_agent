#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试知识点分析功能
"""
import os
import sys
import json
import tempfile
import time

# 添加src目录到Python路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))

try:
    from app.api.routers.video_analysis import analyze_key_knowledge
    from app.core.config import settings

    print(f"使用的模型: {settings.LLM_MODEL_NAME}")
    print(f"使用的API Base: {settings.OPENAI_API_BASE}")

    # 使用之前转录得到的文本文件
    transcript_file = "/var/folders/gh/7m_kzhvj2vsbcxp6qlfblz5c0000gn/T/"

    if os.path.exists(transcript_file):
        print("\n1. 读取转录文本...")
        with open(transcript_file, "r", encoding="utf-8") as f:
            transcript_text = f.read()

        print(f"转录文本长度: {len(transcript_text)} 字符")
        print("转录文本预览 (前200字符):")
        print(transcript_text[:200] + "...")

        # 开始知识点分析
        print("\n2. 开始知识点分析...")
        start_time = time.time()

        try:
            # 调用知识点分析函数
            knowledge_data = analyze_key_knowledge(transcript_text)

            # 计算耗时
            elapsed_time = time.time() - start_time

            print("知识点分析完成！")
            print(f"耗时: {elapsed_time:.2f} 秒")

            # 解析JSON响应
            if isinstance(knowledge_data, str):
                knowledge_json = json.loads(knowledge_data)
            else:
                knowledge_json = knowledge_data

            # 保存分析结果
            result_file = os.path.join(
                tempfile.gettempdir(), "knowledge_analysis_result.json"
            )
            with open(result_file, "w", encoding="utf-8") as f:
                json.dump(knowledge_json, f, ensure_ascii=False, indent=2)

            print(f"\n分析结果已保存到: {result_file}")

            # 输出分析结果摘要
            print("\n3. 分析结果摘要:")
            print(f"   - 总结: {knowledge_json.get('summary', '')[:200]}...")

            knowledge_points = knowledge_json.get("knowledge_points", [])
            print(f"   - 知识点数量: {len(knowledge_points)}")

            print("\n   - 一级知识点列表:")
            for point in knowledge_points:
                if point.get("level") == 1:
                    print(f"     * {point.get('title')}")
                    # 显示二级知识点
                    for sub_point in knowledge_points:
                        if sub_point.get("level") == 2 and sub_point.get(
                            "parent_id"
                        ) == point.get("id"):
                            print(f"       - {sub_point.get('title')}")
                    print()

        except json.JSONDecodeError as e:
            print(f"JSON解析错误: {str(e)}")
            print(f"响应内容: {knowledge_data[:500]}...")

    else:
        print("错误: 转录文本文件不存在")
        print("请先运行test_audio_transcribe.py生成转录文件")

except Exception as e:
    print(f"测试过程中发生错误: {str(e)}")
    import traceback

    traceback.print_exc()
