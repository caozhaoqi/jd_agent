import asyncio
import platform
import subprocess
import tempfile
import os
import uuid
import pyttsx3
from pydub import AudioSegment
from pydub.exceptions import CouldntDecodeError
from fastapi import APIRouter, UploadFile, File
from core.error_handler import (
    raise_bad_request,
    raise_internal_error,
    raise_not_found,
)
from fastapi.responses import Response
from loguru import logger
from core.config import settings
from core.models import TTSRequest

router = APIRouter()

# Windows/Linux 引擎初始化
try:
    if platform.system() != "Darwin":
        engine = pyttsx3.init()
except Exception as e:
    logger.error(f"pyttsx3 init failed: {e}")


@router.post("/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    """
    ASR: 语音转文字 (适配 SiliconFlow SenseVoiceSmall)
    支持音频和视频文件输入
    """
    from openai import OpenAI
    from core.config import settings
    from utils.video_utils import extract_audio_from_video_bytes

    # 1. 初始化客户端
    # 确保使用的是支持 Audio 的 API Key (如 SiliconFlow)
    client = OpenAI(
        api_key=settings.AUDIO_API_KEY or settings.OPENAI_API_KEY,
        base_url=settings.AUDIO_API_BASE or settings.OPENAI_API_BASE,
    )

    try:
        # 2. 读取文件二进制内容
        file_content = await file.read()
        filename = file.filename or "media.wav"

        # 3. 检测是否为视频文件
        video_extensions = [".mp4", ".avi", ".mov", ".mkv", ".flv", ".wmv", ".webm"]
        is_video = any(filename.lower().endswith(ext) for ext in video_extensions)

        # 4. 如果是视频文件，先提取音频
        if is_video:
            file_content = extract_audio_from_video_bytes(file_content, filename)
            filename = "extracted_audio.wav"

        # 5. 构造 OpenAI SDK 认可的文件元组 (关键修复!)
        # 格式: (文件名, 二进制数据, MIME类型)
        file_tuple = (filename, file_content, "audio/wav")

        # 6. 调用 API
        transcript = client.audio.transcriptions.create(
            model=settings.ASR_MODEL,  # 确保 .env 是 FunAudioLLM/SenseVoiceSmall
            file=file_tuple,  # 传入构造好的元组
            temperature=0.0,
        )
        return {"text": transcript.text}

    except Exception as e:
        logger.debug(f"❌ ASR Error: {e}")
        return {"text": "", "error": str(e)}


@router.post("/tts")
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
        raise_bad_request(message="文本为空")

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
                ["say", "-o", output_path, text], capture_output=True, text=True
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
            # 注意：pyttsx3 是同步阻塞的，使用 asyncio.to_thread 避免阻塞主线程

            def generate_audio_sync():
                # 同步代码块，将在单独的线程中运行
                engine.save_to_file(text, output_path)
                engine.runAndWait()

            # 在单独的线程中运行阻塞的pyttsx3调用
            await asyncio.to_thread(generate_audio_sync)

        # ============================
        # 3. 读取并清理
        # ============================
        if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
            raise Exception("音频文件生成失败")

        try:
            # 将生成的音频转换为MP3格式
            audio_segment = AudioSegment.from_file(output_path)

            # 创建临时MP3文件
            mp3_output_path = os.path.join(temp_dir, f"tts_{unique_id}.mp3")

            # 导出为MP3格式，设置比特率为128k
            audio_segment.export(mp3_output_path, format="mp3", bitrate="128k")

            # 读取MP3文件数据
            with open(mp3_output_path, "rb") as f:
                audio_data = f.read()

            # 更新MIME类型为MP3
            mime_type = "audio/mp3"

            # 删除临时文件
            if os.path.exists(output_path):
                os.remove(output_path)
            if os.path.exists(mp3_output_path):
                os.remove(mp3_output_path)

        except CouldntDecodeError:
            # 如果转码失败，回退到原始格式
            logger.warning("音频转码失败，回退到原始格式")
            if os.path.exists(output_path):
                with open(output_path, "rb") as f:
                    audio_data = f.read()
                os.remove(output_path)
        except Exception as e:
            # 其他转码错误也回退到原始格式
            logger.warning(f"音频转码出现未知错误 {e}，回退到原始格式")
            if os.path.exists(output_path):
                with open(output_path, "rb") as f:
                    audio_data = f.read()
                os.remove(output_path)

        return Response(content=audio_data, media_type=mime_type)

    except Exception as e:
        logger.debug(f"❌ [TTS Error] OS: {system_os} | Error: {e}")
        # 尝试清理残余文件
        if "output_path" in locals() and os.path.exists(output_path):
            os.remove(output_path)
        raise_internal_error(message="TTS生成失败", exc=e)
