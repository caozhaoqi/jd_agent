import platform
import subprocess
import tempfile
import os
import uuid
import pyttsx3
from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import Response
from loguru import logger
from app.core.config import settings
from app.core.models import TTSRequest

router = APIRouter()

# Windows/Linux 引擎初始化
try:
    if platform.system() != "Darwin":
        engine = pyttsx3.init()
except Exception as e:
    logger.error(f"pyttsx3 init failed: {e}")


@router.post("/audio/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    """
    ASR: 语音转文字 (适配 SiliconFlow SenseVoiceSmall)
    """
    from openai import OpenAI
    from app.core.config import settings

    # 1. 初始化客户端
    # 确保使用的是支持 Audio 的 API Key (如 SiliconFlow)
    client = OpenAI(
        api_key=settings.AUDIO_API_KEY or settings.OPENAI_API_KEY,
        base_url=settings.AUDIO_API_BASE or settings.OPENAI_API_BASE
    )

    try:
        # 2. 读取文件二进制内容
        file_content = await file.read()

        # 3. 构造 OpenAI SDK 认可的文件元组 (关键修复!)
        # 格式: (文件名, 二进制数据, MIME类型)
        # 如果 file.filename 为空，强制给一个 "audio.wav"
        filename = file.filename or "audio.wav"

        # 强制指定 MIME 类型，SiliconFlow 对此很敏感
        file_tuple = (filename, file_content, "audio/wav")

        # 4. 调用 API
        transcript = client.audio.transcriptions.create(
            model=settings.ASR_MODEL,  # 确保 .env 是 FunAudioLLM/SenseVoiceSmall
            file=file_tuple,  # 传入构造好的元组
            temperature=0.0
        )
        return {"text": transcript.text}

    except Exception as e:
        logger.debug(f"❌ ASR Error: {e}")
        return {"text": "", "error": str(e)}


@router.post("/audio/tts")
async def text_to_speech(request: TTSRequest):
    """
    跨平台 TTS 接口 (完全离线，零延迟)
    - macOS: 调用 'say' 命令 -> .m4a
    - Windows/Linux: 调用 pyttsx3 -> .wav
    """
    text = request.text
    """
    跨平台 TTS 接口 (完全离线，零延迟)
    - macOS: 调用 'say' 命令 -> .m4a
    - Windows/Linux: 调用 pyttsx3 -> .wav
    """
    if not text or not text.strip():
        raise HTTPException(status_code=400, detail="文本为空")

    # 获取当前操作系统名称 ('Darwin', 'Windows', 'Linux')
    system_os = platform.system()

    # 定义临时文件路径
    unique_id = uuid.uuid4()
    temp_dir = tempfile.gettempdir()

    try:
        audio_data = None
        mime_type = ""
        output_path = ""

        # ============================
        # 🍎 方案 A: macOS (Darwin)
        # ============================
        if system_os == "Darwin":
            output_path = os.path.join(temp_dir, f"tts_{unique_id}.m4a")
            mime_type = "audio/mp4"  # m4a 属于 mp4 容器

            # 使用 macOS 原生 say 命令
            process = subprocess.run(
                ["say", "-o", output_path, text],
                capture_output=True,
                text=True
            )
            if process.returncode != 0:
                raise Exception(f"Mac TTS failed: {process.stderr}")

        # ============================
        # 🪟/🐧 方案 B: Windows / Linux
        # ============================
        else:
            output_path = os.path.join(temp_dir, f"tts_{unique_id}.wav")
            mime_type = "audio/wav"

            # 使用 pyttsx3 (SAPI5 / eSpeak)
            # 注意：pyttsx3 是同步阻塞的，高并发建议放入线程池，单人使用无所谓
            engine.save_to_file(text, output_path)
            engine.runAndWait()

        # ============================
        # 3. 读取并清理
        # ============================
        if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
            raise Exception("音频文件生成失败")

        with open(output_path, "rb") as f:
            audio_data = f.read()

        # 删除临时文件
        os.remove(output_path)

        return Response(content=audio_data, media_type=mime_type)

    except Exception as e:
        logger.debug(f"❌ [TTS Error] OS: {system_os} | Error: {e}")
        # 尝试清理残余文件
        if 'output_path' in locals() and os.path.exists(output_path):
            os.remove(output_path)
        raise HTTPException(status_code=500, detail=f"TTS生成失败: {str(e)}")
