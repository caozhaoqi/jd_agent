#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单测试知识点分析功能，避免不必要的依赖
"""
import os
import sys
import json
import tempfile
import time
from openai import OpenAI

# 添加src目录到Python路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))

try:
    from app.core.config import settings
    
    print(f"使用的模型: {settings.MODEL_NAME}")
    print(f"使用的API Base: {settings.OPENAI_API_BASE}")
    
    # 使用之前转录得到的文本文件
    transcript_file = "/var/folders/gh/7m_kz"
    
    if os.path.exists(transcript_file):
        print(f"\n1. 读取转录文本...")
        with open(transcript_file, "r", encoding="utf-8") as f:
            transcript_text = f.read()
        
        print(f"转录文本长度: {len(transcript_text)} 字符")
        print(f"转录文本预览 (前200字符):")
        print(transcript_text[:200] + "...")
        
        # 初始化OpenAI客户端
        print(f"\n2. 初始化OpenAI客户端...")
        client = OpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_API_BASE
        )
        
        # 准备分析提示
        messages = [
            {
                "role": "system",
                "content": "你是一位专业的课程分析助手，请从以下课程文字内容中提取关键知识点，按照层级结构组织，并对每个知识点进行简要说明。输出格式为JSON，包含knowledge_points（知识点列表）和summary（总结）。每个知识点应包含title（标题）、description（描述）和level（层级，1-3）。"
            },
            {
                "role": "user",
                "content": transcript_text
            }
        ]
        
        # 开始知识点分析
        print(f"\n3. 开始知识点分析...")
        start_time = time.time()
        
        response = client.chat.completions.create(
            model=settings.MODEL_NAME,
            messages=messages,
            response_format={"type": "json_object"}
        )
        
        # 计算耗时
        elapsed_time = time.time() - start_time
        
        print(f"知识点分析完成！")
        print(f"耗时: {elapsed_time:.2f} 秒")
        
        # 处理响应
        knowledge_data = response.choices[0].message.content
        
        # 解析JSON响应
        knowledge_json = json.loads(knowledge_data)
        
        # 保存分析结果
        result_file = os.path.join(tempfile.gettempdir(), "knowledge_analysis_result.json")
        with open(result_file, "w", encoding="utf-8") as f:
            json.dump(knowledge_json, f, ensure_ascii=False, indent=2)
        
        print(f"\n分析结果已保存到: {result_file}")
        
        # 输出分析结果摘要
        print(f"\n4. 分析结果摘要:")
        print(f"   - 总结: {knowledge_json.get('summary', '')[:200]}...")
        
        knowledge_points = knowledge_json.get('knowledge_points', [])
        print(f"   - 知识点数量: {len(knowledge_points)}")
        
        print(f"\n   - 一级知识点列表:")
        for point in knowledge_points:
            if point.get('level') == 1:
                print(f"     * {point.get('title')}")
                # 统计二级知识点数量
                sub_points_count = sum(1 for p in knowledge_points if p.get('level') == 2)
                print(f"       (包含 {sub_points_count} 个二级知识点)")
                    
    else:
        print(f"错误: 转录文本文件不存在")
        print(f"请先运行test_audio_transcribe.py生成转录文件")
        
except Exception as e:
    print(f"测试过程中发生错误: {str(e)}")
    import traceback
    traceback.print_exc()
