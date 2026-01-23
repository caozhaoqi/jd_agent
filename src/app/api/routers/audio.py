import asyncio
import platform
import subprocess
import tempfile
import os
import uuid
import pyttsx3
from pydub import AudioSegment
from pydub.exceptions import CouldntDecodeError
from fastapi import APIRouter, UploadFile, File, WebSocket
from core.error_handler import (
    raise_bad_request,
    raise_internal_error,
    raise_not_found,
)
from fastapi.responses import Response
from loguru import logger
from core.config import settings
from core.models import TTSRequest
import queue

# 尝试导入可选依赖
try:
    import sounddevice as sd
    import numpy as np
    SOUNDDEVICE_AVAILABLE = True
except ImportError:
    logger.warning("sounddevice not available, using basic audio processing")
    SOUNDDEVICE_AVAILABLE = False

router = APIRouter()

# Windows/Linux 引擎初始化
try:
    if platform.system() != "Darwin":
        engine = pyttsx3.init()
except Exception as e:
    logger.error(f"pyttsx3 init failed: {e}")

# 音频队列管理
class AudioQueueManager:
    def __init__(self):
        self.queue = queue.Queue()
        self.is_playing = False
        self.current_task = None
        self.lock = asyncio.Lock()
    
    async def add_to_queue(self, audio_data, mime_type):
        """添加音频到队列"""
        self.queue.put((audio_data, mime_type))
        if not self.is_playing:
            await self.process_queue()
    
    async def process_queue(self):
        """处理音频队列"""
        async with self.lock:
            if self.is_playing or self.queue.empty():
                return
            
            self.is_playing = True
            try:
                while not self.queue.empty():
                    audio_data, mime_type = self.queue.get()
                    # 播放音频
                    await self.play_audio(audio_data, mime_type)
                    self.queue.task_done()
            finally:
                self.is_playing = False
    
    async def play_audio(self, audio_data, mime_type):
        """播放音频"""
        # 这里可以添加音频播放逻辑
        # 目前使用临时文件的方式，后续可以优化为内存播放
        pass
    
    def clear_queue(self):
        """清空队列"""
        while not self.queue.empty():
            self.queue.get()
            self.queue.task_done()

# 创建全局音频队列管理器
audio_queue = AudioQueueManager()

# 音频活跃度检测
class VADDetector:
    def __init__(self):
        self.silence_threshold = 0.01
        self.speech_frames = 0
        self.speech_threshold = 10
    
    def detect(self, audio_data):
        """检测音频活跃度"""
        if SOUNDDEVICE_AVAILABLE and 'np' in globals():
            try:
                # 将音频数据转换为numpy数组
                audio_array = np.frombuffer(audio_data, dtype=np.int16)
                # 计算音量
                volume = np.sqrt(np.mean(audio_array ** 2))
                
                if volume > self.silence_threshold:
                    self.speech_frames += 1
                else:
                    self.speech_frames = max(0, self.speech_frames - 1)
                
                return self.speech_frames > self.speech_threshold
            except Exception as e:
                logger.warning(f"VAD detection failed: {e}")
                return False
        else:
            # 基本实现：基于音频长度和能量
            # 简单判断：音频长度大于一定阈值认为是语音
            return len(audio_data) > 10000

# 创建全局VAD检测器
vad_detector = VADDetector()


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

        # 5. 音频活跃度检测
        is_speech = vad_detector.detect(file_content)

        # 6. 构造 OpenAI SDK 认可的文件元组 (关键修复!)
        # 格式: (文件名, 二进制数据, MIME类型)
        file_tuple = (filename, file_content, "audio/wav")

        # 7. 调用 API
        transcript = client.audio.transcriptions.create(
            model=settings.ASR_MODEL,  # 确保 .env 是 FunAudioLLM/SenseVoiceSmall
            file=file_tuple,  # 传入构造好的元组
            temperature=0.0,
        )
        
        # 8. 如果检测到说话，清空音频队列（打断功能）
        if is_speech:
            audio_queue.clear_queue()
            logger.info("Audio queue cleared due to speech detection")
        
        return {"text": transcript.text, "is_speech": is_speech}

    except Exception as e:
        logger.debug(f"❌ ASR Error: {e}")
        return {"text": "", "error": str(e), "is_speech": False}


@router.post("/transcribe/stream")
async def transcribe_audio_stream(file: UploadFile = File(...)):
    """
    低延迟语音转文字
    适用于实时对话场景
    """
    from openai import OpenAI
    from core.config import settings

    # 初始化客户端
    client = OpenAI(
        api_key=settings.AUDIO_API_KEY or settings.OPENAI_API_KEY,
        base_url=settings.AUDIO_API_BASE or settings.OPENAI_API_BASE,
    )

    try:
        # 读取文件内容
        file_content = await file.read()
        filename = file.filename or "stream.wav"

        # 构造文件元组
        file_tuple = (filename, file_content, "audio/wav")

        # 调用 API 进行转录
        transcript = client.audio.transcriptions.create(
            model=settings.ASR_MODEL,
            file=file_tuple,
            temperature=0.0,
        )
        
        # 检测活跃度并打断
        is_speech = vad_detector.detect(file_content)
        if is_speech:
            audio_queue.clear_queue()
        
        return {"text": transcript.text, "is_speech": is_speech, "latency": "low"}

    except Exception as e:
        logger.debug(f"❌ Stream ASR Error: {e}")
        return {"text": "", "error": str(e), "is_speech": False}


@router.post("/tts")
async def text_to_speech(request: TTSRequest):
    """
    跨平台 TTS 接口 (完全离线，零延迟)
    - macOS: 调用 'say' 命令 -> .m4a
    - Windows/Linux: 调用 pyttsx3 -> .wav
    """
    text = request.text
    if not text or not text.strip():
        raise_bad_request("文本为空")

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


@router.post("/tts/queue")
async def text_to_speech_queue(request: TTSRequest):
    """
    带队列的 TTS 接口
    支持音频队列管理和打断功能
    """
    text = request.text
    if not text or not text.strip():
        raise_bad_request("文本为空")

    # 获取当前操作系统名称
    system_os = platform.system()
    unique_id = uuid.uuid4()
    temp_dir = tempfile.gettempdir()

    try:
        audio_data = None
        mime_type = ""
        output_path = ""

        # 生成音频
        if system_os == "Darwin":
            output_path = os.path.join(temp_dir, f"tts_queue_{unique_id}.m4a")
            mime_type = "audio/mp4"

            process = subprocess.run(
                ["say", "-o", output_path, text], capture_output=True, text=True
            )
            if process.returncode != 0:
                raise Exception(f"Mac TTS failed: {process.stderr}")

        else:
            output_path = os.path.join(temp_dir, f"tts_queue_{unique_id}.wav")
            mime_type = "audio/wav"

            def generate_audio_sync():
                engine.save_to_file(text, output_path)
                engine.runAndWait()

            await asyncio.to_thread(generate_audio_sync)

        # 读取音频数据
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            with open(output_path, "rb") as f:
                audio_data = f.read()
            os.remove(output_path)
        else:
            raise Exception("音频文件生成失败")

        # 添加到队列
        await audio_queue.add_to_queue(audio_data, mime_type)

        return {"msg": "音频已添加到队列", "queue_length": audio_queue.queue.qsize()}

    except Exception as e:
        logger.debug(f"❌ [TTS Queue Error] OS: {system_os} | Error: {e}")
        if "output_path" in locals() and os.path.exists(output_path):
            os.remove(output_path)
        raise_internal_error(message="TTS队列添加失败", exc=e)


@router.post("/tts/interrupt")
async def interrupt_tts():
    """
    打断当前 TTS 播放
    """
    try:
        audio_queue.clear_queue()
        return {"msg": "TTS播放已打断", "queue_length": audio_queue.queue.qsize()}
    except Exception as e:
        logger.error(f"打断TTS失败: {e}")
        raise_internal_error(message="打断TTS失败", exc=e)
