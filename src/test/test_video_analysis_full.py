#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试完整的视频分析流程
"""
import os
import sys
import json
import time
import subprocess
import requests

# 添加src目录到Python路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))

def start_server():
    """启动FastAPI服务器"""
    print("启动FastAPI服务器...")
    server_process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--reload", "--port", "8000"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )
    
    # 等待服务器启动
    time.sleep(5)
    
    # 检查服务器是否正在运行
    try:
        response = requests.get("http://localhost:8000/docs")
        if response.status_code == 200:
            print("FastAPI服务器已成功启动!")
            return server_process
        else:
            print("服务器启动失败")
            server_process.terminate()
            return None
    except requests.ConnectionError:
        print("无法连接到服务器，启动失败")
        server_process.terminate()
        return None

def test_video_analysis_api(video_dir):
    """测试视频分析API"""
    print(f"\n测试视频分析API，目录: {video_dir}")
    
    url = "http://localhost:8000/api/v1/video/analyze-directory"
    
    try:
        # 调用API
        response = requests.post(url, data={"directory_path": video_dir})
        
        if response.status_code == 200:
            result = response.json()
            print("API调用成功!")
            print(f"目录: {result.get('directory')}")
            print(f"视频总数: {result.get('total_videos')}")
            print(f"已处理视频: {result.get('processed_videos')}")
            
            # 保存结果
            result_file = "video_analysis_full_result.json"
            with open(result_file, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(f"完整分析结果已保存到: {result_file}")
            
            return result
        else:
            print(f"API调用失败，状态码: {response.status_code}")
            print(f"错误信息: {response.text}")
            return None
    except Exception as e:
        print(f"API调用过程中发生错误: {str(e)}")
        return None

def stop_server(server_process):
    """停止服务器"""
    print("\n停止FastAPI服务器...")
    server_process.terminate()
    server_process.wait(timeout=5)
    print("服务器已停止")

if __name__ == "__main__":
    # 测试视频目录
    video_dir = "/Users/caozhaoqi/Downloads/03-Paas 培训_2508~09 线上"
    
    # 验证目录是否存在
    if not os.path.exists(video_dir):
        print(f"错误: 视频目录不存在: {video_dir}")
        sys.exit(1)
    
    # 启动服务器
    server = start_server()
    
    if server:
        try:
            # 测试API
            result = test_video_analysis_api(video_dir)
        finally:
            # 停止服务器
            stop_server(server)
    else:
        print("无法启动服务器，测试终止")
