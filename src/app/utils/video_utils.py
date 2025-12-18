import os
import tempfile
import logging
from pathlib import Path

import ffmpeg
from pydub import AudioSegment

logger = logging.getLogger(__name__)


def add_subtitle_to_video(video_path: str, subtitle_path: str, output_path: str = None) -> str:
    """
    向视频文件添加字幕
    :param video_path: 视频文件路径
    :param subtitle_path: 字幕文件路径 (支持SRT、ASS等格式)
    :param output_path: 输出视频文件路径，如果为None则自动生成
    :return: 处理后的视频文件路径
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"视频文件不存在: {video_path}")
    
    if not os.path.exists(subtitle_path):
        raise FileNotFoundError(f"字幕文件不存在: {subtitle_path}")
    
    # 验证字幕文件格式
    subtitle_ext = Path(subtitle_path).suffix.lower()
    if subtitle_ext not in ['.srt', '.ass', '.ssa', '.sub']:
        raise ValueError(f"不支持的字幕格式: {subtitle_ext}，仅支持SRT、ASS、SSA、SUB格式")
    
    # 生成输出路径
    if output_path is None:
        temp_dir = tempfile.gettempdir()
        video_basename = os.path.basename(video_path)
        output_path = os.path.join(temp_dir, f"subtitled_{video_basename}")
    
    try:
            logger.info(f"正在向视频添加字幕: {video_path}")
            logger.info(f"使用字幕文件: {subtitle_path}")
            
            # 根据字幕格式选择不同的ffmpeg命令
            if subtitle_ext == '.ass':
                # ASS字幕需要特殊处理
                (ffmpeg
                    .input(video_path)
                    .output(output_path,
                           vf=f"ass={subtitle_path}",
                           crf=23,
                           preset="medium")
                    .overwrite_output()
                    .run(capture_stdout=True, capture_stderr=True)
                )
            else:
                # SRT等其他格式字幕
                (ffmpeg
                    .input(video_path)
                    .output(output_path,
                           vf=f"subtitles={subtitle_path}",
                           crf=23,
                           preset="medium")
                    .overwrite_output()
                    .run(capture_stdout=True, capture_stderr=True)
                )
            
            logger.info(f"字幕添加完成: {output_path}")
            return output_path
        
    except ffmpeg.Error as e:
        logger.error(f"ffmpeg 添加字幕错误: {e.stderr.decode()}")
        raise RuntimeError(f"向视频添加字幕失败: {e.stderr.decode()}")
    except Exception as e:
        logger.error(f"添加字幕过程中发生错误: {e}")
        raise


def extract_audio_from_video(video_path: str) -> str:
    """
    从视频文件中提取音频
    :param video_path: 视频文件路径
    :return: 提取后的音频文件路径 (WAV格式)
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"视频文件不存在: {video_path}")

    # 创建临时音频文件路径
    temp_dir = tempfile.gettempdir()
    temp_audio_path = os.path.join(
        temp_dir, f"extracted_audio_{os.path.basename(video_path)}.wav"
    )

    try:
        # 使用 ffmpeg-python 进行视频转音频
        logger.info(f"正在从视频中提取音频: {video_path}")

        (
            ffmpeg.input(video_path)
            .output(temp_audio_path, format="wav", acodec="pcm_s16le", ac=1, ar="16000")
            .overwrite_output()
            .run(capture_stdout=True, capture_stderr=True)
        )

        logger.info(f"音频提取完成: {temp_audio_path}")
        return temp_audio_path

    except ffmpeg.Error as e:
        logger.error(f"ffmpeg 转码错误: {e.stderr.decode()}")
        raise RuntimeError(f"视频转音频失败: {e.stderr.decode()}")
    except Exception as e:
        logger.error(f"视频转音频过程中发生错误: {e}")
        raise


def extract_audio_from_video_bytes(
    video_bytes: bytes, video_filename: str = "video.mp4"
) -> bytes:
    """
    从视频字节数据中提取音频
    :param video_bytes: 视频文件的字节数据
    :param video_filename: 视频文件名（用于推断格式）
    :return: 提取后的音频字节数据 (WAV格式)
    """
    # 创建临时视频文件
    temp_dir = tempfile.gettempdir()
    temp_video_path = os.path.join(temp_dir, video_filename)

    try:
        # 保存视频字节到临时文件
        with open(temp_video_path, "wb") as f:
            f.write(video_bytes)

        # 提取音频
        temp_audio_path = extract_audio_from_video(temp_video_path)

        # 读取音频字节
        with open(temp_audio_path, "rb") as f:
            audio_bytes = f.read()

        return audio_bytes

    finally:
        # 清理临时文件
        if os.path.exists(temp_video_path):
            os.remove(temp_video_path)
        if "temp_audio_path" in locals() and os.path.exists(temp_audio_path):
            os.remove(temp_audio_path)


def list_video_files(directory: str) -> list[str]:
    """
    列出目录中的所有视频文件
    :param directory: 目录路径
    :return: 视频文件路径列表
    """
    video_extensions = [".mp4", ".avi", ".mov", ".mkv", ".flv", ".wmv", ".webm"]
    video_files = []

    for root, dirs, files in os.walk(directory):
        for file in files:
            file_path = os.path.join(root, file)
            if Path(file_path).suffix.lower() in video_extensions:
                video_files.append(file_path)

    return video_files


def convert_audio_to_wav(audio_path: str) -> str:
    """
    转换音频文件为WAV格式
    :param audio_path: 原始音频文件路径
    :return: 转换后的WAV文件路径
    """
    temp_dir = tempfile.gettempdir()
    wav_path = os.path.join(temp_dir, f"converted_{os.path.basename(audio_path)}.wav")

    try:
        audio = AudioSegment.from_file(audio_path)
        audio = audio.set_channels(1).set_frame_rate(16000)
        audio.export(wav_path, format="wav")
        return wav_path
    except Exception as e:
        logger.error(f"音频转WAV失败: {e}")
        raise
