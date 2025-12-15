#!/usr/bin/env python3
"""
Audio模块单元测试
"""

import pytest
from fastapi.testclient import TestClient
from fastapi import HTTPException
from io import BytesIO
import os
import tempfile
import platform
from unittest.mock import patch, MagicMock
from app.core.models import TTSRequest


@pytest.fixture
def mock_tts_text():
    """模拟的TTS文本"""
    return "这是一段测试文本，用于测试文字转语音功能"


@pytest.fixture
def mock_audio_data():
    """模拟的音频数据"""
    # 创建一个简单的WAV文件头和一些音频数据
    # 这是一个非常简单的8kHz, 8位单声道WAV文件
    wav_header = bytes([
        0x52, 0x49, 0x46, 0x46,  # RIFF
        0x24, 0x00, 0x00, 0x00,  # 文件大小
        0x57, 0x41, 0x56, 0x45,  # WAVE
        0x66, 0x6D, 0x74, 0x20,  # fmt 
        0x10, 0x00, 0x00, 0x00,  # 子块大小
        0x01, 0x00,              # 音频格式 (PCM)
        0x01, 0x00,              # 声道数 (单声道)
        0x40, 0x1F, 0x00, 0x00,  # 采样率 (8000 Hz)
        0x80, 0x3E, 0x00, 0x00,  # 字节率 (16000 Bps)
        0x02, 0x00,              # 块对齐 (2 bytes/sample)
        0x08, 0x00,              # 位深度 (8 bits)
        0x64, 0x61, 0x74, 0x61,  # data
        0x04, 0x00, 0x00, 0x00,  # 数据大小
        0x7F, 0x7F, 0x7F, 0x7F   # 音频数据 (4个样本)
    ])
    return wav_header


@patch('openai.OpenAI')
async def test_transcribe_audio(mock_openai, client: TestClient, test_token: str, mock_audio_data):
    """测试语音转文字接口"""
    # 配置模拟对象
    mock_transcript = MagicMock()
    mock_transcript.text = "这是一段测试语音转换后的文本"
    mock_openai_instance = MagicMock()
    mock_openai_instance.audio.transcriptions.create.return_value = mock_transcript
    mock_openai.return_value = mock_openai_instance
    
    # 创建测试文件
    test_file = BytesIO(mock_audio_data)
    
    response = client.post(
        "/api/v1/audio/transcribe",
        files={"file": ("test_audio.wav", test_file, "audio/wav")},
        headers={"Authorization": f"Bearer {test_token}"}
    )
    
    assert response.status_code == 200
    
    result = response.json()
    assert "text" in result
    assert result["text"] == "这是一段测试语音转换后的文本"
    assert "error" not in result


@patch('openai.OpenAI')
async def test_transcribe_audio_empty_file(mock_openai, client: TestClient, test_token: str):
    """测试上传空音频文件"""
    # 配置模拟对象
    mock_transcript = MagicMock()
    mock_transcript.text = ""
    mock_openai_instance = MagicMock()
    mock_openai_instance.audio.transcriptions.create.return_value = mock_transcript
    mock_openai.return_value = mock_openai_instance
    
    # 创建空测试文件
    test_file = BytesIO(b"")
    
    response = client.post(
        "/api/v1/audio/transcribe",
        files={"file": ("empty_audio.wav", test_file, "audio/wav")},
        headers={"Authorization": f"Bearer {test_token}"}
    )
    
    assert response.status_code == 200
    
    result = response.json()
    assert "text" in result
    assert "error" not in result


@patch('openai.OpenAI')
async def test_transcribe_audio_api_error(mock_openai, client: TestClient, test_token: str, mock_audio_data):
    """测试API调用失败的情况"""
    # 配置模拟对象抛出异常
    mock_openai_instance = MagicMock()
    mock_openai_instance.audio.transcriptions.create.side_effect = Exception("API调用失败")
    mock_openai.return_value = mock_openai_instance
    
    # 创建测试文件
    test_file = BytesIO(mock_audio_data)
    
    response = client.post(
        "/api/v1/audio/transcribe",
        files={"file": ("test_audio.wav", test_file, "audio/wav")},
        headers={"Authorization": f"Bearer {test_token}"}
    )
    
    assert response.status_code == 200
    
    result = response.json()
    assert "text" in result
    assert result["text"] == ""
    assert "error" in result


@patch('app.api.routers.audio.subprocess.run')
@patch('app.api.routers.audio.AudioSegment')
@patch('os.path.exists')
@patch('os.path.getsize')
@patch('os.remove')
@patch('builtins.open', new_callable=MagicMock)
async def test_text_to_speech_mac(mock_open, mock_remove, mock_getsize, mock_exists, mock_audiosegment, mock_subprocess, client: TestClient, test_token: str, mock_tts_text):
    """测试macOS下的文字转语音接口"""
    # 模拟macOS系统
    with patch('platform.system', return_value='Darwin'):
        # 配置模拟对象
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_subprocess.return_value = mock_process
        
        # 模拟文件系统操作
        mock_exists.return_value = True
        mock_getsize.return_value = 100  # 非空文件
        
        # 模拟文件打开
        mock_file = MagicMock()
        mock_file.read.return_value = b'mock mp3 data'
        mock_open.return_value.__enter__.return_value = mock_file
        
        # 模拟AudioSegment
        mock_segment = MagicMock()
        mock_audiosegment.from_file.return_value = mock_segment
        
        # 创建TTS请求
        request_data = TTSRequest(text=mock_tts_text)
        
        response = client.post(
            "/api/v1/audio/tts",
            json=request_data.dict(),
            headers={"Authorization": f"Bearer {test_token}"}
        )
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "audio/mp3"


@patch('app.api.routers.audio.asyncio.to_thread')
@patch('app.api.routers.audio.AudioSegment')
@patch('os.path.exists')
@patch('os.path.getsize')
@patch('os.remove')
@patch('builtins.open', new_callable=MagicMock)
async def test_text_to_speech_windows(mock_open, mock_remove, mock_getsize, mock_exists, mock_audiosegment, mock_tothread, client: TestClient, test_token: str, mock_tts_text):
    """测试Windows下的文字转语音接口"""
    # 模拟Windows系统
    with patch('platform.system', return_value='Windows'):
        # 配置模拟对象
        mock_tothread.return_value = None
        
        # 模拟文件系统操作
        mock_exists.return_value = True
        mock_getsize.return_value = 100  # 非空文件
        
        # 模拟文件打开
        mock_file = MagicMock()
        mock_file.read.return_value = b'mock wav data'
        mock_open.return_value.__enter__.return_value = mock_file
        
        # 模拟AudioSegment
        mock_segment = MagicMock()
        mock_audiosegment.from_file.return_value = mock_segment
        
        # 创建TTS请求
        request_data = TTSRequest(text=mock_tts_text)
        
        response = client.post(
            "/api/v1/audio/tts",
            json=request_data.dict(),
            headers={"Authorization": f"Bearer {test_token}"}
        )
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "audio/mp3"


@patch('app.api.routers.audio.subprocess.run')
@patch('app.api.routers.audio.AudioSegment')
@patch('os.remove')
async def test_text_to_speech_empty_text(mock_remove, mock_audiosegment, mock_subprocess, client: TestClient, test_token: str):
    """测试空文本的文字转语音接口"""
    # 模拟macOS系统
    with patch('platform.system', return_value='Darwin'):
        # 创建空TTS请求
        request_data = TTSRequest(text="")
        
        response = client.post(
            "/api/v1/audio/tts",
            json=request_data.dict(),
            headers={"Authorization": f"Bearer {test_token}"}
        )
        
        assert response.status_code == 400


@patch('app.api.routers.audio.subprocess.run')
@patch('os.remove')
async def test_text_to_speech_mac_failure(mock_remove, mock_subprocess, client: TestClient, test_token: str, mock_tts_text):
    """测试macOS下TTS命令执行失败的情况"""
    # 模拟macOS系统
    with patch('platform.system', return_value='Darwin'):
        # 配置模拟对象抛出异常
        mock_process = MagicMock()
        mock_process.returncode = 1
        mock_process.stderr = "Command failed"
        mock_subprocess.return_value = mock_process
        
        # 创建TTS请求
        request_data = TTSRequest(text=mock_tts_text)
        
        response = client.post(
            "/api/v1/audio/tts",
            json=request_data.dict(),
            headers={"Authorization": f"Bearer {test_token}"}
        )
        
        assert response.status_code == 500
